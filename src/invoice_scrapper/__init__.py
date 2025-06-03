from pathlib import Path

from loguru import logger

from models import Invoice
from utils import detect_file_type, read_pdf_file, read_png_file


class InvoiceScrapper:
    @classmethod
    def _read_invoice_file(cls, invoice_file: str) -> str:

        text: str = ""
        if not Path(invoice_file).exists():
            raise SystemExit(logger.error(f"File not found: {invoice_file}"))

        if (file_type := detect_file_type(invoice_file)) == "pdf":
            text = read_pdf_file(invoice_file)
        elif file_type == "png":
            text = read_png_file(invoice_file)
        elif not file_type:
            raise SystemExit(logger.error(f"Unsupported file type: {file_type}"))

        if text == "":
            raise SystemExit(logger.error(f"Error reading file: {invoice_file}"))

        return text

    @classmethod
    def get_invoice(cls, invoice_file: str) -> Invoice:
        text = cls._read_invoice_file(invoice_file)

        if "consum" in (t := text.lower()):
            from consum_scrapper import ConsumScrapper

            cls.supermarket = "Consum"
            return ConsumScrapper.get_invoice(text)
        elif "mercadona" in t:
            from mdona_scrapper import MercadonaScrapper

            cls.supermarket = "Mercadona"
            return MercadonaScrapper.get_invoice(text)
        else:
            raise SystemExit("Unsupported invoice format or supermarket.")
