"""Aplicação Flask principal da Prefeitura de Orlândia."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import click
from flask import abort, Flask, render_template
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

    @app.context_processor
    def inject_navigation_pages() -> dict[str, object]:
        """Disponibiliza as páginas visíveis e o ano atual em todos os templates."""

        try:
            visible_pages = Page.query.filter_by(visible=True).order_by(Page.title).all()
        except OperationalError:
            # Comentário: primeira execução pode ocorrer antes da criação das tabelas.
            visible_pages = []
        return {
            "pages": visible_pages,
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
