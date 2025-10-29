"""Modelos de dados utilizados pela aplicação."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, Integer, String, Text

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
