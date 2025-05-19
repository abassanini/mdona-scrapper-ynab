import argparse
import datetime
import os
from pprint import pprint

# from ynab.api.budgets_api import BudgetsApi
from ynab.api.transactions_api import TransactionsApi
from ynab.api_client import ApiClient
from ynab.configuration import Configuration
from ynab.exceptions import ApiException
from ynab.models.new_transaction import NewTransaction
from ynab.models.post_transactions_wrapper import PostTransactionsWrapper
from ynab.models.save_sub_transaction import SaveSubTransaction

parser = argparse.ArgumentParser(description="Insert test transaction in YNAB.")
parser.add_argument("-t", "--token", type=str, help="YNAB Token", required=True)
args = parser.parse_args()
ynab_access_token = args.token

try:
    budget_id = os.environ["BUDGET_ID"]  # Spain
    account_id = os.environ["ACCOUNT_ID"]  # Wise
    category_id = os.environ["CATEGORY_ID"]  # Split
    sub_category_id = os.environ["SUB_CATEGORY_ID"]  # Groceries
    payee_id = os.environ["PAYEE_ID_MERCADONA"]  # Mercadona
except KeyError as e:
    print(f"Please set environment variables: {e}")
    exit(1)

configuration = Configuration(access_token=ynab_access_token)

data = PostTransactionsWrapper(
    transaction=NewTransaction(
        account_id=account_id,
        date=datetime.date.today(),
        amount=10000,
        payee_id=payee_id,
        category_id=category_id,
        memo="Test Memo",
        approved=True,
        subtransactions=[
            SaveSubTransaction(
                amount=8000,
                payee_id=payee_id,
                category_id=sub_category_id,
                memo="Item 01",
            ),
            SaveSubTransaction(
                amount=2000,
                payee_id=payee_id,
                category_id=sub_category_id,
                memo="Item 02",
            ),
        ],
    ),
)

with ApiClient(configuration) as api_client:
    # budgets_api = BudgetsApi(api_client)
    # budgets_response = budgets_api.get_budgets()
    # budgets = budgets_response.data.budgets

    # for budget in budgets:
    #     print(f"{budget.id}: {budget.name}")

    trx_api = TransactionsApi(api_client)
    trx_response = trx_api.get_transactions(
        budget_id=budget_id,
        # since_date=datetime.date(2025, 5, 5)
        since_date=datetime.date.today() - datetime.timedelta(days=3),
    )
    for trx in trx_response.data.transactions:
        print(trx)

    exit(1)
    try:
        # Create a single transaction
        api_response = trx_api.create_transaction(budget_id, data)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling TransactionsApi->create_transaction: %s\n" % e)
