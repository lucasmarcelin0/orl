"""Configurações centrais da aplicação Flask."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)
from urllib.parse import splitport


def _encode_host(host: str | None) -> str:
    """Garante que o host esteja em ASCII utilizando IDNA quando possível."""

    if not host:
        return ""

    if host.startswith("[") and host.endswith("]"):
        return host

    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return host


def _combine_host_port(host: str, port: str | None) -> str:
    """Reconstrói o host com a porta preservando IPv6 quando necessário."""

    if not host and not port:
        return ""

    if host and ":" in host and not host.startswith("["):
        host = f"[{host}]"

    if port:
        return f"{host}:{port}" if host else f":{port}"
    return host


def _encode_path(path: str) -> str:
    """Normaliza o caminho (nome do banco) para conter apenas ASCII."""

    if not path:
        return path
    return quote(unquote(path), safe="/")


def _encode_query(query: str) -> str:
    """Percent-encode consistente para a string de query."""

    if not query:
        return query
    pairs = parse_qsl(query, keep_blank_values=True)
    return urlencode(pairs, doseq=True, encoding="utf-8", safe="")


def _encode_fragment(fragment: str) -> str:
    """Normaliza o fragmento da URL."""

    if not fragment:
        return fragment
    return quote(unquote(fragment), safe="")


def _repair_surrogates(value: str) -> str:
    """Reinterpreta variáveis com caracteres substitutos oriundos do Windows."""

    # Comentário: em ambientes Windows, variáveis com caracteres fora de ASCII
    # podem chegar como "surrogateescape" (\udc80-\udcff). Reconstruímos os
    # bytes originais e decodificamos usando codificações compatíveis.
    if not any("\udc80" <= char <= "\udcff" for char in value):
        return value

    raw_bytes = value.encode("utf-8", "surrogateescape")
    for encoding in ("utf-8", sys.getfilesystemencoding() or "utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw_bytes.decode("utf-8", "ignore")


class Config:
    """Configuração padrão com valores voltados ao ambiente local."""

    # Comentário: o diretório base é calculado para facilitar o uso em qualquer SO.
    BASE_DIR = Path(__file__).resolve().parent

    # Comentário: caminho para o banco SQLite armazenado na pasta do projeto.
    _database_url_raw = os.getenv("DATABASE_URL")
    _database_url = (
        _repair_surrogates(_database_url_raw)
        if isinstance(_database_url_raw, str)
        else _database_url_raw
    )
    _normalize_database_url = os.getenv("DATABASE_URL_NORMALIZE", "1").lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    def _normalized_database_url(database_url: str) -> str:
        """Normaliza a URL de banco para lidar com credenciais não ASCII."""

        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://", "postgresql+psycopg2://", 1
            )

        parsed = urlsplit(database_url)
        if "@" not in parsed.netloc:
            host, port = splitport(parsed.netloc)
            ascii_host = _encode_host(host)
            if ascii_host == host:
                path = _encode_path(parsed.path)
                query = _encode_query(parsed.query)
                fragment = _encode_fragment(parsed.fragment)
                normalized = parsed._replace(path=path, query=query, fragment=fragment)
                return urlunsplit(normalized)
            path = _encode_path(parsed.path)
            query = _encode_query(parsed.query)
            fragment = _encode_fragment(parsed.fragment)
            netloc = _combine_host_port(ascii_host, port)
            normalized = parsed._replace(netloc=netloc, path=path, query=query, fragment=fragment)
            return urlunsplit(normalized)

        userinfo, hostinfo = parsed.netloc.rsplit("@", 1)
        if not userinfo:
            host, port = splitport(hostinfo)
            ascii_host = _encode_host(host)
            path = _encode_path(parsed.path)
            query = _encode_query(parsed.query)
            fragment = _encode_fragment(parsed.fragment)
            netloc = _combine_host_port(ascii_host, port)
            normalized = parsed._replace(netloc=netloc, path=path, query=query, fragment=fragment)
            return urlunsplit(normalized)

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

        host, port = splitport(hostinfo)
        ascii_host = _encode_host(host)
        new_netloc = f"{new_userinfo}@{_combine_host_port(ascii_host, port)}"
        path = _encode_path(parsed.path)
        query = _encode_query(parsed.query)
        fragment = _encode_fragment(parsed.fragment)
        normalized = parsed._replace(
            netloc=new_netloc, path=path, query=query, fragment=fragment
        )
        return urlunsplit(normalized)


    if _database_url and _normalize_database_url:
        try:
            _database_url = _normalized_database_url(_database_url)
        except Exception:
            # Comentário: se ocorrer qualquer erro durante a normalização,
            # retomamos a URL original para não impedir a aplicação de iniciar.
            _database_url = _database_url_raw

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
