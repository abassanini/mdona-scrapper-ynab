import logging
import re
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import List

import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError


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
    TOTAL_INVOICE_RE = re.compile(r"importe a abonar\s+(\d+[.,]\d+)", re.IGNORECASE)
    PAYMENT_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s(\d{2}):(\d{2})")

    UNITARY_PRODUCT_RE = re.compile(
        r"^(-?1)\s+(.+?)\s+(-?\d+[.,]\d+)$",
        re.MULTILINE,
    )
    MULTIPLE_PRODUCT_RE = re.compile(
        r"^(-?\d+)\s+(.+)\s+(-?\d*[.,]\d*)\s+(-?\d+[.,]\d+)$",
        re.MULTILINE,
    )
    FRACTIONAL_PRODUCT_RE = re.compile(
        r"^(-?\d+[.,]\d+)\s+(.+)\s+(-?\d+[.,]\d+)$", re.MULTILINE
    )

    DISCOUNT_RE = re.compile(
        r"^(Descuento.+|Dto Mis Fav.+)\s+(-?\d+[.,]\d+)$",
        re.MULTILINE,
    )

    @classmethod
    def _get_unitary_products(cls, text):
        return [
            Product(
                quantity=int(quantity),
                name=name.strip(),
                unit="",
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=t,
            )
            for (
                quantity,
                name,
                total_price,
            ) in cls.UNITARY_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_multiple_products(cls, text):
        return [
            Product(
                quantity=int(quantity),
                name=name.strip(),
                unit="",
                unit_price=round(float(unit_price.replace(",", ".")), 2),
                total_price=round(float(total_price.replace(",", ".")), 2),
            )
            for (
                quantity,
                name,
                unit_price,
                total_price,
            ) in cls.MULTIPLE_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_fractional_products(cls, text):
        return [
            Product(
                quantity=(q := round(float(quantity.replace(",", ".")), 3)),
                name=name.strip(),
                unit="",
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=round((t / q if q != 0 else 0), 2),
            )
            for (
                quantity,
                name,
                total_price,
            ) in cls.FRACTIONAL_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_discount(cls, text):
        return [
            Product(
                quantity=0,
                name=name.strip(),
                unit="",
                total_price=round(float(total_price.replace(",", ".")), 2),
                unit_price=0,
            )
            for (
                name,
                total_price,
            ) in cls.DISCOUNT_RE.findall(text)
        ]

    @classmethod
    def _get_products(cls, text) -> List[Product]:
        return (
            cls._get_unitary_products(text)
            + cls._get_multiple_products(text)
            + cls._get_fractional_products(text)
            + cls._get_discount(text)
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

        logging.debug(text)

        return ConsumInvoice(
            products=cls._get_products(text),
            order_number=cls._get_order_number(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
            total=cls._get_invoice_total(text),
        )
