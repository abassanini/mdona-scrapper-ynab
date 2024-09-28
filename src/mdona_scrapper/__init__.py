import re
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import List

import pandas as pd
from pypdf import PdfReader


@dataclass
class Product:
    name: str
    total_price: float
    unit: str
    quantity: float
    unit_price: float


@dataclass
class MercadonaInvoice:
    products: List[Product]
    order_number: int
    invoice_number: str
    payment_date: datetime

    @property
    def dataframe(self):
        return pd.DataFrame(
            (
                {
                    "name": product.name,
                    "total_price": product.total_price,
                    "unit": product.unit,
                    "quantity": product.quantity,
                    "unit_price": product.unit_price,
                    "order_number": self.order_number,
                    "invoice_number": self.invoice_number,
                    "payment_date": self.payment_date,
                }
                for product in self.products
            )
        )


class MercadonaScrapper:
    ORDER_NUMBER_RE = re.compile(r"Pedido Nº ([0-9]+)")
    INVOICE_NUMBER_RE = re.compile(r"Factura \w+ ([0-9\- ]+)\n")
    PAYMENT_DATE_RE = re.compile(
        r"Cobrado el ([0-9]+)/([0-9]+)/([0-9]+) a las? ([0-9]+):([0-9]+)"
    )

    SPECIAL_PRODUCT_RE = re.compile(
        r"([\w\d \-\&\+%]+)\n([0-9]+) ([0-9]+,[0-9]+) ?€\n- Peso: ([0-9]+,[0-9]+) ([a-zA-Z0-9.]+) Precio ([a-zA-Z0-9.]+): ([0-9]+,[0-9]+) €"
    )

    NORMAL_PRODUCT_RE = re.compile(r"([\w\d \-\&\+%]+) ([0-9]+) ([0-9]+,[0-9]+) ?€\n")

    NORMAL_PARTIAL_PRODUCT_RE = re.compile(r"([\w\d \-\&\+%]+) ([0-9]+) de")

    @classmethod
    def _get_special_products(cls, text):
        return [
            Product(
                name=name,
                total_price=float(total_price.replace(",", ".")),
                unit=unit,
                quantity=float(quantity.replace(",", ".")),
                unit_price=float(unit_price.replace(",", ".")),
            )
            for (
                name,
                _,
                total_price,
                quantity,
                unit,
                _,
                unit_price,
            ) in cls.SPECIAL_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _normal_tuple_to_product(cls, tup) -> Product:
        (name, quantity, total_price) = tup
        if name.endswith(" de"):
            (name, quantity) = cls.NORMAL_PARTIAL_PRODUCT_RE.search(name).groups()

        quantity = float(quantity.replace(",", "."))
        total_price = float(total_price.replace(",", "."))

        unit_price = total_price / quantity if quantity != 0 else 0

        return Product(
            name=name,
            total_price=total_price,
            unit="",
            quantity=quantity,
            unit_price=unit_price,
        )

    @classmethod
    def _get_normal_products(cls, text) -> List[Product]:
        return [
            cls._normal_tuple_to_product(tup)
            for tup in cls.NORMAL_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_products(cls, text) -> List[Product]:
        return cls._get_special_products(text) + cls._get_normal_products(text)

    @classmethod
    def _get_order_number(cls, text) -> int:
        return int(cls.ORDER_NUMBER_RE.search(text).group(1))

    @classmethod
    def _get_invoice_number(cls, text) -> str:
        return cls.INVOICE_NUMBER_RE.search(text).group(1)

    @classmethod
    def _get_payment_date(cls, text) -> datetime:
        day, month, year, hour, minute = map(
            int, cls.PAYMENT_DATE_RE.search(text).groups()
        )
        return datetime(year + 2000, month, day, hour, minute)

    @classmethod
    def get_invoice(
        cls, path_or_fp: str | Path | BufferedReader | BytesIO
    ) -> MercadonaInvoice:
        with PdfReader(path_or_fp) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages])

        return MercadonaInvoice(
            products=cls._get_products(text),
            order_number=cls._get_order_number(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
        )
