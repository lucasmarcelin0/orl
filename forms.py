"""Formulários utilizados nas telas administrativas."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import BooleanField, PasswordField, StringField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class PageForm(FlaskForm):
    """Formulário para criação e edição de páginas dinâmicas."""

    # Comentário: título exibido na lista e no cabeçalho da página.
    title = StringField("Título", validators=[DataRequired(), Length(max=150)])

    # Comentário: slug utilizado na URL e no menu. Precisa ser curto para compor URLs amigáveis.
    slug = StringField(
        "Slug",
        validators=[Length(max=150)],
        description=(
            "Identificador usado na URL. Se deixado em branco, será gerado automaticamente."
        ),
    )

    # Comentário: campo de conteúdo com editor WYSIWYG fornecido pelo CKEditor.
    content = CKEditorField("Conteúdo", validators=[DataRequired()])

    # Comentário: checkbox para definir se a página aparece no menu principal.
    visible = BooleanField("Exibir no menu", default=True)


class LoginForm(FlaskForm):
    """Formulário de autenticação para o painel administrativo."""

    username = StringField(
        "Usuário",
        validators=[DataRequired(message="Informe o usuário."), Length(max=80)],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired(message="Informe a senha."), Length(min=6, max=128)],
    )


class UserProfileForm(FlaskForm):
    """Permite que os colaboradores atualizem seus dados pessoais."""

    name = StringField(
        "Nome completo",
        validators=[DataRequired(), Length(max=150)],
    )
    email = EmailField(
        "E-mail",
        validators=[Optional(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Nova senha",
        validators=[Optional(), Length(min=6, max=128)],
    )
    confirm_password = PasswordField(
        "Confirmar nova senha",
        validators=[Optional(), EqualTo("password", message="As senhas não conferem.")],
    )
