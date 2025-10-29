"""Formulários utilizados nas telas administrativas."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Length


class PageForm(FlaskForm):
    """Formulário para criação e edição de páginas dinâmicas."""

    # Comentário: título exibido na lista e no cabeçalho da página.
    title = StringField("Título", validators=[DataRequired(), Length(max=150)])

    # Comentário: slug utilizado na URL e no menu. Precisa ser curto para compor URLs amigáveis.
    slug = StringField("Slug", validators=[DataRequired(), Length(max=150)])

    # Comentário: campo de conteúdo com editor WYSIWYG fornecido pelo CKEditor.
    content = CKEditorField("Conteúdo", validators=[DataRequired()])

    # Comentário: checkbox para definir se a página aparece no menu principal.
    visible = BooleanField("Exibir no menu", default=True)
