"""Configurações centrais da aplicação Flask."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit


class Config:
    """Configuração padrão com valores voltados ao ambiente local."""

    # Comentário: o diretório base é calculado para facilitar o uso em qualquer SO.
    BASE_DIR = Path(__file__).resolve().parent

    # Comentário: caminho para o banco SQLite armazenado na pasta do projeto.
    _database_url = os.getenv("DATABASE_URL")

    def _normalized_database_url(database_url: str) -> str:
        """Normaliza a URL de banco para lidar com credenciais não ASCII."""

        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://", "postgresql+psycopg2://", 1
            )

        parsed = urlsplit(database_url)
        if "@" not in parsed.netloc:
            return database_url

        userinfo, hostinfo = parsed.netloc.rsplit("@", 1)
        if not userinfo:
            return database_url

        if ":" in userinfo:
            raw_username, raw_password = userinfo.split(":", 1)
        else:
            raw_username, raw_password = userinfo, None

        username = unquote(raw_username)
        password = unquote(raw_password) if raw_password is not None else None

        encoded_username = quote(username, safe="")
        encoded_password = (
            quote(password, safe="") if password is not None else None
        )

        if encoded_username == raw_username and (
            raw_password is None or encoded_password == raw_password
        ):
            return database_url

        new_userinfo = encoded_username
        if encoded_password is not None:
            new_userinfo = f"{new_userinfo}:{encoded_password}"

        new_netloc = f"{new_userinfo}@{hostinfo}"
        normalized = parsed._replace(netloc=new_netloc)
        return urlunsplit(normalized)

    if _database_url:
        _database_url = _normalized_database_url(_database_url)

    SQLALCHEMY_DATABASE_URI = (
        _database_url or f"sqlite:///{BASE_DIR / 'project.db'}"
    )

    # Comentário: chave secreta utilizada para sessões e formulários.
    SECRET_KEY = os.getenv("SECRET_KEY", "prefeitura-orlandia")

    # Comentário: configuração silenciosa do SQLAlchemy para evitar warnings desnecessários.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Comentário: credenciais de acesso ao painel administrativo.
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "senha-segura")

    # Comentário: ajustes globais do CKEditor para oferecer uma experiência completa.
    CKEDITOR_PKG_TYPE = "full"
    CKEDITOR_LANGUAGE = "pt-br"
    CKEDITOR_HEIGHT = 400
    CKEDITOR_FILE_UPLOADER = "upload_ckeditor_image"
    CKEDITOR_UPLOADS_PATH = str(BASE_DIR / "static" / "uploads")
    CKEDITOR_ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    CKEDITOR_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

    # Comentário: diretório e tipos aceitos para os documentos publicados no site.
    DOCUMENTS_UPLOAD_PATH = str(BASE_DIR / "static" / "uploads" / "documents")
    DOCUMENTS_ALLOWED_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "odt",
        "ods",
        "odp",
        "zip",
    }
