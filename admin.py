"""Configuração do painel administrativo com Flask-Admin."""

from __future__ import annotations

import re
import unicodedata

from flask import current_app, request, Response
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_ckeditor import CKEditorField

from forms import PageForm
from models import db, HomepageSection, Page, SectionItem


SECTION_INLINE_FORM_COLUMNS = (
    "id",
    "title",
    "summary",
    "link_url",
    "link_label",
    "icon_class",
    "image_url",
    "badge",
    "display_date",
    "display_order",
    "is_active",
)


class BasicAuthMixin:
    """Mixin que aplica autenticação HTTP básica às views do Flask-Admin."""

    # Comentário: método utilitário que verifica usuário e senha informados.
    def _authenticate(self) -> bool:
        auth = request.authorization
        if not auth:
            return False

        expected_user = current_app.config["ADMIN_USERNAME"]
        expected_password = current_app.config["ADMIN_PASSWORD"]
        return auth.username == expected_user and auth.password == expected_password

    # Comentário: utilizado pelo Flask-Admin para liberar o acesso à view.
    def is_accessible(self) -> bool:  # type: ignore[override]
        return self._authenticate()

    # Comentário: resposta enviada quando a autenticação falha.
    def inaccessible_callback(self, name: str, **kwargs):  # type: ignore[override]
        return Response(
            "Acesso restrito. Informe as credenciais administrativas.",
            401,
            {"WWW-Authenticate": 'Basic realm="Administração"'},
        )


class PageAdminView(BasicAuthMixin, ModelView):
    """Interface administrativa para gerenciar páginas dinâmicas."""

    # Comentário: formulário personalizado com suporte ao CKEditor.
    form = PageForm

    # Comentário: campos exibidos nas listagens e formulários do administrador.
    column_list = ("title", "slug", "visible")
    column_labels = {
        "title": "Título",
        "slug": "Identificador (slug)",
        "visible": "Exibir no menu",
    }
    form_columns = ("title", "slug", "content", "visible")

    # Comentário: substitui o campo padrão pelo editor WYSIWYG do CKEditor.
    form_overrides = {"content": CKEditorField}

    # Comentário: ordenação padrão alfabética para facilitar a navegação.
    column_default_sort = ("title", False)

    # Comentário: mensagens padronizadas exibidas após operações CRUD.
    create_modal = False
    edit_modal = False

    def _slugify(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode(
            "ascii"
        )
        value = re.sub(r"[^\w\s-]", "", value).strip().lower()
        return re.sub(r"[-\s]+", "-", value)

    def _ensure_unique_slug(self, model: Page) -> None:
        base_slug = self._slugify(model.slug or model.title)
        slug = base_slug or "pagina"
        index = 2

        while True:
            query = Page.query.filter(Page.slug == slug)
            if model.id:
                query = query.filter(Page.id != model.id)
            if query.first() is None:
                model.slug = slug
                break
            slug = f"{base_slug}-{index}"
            index += 1

    def on_model_change(self, form, model: Page, is_created: bool) -> None:  # type: ignore[override]
        if not model.title:
            raise ValueError("A página precisa de um título para gerar o link.")

        if model.slug:
            model.slug = self._slugify(model.slug)

        self._ensure_unique_slug(model)

        return super().on_model_change(form, model, is_created)


class ProtectedAdminIndexView(BasicAuthMixin, AdminIndexView):
    """Tela inicial do painel administrativo com autenticação básica."""

    name = "Início"


class HomepageSectionAdminView(BasicAuthMixin, ModelView):
    """Permite gerenciar as seções exibidas na página inicial."""

    column_list = ("name", "section_type", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "name": "Título da seção",
        "section_type": "Tipo da seção",
        "display_order": "Ordem de exibição",
        "is_active": "Ativa",
    }
    form_columns = (
        "name",
        "slug",
        "description",
        "section_type",
        "display_order",
        "is_active",
        "items",
    )
    form_labels = {
        "name": "Título da seção",
        "slug": "Identificador (slug)",
        "description": "Descrição",
        "section_type": "Tipo da seção",
        "display_order": "Ordem de exibição",
        "is_active": "Seção ativa",
        "items": "Itens da seção",
    }
    form_choices = {
        "section_type": [
            ("services", "Serviços"),
            ("news", "Notícias"),
            ("transparency", "Transparência"),
            ("custom", "Personalizado"),
        ]
    }
    inline_models = [
        (
            SectionItem,
            dict(
                form_columns=SECTION_INLINE_FORM_COLUMNS,
                form_args={
                    "id": {"label": "ID"},
                    "title": {"label": "Título"},
                    "summary": {"label": "Resumo"},
                    "link_url": {"label": "Endereço do link"},
                    "link_label": {"label": "Texto do link"},
                    "icon_class": {"label": "Ícone (classe CSS)"},
                    "image_url": {"label": "Imagem (URL)"},
                    "badge": {"label": "Selo"},
                    "display_date": {"label": "Data exibida"},
                    "display_order": {"label": "Ordem de exibição"},
                    "is_active": {"label": "Ativo"},
                },
            ),
        )
    ]


class SectionItemAdminView(BasicAuthMixin, ModelView):
    """Administração individual dos cartões que compõem as seções."""

    column_list = ("title", "section", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "title": "Título",
        "section": "Seção",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    form_columns = ("section",) + SECTION_INLINE_FORM_COLUMNS
    form_labels = {
        "section": "Seção",
        "title": "Título",
        "summary": "Resumo",
        "link_url": "Endereço do link",
        "link_label": "Texto do link",
        "icon_class": "Ícone (classe CSS)",
        "image_url": "Imagem (URL)",
        "badge": "Selo",
        "display_date": "Data exibida",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }


def init_admin(app) -> Admin:
    """Inicializa o painel administrativo integrado ao aplicativo Flask."""

    # Comentário: instancia o objeto Admin reutilizando a sessão do SQLAlchemy.
    admin = Admin(
        app,
        name="Prefeitura de Orlândia",
        index_view=ProtectedAdminIndexView(),
    )

    # Comentário: compatibilidade com versões mais recentes do Flask-Admin.
    if hasattr(admin, "template_mode"):
        admin.template_mode = "bootstrap4"

    # Comentário: registra a view que permite gerenciar o modelo Page.
    admin.add_view(
        PageAdminView(
            Page,
            db.session,
            category="Conteúdo",
            name="Páginas institucionais",
        )
    )
    admin.add_view(
        HomepageSectionAdminView(
            HomepageSection,
            db.session,
            category="Página inicial",
            name="Seções da página",
        )
    )
    admin.add_view(
        SectionItemAdminView(
            SectionItem,
            db.session,
            category="Página inicial",
            name="Itens das seções",
        )
    )

    return admin
