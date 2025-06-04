import argparse

from loguru import logger
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

parser = argparse.ArgumentParser(
    description="Extract text from invoice (PDF or image) file."
)

parser.add_argument(
    "-f",
    "--invoice_file",
    type=str,
    help="Path to the invoice file to use",
    required=True,
)

args = parser.parse_args()
invoice_file: str = args.invoice_file

processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model = VisionEncoderDecoderModel.from_pretrained(
    "naver-clova-ix/donut-base-finetuned-docvqa"
)

image = Image.open(invoice_file)
task_prompt = (
    "<s_docvqa><s_question>Extrae la tabla de productos</s_question><s_answer>"
)
inputs = processor(image, task_prompt, return_tensors="pt")
outputs = model.generate(**inputs)
result = processor.decode(outputs[0], skip_special_tokens=True)
logger.info(result)
