from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd


@dataclass
class Product:
    name: str
    total_price: float
    unit: str
    quantity: float
    unit_price: float


@dataclass
class Invoice:
    """Invoice Class."""

    supermarket: str
    products: List[Product]
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
