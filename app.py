"""Aplicação principal da Prefeitura de Orlândia."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

from types import SimpleNamespace
from typing import Any

from flask import Flask, render_template
from dotenv import load_dotenv
from flask import Flask, render_template

# 🔹 Carrega as variáveis de ambiente antes de tudo
load_dotenv()

# 🔹 Importa o blueprint administrativo
from admin import admin_bp

RouteSpec = Tuple[str, str, str]


def register_simple_routes(app: Flask, routes: Iterable[RouteSpec]) -> None:
    """Registra rotas simples que renderizam templates estáticos."""
    for endpoint, rule, template_name in routes:
        app.add_url_rule(
            rule,
            endpoint,
            lambda template_name=template_name: render_template(template_name),
        )


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

    content_routes: Iterable[RouteSpec] = [
        ("historia", "/historia", "historia.html"),
        ("dados_municipio", "/dados-do-municipio", "dados_municipio.html"),
        ("prefeito", "/prefeito", "prefeito.html"),
        ("vice_prefeito", "/vice-prefeito", "vice_prefeito.html"),
        ("hino", "/hino", "hino.html"),
        ("fotos_antigas", "/fotos-antigas", "fotos_antigas.html"),
        ("fotos_recentes", "/fotos-recentes", "fotos_recentes.html"),
        ("galeria_imagens", "/galeria-de-imagens", "galeria_imagens.html"),
        ("como_chegar", "/como-chegar", "como_chegar.html"),
        ("enderecos_publicos", "/enderecos-publicos", "enderecos_publicos.html"),
        ("turismo", "/turismo", "turismo.html"),
        ("leis", "/leis", "leis.html"),
        ("concursos", "/concursos", "concursos.html"),
        ("processos_seletivos", "/processos-seletivos", "processos_seletivos.html"),
        ("decretos", "/decretos", "decretos.html"),
        ("licitacoes_carta_convite", "/licitacoes/carta-convite", "licitacoes/carta_convite.html"),
        ("licitacoes_chamada_publica", "/licitacoes/chamada-publica", "licitacoes/chamada_publica.html"),
        ("licitacoes_pregao_eletronico", "/licitacoes/pregao-eletronico", "licitacoes/pregao_eletronico.html"),
        ("servicos_curriculo_paulista", "/servicos/curriculo-paulista", "servicos/curriculo_paulista.html"),
        ("servicos_banco_dados_ambiental", "/servicos/banco-de-dados-ambiental", "servicos/banco_dados_ambiental.html"),
        ("servicos_cadastro_tributario", "/servicos/cadastro-tributario", "servicos/cadastro_tributario.html"),
        ("servicos_nota_fiscal", "/servicos/nota-fiscal", "servicos/nota_fiscal.html"),
        ("servicos_links_uteis", "/servicos/links-uteis", "servicos/links_uteis.html"),
        ("servicos_servidor_publico", "/servicos/servidor-publico", "servicos/servidor_publico.html"),
        ("servicos_plano_mobilidade", "/servicos/plano-de-mobilidade", "servicos/plano_mobilidade.html"),
        ("servicos_plano_educacao", "/servicos/plano-de-educacao", "servicos/plano_educacao.html"),
        ("servicos_plano_residuos", "/servicos/plano-de-residuos", "servicos/plano_residuos.html"),
        ("servicos_plano_saneamento", "/servicos/plano-de-saneamento", "servicos/plano_saneamento.html"),
        ("servicos_contorno2022", "/servicos/contorno-2022", "servicos/contorno2022.html"),
        ("parceria", "/parcerias-e-editais", "parceria.html"),
    ]

    register_simple_routes(app, content_routes)

    # 🔹 Página principal (pública)
    @app.route("/")
    def index() -> str:
        page_content = _load_page_content(Path(app.config["PAGE_CONTENT_PATH"]), app.logger)
        return render_template("index.html", page=page_content)

    @app.context_processor
    def inject_defaults() -> dict[str, int]:
        return {"current_year": datetime.now().year}

    # 🔹 Rota de fallback para erros
    @app.errorhandler(404)
    def page_not_found(e):  # type: ignore[override]
        return render_template("404.html"), 404

    return app


# Cria a aplicação
app = create_app()

if __name__ == "__main__":
    # Executa o servidor Flask
    app.run(debug=True)
