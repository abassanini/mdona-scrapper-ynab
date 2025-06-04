import argparse
import os

from loguru import logger
from ynab.api.transactions_api import TransactionsApi
from ynab.api_client import ApiClient
from ynab.configuration import Configuration
from ynab.exceptions import ApiException
from ynab.models.new_transaction import NewTransaction
from ynab.models.post_transactions_wrapper import PostTransactionsWrapper
from ynab.models.save_sub_transaction import SaveSubTransaction

from invoice_scrapper import InvoiceScrapper
from utils import setup_logging

parser = argparse.ArgumentParser(
    description="Extract text from PDF or image bills and send it to YNAB."
)

parser.add_argument(
    "-f",
    "--invoice_file",
    type=str,
    help="Path to the invoice file to use",
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
    "-d",
    "--debug",
    help="Debug mode: info, debug, trace.  Default is 'info'.",
    choices=["info", "debug", "trace"],
    default="info",
    type=str.lower,
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
setup_logging(args.debug)

invoice = InvoiceScrapper.get_invoice(invoice_file)

try:
    budget_id = os.environ["BUDGET_ID"]
    account_id = os.environ["ACCOUNT_ID"]
    category_id = os.environ["CATEGORY_ID"]
    sub_category_id = os.environ["SUB_CATEGORY_ID"]
    if invoice.supermarket == "Consum":
        payee_id = os.environ["PAYEE_ID_CONSUM"]
    elif invoice.supermarket == "Mercadona":
        payee_id = os.environ["PAYEE_ID_MERCADONA"]
except KeyError as e:
    raise SystemExit(logger.error(f"Please set environment variables: {e}"))

producs = invoice.products
invoice_number = invoice.invoice_number
payment_date = invoice.payment_date
total = invoice.total

configuration = Configuration(access_token=ynab_access_token)
data = PostTransactionsWrapper(
    transaction=NewTransaction(
        account_id=account_id,
        date=invoice.payment_date.date(),
        amount=int(-invoice.total * 1000),
        payee_id=payee_id,
        category_id=category_id,
        memo=f"YNAB API: Factura={invoice.invoice_number}",
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


[logger.debug(i) for i in invoice.products]
sum_total = round(sum([i.total_price for i in invoice.products]), 2)

if total != sum_total:
    raise SystemExit(logger.error(f"ERROR: Total Missmatch: {total} != {sum_total}"))

logger.info(
    f"Invoice number: {invoice.invoice_number}, Payment date: {invoice.payment_date}"
)
logger.success(f"{total=}, {sum_total=}")


logger.debug(
    (
        "YNAB transation data:",
        f"{data.transaction.var_date=}, {data.transaction.amount=}, {data.transaction.payee_id=}",
        f"{data.transaction.category_id=}, {data.transaction.memo=}",
    )
)
[logger.debug(i) for i in data.transaction.subtransactions]

if args.dry_run:
    logger.warning(
        (
            f"Dry run: not sending data to YNAB. "
            f"- Date: {data.transaction.var_date} "
            f"- Subtransaction items: {len(data.transaction.subtransactions)} "
            f"- Total: {total}"
        ),
    )
    raise SystemExit(logger.info("Exiting due to dry run mode."))

# Create a YNAB new transaction
with ApiClient(configuration) as api_client:
    trx_api = TransactionsApi(api_client)
    try:
        api_response = trx_api.create_transaction(budget_id, data)
        logger.success(f"YNAB API Response: {api_response.data.transaction_ids}")
    except ApiException as e:
        logger.error(
            "Exception when calling TransactionsApi->create_transaction: %s\n" % e
        )
