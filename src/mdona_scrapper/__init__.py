import re
from datetime import datetime
from typing import List

from loguru import logger

from invoice_scrapper import InvoiceScrapper
from models import Invoice, Product


class MercadonaScrapper(InvoiceScrapper):
    INVOICE_NUMBER_RE = re.compile(
        r"^Factura \w+:\s*([0-9\- ]+)", re.IGNORECASE | re.MULTILINE
    )
    TOTAL_INVOICE_RE = re.compile(
        r"TOTAL.*€.*?(\d+[.,]\d+)$", re.IGNORECASE | re.MULTILINE
    )
    PAYMENT_DATE_RE = re.compile(
        r"(?:Fecha factura simplificada\s*:\s*|^)([0-9]+)/([0-9]+)/([0-9]+)",
        re.MULTILINE,
    )

    SPECIAL_PRODUCT_RE = re.compile(
        r"^[1-9]\d*\s+(.+)\n(\d+[.,]\d+)\s+(.+)(\d+[.,]\d+)$", re.MULTILINE
    )

    NORMAL_PRODUCT_RE = re.compile(r"^([1-9]\d*)\s+(.+)\s(\d+[.,]\d+)$", re.MULTILINE)
    UNIT_PRODUCT_PRICE_RE = re.compile(r"(.*)\s(\d+[,.]\d{2})$")

    UNITARY_INVOICE_PRODUCT_RE = re.compile(
        r"^(.+)\s+1\s+(?:\d+[.,]\d+)\s+(?:\d+[.,]\d+)\s+(?:\d+%)\s+(?:\d+[.,]\d+)\s+(\d+[.,]\d+)$",
        re.MULTILINE,
    )

    MULTIPLE_INVOICE_PRODUCT_RE = re.compile(
        r"^(.+)\s+([2-9]|\d{2,})\s+(?:\d+[.,]\d+)\s+(?:\d+[.,]\d+)\s+(?:\d+%)\s+(?:\d+[.,]\d+)\s+(\d+[.,]\d+)$",
        re.MULTILINE,
    )

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
                raise SystemExit(
                    logger.error(f"Probably regex missmatch in {name=}.  Error: {e}")
                )

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
    def _get_unitary_invoice_products(cls, text) -> List[Product]:
        return [
            Product(
                name=name.strip(),
                quantity=1,
                unit="",
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=t,
            )
            for (
                name,
                total_price,
            ) in cls.UNITARY_INVOICE_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_multiple_invoice_products(cls, text) -> List[Product]:
        return [
            Product(
                name=name.strip(),
                quantity=(q := int(quantity)),
                total_price=(t := round(float(total_price.replace(",", ".")), 2)),
                unit_price=(u := round(t / q, 2) if q != 0 else 0),
                unit=f"({q} x {u}€)",
            )
            for (
                name,
                quantity,
                total_price,
            ) in cls.MULTIPLE_INVOICE_PRODUCT_RE.findall(text)
        ]

    @classmethod
    def _get_invoice_products(cls, text) -> List[Product]:
        return cls._get_unitary_invoice_products(
            text
        ) + cls._get_multiple_invoice_products(text)

    @classmethod
    def _get_products(cls, text) -> List[Product]:
        return (
            cls._get_special_products(text)
            + cls._get_normal_products(text)
            + cls._get_invoice_products(text)
        )

    @classmethod
    def _get_invoice_number(cls, text) -> str:
        if (match := cls.INVOICE_NUMBER_RE.search(text)) is None:
            raise SystemExit(
                logger.error("Regex INVOICE_NUMBER or quality image error.")
            )
        else:
            return match.group(1)

    @classmethod
    def _get_payment_date(cls, text) -> datetime:

        if (match := cls.PAYMENT_DATE_RE.search(text)) is None:
            raise SystemExit(logger.error("Regex PAYMENT_DATE or quality image error."))
        else:
            day, month, year = map(int, match.groups())
            return datetime(year, month, day)

    @classmethod
    def _get_invoice_total(cls, text) -> float:
        if (match := cls.TOTAL_INVOICE_RE.search(text)) is None:
            raise SystemExit(
                logger.error("Regex TOTAL_INVOICE or quality image error.")
            )
        else:
            return float(match.group(1).replace(",", "."))

    @classmethod
    def get_invoice(cls, text: str) -> Invoice:

        return Invoice(
            supermarket=Invoice.supermarket,
            products=cls._get_products(text),
            invoice_number=cls._get_invoice_number(text),
            payment_date=cls._get_payment_date(text),
            total=cls._get_invoice_total(text),
        )
