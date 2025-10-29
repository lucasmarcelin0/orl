"""Aplicação principal da Prefeitura de Orlândia."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template

from admin import admin_bp
from content_store import load_content


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""

    app = Flask(__name__)

    base_dir = Path(__file__).resolve().parent
    app.config.setdefault("SECRET_KEY", os.environ.get("SECRET_KEY", "altere-esta-chave"))
    app.config.setdefault("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "prefeitura"))
    app.config.setdefault("PAGE_CONTENT_PATH", base_dir / "data" / "page_content.json")

    app.register_blueprint(admin_bp)

    @app.route("/")
    def index() -> str:
        content_path = Path(app.config["PAGE_CONTENT_PATH"])
        page_content = load_content(content_path)
        return render_template("index.html", page=page_content)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
