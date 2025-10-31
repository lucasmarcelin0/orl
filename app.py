"""Aplicação Flask principal da Prefeitura de Orlândia."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Iterable
import uuid

import click
from flask import (
    abort,
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from sqlalchemy import inspect, or_, text
from sqlalchemy.exc import OperationalError
from werkzeug.utils import secure_filename

from admin import init_admin
from config import Config

from models import (
    db,
    EmergencyService,
    Document,
    FooterColumn,
    HomepageSection,
    Page,
    QuickLink,
    SectionItem,
)

# Comentário: extensões globais reutilizadas pela aplicação.
migrate = Migrate()
ckeditor = CKEditor()


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""

    app = Flask(__name__)
    app.config.from_object(Config)

    # Comentário: inicialização das extensões com as configurações carregadas.
    db.init_app(app)
    migrate.init_app(app, db)
    ckeditor.init_app(app)

    def ensure_database_schema() -> None:
        """Garante a existência das colunas esperadas em instalações antigas."""

        try:
            db.create_all()
        except OperationalError:
            return

        try:
            engine = db.session.get_bind()
        except OperationalError:
            return
        if engine is None:
            return

        inspector = inspect(engine)
        try:
            document_columns = {
                column["name"] for column in inspector.get_columns("document")
            }
        except Exception:  # pragma: no cover - fallback defensivo
            document_columns = set()

        if document_columns and "section_item_id" not in document_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE document ADD COLUMN section_item_id INTEGER")
                )

        try:
            quick_link_columns = {
                column["name"] for column in inspector.get_columns("quick_link")
            }
        except Exception:  # pragma: no cover - tabela inexistente em instalações novas
            quick_link_columns = set()

        if quick_link_columns and "footer_column_id" not in quick_link_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE quick_link ADD COLUMN footer_column_id INTEGER")
                )

    def ensure_homepage_sections() -> None:
        """Carrega um conteúdo inicial da home quando o banco está vazio."""

        data_file = Path(app.root_path) / "content" / "homepage.json"
        if not data_file.exists():
            return

        try:
            db.create_all()
        except OperationalError:
            return

        try:
            has_sections = HomepageSection.query.count() > 0
        except OperationalError:
            # Comentário: tabelas ainda não foram criadas.
            return

        if has_sections:
            return

        raw_data = json.loads(data_file.read_text(encoding="utf-8"))
        sections_data = raw_data.get("sections", [])

        for order, section_data in enumerate(sections_data):
            section = HomepageSection(
                name=section_data.get("title", "Seção"),
                slug=section_data.get("id", f"secao-{order}"),
                description=section_data.get("description"),
                section_type=section_data.get("id", "custom"),
                display_order=order,
                is_active=True,
            )
            db.session.add(section)

            default_label = "Acessar"
            if section.section_type == "news":
                default_label = "Leia mais"
            elif section.section_type == "transparency":
                default_label = "Consultar"

            for item_order, item_data in enumerate(section_data.get("items", [])):
                item = SectionItem(
                    section=section,
                    title=item_data.get("title", "Item"),
                    summary=item_data.get("description"),
                    link_url=item_data.get("url"),
                    link_label=item_data.get("link_label") or default_label,
                    icon_class=item_data.get("icon"),
                    image_url=item_data.get("image"),
                    badge=item_data.get("badge"),
                    display_date=item_data.get("date"),
                    display_order=item_order,
                    is_active=True,
                )
                db.session.add(item)

        db.session.commit()

    def ensure_emergency_services() -> None:
        """Popula serviços de emergência padrão em instalações novas."""

        defaults = [
            {
                "name": "SAMU",
                "phone": "192",
                "icon_class": "fas fa-ambulance",
            },
            {
                "name": "Bombeiros",
                "phone": "193",
                "icon_class": "fas fa-fire-extinguisher",
            },
            {
                "name": "Polícia Militar",
                "phone": "190",
                "icon_class": "fas fa-shield-alt",
            },
            {
                "name": "Pronto Socorro",
                "phone": "(16) 3820-2000",
                "icon_class": "fas fa-hospital",
            },
        ]

        try:
            db.create_all()
        except OperationalError:
            return

        try:
            has_services = EmergencyService.query.count() > 0
        except OperationalError:
            return

        if has_services:
            return

        for order, data in enumerate(defaults):
            db.session.add(
                EmergencyService(
                    name=data.get("name", "Serviço"),
                    phone=data.get("phone"),
                    icon_class=data.get("icon_class"),
                    display_order=order,
                    is_active=True,
                )
            )

        db.session.commit()

    with app.app_context():
        ensure_database_schema()
        init_admin(app)
        ensure_homepage_sections()
        ensure_emergency_services()

    def _resolve_upload_path() -> Path:
        upload_path = Path(app.config.get("CKEDITOR_UPLOADS_PATH", "static/uploads"))
        if not upload_path.is_absolute():
            upload_path = Path(app.root_path) / upload_path
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    def _allowed_file(filename: str) -> bool:
        allowed_extensions = app.config.get("CKEDITOR_ALLOWED_IMAGE_EXTENSIONS", set())
        if not filename or "." not in filename:
            return False
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in {ext.lower() for ext in allowed_extensions}

    @app.route("/admin/ckeditor/uploads/<path:filename>")
    def ckeditor_uploaded_file(filename: str):
        upload_path = _resolve_upload_path()
        return send_from_directory(str(upload_path), filename)

    @app.route("/admin/ckeditor/upload", methods=["POST"])
    def upload_ckeditor_image():
        upload = request.files.get("upload")
        if upload is None or upload.filename == "":
            return (
                jsonify({"uploaded": 0, "error": {"message": "Nenhum arquivo foi enviado."}}),
                400,
            )

        if not _allowed_file(upload.filename):
            return (
                jsonify(
                    {
                        "uploaded": 0,
                        "error": {
                            "message": "Formato de arquivo não suportado. Utilize imagens PNG, JPG, JPEG, GIF ou WEBP.",
                        },
                    }
                ),
                400,
            )

        max_size = app.config.get("CKEDITOR_MAX_IMAGE_SIZE")
        if max_size:
            upload.stream.seek(0, os.SEEK_END)
            file_size = upload.stream.tell()
            upload.stream.seek(0)
            if file_size > max_size:
                return (
                    jsonify(
                        {
                            "uploaded": 0,
                            "error": {
                                "message": "Imagem excede o tamanho máximo permitido de 5 MB.",
                            },
                        }
                    ),
                    413,
                )

        secure_name = secure_filename(upload.filename)
        if not secure_name:
            return (
                jsonify({"uploaded": 0, "error": {"message": "Nome de arquivo inválido."}}),
                400,
            )

        extension = secure_name.rsplit(".", 1)[1].lower()
        unique_name = f"ckeditor-{uuid.uuid4().hex}.{extension}"
        upload_path = _resolve_upload_path()
        destination = upload_path / unique_name
        upload.save(destination)

        file_url = url_for("ckeditor_uploaded_file", filename=unique_name)
        return jsonify({"uploaded": 1, "fileName": unique_name, "url": file_url})

    def _chunk_pages(pages: Iterable[Page], columns: int = 3) -> list[list[Page]]:
        pages = list(pages)
        if not pages:
            return []

        columns = max(1, columns)
        per_column = max(1, (len(pages) + columns - 1) // columns)
        return [pages[i : i + per_column] for i in range(0, len(pages), per_column)]

    @app.context_processor
    def inject_navigation_pages() -> dict[str, object]:
        """Disponibiliza as páginas e links auxiliares em todos os templates."""

        try:
            visible_pages = Page.query.filter_by(visible=True).order_by(Page.title).all()
        except OperationalError:
            # Comentário: primeira execução pode ocorrer antes da criação das tabelas.
            visible_pages = []

        admin_navigation: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        admin_index_url = None

        admin_ext = app.extensions.get("admin", [])
        if admin_ext:
            admin = admin_ext[0]
            for view in admin._views:
                endpoint = getattr(view, "endpoint", None)
                if not endpoint:
                    continue

                view_endpoint = f"{endpoint}.index_view"
                try:
                    view_url = url_for(view_endpoint)
                except Exception:  # pragma: no cover - fallback seguro
                    continue

                if endpoint == "admin":
                    admin_index_url = view_url

                category = view.category or "Painel administrativo"
                admin_navigation.setdefault(category, []).append(
                    {"name": view.name, "url": view_url}
                )

        if admin_index_url is None:
            try:
                admin_index_url = url_for("admin.index")
            except Exception:  # pragma: no cover - rota indisponível
                admin_index_url = None

        try:
            quick_access_links = (
                QuickLink.query.filter(
                    QuickLink.location == QuickLink.LOCATION_QUICK_ACCESS,
                    QuickLink.is_active.isnot(False),
                )
                .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                .all()
            )
            quick_access_configured = (
                QuickLink.query.filter_by(location=QuickLink.LOCATION_QUICK_ACCESS).count()
                > 0
            )
        except OperationalError:
            quick_access_links = []
            quick_access_configured = False

        if not quick_access_links and not quick_access_configured:
            quick_access_links = [
                {"label": "Editais e Licitações", "url": url_for("licitacoes")},
                {"label": "Concursos Públicos", "url": url_for("concursos")},
                {"label": "IPTU Online", "url": url_for("iptu_online")},
                {"label": "Alvarás", "url": url_for("alvaras")},
            ]

        try:
            footer_columns = (
                FooterColumn.query.filter(FooterColumn.is_active.isnot(False))
                .order_by(FooterColumn.display_order.asc(), FooterColumn.id.asc())
                .all()
            )
        except OperationalError:
            footer_columns = []

        footer_columns_payload = []

        if footer_columns:
            column_ids = [column.id for column in footer_columns]

            if column_ids:
                try:
                    footer_links = (
                        QuickLink.query.filter(
                            QuickLink.location == QuickLink.LOCATION_FOOTER,
                            QuickLink.is_active.isnot(False),
                            QuickLink.footer_column_id.in_(column_ids),
                        )
                        .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                        .all()
                    )
                except OperationalError:
                    footer_links = []
            else:
                footer_links = []

            links_by_column: dict[int | None, list[QuickLink]] = {
                column_id: [] for column_id in column_ids
            }
            for link in footer_links:
                links_by_column.setdefault(link.footer_column_id, []).append(link)

            for column in footer_columns:
                footer_columns_payload.append(
                    {
                        "title": column.title,
                        "links": links_by_column.get(column.id, []),
                    }
                )
        else:
            try:
                legacy_footer_links = (
                    QuickLink.query.filter(
                        QuickLink.location == QuickLink.LOCATION_FOOTER,
                        QuickLink.is_active.isnot(False),
                        QuickLink.footer_column_id.is_(None),
                    )
                    .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                    .all()
                )
                legacy_configured = (
                    QuickLink.query.filter_by(
                        location=QuickLink.LOCATION_FOOTER
                    ).count()
                    > 0
                )
            except OperationalError:
                legacy_footer_links = []
                legacy_configured = False

            if legacy_footer_links:
                footer_columns_payload = [
                    {"title": "Serviços online", "links": legacy_footer_links}
                ]
            elif not legacy_configured:
                footer_columns_payload = [
                    {
                        "title": "Serviços online",
                        "links": [
                            {"label": "Licitações", "url": url_for("licitacoes")},
                            {"label": "Concursos", "url": url_for("concursos")},
                            {"label": "IPTU Online", "url": url_for("iptu_online")},
                            {"label": "Alvarás", "url": url_for("alvaras")},
                        ],
                    }
                ]
            else:
                footer_columns_payload = [
                    {"title": "Serviços online", "links": []}
                ]

        return {
            "pages": visible_pages,
            "page_columns": _chunk_pages(visible_pages, columns=3),
            "admin_navigation": admin_navigation,
            "admin_index_url": admin_index_url,
            "footer_columns": footer_columns_payload,
            "quick_access_links": quick_access_links,
            "current_year": datetime.utcnow().year,
        }

    @app.route("/")
    def index() -> str:
        """Rota principal que exibe a página inicial estática."""

        try:
            sections = (
                HomepageSection.query.filter_by(is_active=True)
                .order_by(
                    HomepageSection.display_order.asc(),
                    HomepageSection.id.asc(),
                )
                .all()
            )
        except OperationalError:
            sections = []

        try:
            emergency_services = (
                EmergencyService.query.filter_by(is_active=True)
                .order_by(
                    EmergencyService.display_order.asc(),
                    EmergencyService.name.asc(),
                )
                .all()
            )
        except OperationalError:
            emergency_services = []

        return render_template(
            "index.html",
            sections=sections,
            emergency_services=emergency_services,
        )

    @app.route("/buscar")
    def search() -> str:
        """Permite localizar páginas, serviços e documentos pelo termo informado."""

        query = (request.args.get("q", "") or "").strip()
        if not query:
            return redirect(url_for("index"))

        search_pattern = f"%{query}%"

        try:
            page_results = (
                Page.query.filter(Page.visible.is_(True))
                .filter(
                    or_(
                        Page.title.ilike(search_pattern),
                        Page.content.ilike(search_pattern),
                    )
                )
                .order_by(Page.title.asc())
                .all()
            )
        except OperationalError:
            page_results = []

        try:
            section_item_results = (
                SectionItem.query.join(HomepageSection)
                .filter(
                    HomepageSection.is_active.is_(True),
                    SectionItem.is_active.is_(True),
                    or_(
                        SectionItem.title.ilike(search_pattern),
                        SectionItem.summary.ilike(search_pattern),
                        SectionItem.badge.ilike(search_pattern),
                        SectionItem.display_date.ilike(search_pattern),
                    ),
                )
                .order_by(
                    HomepageSection.display_order.asc(),
                    SectionItem.display_order.asc(),
                    SectionItem.id.asc(),
                )
                .all()
            )
        except OperationalError:
            section_item_results = []

        try:
            document_results = (
                Document.query.join(SectionItem)
                .join(HomepageSection)
                .filter(
                    Document.is_active.is_(True),
                    SectionItem.is_active.is_(True),
                    HomepageSection.is_active.is_(True),
                    or_(
                        Document.title.ilike(search_pattern),
                        Document.description.ilike(search_pattern),
                    ),
                )
                .order_by(Document.display_order.asc(), Document.title.asc())
                .all()
            )
        except OperationalError:
            document_results = []

        total_results = (
            len(page_results)
            + len(section_item_results)
            + len(document_results)
        )

        return render_template(
            "search_results.html",
            query=query,
            page_results=page_results,
            section_item_results=section_item_results,
            document_results=document_results,
            total_results=total_results,
        )

    @app.route("/destaques/<int:item_id>")
    def home_item_detail(item_id: int) -> str:
        """Exibe uma página detalhada para itens das seções da página inicial."""

        try:
            item = SectionItem.query.get(item_id)
        except OperationalError:
            abort(404)

        if item is None or item.section is None:
            abort(404)

        if item.section.section_type == "news":
            abort(404)

        return render_template("home_item_detail.html", item=item)

    @app.route("/licitacoes")
    def licitacoes() -> str:
        """Disponibiliza a página com os editais e processos licitatórios."""

        return render_template("licitacoes/index.html")

    @app.route("/concursos")
    def concursos() -> str:
        """Exibe as informações sobre concursos públicos vigentes."""

        return render_template("concursos.html")

    @app.route("/iptu-online")
    def iptu_online() -> str:
        """Apresenta os serviços disponíveis para o IPTU online."""

        return render_template("iptu_online.html")

    @app.route("/alvaras")
    def alvaras() -> str:
        """Fornece orientações sobre emissão e renovação de alvarás."""

        return render_template("alvaras.html")

    @app.route("/transparencia/plano-plurianual")
    def plano_plurianual() -> str:
        """Disponibiliza os principais documentos do Plano Plurianual."""

        return render_template("transparencia/plano_plurianual.html")

    @app.route("/transparencia/relatorios-gestao")
    def relatorios_gestao() -> str:
        """Apresenta os relatórios anuais de gestão do município."""

        return render_template("transparencia/relatorios_gestao.html")

    @app.route("/transparencia/gastos-covid-19")
    def gastos_covid19() -> str:
        """Exibe dados sobre despesas realizadas no enfrentamento à COVID-19."""

        return render_template("transparencia/gastos_covid19.html")

    @app.route("/transparencia/pesquisa-satisfacao")
    def pesquisa_satisfacao() -> str:
        """Disponibiliza formulários e resultados das pesquisas de satisfação."""

        return render_template("transparencia/pesquisa_satisfacao.html")

    @app.route("/transparencia/lista-obras")
    def lista_obras() -> str:
        """Reúne as informações das obras públicas em andamento e concluídas."""

        return render_template("transparencia/lista_obras.html")

    @app.route("/transparencia/iluminacao-publica")
    def iluminacao_publica() -> str:
        """Traz relatórios e canais de atendimento da iluminação pública."""

        return render_template("transparencia/iluminacao_publica.html")

    @app.route("/noticias/<int:item_id>")
    def news_detail(item_id: int) -> str:
        """Mostra o conteúdo completo de uma notícia cadastrada na home."""

        try:
            item = SectionItem.query.get(item_id)
        except OperationalError:
            abort(404)

        if item is None or item.section is None or item.section.section_type != "news":
            abort(404)

        return render_template("news_detail.html", item=item)

    @app.route("/<slug>")
    def show_page(slug: str) -> str:
        """Exibe o conteúdo dinâmico associado ao slug informado."""

        try:
            page = Page.query.filter_by(slug=slug).first()
        except OperationalError:
            # Comentário: quando o banco ainda não foi inicializado, evita erro 500.
            abort(404)

        if page is None:
            abort(404)
        return render_template("dynamic_page.html", page=page)

    @app.errorhandler(404)
    def handle_not_found(_: Exception) -> tuple[str, int]:
        """Exibe uma página personalizada para recursos inexistentes."""

        return render_template("404.html"), 404

    @app.errorhandler(500)
    def handle_internal_error(_: Exception) -> tuple[str, int]:
        """Garante mensagem em português quando ocorrer erro interno."""

        return render_template("500.html"), 500

    @app.cli.command("bootstrap-app")
    @click.option("--host", default="127.0.0.1", help="Host de execução do servidor.")
    @click.option("--port", default=5000, help="Porta em que o servidor ficará disponível.")
    @click.option("--debug/--no-debug", default=True, help="Ativa ou não o modo debug.")
    def bootstrap_app(host: str, port: int, debug: bool) -> None:
        """Cria o banco de dados (caso não exista) e inicia a aplicação."""

        with app.app_context():
            ensure_database_schema()
            click.echo("Banco de dados verificado com sucesso.")
        app.run(host=host, port=port, debug=debug)

    return app


# Comentário: instância utilizada por servidores WSGI ou pelo Flask CLI.
app = create_app()


if __name__ == "__main__":
    # Comentário: execução direta do módulo para ambientes de desenvolvimento.
    app.run(debug=True)
