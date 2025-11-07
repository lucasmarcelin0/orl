"""Modelos de dados utilizados pela aplicação."""

from __future__ import annotations

from datetime import datetime

from flask import has_request_context, url_for
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declared_attr, relationship

# Comentário: instância global do SQLAlchemy para ser compartilhada entre módulos.
db = SQLAlchemy()


class AuditMixin:
    """Campos utilitários para registrar autoria e datas de alterações."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    @declared_attr
    def created_by(cls):  # type: ignore[override]
        return relationship(
            "User",
            foreign_keys=[cls.created_by_id],
            backref="created_%s" % cls.__tablename__,
        )

    @declared_attr
    def updated_by(cls):  # type: ignore[override]
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_id],
            backref="updated_%s" % cls.__tablename__,
        )


class User(UserMixin, db.Model):
    """Usuários autorizados a acessar o painel administrativo."""

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def set_password(self, password: str) -> None:
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<User {self.username!r}>"


class Page(AuditMixin, db.Model):
    """Representa uma página institucional com conteúdo dinâmico."""

    # Comentário: chave primária incremental usada pelo SQLAlchemy.
    id = Column(Integer, primary_key=True)

    # Comentário: título exibido ao usuário no menu e na página.
    title = Column(String(150), nullable=False)

    # Comentário: slug único utilizado na URL amigável.
    slug = Column(String(150), unique=True, nullable=False)

    # Comentário: conteúdo HTML armazenado como texto amplo.
    content = Column(Text, nullable=False)

    # Comentário: flag que indica se a página deve aparecer no menu principal.
    visible = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<Page {self.slug!r}>"


class HomepageSection(AuditMixin, db.Model):
    """Define um agrupamento de cartões exibidos na página inicial."""

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    section_type = Column(String(50), nullable=False, default="custom")
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    items = relationship(
        "SectionItem",
        back_populates="section",
        order_by=lambda: (SectionItem.display_order, SectionItem.id),
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<HomepageSection {self.slug!r}>"


class Document(AuditMixin, db.Model):
    """Arquivo disponibilizado para download pelos moradores."""

    id = Column(Integer, primary_key=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    icon_class = Column(String(120), nullable=True)
    file_path = Column(String(255), nullable=False)
    section_item_id = Column(Integer, ForeignKey("section_item.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    section_item = relationship("SectionItem", back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<Document {self.title!r}>"

    @property
    def filename(self) -> str:
        """Retorna apenas o nome do arquivo armazenado."""

        file_path = (self.file_path or "").strip()
        if not file_path:
            return ""

        normalized = file_path.replace("\\", "/")
        return normalized.rsplit("/", 1)[-1]

    @property
    def public_path(self) -> str:
        """Caminho relativo dentro da pasta estática de documentos."""

        file_path = (self.file_path or "").strip()
        if not file_path:
            return ""

        normalized = file_path.replace("\\", "/").strip()

        if normalized.startswith(("http://", "https://", "//")):
            return ""

        normalized = normalized.lstrip("/")

        static_prefix = "static/"
        if normalized.startswith(static_prefix):
            normalized = normalized[len(static_prefix) :]

        documents_prefix = "uploads/documents/"
        if normalized.startswith(documents_prefix):
            return normalized

        return f"{documents_prefix}{normalized}"

    @property
    def public_url(self) -> str:
        """URL final utilizada nos templates públicos."""

        file_path = (self.file_path or "").strip()
        if not file_path:
            return ""

        normalized = file_path.replace("\\", "/").strip()

        if normalized.startswith(("http://", "https://", "//")):
            return normalized

        normalized = normalized.lstrip("/")

        static_prefix = "static/"
        if normalized.startswith(static_prefix):
            normalized = normalized[len(static_prefix) :]

        documents_prefix = "uploads/documents/"
        if not normalized.startswith(documents_prefix):
            normalized = f"{documents_prefix}{normalized}"

        if has_request_context():
            return url_for("static", filename=normalized)

        return f"/static/{normalized}"


class EmergencyService(AuditMixin, db.Model):
    """Serviço de emergência exibido em destaque na página inicial."""

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(60), nullable=True)
    description = Column(Text, nullable=True)
    icon_class = Column(String(120), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<EmergencyService {self.name!r}>"


class FooterColumn(AuditMixin, db.Model):
    """Bloco configurável contendo links exibidos no rodapé."""

    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    links = relationship(
        "QuickLink",
        back_populates="footer_column",
        order_by="QuickLink.display_order, QuickLink.id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<FooterColumn {self.title!r}>"


class QuickLink(AuditMixin, db.Model):
    """Atalho configurável exibido no acesso rápido ou no rodapé."""

    LOCATION_QUICK_ACCESS = "quick_access"
    LOCATION_FOOTER = "footer"

    id = Column(Integer, primary_key=True)
    label = Column(String(150), nullable=False)
    url = Column(String(500), nullable=False)
    location = Column(String(50), nullable=False, default=LOCATION_QUICK_ACCESS)
    footer_column_id = Column(Integer, ForeignKey("footer_column.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    footer_column = relationship("FooterColumn", back_populates="links")

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<QuickLink {self.label!r} ({self.location})>"


class SectionItem(AuditMixin, db.Model):
    """Representa um cartão individual dentro de uma seção da home."""

    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("homepage_section.id"), nullable=False)
    title = Column(String(180), nullable=False)
    summary = Column(Text, nullable=True)
    link_url = Column(String(500), nullable=True)
    link_label = Column(String(100), nullable=True)
    icon_class = Column(String(120), nullable=True)
    image_url = Column(String(500), nullable=True)
    badge = Column(String(120), nullable=True)
    display_date = Column(String(120), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    section = relationship("HomepageSection", back_populates="items")
    documents = relationship(
        "Document",
        back_populates="section_item",
        order_by="Document.display_order, Document.id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<SectionItem {self.title!r} ({self.section_id})>"
