import re
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import List

import pandas as pd
from pypdf import PdfReader
from pypdf.errors import PyPdfError


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
    total: float = 0.0

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
                    "invoice_total": self.total,
                }
                for product in self.products
            )
        )


class MercadonaScrapper:
    ORDER_NUMBER_RE = re.compile(r"(?:Pedido Nº|OP):\s+([0-9]+)")
    INVOICE_NUMBER_RE = re.compile(r"Factura \w+:\s+([0-9\- ]+)\n", re.IGNORECASE)
    TOTAL_INVOICE_RE = re.compile(r"TOTAL.*€.*?(\d+[.,]\d+)", re.IGNORECASE)
    PAYMENT_DATE_RE = re.compile(
        r"(?:Cobrado el )?([0-9]+)/([0-9]+)/([0-9]+)(?: a las)?\s+([0-9]+):([0-9]+)"
    )

    SPECIAL_PRODUCT_RE = re.compile(
        r"^[1-9]\d*\s+(.+)\n(\d+[.,]\d+)\s+(.+)(\d+[.,]\d+)$", re.MULTILINE
    )

    NORMAL_PRODUCT_RE = re.compile(r"^([1-9]\d*)\s+(.+)\s(\d+[.,]\d+)$", re.MULTILINE)
    UNIT_PRODUCT_PRICE_RE = re.compile(r"(.*)\s(\d+[,.]\d{2})$")

    @classmethod
    def _get_special_products(cls, text):
        return [
            Product(
                name=name.strip(),
                unit=f"{quantity} {unit}".strip(),
                quantity=(q := float(quantity.replace(",", "."))),
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=round(
                    t / q if q != 0 else 0,
                    2,
                ),
            )
            for (
                name,
                quantity,
                unit,
                total_price,
            ) in cls.SPECIAL_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_unit_price(cls, text) -> str:
        unit: str = (
            match.group(1) if (match := cls.UNIT_PRODUCT_PRICE_RE.search(text)) else ""
        )

        return unit.replace(",", ".")

    @classmethod
    def _normal_tuple_to_product(cls, tup) -> Product:
        (quantity, name, total_price) = tup

        unit: str = ""
        quantity = int(quantity)
        total_price = float(total_price.replace(",", "."))

        if quantity > 1:
            try:
                (name, unit) = (
                    match.groups()
                    if (match := cls.UNIT_PRODUCT_PRICE_RE.search(name))
                    else None
                )
            except ValueError as e:
                print(f"Probably regex missmatch in {name=}.  Error: {e}")
                exit(1)

        unit_price = total_price / quantity if quantity != 0 else 0
        unit = f"({quantity} x {unit.replace(',', '.').strip()}€)" if unit else unit

        return Product(
            name=name.strip(),
            total_price=total_price,
            unit=unit,
            quantity=quantity,
            unit_price=unit_price,
        )

    @classmethod
    def _get_normal_products(cls, text) -> List[Product]:
        return [
            cls._normal_tuple_to_product(tup)
            for tup in cls.NORMAL_PRODUCT_RE.findall(text)
            if len(tup[0].strip()) > 0
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
        return datetime(year, month, day, hour, minute)

    @classmethod
    def _get_invoice_total(cls, text) -> float:
        return float(cls.TOTAL_INVOICE_RE.search(text).group(1).replace(",", "."))

    @classmethod
    def get_invoice(
        cls, path_or_fp: str | Path | BufferedReader | BytesIO
    ) -> MercadonaInvoice:
        try:
            with PdfReader(path_or_fp) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages])
        except PyPdfError:
            raise SystemExit(f"Error reading PDF file: {path_or_fp}")
        except FileNotFoundError:
            raise SystemExit(f"File not found: {path_or_fp}")

        return MercadonaInvoice(
            products=cls._get_products(text),
            order_number=cls._get_order_number(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
            total=cls._get_invoice_total(text),
        )
