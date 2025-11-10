"""Helpers for integrating with external file storage providers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from flask import current_app


class StorageError(RuntimeError):
    """Raised when a storage operation fails."""


def init_cloudinary(app) -> bool:
    """Configure Cloudinary based on the application settings."""

    cloudinary_url = app.config.get("CLOUDINARY_URL")
    enabled = bool(cloudinary_url)

    cloudinary_config = app.extensions.setdefault("cloudinary", {})
    cloudinary_config["enabled"] = enabled

    if not enabled:
        return False

    cloudinary.config(cloudinary_url=cloudinary_url)
    return True


def is_cloudinary_enabled(app=None) -> bool:
    """Return True when Cloudinary is configured for the given app."""

    if app is None:
        app = current_app

    config = getattr(app, "extensions", {}).get("cloudinary", {})
    return bool(config.get("enabled"))


def upload_to_cloudinary(
    file_storage,
    *,
    filename: str,
    folder: Optional[str],
    resource_type: str,
) -> str:
    """Upload a file object to Cloudinary and return its secure URL."""

    if not is_cloudinary_enabled():
        raise StorageError("Cloudinary não está configurado para esta aplicação.")

    path = Path(filename)
    options = {
        "resource_type": resource_type,
        "invalidate": True,
        "overwrite": True,
        "unique_filename": False,
        "use_filename": False,
    }

    folder = (folder or "").strip("/")
    if folder:
        options["folder"] = folder

    public_id = path.stem or None
    if public_id:
        options["public_id"] = public_id

    extension = path.suffix.lstrip(".")
    if extension:
        options["format"] = extension

    try:
        result = cloudinary.uploader.upload(file_storage, **options)
    except CloudinaryError as exc:  # pragma: no cover - network failure guard
        raise StorageError("Falha ao enviar arquivo ao Cloudinary.") from exc

    secure_url = result.get("secure_url") or result.get("url")
    if not secure_url:
        raise StorageError("Cloudinary não retornou a URL do arquivo enviado.")

    return secure_url


def _extract_public_id(url: str) -> Optional[Tuple[str, str]]:
    """Extract the resource type and public ID from a Cloudinary URL."""

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) < 3:
        return None

    # Cloudinary URLs follow the pattern
    # /<cloud_name>/<resource_type>/<delivery_type>/<asset_path>
    resource_type = segments[1]
    asset_segments = segments[3:]
    if not asset_segments:
        return None

    # Signed URLs include a signature segment right after the delivery type.
    if asset_segments and asset_segments[0].startswith("s--") and asset_segments[0].endswith("--"):
        asset_segments = asset_segments[1:]

    if not asset_segments:
        return None

    # Transformations may appear before the optional version segment. We discard
    # them to isolate the actual public ID even when transformations are present.
    version_index: Optional[int] = None
    for index, segment in enumerate(asset_segments):
        if segment.startswith("v") and segment[1:].isdigit():
            version_index = index
            break

    if version_index is not None:
        asset_segments = asset_segments[version_index + 1 :]
    else:
        while asset_segments and "," in asset_segments[0]:
            asset_segments = asset_segments[1:]

    if not asset_segments:
        return None

    last_segment = asset_segments[-1]
    if "." in last_segment:
        asset_segments[-1] = last_segment.rsplit(".", 1)[0]

    public_id = "/".join(asset_segments)
    if not public_id:
        return None

    return resource_type, public_id


def delete_cloudinary_asset(url: str, *, resource_type: str) -> bool:
    """Attempt to delete an asset from Cloudinary given its URL."""

    if not url:
        return False

    if not is_cloudinary_enabled():
        return False

    extracted = _extract_public_id(url)
    if not extracted:
        return False

    url_resource_type, public_id = extracted
    delete_resource_type = resource_type or url_resource_type

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type=delete_resource_type,
            invalidate=True,
        )
    except CloudinaryError as exc:  # pragma: no cover - defensive logging
        logger = getattr(current_app, "logger", logging.getLogger(__name__))
        logger.warning(
            "Não foi possível excluir o arquivo do Cloudinary", exc_info=exc
        )
        return False

    return True
