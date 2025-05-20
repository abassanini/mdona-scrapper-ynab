import argparse
import os
from pprint import pprint

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
args = parser.parse_args()
invoice_file: str = args.invoice_file
ynab_access_token: str = args.token
supermarket: str = args.supermarket

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
    print(f"Please set environment variables: {e}")
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

pprint(invoice.products)
# pprint(data)
exit(1)

with ApiClient(configuration) as api_client:
    trx_api = TransactionsApi(api_client)
    try:
        api_response = trx_api.create_transaction(budget_id, data)
        pprint(api_response.data.transaction_ids)
    except ApiException as e:
        print("Exception when calling TransactionsApi->create_transaction: %s\n" % e)
