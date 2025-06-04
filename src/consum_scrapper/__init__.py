import re
from datetime import datetime
from typing import List

from invoice_scrapper import InvoiceScrapper
from models import Invoice, Product


class ConsumScrapper(InvoiceScrapper):
    """Consum invoice scrapper."""

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
        r"^([2-9]|\d{2,})\s+(.+)\s+(-?\d*[.,]\d*)\s+(-?\d+[.,]\d+)$",
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
                name=name.strip(),
                quantity=(q := int(quantity)),
                total_price=round(float(total_price.replace(",", ".")), 2),
                unit_price=(u := round(float(unit_price.replace(",", ".")), 2)),
                unit=f"({q} x {u}€)",
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
                name=name.strip(),
                quantity=(q := round(float(quantity.replace(",", ".")), 3)),
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=(u := round((t / q if q != 0 else 0), 2)),
                unit=f"({q} x {u}€)",
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
    def _get_invoice_number(cls, text) -> str:
        return " - ".join(cls.INVOICE_NUMBER_RE.search(text).groups())

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
    def get_invoice(cls, text: str) -> Invoice:

        return Invoice(
            supermarket=Invoice.supermarket,
            products=cls._get_products(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
            total=cls._get_invoice_total(text),
        )
