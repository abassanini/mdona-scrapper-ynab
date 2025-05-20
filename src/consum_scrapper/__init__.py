import re
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import List

import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError

# from pypdf import PdfReader
# from pypdf.errors import PyPdfError


@dataclass
class Product:
    name: str
    total_price: float
    unit: str
    quantity: float
    unit_price: float


@dataclass
class ConsumInvoice:
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


class ConsumScrapper:
    INVOICE_NUMBER_RE = re.compile(
        r"(C:\d+\s\d+\/\d+)\s\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}\s(\d+)", re.IGNORECASE
    )
    TOTAL_INVOICE_RE = re.compile(r"Total factura:\s(\d+[.,]\d+)", re.IGNORECASE)
    PAYMENT_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s(\d{2}):(\d{2})")

    UNITARY_PRODUCT_RE = re.compile(
        r"^1\s([a-zA-Z0-9ñÑ\-%.\/\s]+)\s(\d+[.,]\d+)", re.MULTILINE
    )
    MULTIPLE_PRODUCT_RE = re.compile(
        r"^(\d+)\s([a-zA-Z0-9ñÑ\-.\/\s]+)\s(\d*[.,]\d+)\s(\d+[.,]\d+)", re.MULTILINE
    )
    FRACTIONAL_PRODUCT_RE = re.compile(
        r"^0[.,]\d+\s[a-zA-Z0-9ñÑ\-%.\/\s]+\s(\d+[.,]\d+)", re.MULTILINE
    )
    NEGATIVE_PRODUCT_RE = re.compile(
        r"^-\d+\s[a-zA-Z0-9ñÑ\-%.\/\s]+\s(-\d*[.,]\d*)", re.MULTILINE
    )

    @classmethod
    def _get_unitary_products(cls, text):
        return [
            Product(
                name=name.strip(),
                unit="",
                quantity=1,
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=t,
            )
            for (
                name,
                total_price,
            ) in cls.UNITARY_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_multiple_products(cls, text):
        return [
            Product(
                name=name.strip(),
                unit="",
                quantity=1,
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=t,
            )
            for (
                name,
                total_price,
            ) in cls.MULTIPLE_PRODUCT_RE.findall(text)
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
        return (
            cls._get_unitary_products(text)
            # + cls._get_normal_products(text)
            # + cls._get_negative_products(text)
            # + cls._get_fractional_products(text)
        )

    @classmethod
    def _get_order_number(cls, text) -> int:
        return cls.INVOICE_NUMBER_RE.search(text).group(1)

    @classmethod
    def _get_invoice_number(cls, text) -> str:
        return cls.INVOICE_NUMBER_RE.search(text).group(2)

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
    ) -> ConsumInvoice:
        try:
            # with PdfReader(path_or_fp) as pdf:
            #     text = "\n".join([page.extract_text() for page in pdf.pages])
            image = Image.open(path_or_fp)
            image = image.convert("L")
            image = image.filter(ImageFilter.MedianFilter())

            # enhancer = ImageEnhance.Contrast(image)
            # image = enhancer.enhance(2)
            # image = image.convert("1")

            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(8.0)
            image = image.convert("L").point(lambda x: 255 if x > 150 else 0, mode="1")

            text = pytesseract.image_to_string(image, lang="spa")
        except UnidentifiedImageError:
            raise SystemExit(f"Error reading invoice file: {path_or_fp}")
        except FileNotFoundError:
            raise SystemExit(f"File not found: {path_or_fp}")

        print(text)

        return ConsumInvoice(
            products=cls._get_products(text),
            order_number=cls._get_order_number(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
            total=cls._get_invoice_total(text),
        )
