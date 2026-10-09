"""Throwaway Docling spike: convert one PDF and walk its items.

usage: python scripts/spike_docling.py <pdf> [page] [--ocr]

  page   1-based PDF page index; walk only that page (default: all pages)
  --ocr  turn OCR on (only bajaj-motor-scanned-2013 needs it)

x is the left edge of the item in PDF points. On a two-page spread (Post Office,
839 pt wide) the left printed page is x < 420 and the right one is x > 420.
"""

import sys

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ContentLayer

# OCR output can contain characters a cp1252 console cannot encode.
sys.stdout.reconfigure(errors="replace")

positional = [a for a in sys.argv[1:] if not a.startswith("--")]
pdf_path = positional[0]
only_page = int(positional[1]) if len(positional) > 1 else None

# Default OCR mode also fires on regions that overlap vector shapes (table
# borders, shading), so on text-layer PDFs it burns minutes for nothing.
opts = PdfPipelineOptions()
opts.do_ocr = "--ocr" in sys.argv

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
)

result = converter.convert(pdf_path)
doc = result.document

print(result.status)
print(f"pages: {doc.num_pages()}")
print(f"tables: {len(doc.tables)}")

# FURNITURE is included so page_header / page_footer items (printed page
# numbers) are visible here; the chunker will walk BODY only.
print()
for item, _depth in doc.iterate_items(
    page_no=only_page,
    included_content_layers={ContentLayer.BODY, ContentLayer.FURNITURE},
):
    page = item.prov[0].page_no if item.prov else "-"
    x = int(item.prov[0].bbox.l) if item.prov else "-"
    text = getattr(item, "text", "").replace("\n", " ")[:70]
    print(f"p{page}  x={x:<4} {item.label.value:<15} {text}")
