"""Aplicação principal da Prefeitura de Orlândia."""

from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, render_template
from dotenv import load_dotenv

# 🔹 Carrega as variáveis de ambiente antes de tudo
load_dotenv()

# 🔹 Importa o blueprint administrativo
from admin import admin_bp


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)

    # Caminho base do projeto
    base_dir = Path(__file__).resolve().parent

    # Configurações principais
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "altere-esta-chave")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "prefeitura")
    app.config["INDEX_TEMPLATE_PATH"] = base_dir / "templates" / "index.html"

    # Registro do Blueprint administrativo
    app.register_blueprint(admin_bp)

    # 🔹 Página principal (pública)
    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    # 🔹 Rota de fallback para erros
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    return app


# Cria a aplicação
app = create_app()

if __name__ == "__main__":
    # Executa o servidor Flask
    app.run(debug=True)
