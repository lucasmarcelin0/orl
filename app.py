"""Aplicação principal da Prefeitura de Orlândia."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from flask import Flask, render_template
from dotenv import load_dotenv

# 🔹 Carrega as variáveis de ambiente antes de tudo
load_dotenv()

# 🔹 Importa o blueprint administrativo
from admin import admin_bp


def _to_namespace(data: Any) -> Any:
    """Converte estruturas aninhadas em ``SimpleNamespace``.

    Ao transformar dicionários em objetos simples, evitamos conflitos com
    métodos internos como ``dict.items`` e garantimos que o acesso por ponto
    (``obj.attr``) funcione corretamente dentro dos templates Jinja.
    """

    if isinstance(data, dict):
        return SimpleNamespace(**{key: _to_namespace(value) for key, value in data.items()})
    if isinstance(data, list):
        return [_to_namespace(item) for item in data]
    return data


def _load_page_content(content_path: Path, logger) -> SimpleNamespace:
    """Carrega os dados estruturados da página inicial.

    Caso o arquivo não exista ou contenha dados inválidos, devolve um namespace
    vazio para que os templates possam tratar a ausência de conteúdo sem gerar
    erros em tempo de execução.
    """

    if not content_path.exists():
        logger.warning("Arquivo de conteúdo %s não encontrado. Usando dados vazios.", content_path)
        return SimpleNamespace()

    try:
        raw_content = json.loads(content_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Não foi possível carregar o conteúdo da página inicial: %s", error)
        return SimpleNamespace()

    return _to_namespace(raw_content)


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)

    # Caminho base do projeto
    base_dir = Path(__file__).resolve().parent

    # Configurações principais
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "altere-esta-chave")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "prefeitura")
    app.config["INDEX_TEMPLATE_PATH"] = base_dir / "templates" / "index.html"
    app.config["PAGE_CONTENT_PATH"] = base_dir / "content" / "homepage.json"

    # Registro do Blueprint administrativo
    app.register_blueprint(admin_bp)

    # 🔹 Página principal (pública)
    @app.route("/")
    def index() -> str:
        page_content = _load_page_content(Path(app.config["PAGE_CONTENT_PATH"]), app.logger)
        return render_template("index.html", page=page_content)

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
