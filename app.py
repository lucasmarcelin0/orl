"""Aplicação Flask principal da Prefeitura de Orlândia."""

from __future__ import annotations

from datetime import datetime

import click
from flask import abort, Flask, render_template
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from sqlalchemy.exc import IntegrityError, OperationalError

from admin import init_admin
from config import Config
from models import db, Page
from content.default_pages import DEFAULT_PAGES

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

    def ensure_default_pages() -> None:
        """Garante que as páginas essenciais existam no banco de dados."""

        try:
            db.create_all()
        except OperationalError:
            return

        for page_data in DEFAULT_PAGES:
            try:
                if Page.query.filter_by(slug=page_data["slug"]).first() is None:
                    page = Page(**page_data)
                    db.session.add(page)
            except OperationalError:
                db.session.rollback()
                return

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    with app.app_context():
        ensure_default_pages()

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

        return render_template("index.html")

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
