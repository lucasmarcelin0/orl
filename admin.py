"""Configuração do painel administrativo com Flask-Admin."""

from __future__ import annotations

from flask import current_app, request, Response
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_ckeditor import CKEditorField

from forms import PageForm
from models import db, HomepageSection, Page, SectionItem


SECTION_INLINE_FORM_COLUMNS = (
    "title",
    "summary",
    "link_label",
    "link_url",
    "image_url",
    "icon_class",
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
    form_columns = ("title", "slug", "content", "visible")

    # Comentário: substitui o campo padrão pelo editor WYSIWYG do CKEditor.
    form_overrides = {"content": CKEditorField}

    # Comentário: ordenação padrão alfabética para facilitar a navegação.
    column_default_sort = ("title", False)

    # Comentário: mensagens padronizadas exibidas após operações CRUD.
    create_modal = False
    edit_modal = False


class ProtectedAdminIndexView(BasicAuthMixin, AdminIndexView):
    """Tela inicial do painel administrativo com autenticação básica."""

    pass


class HomepageSectionAdminView(BasicAuthMixin, ModelView):
    """Permite gerenciar as seções exibidas na página inicial."""

    column_list = ("name", "section_type", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    form_columns = (
        "name",
        "slug",
        "description",
        "section_type",
        "display_order",
        "is_active",
        "items",
    )
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
            dict(form_columns=SECTION_INLINE_FORM_COLUMNS),
        )
    ]


class SectionItemAdminView(BasicAuthMixin, ModelView):
    """Administração individual dos cartões que compõem as seções."""

    column_list = ("title", "section", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    form_columns = ("section",) + SECTION_INLINE_FORM_COLUMNS
    column_labels = {
        "title": "Título",
        "section": "Seção",
        "summary": "Descrição",
        "link_label": "Texto do botão",
        "link_url": "Link do botão",
        "image_url": "Imagem (URL)",
        "icon_class": "Ícone CSS",
        "badge": "Selo destacado",
        "display_date": "Data exibida",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    form_widget_args = {
        "summary": {"rows": 4, "placeholder": "Resumo curto exibido no cartão."},
        "link_label": {"placeholder": "Texto do botão/ação."},
        "link_url": {
            "placeholder": "https://exemplo.gov.br/servico ou caminho interno",
        },
        "image_url": {"placeholder": "Endereço completo da imagem (opcional)."},
        "icon_class": {"placeholder": "Classe CSS do ícone, ex.: fas fa-bullhorn."},
        "badge": {"placeholder": "Texto curto como 'Novo' ou 'Em andamento'."},
        "display_date": {"placeholder": "Texto livre para a data exibida."},
        "display_order": {"placeholder": "Use números menores para exibir antes."},
    }
    form_descriptions = {
        "section": "Escolha onde o cartão aparecerá na página inicial.",
        "is_active": "Desmarque para ocultar temporariamente sem apagar.",
    }
    form_create_rules = form_edit_rules = (
        rules.Header("Conteúdo principal"),
        "section",
        "title",
        "summary",
        rules.Header("Ação do cartão"),
        "link_label",
        "link_url",
        rules.Header("Elementos visuais"),
        "image_url",
        "icon_class",
        "badge",
        "display_date",
        rules.Header("Controle de exibição"),
        "display_order",
        "is_active",
    )


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
    admin.add_view(PageAdminView(Page, db.session, category="Conteúdo"))
    admin.add_view(
        HomepageSectionAdminView(HomepageSection, db.session, category="Página inicial")
    )
    admin.add_view(
        SectionItemAdminView(SectionItem, db.session, category="Página inicial")
    )

    return admin
