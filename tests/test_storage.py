from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage import _extract_public_id


def test_extract_public_id_basic_image():
    url = "https://res.cloudinary.com/demo/image/upload/v12345/sample.jpg"
    assert _extract_public_id(url) == ("image", "sample")


def test_extract_public_id_with_folder():
    url = "https://res.cloudinary.com/demo/image/upload/v12345/folder/sample.pdf"
    assert _extract_public_id(url) == ("image", "folder/sample")


def test_extract_public_id_with_transformation_and_version():
    url = (
        "https://res.cloudinary.com/demo/image/upload/"
        "c_scale,w_200/v12345/sample.jpg"
    )
    assert _extract_public_id(url) == ("image", "sample")


def test_extract_public_id_with_transformation_and_folder():
    url = (
        "https://res.cloudinary.com/demo/image/upload/"
        "c_scale,w_200/v12345/folder/sample.jpg"
    )
    assert _extract_public_id(url) == ("image", "folder/sample")


def test_extract_public_id_with_transformation_without_version():
    url = (
        "https://res.cloudinary.com/demo/image/upload/"
        "c_scale,w_200/sample.jpg"
    )
    assert _extract_public_id(url) == ("image", "sample")


def test_extract_public_id_with_signature():
    url = (
        "https://res.cloudinary.com/demo/image/upload/"
        "s--abc123--/c_fill,w_120,h_120/v157/sample.png"
    )
    assert _extract_public_id(url) == ("image", "sample")


def test_extract_public_id_invalid_url():
    assert _extract_public_id("https://example.com/foo/bar") is None


def test_extract_public_id_incomplete_path():
    assert _extract_public_id("https://res.cloudinary.com/demo/image/upload/") is None
