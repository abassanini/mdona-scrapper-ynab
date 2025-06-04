from models import Invoice
from utils import read_invoice_file


class InvoiceScrapper:
    @classmethod
    def get_invoice(cls, invoice_file: str) -> Invoice:
        text = read_invoice_file(invoice_file)

        if "consum" in (t := text.lower()):
            from consum_scrapper import ConsumScrapper

            Invoice.supermarket = "Consum"
            return ConsumScrapper.get_invoice(text)
        elif "mercadona" in t:
            from mdona_scrapper import MercadonaScrapper

            Invoice.supermarket = "Mercadona"
            return MercadonaScrapper.get_invoice(text)
        else:
            raise SystemExit("Unsupported invoice format or supermarket.")
