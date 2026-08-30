"""Upload validation: what a file claims to be versus what it is.

A client-provided content type is a hint, never evidence. Adapted from
document-intelligence-mvp, reduced to the two types this MVP accepts.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_TYPES: dict[str, tuple[str, frozenset[str]]] = {
    ".pdf": ("application/pdf", frozenset({"application/pdf"})),
    ".txt": ("text/plain", frozenset({"text/plain"})),
}

_MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF-",
}

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class UnsupportedFileType(ValueError):
    """The file is not a type this service accepts."""


class InvalidFile(ValueError):
    """The file is empty, too large, or malformed."""


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    mime_type: str
    file_hash: str
    size: int
    extension: str


def safe_filename(filename: str) -> str:
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    base = unicodedata.normalize("NFKD", base)
    base = _UNSAFE_FILENAME_CHARS.sub("_", base).strip("._")
    if not base:
        base = "upload"
    return base[:200]


def extension_of(filename: str) -> str:
    name = safe_filename(filename).lower()
    _, separator, extension = name.rpartition(".")
    return f".{extension}" if separator else ""


def validate_upload(
    *, filename: str, declared_mime_type: str | None, content: bytes, max_bytes: int
) -> ValidatedUpload:
    if not content:
        raise InvalidFile("empty")
    if len(content) > max_bytes:
        raise InvalidFile("too_large")

    name = safe_filename(filename)
    extension = extension_of(name)
    if extension not in SUPPORTED_TYPES:
        raise UnsupportedFileType(extension or "none")

    canonical_mime, accepted = SUPPORTED_TYPES[extension]
    if declared_mime_type:
        declared = declared_mime_type.split(";", 1)[0].strip().lower()
        if declared and declared != "application/octet-stream" and declared not in accepted:
            raise UnsupportedFileType(declared)

    magic = _MAGIC.get(extension)
    if magic and not content.startswith(magic):
        raise UnsupportedFileType(extension)

    return ValidatedUpload(
        filename=name,
        mime_type=canonical_mime,
        file_hash=hashlib.sha256(content).hexdigest(),
        size=len(content),
        extension=extension,
    )


def extract_text(content: bytes, extension: str) -> str:
    if extension == ".txt":
        return _extract_txt(content)
    if extension == ".pdf":
        return _extract_pdf(content)
    raise UnsupportedFileType(extension)


def _extract_txt(content: bytes) -> str:
    if b"\x00" in content:
        raise InvalidFile("binary")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidFile("undecodable") from exc
    if not text.strip():
        raise InvalidFile("empty")
    return text


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
    except (PdfReadError, ValueError, OSError) as exc:
        raise InvalidFile("malformed") from exc
    if getattr(reader, "is_encrypted", False):
        raise InvalidFile("encrypted")
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise InvalidFile("empty")
    return text
