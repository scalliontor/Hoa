"""Print the number of pages of each chapter from the PDF bookmarks (pymupdf or pypdf)."""
import sys


def chapters(path):
    try:
        import pymupdf
        doc = pymupdf.open(path)
        return [(title, page) for level, title, page in doc.get_toc() if level == 1], doc.page_count
    except ImportError:
        from pypdf import PdfReader
        reader = PdfReader(path)
        top = [item for item in reader.outline if not isinstance(item, list)]
        return [(item.title, reader.get_destination_page_number(item) + 1) for item in top], len(reader.pages)


top, total = chapters(sys.argv[1])
for (title, start), nxt in zip(top, top[1:] + [("", total + 1)]):
    print(f"{nxt[1] - start:3d}  {title}")
print(f"{total:3d}  total pages")
