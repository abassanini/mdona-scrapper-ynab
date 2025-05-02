import argparse

from mdona_scrapper import MercadonaScrapper

parser = argparse.ArgumentParser(
    description="Extract text from PDF and send it to YNAB."
)
parser.add_argument("pdf_file", type=str, help="Path to the PDF file to use")
args = parser.parse_args()
pdf_file = args.pdf_file

invoice = MercadonaScrapper.get_invoice(pdf_file)

producs = invoice.products
order_number = invoice.order_number
invoice_number = invoice.invoice_number
payment_date = invoice.payment_date
total = invoice.total

print(f"{order_number=}")
print(f"{invoice_number=}")
print(f"{payment_date=}")
print(f"{len(producs)=} \n{producs=}")
print(f"{total=}")
