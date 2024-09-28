# Mercadona's invoice scrapper

This package allows you to extract the information from a Mercadona's invoice in PDF format and convert it to a pandas DataFrame.

## Installation

```bash
pip install mdona-scrapper
```

## Usage

```python
from mdona_scrapper import MercadonaScrapper

invoice = MercadonaScrapper.get_invoce('path/to/invoice.pdf')

producs = invoice.products
order_number = invoice.order_number
invoice_number = invoice.invoice_number
payment_date = invoice.payment_date

df = invoice.dataframe
```
