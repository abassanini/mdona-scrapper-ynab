from mdona_scrapper import MercadonaScrapper

invoice = MercadonaScrapper.get_invoice("mercadona_04.pdf")

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
