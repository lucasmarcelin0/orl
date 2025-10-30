"""Configurações centrais da aplicação Flask."""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Configuração padrão com valores voltados ao ambiente local."""

    # Comentário: o diretório base é calculado para facilitar o uso em qualquer SO.
    BASE_DIR = Path(__file__).resolve().parent

    # Comentário: caminho para o banco SQLite armazenado na pasta do projeto.
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL")
        or f"sqlite:///{BASE_DIR / 'project.db'}"
    )

    # Comentário: chave secreta utilizada para sessões e formulários.
    SECRET_KEY = os.getenv("SECRET_KEY", "prefeitura-orlandia")

    # Comentário: configuração silenciosa do SQLAlchemy para evitar warnings desnecessários.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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
