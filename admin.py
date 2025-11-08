"""Configuração do painel administrativo com Flask-Admin."""

from __future__ import annotations

import re
import unicodedata

from datetime import datetime
import uuid
from pathlib import Path
from types import SimpleNamespace

from flask import current_app, redirect, request, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView, filters as sqla_filters
from flask_admin.form import rules
from flask_admin.form.upload import FileUploadField
from flask_admin.menu import MenuLink
from flask_admin.model.form import InlineFormAdmin
from flask_login import current_user
from flask_ckeditor import CKEditorField
from sqlalchemy.exc import OperationalError
from wtforms import HiddenField, PasswordField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from forms import PageForm
import storage
from models import (
    db,
    Document,
    EmergencyService,
    FooterColumn,
    HomepageSection,
    Page,
    QuickLink,
    SectionItem,
    User,
)


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
            <i class=\"fa-solid fa-arrow-right\" aria-hidden=\"true\"></i>
        </a>
    </footer>
</section>
"""


QUICK_LINK_LOCATIONS = (
    (QuickLink.LOCATION_QUICK_ACCESS, "Acesso rápido"),
    (QuickLink.LOCATION_FOOTER, "Rodapé"),
)


class AuthenticatedAdminMixin:
    """Mixin que exige que o usuário esteja autenticado para acessar a view."""

    def is_accessible(self) -> bool:  # type: ignore[override]
        return bool(current_user.is_authenticated and current_user.is_active)

    def inaccessible_callback(self, name: str, **kwargs):  # type: ignore[override]
        login_url = url_for("auth.login", next=request.url)
        return redirect(login_url)


class AdminOnlyMixin(AuthenticatedAdminMixin):
    """Restringe o acesso apenas aos administradores."""

    def is_accessible(self) -> bool:  # type: ignore[override]
        return bool(
            current_user.is_authenticated
            and current_user.is_active
            and getattr(current_user, "is_admin", False)
        )

    def inaccessible_callback(self, name: str, **kwargs):  # type: ignore[override]
        if not current_user.is_authenticated:
            return super().inaccessible_callback(name, **kwargs)
        return redirect(url_for("admin.index"))


class SecuredModelView(AuthenticatedAdminMixin, ModelView):
    """View base que garante segurança e registra autoria das alterações."""

    def on_model_change(self, form, model, is_created):  # type: ignore[override]
        if current_user.is_authenticated:
            if hasattr(model, "updated_by"):
                model.updated_by = current_user
            if is_created and hasattr(model, "created_by"):
                model.created_by = current_user
        return super().on_model_change(form, model, is_created)


class PageAdminView(SecuredModelView):
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


class ProtectedAdminIndexView(AuthenticatedAdminMixin, AdminIndexView):
    """Tela inicial do painel administrativo com autenticação básica."""

    name = "Início"

    def __init__(self, *args, **kwargs):
        """Define um nome em português para a entrada de menu principal."""
        kwargs.setdefault("name", self.name)
        super().__init__(*args, **kwargs)

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
        total_documents = _safe_query(lambda: Document.query.count(), 0)
        active_documents = _safe_query(
            lambda: Document.query.filter_by(is_active=True).count(), 0
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
        recent_documents = _safe_query(
            lambda: Document.query.order_by(Document.id.desc()).limit(5).all(),
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
            {
                "title": "Publicar documento",
                "description": "Disponibilize arquivos oficiais para download imediato.",
                "url": _safe_url("document.create_view"),
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
        for document in recent_documents:
            recent_activity.append(
                {
                    "label": "Documento",
                    "name": document.title,
                    "status": "Publicado" if document.is_active else "Rascunho",
                    "url": _safe_url("document.edit_view", id=document.id),
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
                "documents": {
                    "total": total_documents,
                    "active": active_documents,
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


class HomepageSectionAdminView(SecuredModelView):
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


def _section_filter_options() -> list[tuple[int, str]]:
    """Retorna as opções disponíveis para o filtro de seção."""

    try:
        sections = HomepageSection.query.order_by(HomepageSection.name).all()
    except OperationalError:
        return []

    return [(section.id, section.name) for section in sections]


def _section_item_filter_options() -> list[tuple[int, str]]:
    """Retorna os itens disponíveis para vincular documentos."""

    try:
        items = (
            SectionItem.query.outerjoin(HomepageSection)
            .order_by(SectionItem.title.asc())
            .all()
        )
    except OperationalError:
        return []

    options: list[tuple[int, str]] = []
    for item in items:
        section_name = getattr(item.section, "name", "Sem seção")
        options.append((item.id, f"{section_name} - {item.title}"))
    return options


class CloudinaryUploadField(FileUploadField):
    """Campo de upload que salva arquivos diretamente no Cloudinary."""

    def __init__(self, *args, folder: str, resource_type: str, **kwargs):
        super().__init__(*args, base_path="", **kwargs)
        self._cloudinary_folder = folder
        self._cloudinary_resource_type = resource_type
        self._allow_overwrite = True

    def _save_file(self, data, filename):  # type: ignore[override]
        try:
            return storage.upload_to_cloudinary(
                data,
                filename=filename,
                folder=self._cloudinary_folder,
                resource_type=self._cloudinary_resource_type,
            )
        except storage.StorageError as exc:
            current_app.logger.exception(
                "Falha ao enviar arquivo ao Cloudinary."
            )
            raise ValueError(
                "Não foi possível enviar o arquivo ao armazenamento externo. Tente novamente."
            ) from exc

    def _delete_file(self, filename):  # type: ignore[override]
        storage.delete_cloudinary_asset(
            filename,
            resource_type=self._cloudinary_resource_type,
        )


class DocumentUploadMixin:
    """Funcionalidades compartilhadas para upload e nomenclatura de documentos."""

    def _documents_upload_path(self) -> Path:
        config_path = current_app.config.get("DOCUMENTS_UPLOAD_PATH")
        if not config_path:
            config_path = Path("static") / "uploads" / "documents"
        upload_path = Path(config_path)
        if not upload_path.is_absolute():
            upload_path = Path(current_app.root_path) / upload_path
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    def _allowed_extensions(self) -> set[str]:
        configured = current_app.config.get("DOCUMENTS_ALLOWED_EXTENSIONS") or {"pdf"}
        return {ext.lower() for ext in configured}

    def _generate_filename(self, _model, file_data) -> str:
        extension = Path(file_data.filename or "").suffix.lower()
        if extension:
            extension = extension.lstrip(".")
        else:
            extension = "dat"
        return f"documento-{uuid.uuid4().hex}.{extension}"

    def _build_document_upload_field(self) -> FileUploadField:
        if storage.is_cloudinary_enabled():
            upload_field = CloudinaryUploadField(
                "Arquivo",
                namegen=self._generate_filename,
                allowed_extensions=self._allowed_extensions(),
                folder=current_app.config.get("CLOUDINARY_DOCUMENTS_FOLDER"),
                resource_type="raw",
            )
        else:
            upload_field = FileUploadField(
                "Arquivo",
                base_path=str(self._documents_upload_path()),
                namegen=self._generate_filename,
                allowed_extensions=self._allowed_extensions(),
            )
            upload_field._allow_overwrite = False
            upload_field.allow_overwrite = False
        return upload_field


class DocumentInlineForm(DocumentUploadMixin, InlineFormAdmin):
    """Permite gerenciar documentos diretamente no formulário do item."""

    form_columns = (
        "id",
        "title",
        "description",
        "icon_class",
        "file_path",
        "display_order",
        "is_active",
    )
    form_label = "Documentos"
    form_widget_args = {
        "id": {
            "type": "hidden",
        },
        "title": {
            "placeholder": "Nome exibido aos cidadãos",
        },
        "description": {
            "placeholder": "Complemento opcional exibido abaixo do link",
            "rows": 3,
        },
        "icon_class": {
            "placeholder": "Ex.: fa-solid fa-file-arrow-down",
        },
        "display_order": {
            "placeholder": "0",
        },
    }
    form_args = {
        "title": {"label": "Título"},
        "description": {"label": "Descrição"},
        "icon_class": {"label": "Ícone (classe CSS)"},
        "file_path": {"label": "Arquivo"},
        "display_order": {"label": "Ordem de exibição"},
        "is_active": {"label": "Ativo"},
    }

    def postprocess_form(self, form_class):  # type: ignore[override]
        form_class = super().postprocess_form(form_class)
        form_class.id = HiddenField()
        form_class.file_path = self._build_document_upload_field()
        return form_class


class SectionItemAdminView(SecuredModelView):
    """Administração individual dos cartões que compõem as seções."""

    column_list = ("title", "section", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_filters = (
        sqla_filters.FilterEqual(
            SectionItem.section_id,
            "Seção",
            options=_section_filter_options,
        ),
        sqla_filters.BooleanEqualFilter(SectionItem.is_active, "Ativo"),
    )
    column_formatters = {
        "section": lambda _v, _c, m, _p: getattr(m.section, "name", "-"),
    }
    column_labels = {
        "title": "Título",
        "section": "Seção",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    form_overrides = {"summary": CKEditorField}
    # Comentário: preservamos o campo ``id`` no formulário para satisfazer as
    # regras de layout do Flask-Admin, mas o renderizamos como oculto para que
    # os administradores não o modifiquem manualmente.
    form_widget_args = {
        "id": {
            "type": "hidden",
        },
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
            "data-card-image-input": "1",
        },
        "badge": {
            "placeholder": "Ex.: Novo, Destaque, Inscrições abertas",
        },
        "display_date": {
            "placeholder": "Texto de data exibido abaixo do selo",
        },
    }

    def _bind_image_upload_endpoint(self, form):
        image_field = getattr(form, "image_url", None)
        if not image_field:
            return form

        try:
            endpoint = url_for("upload_section_item_image")
        except Exception:  # pragma: no cover - rota indisponível
            endpoint = None

        render_kw = dict(getattr(image_field, "render_kw", {}) or {})
        render_kw.setdefault("data-card-image-input", "1")
        if endpoint:
            render_kw["data-card-image-endpoint"] = endpoint
        image_field.render_kw = render_kw
        return form

    def create_form(self, obj=None):  # type: ignore[override]
        form = super().create_form(obj)
        return self._bind_image_upload_endpoint(form)

    def edit_form(self, obj=None):  # type: ignore[override]
        form = super().edit_form(obj)
        return self._bind_image_upload_endpoint(form)
    form_create_rules = form_edit_rules = (
        rules.Field("id"),
        rules.HTML(
            "<div class=\"section-item-designer\">"
            "<div class=\"section-item-designer__form\">"
            "<section class=\"section-item-section section-item-section--content\">"
            "<header class=\"section-item-section__header\">"
            "<h3 class=\"section-item-section__title\">Conteúdo do cartão</h3>"
            "<p class=\"section-item-section__description\">"
            "Preencha as informações principais exibidas aos cidadãos."
            "</p>"
            "</header>"
            "<div class=\"section-item-section__body\">"
            "<div class=\"section-item-section__field section-item-section__field--wide\">"
        ),
        rules.Field("section"),
        rules.HTML("</div>"),
        rules.HTML(
            "<div class=\"section-item-section__field section-item-section__field--inline\">"
        ),
        rules.Field("is_active"),
        rules.HTML("</div>"),
        rules.HTML("<div class=\"section-item-section__field\">"),
        rules.Field("title"),
        rules.HTML("</div>"),
        rules.HTML(
            "<div class=\"section-item-section__field section-item-section__field--full\">"
        ),
        rules.Field("summary"),
        rules.HTML("</div>"),
        rules.HTML("<div class=\"section-item-section__field\">"),
        rules.Field("link_label"),
        rules.HTML("</div>"),
        rules.HTML("<div class=\"section-item-section__field\">"),
        rules.Field("link_url"),
        rules.HTML("</div>"),
        rules.HTML("</div></section>"),
        rules.HTML(
            "<section class=\"section-item-section section-item-section--visual\">"
            "<header class=\"section-item-section__header\">"
            "<h3 class=\"section-item-section__title\">Complementos visuais</h3>"
            "<p class=\"section-item-section__description\">"
            "Itens opcionais que reforçam a identidade do cartão."
            "</p>"
            "</header>"
            "<div class=\"section-item-section__body\">"
            "<div class=\"section-item-section__field\">"
        ),
        rules.Field("icon_class"),
        rules.HTML("</div>"),
        rules.HTML(
            "<div class=\"section-item-section__field section-item-section__field--full\">"
        ),
        rules.Field("image_url"),
        rules.HTML("</div>"),
        rules.HTML("<div class=\"section-item-section__field\">"),
        rules.Field("badge"),
        rules.HTML("</div>"),
        rules.HTML("<div class=\"section-item-section__field\">"),
        rules.Field("display_date"),
        rules.HTML("</div>"),
        rules.HTML(
            "<div class=\"section-item-section__field section-item-section__field--small\">"
        ),
        rules.Field("display_order"),
        rules.HTML("</div>"),
        rules.HTML("</div></section>"),
        rules.HTML(
            "<section class=\"section-item-section section-item-section--documents\">"
            "<header class=\"section-item-section__header\">"
            "<h3 class=\"section-item-section__title\">Documentos vinculados</h3>"
            "<p class=\"section-item-section__description\">"
            "Adicione arquivos de apoio relacionados ao conteúdo."
            "</p>"
            "</header>"
            "<div class=\"section-item-section__body\">"
            "<div class=\"section-item-section__field section-item-section__field--full\">"
        ),
        rules.Field("documents"),
        rules.HTML("</div></div></section>"),
        rules.HTML("</div>"),
        rules.HTML(
            "<aside class=\"section-item-designer__preview\">"
            "<h4>Pré-visualização em tempo real</h4>"
            "<p>Veja como o cartão será apresentado para os moradores.</p>"
            f"{SECTION_ITEM_PREVIEW_HTML}"
            "</aside>"
        ),
        rules.HTML("</div>"),
    )
    extra_css = ("/static/css/admin/section-item-form.css",)
    extra_js = ("/static/js/admin/section-item-form.js",)
    form_columns = ("section",) + SECTION_INLINE_FORM_COLUMNS + ("documents",)
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
        "documents": "Documentos",
    }
    inline_models = (DocumentInlineForm(Document),)

    def scaffold_form(self):  # type: ignore[override]
        """Oculta o campo ``id`` para evitar validações indevidas na criação."""

        form_class = super().scaffold_form()
        form_class.id = HiddenField()
        form_class.id.validators = []
        return form_class


class DocumentAdminView(DocumentUploadMixin, SecuredModelView):
    """Gerencia os arquivos disponibilizados para download na página inicial."""

    column_list = ("title", "section_item", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "title": "Título",
        "description": "Descrição",
        "icon_class": "Ícone (classe CSS)",
        "file_path": "Arquivo",
        "section_item": "Item da seção",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    form_columns = (
        "title",
        "description",
        "icon_class",
        "file_path",
        "section_item",
        "display_order",
        "is_active",
    )
    column_formatters = {
        "section_item": lambda _v, _c, m, _p: getattr(m.section_item, "title", "-"),
    }
    column_filters = (
        sqla_filters.BooleanEqualFilter(Document.is_active, "Ativo"),
        sqla_filters.FilterEqual(
            Document.section_item_id,
            "Item da seção",
            options=_section_item_filter_options,
        ),
    )
    column_searchable_list = ("title", "description")
    form_widget_args = {
        "title": {
            "placeholder": "Nome exibido aos cidadãos",
        },
        "description": {
            "placeholder": "Complemento opcional exibido abaixo do link",
            "rows": 3,
        },
        "icon_class": {
            "placeholder": "Ex.: fa-solid fa-file-arrow-down",
        },
        "section_item": {
            "data-placeholder": "Selecione um item para vincular o documento",
        },
        "display_order": {
            "placeholder": "0",
        },
    }
    form_args = {
        "section_item": {
            "label": "Item da seção",
            "allow_blank": True,
        }
    }
    form_ajax_refs = {
        "section_item": {
            "fields": ("title",),
            "page_size": 10,
        }
    }

    def scaffold_form(self):  # type: ignore[override]
        form_class = super().scaffold_form()
        form_class.file_path = self._build_document_upload_field()
        return form_class

    def on_model_delete(self, model):  # type: ignore[override]
        if storage.is_cloudinary_enabled() and getattr(model, "file_path", None):
            storage.delete_cloudinary_asset(model.file_path, resource_type="raw")
        return super().on_model_delete(model)


class FooterColumnAdminView(SecuredModelView):
    """Administra as colunas configuráveis exibidas no rodapé."""

    column_list = ("title", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "title": "Título da coluna",
        "display_order": "Ordem de exibição",
        "is_active": "Ativa",
    }
    form_columns = ("title", "display_order", "is_active")
    column_searchable_list = ("title",)
    column_filters = (
        sqla_filters.BooleanEqualFilter(FooterColumn.is_active, "Ativa"),
    )
    form_widget_args = {
        "title": {
            "placeholder": "Ex.: Serviços online",
        },
        "display_order": {
            "placeholder": "0",
        },
    }


class QuickLinkAdminView(SecuredModelView):
    """Gerencia os atalhos exibidos no acesso rápido e no rodapé."""

    column_list = ("label", "location", "footer_column", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "label": "Texto exibido",
        "url": "Endereço (URL)",
        "location": "Local",
        "footer_column": "Coluna do rodapé",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    column_choices = {
        "location": QUICK_LINK_LOCATIONS,
    }
    column_filters = (
        sqla_filters.FilterEqual(QuickLink.location, "Local", options=QUICK_LINK_LOCATIONS),
        sqla_filters.BooleanEqualFilter(QuickLink.is_active, "Ativo"),
    )
    column_formatters = {
        "footer_column": lambda _v, _c, m, _p: getattr(m.footer_column, "title", "-"),
    }
    column_searchable_list = ("label", "url")
    form_columns = (
        "label",
        "url",
        "location",
        "footer_column",
        "display_order",
        "is_active",
    )
    form_choices = {
        "location": QUICK_LINK_LOCATIONS,
    }
    form_widget_args = {
        "label": {
            "placeholder": "Ex.: Portal da transparência",
        },
        "url": {
            "placeholder": "Cole aqui o endereço completo",
        },
        "display_order": {
            "placeholder": "0",
        },
        "footer_column": {
            "data-placeholder": "Selecione a coluna em que o link será exibido",
        },
    }
    form_args = {
        "footer_column": {
            "label": "Coluna do rodapé",
            "allow_blank": True,
            "blank_text": "Selecione uma coluna",
        }
    }
    form_ajax_refs = {
        "footer_column": {
            "fields": ("title",),
            "page_size": 10,
            "filters": (FooterColumn.is_active.is_(True),),
        }
    }

    def on_model_change(self, form, model: QuickLink, is_created: bool) -> None:  # type: ignore[override]
        if model.location == QuickLink.LOCATION_FOOTER:
            if model.footer_column is None:
                raise ValueError("Selecione uma coluna do rodapé para este link.")
        else:
            model.footer_column = None

        super().on_model_change(form, model, is_created)


class EmergencyServiceAdminView(SecuredModelView):
    """Permite gerenciar os serviços exibidos no painel de emergência."""

    column_list = ("name", "phone", "display_order", "is_active")
    column_default_sort = ("display_order", False)
    column_labels = {
        "name": "Nome do serviço",
        "phone": "Telefone/Contato",
        "description": "Descrição",
        "icon_class": "Ícone (classe CSS)",
        "display_order": "Ordem de exibição",
        "is_active": "Ativo",
    }
    form_columns = (
        "name",
        "phone",
        "description",
        "icon_class",
        "display_order",
        "is_active",
    )
    column_filters = (
        sqla_filters.BooleanEqualFilter(EmergencyService.is_active, "Ativo"),
    )
    column_searchable_list = ("name", "phone", "description")
    form_widget_args = {
        "name": {
            "placeholder": "Ex.: SAMU",
        },
        "phone": {
            "placeholder": "Ex.: 192",
        },
        "icon_class": {
            "placeholder": "Ex.: fa-solid fa-truck-medical",
        },
        "display_order": {
            "placeholder": "0",
        },
        "description": {
            "rows": 3,
        },
    }


class UserAdminView(AdminOnlyMixin, ModelView):
    """Gerencia os usuários responsáveis pelo conteúdo do site."""

    column_list = ("name", "username", "email", "is_admin", "is_active", "last_login_at")
    column_default_sort = ("name", False)
    column_labels = {
        "name": "Nome",
        "username": "Usuário",
        "email": "E-mail",
        "is_admin": "Administrador",
        "is_active": "Ativo",
        "last_login_at": "Último acesso",
    }
    column_searchable_list = ("name", "username", "email")
    column_filters = (
        sqla_filters.BooleanEqualFilter(User.is_admin, "Administrador"),
        sqla_filters.BooleanEqualFilter(User.is_active, "Ativo"),
    )
    column_formatters = {
        "last_login_at": lambda _v, _c, m, _p: m.last_login_at.strftime("%d/%m/%Y %H:%M")
        if m.last_login_at
        else "-",
    }

    form_columns = (
        "name",
        "username",
        "email",
        "is_admin",
        "is_active",
        "password",
        "confirm_password",
    )
    form_overrides = {"email": EmailField}
    form_args = {
        "name": {
            "label": "Nome completo",
            "validators": [DataRequired(), Length(max=150)],
        },
        "username": {
            "label": "Usuário",
            "validators": [DataRequired(), Length(min=3, max=80)],
        },
        "email": {
            "label": "E-mail",
            "validators": [Optional(), Email(), Length(max=255)],
        },
        "is_admin": {"label": "Conceder acesso total"},
        "is_active": {"label": "Usuário ativo"},
    }
    form_extra_fields = {
        "password": PasswordField(
            "Senha",
            validators=[Optional(), Length(min=6, max=128)],
            description="Informe uma senha temporária para o colaborador.",
        ),
        "confirm_password": PasswordField(
            "Confirmar senha",
            validators=[Optional(), EqualTo("password", message="As senhas não conferem.")],
        ),
    }
    can_view_details = True

    def is_visible(self):  # type: ignore[override]
        return bool(
            current_user.is_authenticated
            and getattr(current_user, "is_admin", False)
        )

    def on_model_change(self, form, model: User, is_created: bool) -> None:  # type: ignore[override]
        password = form.password.data or ""
        if is_created and not password:
            raise ValueError("Defina uma senha inicial para o usuário.")
        if password:
            model.set_password(password)

        model.name = (model.name or "").strip()
        model.username = (model.username or "").strip().lower()
        model.email = ((model.email or "").strip().lower()) or None

        return super().on_model_change(form, model, is_created)


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
    admin.add_view(
        DocumentAdminView(
            Document,
            db.session,
            category="Página inicial",
            name="Documentos",
        )
    )
    admin.add_view(
        FooterColumnAdminView(
            FooterColumn,
            db.session,
            category="Página inicial",
            name="Colunas do rodapé",
        )
    )
    admin.add_view(
        QuickLinkAdminView(
            QuickLink,
            db.session,
            category="Página inicial",
            name="Acesso rápido e rodapé",
        )
    )
    admin.add_view(
        EmergencyServiceAdminView(
            EmergencyService,
            db.session,
            category="Página inicial",
            name="Serviços de emergência",
        )
    )
    admin.add_view(
        UserAdminView(
            User,
            db.session,
            category="Equipe",
            name="Usuários do sistema",
        )
    )

    admin.add_link(MenuLink(name="Meu perfil", endpoint="admin_profile"))
    admin.add_link(MenuLink(name="Sair", endpoint="auth.logout"))

    return admin
