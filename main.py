import argparse
import logging
import os

from ynab.api.transactions_api import TransactionsApi
from ynab.api_client import ApiClient
from ynab.configuration import Configuration
from ynab.exceptions import ApiException
from ynab.models.new_transaction import NewTransaction
from ynab.models.post_transactions_wrapper import PostTransactionsWrapper
from ynab.models.save_sub_transaction import SaveSubTransaction

from consum_scrapper import ConsumScrapper
from mdona_scrapper import MercadonaScrapper

parser = argparse.ArgumentParser(
    description="Extract text from PDF or image bills and send it to YNAB."
)

parser.add_argument(
    "-f",
    "--invoice_file",
    type=str,
    help="Path to the PDF file to use",
    required=True,
)
parser.add_argument(
    "-t",
    "--token",
    type=str,
    help="YNAB Token: XxX312DasdXxD_PPPk_yy...",
    required=True,
)
parser.add_argument(
    "-s",
    "--supermarket",
    type=str,
    help="Mercadona (m), Consum (c)",
    required=True,
)

parser.add_argument(
    "-d",
    "--debug",
    help="Debug mode: INFO, DEBUG",
    choices=["INFO", "DEBUG"],
)

parser.add_argument(
    "-r",
    "--dry-run",
    action="store_true",
    help="Dry run: do not send data to YNAB",
)

args = parser.parse_args()
invoice_file: str = args.invoice_file
ynab_access_token: str = args.token
supermarket: str = args.supermarket

if args.debug == "DEBUG":
    logging.basicConfig(
        format="%(asctime)s;%(levelname)s: %(message)s", level=logging.DEBUG
    )
    logging.debug("Verbose output.")
elif args.debug == "INFO":
    logging.basicConfig(
        format="%(asctime)s;%(levelname)s: %(message)s", level=logging.INFO
    )
else:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

try:
    budget_id = os.environ["BUDGET_ID"]  # Spain
    account_id = os.environ["ACCOUNT_ID"]  # Wise
    category_id = os.environ["CATEGORY_ID"]  # Split
    sub_category_id = os.environ["SUB_CATEGORY_ID"]  # Groceries
    if supermarket == "mercadona" or supermarket == "m":
        payee_id = os.environ["PAYEE_ID_MERCADONA"]  # Mercadona
    elif supermarket == "consum" or supermarket == "c":
        payee_id = os.environ["PAYEE_ID_CONSUM"]  # Consum
except KeyError as e:
    logging.error(f"Please set environment variables: {e}")
    exit(1)

configuration = Configuration(access_token=ynab_access_token)

if supermarket == "mercadona" or supermarket == "m":
    invoice = MercadonaScrapper.get_invoice(invoice_file)
elif supermarket == "consum" or supermarket == "c":
    invoice = ConsumScrapper.get_invoice(invoice_file)

producs = invoice.products
order_number = invoice.order_number
invoice_number = invoice.invoice_number
payment_date = invoice.payment_date
total = invoice.total

data = PostTransactionsWrapper(
    transaction=NewTransaction(
        account_id=account_id,
        date=invoice.payment_date.date(),
        amount=int(-invoice.total * 1000),
        payee_id=payee_id,
        category_id=category_id,
        memo=f"YNAB API: Factura={invoice.invoice_number} - Orden={invoice.order_number}",
        approved=True,
        subtransactions=[
            SaveSubTransaction(
                amount=int(round(-product.total_price * 1000, 2)),
                category_id=sub_category_id,
                memo=f"{product.name} {product.unit}".capitalize().strip(),
            )
            for product in invoice.products
        ],
    ),
)


[logging.info(i) for i in invoice.products]
logging.info(
    (
        f"{total=}, sum_total=",
        round(sum([i.total_price for i in invoice.products]), 2),
    )
)

logging.debug(
    (
        "YNAB transation data:",
        f"{data.transaction.var_date=}, {data.transaction.amount=}, {data.transaction.payee_id=}",
        f"{data.transaction.category_id=}, {data.transaction.memo=}",
    )
)
[logging.debug(i) for i in data.transaction.subtransactions]

if args.dry_run:
    logging.warning(
        f"Dry run: not sending data to YNAB - Subtransaction items: {len(data.transaction.subtransactions)}"
    )
    exit(0)

# Create a YNAB new transaction
with ApiClient(configuration) as api_client:
    trx_api = TransactionsApi(api_client)
    try:
        api_response = trx_api.create_transaction(budget_id, data)
        print(f"YNAB API Response: {api_response.data.transaction_ids}")
    except ApiException as e:
        logging.error(
            "Exception when calling TransactionsApi->create_transaction: %s\n" % e
        )
