import sys
from pathlib import Path

import pytesseract
from loguru import logger
from PIL import Image, ImageEnhance, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError


def setup_logging(level: str = "WARNING"):
    """Global logging setup."""

    logger.remove()
    if level == "debug":
        logger.add(sys.stderr, level="DEBUG")
        logger.debug("Verbose output.")
    elif level == "trace":
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="INFO")


def detect_file_type(filepath: str) -> str | None:
    """File type using magic header."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
        if header.startswith(b"%PDF"):
            return "pdf"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        else:
            return None
    except IsADirectoryError:
        raise SystemExit(logger.error(f"Error: {filepath} is a directory, not a file."))


def read_png_file(filepath: str) -> str:
    """Read PNG file."""
    try:
        # 1. Load image:
        image = Image.open(filepath)

        # 2. Image Convert to gray scale:
        # Aunque ya sea B&N, convertir a 'L' asegura que Pillow lo maneje como tal.
        # Si la imagen ya es binaria estricta (1 bit), `convert('L')` la convertirá a 8 bits de gris.
        image = image.convert("L")

        # 3. Upscaling:
        # Aumentar la resolución para mejorar el reconocimiento de texto pequeño.
        # Image.LANCZOS es un filtro de alta calidad para redimensionar (recomendado).
        scale_factor = 1.5  # Adjust as needed: 1.5, 2, 3, etc.
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        image = image.resize((new_width, new_height), Image.LANCZOS)

        # 4. Contrast and Sharpness Adjustment (Optional but usefull):

        # Contraste Adjustment
        # enhancer = ImageEnhance.Contrast(image)
        # image = enhancer.enhance(1.5)  # 1.5 means +50% on contrast. Adjust as needed.

        # Sharpness Adjustment
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)  # 2.0 means double Sharpness. Ajust as needed.

        # 6. PyTesseract OCR:
        # Tesseract Config.
        # --psm 6 good starting point for uniform text blocks.
        # --oem 1 LSTM Engine (Tesseract 4+).
        custom_config = r"--oem 1 --psm 6"
        text = pytesseract.image_to_string(
            image, config=custom_config, lang="spa+eng", timeout=10
        )
    except UnidentifiedImageError:
        raise SystemExit(logger.error(f"Error reading invoice file: {filepath}"))
    except FileNotFoundError:
        raise SystemExit(logger.error(f"File not found: {filepath}"))

    logger.trace(text)
    return text


def read_pdf_file(filepath: str) -> str:
    """Read PDF file."""
    try:
        with PdfReader(filepath) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages])
    except PyPdfError:
        raise SystemExit(logger.error(f"Error reading PDF file: {filepath}"))

    logger.trace(text)
    return text


def read_invoice_file(invoice_file: str) -> str:

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
