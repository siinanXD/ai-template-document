from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.services.files import InvalidFile, UnsupportedFileType, extract_text, validate_upload


def test_txt_upload_is_accepted() -> None:
    upload = validate_upload(
        filename="invoice.txt",
        declared_mime_type="text/plain",
        content=b"Harborline Invoice INV-1",
        max_bytes=1024,
    )
    assert upload.mime_type == "text/plain"
    assert upload.extension == ".txt"
    assert len(upload.file_hash) == 64


def test_filename_is_not_trusted() -> None:
    with pytest.raises(UnsupportedFileType):
        validate_upload(
            filename="invoice.pdf",
            declared_mime_type="application/pdf",
            content=b"not a pdf",
            max_bytes=1024,
        )


def test_empty_file_is_invalid() -> None:
    with pytest.raises(InvalidFile):
        validate_upload(
            filename="invoice.txt",
            declared_mime_type="text/plain",
            content=b"",
            max_bytes=1024,
        )


def test_oversized_file_is_invalid() -> None:
    with pytest.raises(InvalidFile):
        validate_upload(
            filename="invoice.txt",
            declared_mime_type="text/plain",
            content=b"x" * 21,
            max_bytes=20,
        )


def test_png_is_unsupported() -> None:
    with pytest.raises(UnsupportedFileType):
        validate_upload(
            filename="scan.png",
            declared_mime_type="image/png",
            content=b"\x89PNG\r\n\x1a\n",
            max_bytes=1024,
        )


# Header is valid enough for PdfReader() to return; the catalog is resolved lazily
# on reader.pages and must still map to InvalidFile, not a 500.
_BROKEN_ROOT_PDF = b"%PDF-1.1\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def test_malformed_pdf_is_invalid() -> None:
    with pytest.raises(InvalidFile):
        extract_text(b"%PDF-not-a-real-file", ".pdf")


def test_pdf_with_broken_root_is_invalid_not_a_crash() -> None:
    with pytest.raises(InvalidFile, match="malformed"):
        extract_text(_BROKEN_ROOT_PDF, ".pdf")


def test_blank_pdf_is_invalid() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(InvalidFile):
        extract_text(buffer.getvalue(), ".pdf")


def test_null_bytes_in_txt_are_invalid() -> None:
    with pytest.raises(InvalidFile):
        extract_text(b"hello\x00world", ".txt")
