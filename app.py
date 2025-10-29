"""Aplicação principal da Prefeitura de Orlândia."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template

from admin import admin_bp


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""

    app = Flask(__name__)

    base_dir = Path(__file__).resolve().parent
    app.config.setdefault("SECRET_KEY", os.environ.get("SECRET_KEY", "altere-esta-chave"))
    app.config.setdefault("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "prefeitura"))
    app.config.setdefault("INDEX_TEMPLATE_PATH", base_dir / "templates" / "index.html")

    app.register_blueprint(admin_bp)

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
