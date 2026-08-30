from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.core.db import get_db
from app.core.dependencies import get_provider
from app.core.settings import get_settings
from app.schemas.extract import ExtractResponse, ExtractTextRequest
from app.services.extract import (
    InvalidFileError,
    extract_from_file,
    extract_from_text,
)

router = APIRouter()


async def _read_multipart_file(form) -> tuple[str, str | None, bytes]:
    upload = form.get("file")
    if isinstance(upload, UploadFile):
        content = await upload.read()
        if not content:
            raise InvalidFileError("empty")
        return upload.filename or "upload", upload.content_type, content
    if isinstance(upload, (bytes, bytearray)):
        return "upload.bin", "application/octet-stream", bytes(upload)
    if isinstance(upload, str) and upload:
        return "upload.txt", "text/plain", upload.encode("utf-8")
    raise InvalidFileError("empty")


@router.post("/api/v1/documents/extract", response_model=ExtractResponse)
async def extract_document(
    request: Request,
    db: Session = Depends(get_db),
    provider=Depends(get_provider),
) -> ExtractResponse:
    settings = get_settings()
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        try:
            payload = ExtractTextRequest.model_validate(await request.json())
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        return await extract_from_text(db, provider, settings, payload.text)
    if "multipart/form-data" in (request.headers.get("content-type") or "").lower():
        form = await request.form()
        filename, mime_type, content = await _read_multipart_file(form)
        return await extract_from_file(
            db,
            provider,
            settings,
            filename=filename,
            declared_mime_type=mime_type,
            content=content,
        )
    raise InvalidFileError("empty")
