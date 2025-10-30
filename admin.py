"""Configuração do painel administrativo com Flask-Admin."""

from __future__ import annotations

import re
import unicodedata

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from flask import current_app, request, Response, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_ckeditor import CKEditorField
from sqlalchemy.exc import OperationalError

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


SECTION_ITEM_PREVIEW_HTML = """
<section class=\"section-item-preview\" data-section-item-preview>
    <header class=\"section-item-preview__header\">
        <span class=\"section-item-preview__badge\" data-preview-badge>Selo do cartão</span>
        <span class=\"section-item-preview__date\" data-preview-date>Data exibida</span>
    </header>
    <figure class=\"section-item-preview__media\" data-preview-image-wrapper hidden>
        <img
            class=\"section-item-preview__image\"
            src=\"\"
            alt=\"Pré-visualização da imagem do cartão\"
            data-preview-image
        >
    </figure>
    <h3 class=\"section-item-preview__title\" data-preview-title>Título do cartão</h3>
    <div class=\"section-item-preview__summary\" data-preview-summary>
        Utilize o campo “Resumo” para adicionar o conteúdo que aparecerá no site.
    </div>
    <footer class=\"section-item-preview__footer\">
        <a class=\"section-item-preview__link\" data-preview-link href=\"#\">
            <span data-preview-link-label>Texto do link</span>
            <i class=\"fa fa-arrow-right\" aria-hidden=\"true\"></i>
        </a>
    </footer>
</section>
"""


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

    def _to_namespace(self, data):
        """Converte estruturas de dicionário em objetos com acesso por atributo."""

        if isinstance(data, dict):
            return SimpleNamespace(
                **{key: self._to_namespace(value) for key, value in data.items()}
            )
        return data

    @expose("/")
    def index(self):  # type: ignore[override]
        """Exibe um painel inicial com atalhos e métricas úteis."""

        def _safe_query(fn, default):
            try:
                return fn()
            except OperationalError:
                return default

        total_pages = _safe_query(lambda: Page.query.count(), 0)
        published_pages = _safe_query(
            lambda: Page.query.filter_by(visible=True).count(), 0
        )
        total_sections = _safe_query(lambda: HomepageSection.query.count(), 0)
        active_sections = _safe_query(
            lambda: HomepageSection.query.filter_by(is_active=True).count(), 0
        )
        total_items = _safe_query(lambda: SectionItem.query.count(), 0)
        active_items = _safe_query(
            lambda: SectionItem.query.filter_by(is_active=True).count(), 0
        )

        recent_pages = _safe_query(
            lambda: Page.query.order_by(Page.id.desc()).limit(5).all(), []
        )
        recent_sections = _safe_query(
            lambda: HomepageSection.query.order_by(HomepageSection.id.desc())
            .limit(5)
            .all(),
            [],
        )
        recent_items = _safe_query(
            lambda: SectionItem.query.order_by(SectionItem.id.desc()).limit(5).all(),
            [],
        )

        homepage_path = Path(current_app.root_path) / "templates" / "index.html"
        homepage_last_modified = None
        if homepage_path.exists():
            homepage_last_modified = datetime.fromtimestamp(
                homepage_path.stat().st_mtime
            )

        def _safe_url(endpoint: str, **values):
            try:
                return url_for(endpoint, **values)
            except Exception:  # pragma: no cover - rotas podem não existir
                return None

        quick_actions = [
            {
                "title": "Criar nova página",
                "description": "Publique rapidamente comunicados e conteúdos institucionais.",
                "url": _safe_url("page.create_view"),
            },
            {
                "title": "Gerenciar páginas",
                "description": "Atualize textos existentes e defina o que aparece no menu.",
                "url": _safe_url("page.index_view"),
            },
            {
                "title": "Organizar seções da home",
                "description": "Controle a ordem das áreas em destaque na página inicial.",
                "url": _safe_url("homepagesection.index_view"),
            },
            {
                "title": "Adicionar cartões de destaque",
                "description": "Inclua novos links, notícias e serviços para a população.",
                "url": _safe_url("sectionitem.create_view"),
            },
        ]

        recent_activity = []
        for page in recent_pages:
            recent_activity.append(
                {
                    "label": "Página",
                    "name": page.title,
                    "status": "Visível" if page.visible else "Oculta",
                    "url": _safe_url("page.edit_view", id=page.id),
                }
            )
        for section in recent_sections:
            recent_activity.append(
                {
                    "label": "Seção",
                    "name": section.name,
                    "status": "Ativa" if section.is_active else "Inativa",
                    "url": _safe_url("homepagesection.edit_view", id=section.id),
                }
            )
        for item in recent_items:
            section_name = getattr(item.section, "name", "Seção")
            recent_activity.append(
                {
                    "label": "Cartão",
                    "name": item.title,
                    "status": section_name,
                    "url": _safe_url("sectionitem.edit_view", id=item.id),
                }
            )

        stats = self._to_namespace(
            {
                "pages": {
                    "total": total_pages,
                    "published": published_pages,
                },
                "sections": {
                    "total": total_sections,
                    "active": active_sections,
                },
                "items": {
                    "total": total_items,
                    "active": active_items,
                },
            }
        )

        context = {
            "stats": stats,
            "quick_actions": [action for action in quick_actions if action["url"]],
            "recent_activity": recent_activity[:9],
            "homepage_last_modified": homepage_last_modified,
            "admin_name": self.admin.name,
        }

        return self.render("admin/index.html", **context)


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
                    "summary": {
                        "label": "Resumo",
                        "render_kw": {
                            "placeholder": "Conteúdo exibido no cartão.",
                            "data-ckeditor-height": 220,
                        },
                    },
                    "link_url": {"label": "Endereço do link"},
                    "link_label": {"label": "Texto do link"},
                    "icon_class": {"label": "Ícone (classe CSS)"},
                    "image_url": {
                        "label": "Imagem (URL)",
                        "render_kw": {
                            "data-card-image-input": "1",
                            "placeholder": "Endereço da imagem (opcional)",
                        },
                    },
                    "badge": {"label": "Selo"},
                    "display_date": {"label": "Data exibida"},
                    "display_order": {"label": "Ordem de exibição"},
                    "is_active": {"label": "Ativo"},
                },
                form_widget_args={
                    "title": {
                        "placeholder": "Título exibido ao público",
                    },
                    "link_label": {
                        "placeholder": "Texto do botão ou link",
                    },
                    "link_url": {
                        "placeholder": "https://exemplo.com/pagina",
                    },
                    "icon_class": {
                        "placeholder": "Ex.: fa-solid fa-book",
                    },
                    "image_url": {
                        "placeholder": "Endereço da imagem (opcional)",
                        "data-card-image-input": "1",
                    },
                    "badge": {
                        "placeholder": "Texto do selo destaque",
                    },
                    "display_date": {
                        "placeholder": "Ex.: 12/03/2024",
                    },
                },
                form_overrides={"summary": CKEditorField},
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
    form_overrides = {"summary": CKEditorField}
    form_widget_args = {
        "title": {
            "placeholder": "Título principal exibido no cartão",
        },
        "summary": {
            "placeholder": "Conteúdo rico do cartão",
            "data-ckeditor-height": 260,
        },
        "link_label": {
            "placeholder": "Texto do botão, por exemplo: Saiba mais",
        },
        "link_url": {
            "placeholder": "Cole aqui o endereço que o botão abrirá",
        },
        "icon_class": {
            "placeholder": "Classe CSS do ícone (opcional)",
        },
        "image_url": {
            "placeholder": "URL da imagem ilustrativa (opcional)",
        },
        "badge": {
            "placeholder": "Ex.: Novo, Destaque, Inscrições abertas",
        },
        "display_date": {
            "placeholder": "Texto de data exibido abaixo do selo",
        },
    }
    form_create_rules = form_edit_rules = (
        rules.HTML('<div class="section-item-designer">'),
        rules.FieldSet(
            (
                "section",
                "is_active",
                "title",
                "summary",
                "link_label",
                "link_url",
            ),
            "Conteúdo do cartão",
        ),
        rules.FieldSet(
            (
                "icon_class",
                "image_url",
                "badge",
                "display_date",
                "display_order",
            ),
            "Complementos visuais",
        ),
        rules.HTML(
            "<div class=\"section-item-designer__preview\">"
            "<h4>Pré-visualização em tempo real</h4>"
            "<p>Veja como o cartão será apresentado para os moradores.</p>"
            f"{SECTION_ITEM_PREVIEW_HTML}"
            "</div>"
        ),
        rules.HTML("</div>"),
    )
    extra_css = ("/static/css/admin/section-item-form.css",)
    extra_js = ("/static/js/admin/section-item-form.js",)
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
