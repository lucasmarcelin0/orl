"""Aplicação Flask principal da Prefeitura de Orlândia."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import json
from pathlib import Path
from typing import Iterable

import click
from flask import abort, Flask, render_template, url_for
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from sqlalchemy.exc import OperationalError

from admin import init_admin
from config import Config
from models import db, HomepageSection, Page, SectionItem

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

    # Comentário: prepara o painel administrativo com autenticação básica.
    init_admin(app)

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

    with app.app_context():
        ensure_homepage_sections()

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

        service_links = [
            {"label": "Licitações", "url": url_for("licitacoes")},
            {"label": "Concursos", "url": url_for("concursos")},
            {"label": "IPTU Online", "url": url_for("iptu_online")},
            {"label": "Alvarás", "url": url_for("alvaras")},
        ]

        return {
            "pages": visible_pages,
            "page_columns": _chunk_pages(visible_pages, columns=3),
            "admin_navigation": admin_navigation,
            "admin_index_url": admin_index_url,
            "service_links": service_links,
            "current_year": datetime.utcnow().year,
        }

    @app.route("/")
    def index() -> str:
        """Rota principal que exibe a página inicial estática."""

        try:
            sections = (
                HomepageSection.query.filter_by(is_active=True)
                .order_by(HomepageSection.display_order)
                .all()
            )
        except OperationalError:
            sections = []

        sections_map = {section.section_type: section for section in sections}
        custom_sections = [
            section
            for section in sections
            if section.section_type not in {"services", "news", "transparency"}
        ]

        return render_template(
            "index.html",
            sections=sections,
            sections_map=sections_map,
            custom_sections=custom_sections,
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
            db.create_all()
            click.echo("Banco de dados verificado com sucesso.")
        app.run(host=host, port=port, debug=debug)

    return app


# Comentário: instância utilizada por servidores WSGI ou pelo Flask CLI.
app = create_app()


if __name__ == "__main__":
    # Comentário: execução direta do módulo para ambientes de desenvolvimento.
    with app.app_context():
        db.create_all()
    app.run(debug=True)
