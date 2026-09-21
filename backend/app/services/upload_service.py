"""Secure file upload handling.

Defences:
  * server-generated filenames (user filenames are never trusted)
  * extension allow-list
  * content-type / magic-byte validation
  * hard size limit
  * path traversal prevention (path components stripped)
"""

from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile

from app.config import settings
from app.core.exceptions import FileUploadError

# Magic bytes for a few common formats to defend against spoofed extensions.
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF-", "pdf"),
    (b"\x50\x4b\x03\x04", "zip"),  # also docx/xlsx/pptx
    (b"\xd0\xcf\x11\xe0", "ole"),  # legacy office
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),
    (b"GIF8", "gif"),
]

_TEXT_EXTENSIONS = {"txt", "csv", "md", "json", "xml"}

_BLOCKED_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "msi", "sh", "bash", "ps1", "vbs",
    "js", "mjs", "jar", "php", "py", "rb", "pl", "cgi", "jsp", "asp",
    "dll", "so", "bin", "scr", "cpl", "hta", "inf", "reg", "wsf",
}


def _safe_extension(filename: Optional[str]) -> str:
    if not filename:
        raise FileUploadError("Filename is required.")
    # Normalise + strip any directory components the client may send.
    base = os.path.basename(filename.strip())
    if not base or base.startswith("."):
        raise FileUploadError("Invalid filename.")
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if not ext:
        raise FileUploadError("File must have an extension.")
    if ext in _BLOCKED_EXTENSIONS:
        raise FileUploadError(f"Executable/script files (.{ext}) are not allowed.")
    if ext not in settings.allowed_extensions_list:
        raise FileUploadError(
            f"File type .{ext} is not allowed. Allowed: {', '.join(settings.allowed_extensions_list)}"
        )
    return ext


def _validate_content(upload: UploadFile, ext: str) -> None:
    """Best-effort content sniffing: reject clearly-mismatched payloads."""
    declared = (upload.content_type or "").lower()
    guessed, _ = mimetypes.guess_type(f"file.{ext}")
    # Reject when the declared type is a known-dangerous executable type.
    if declared in {
        "application/x-msdownload", "application/x-executable",
        "application/x-msdos-program", "text/x-python", "application/javascript",
    }:
        raise FileUploadError("The declared content type is not allowed.")
    # Text files can't be sniffed; allow them.
    if ext in _TEXT_EXTENSIONS:
        return
    # For office/zip/pdf/images, try magic-byte verification.
    upload.file.seek(0)
    head = upload.file.read(16)
    upload.file.seek(0)
    if not head:
        return
    for magic, kind in _MAGIC_SIGNATURES:
        if head.startswith(magic):
            # zip containers cover docx/xlsx/pptx/zip
            if kind == "ole" and ext in {"doc", "ppt", "xls"}:
                return
            if kind == "zip" and ext in {"docx", "xlsx", "pptx", "zip"}:
                return
            if kind == ext:
                return
            # Mismatch between declared extension and actual payload.
            raise FileUploadError(
                f"File content does not match its .{ext} extension."
            )
    if guessed and declared and declared != guessed and not declared.startswith("application/octet-stream"):
        raise FileUploadError("File content type does not match its extension.")


async def save_upload(
    upload: UploadFile,
    *,
    subfolder: str = "general",
    allowed_extensions: Optional[list[str]] = None,
) -> Tuple[str, str]:
    """Validate and store an upload. Returns (stored_filename, original_name)."""
    if upload is None or not upload.filename:
        raise FileUploadError("No file was provided.")

    ext = _safe_extension(upload.filename)
    if allowed_extensions is not None:
        if ext not in {e.lower().lstrip(".") for e in allowed_extensions}:
            raise FileUploadError(f"This upload only accepts: {', '.join(allowed_extensions)}")

    _validate_content(upload, ext)

    contents = await upload.read()
    if not contents:
        raise FileUploadError("Uploaded file is empty.")
    if len(contents) > settings.max_upload_size_bytes:
        raise FileUploadError(
            f"File exceeds the maximum size of {settings.max_upload_size_mb} MB."
        )

    folder = settings.upload_path / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    stored = f"{uuid.uuid4().hex}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = (folder / stored).resolve()
    # Defence in depth: ensure resolution stays inside the upload root.
    if not str(dest).startswith(str(settings.upload_path.resolve())):
        raise FileUploadError("Invalid upload destination.")

    dest.write_bytes(contents)
    return f"{subfolder}/{stored}", upload.filename


def upload_to_url(stored_path: Optional[str]) -> Optional[str]:
    """Generate download URL for authenticated file access.

    Files are served through authenticated API endpoints for security.
    """
    if not stored_path:
        return None
    # Return storage path - will be used to construct download URL
    return stored_path


def delete_upload(stored_path: Optional[str]) -> None:
    if not stored_path:
        return
    try:
        target = (settings.upload_path / stored_path).resolve()
        root = settings.upload_path.resolve()
        if str(target).startswith(str(root)) and target.is_file():
            target.unlink()
    except Exception:
        pass
