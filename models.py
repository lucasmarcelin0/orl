"""Modelos de dados utilizados pela aplicação."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

# Comentário: instância global do SQLAlchemy para ser compartilhada entre módulos.
db = SQLAlchemy()


class Page(db.Model):
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


class HomepageSection(db.Model):
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


class SectionItem(db.Model):
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

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<SectionItem {self.title!r} ({self.section_id})>"


class Document(db.Model):
    """Arquivo disponibilizado para download pelos moradores."""

    id = Column(Integer, primary_key=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    icon_class = Column(String(120), nullable=True)
    file_path = Column(String(255), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover - representação auxiliar
        return f"<Document {self.title!r}>"

    @property
    def filename(self) -> str:
        """Retorna apenas o nome do arquivo armazenado."""

        return (self.file_path or "").split("/")[-1]

    @property
    def public_path(self) -> str:
        """Caminho relativo dentro da pasta estática de documentos."""

        sanitized = (self.file_path or "").lstrip("/\\")
        return f"uploads/documents/{sanitized}" if sanitized else ""
