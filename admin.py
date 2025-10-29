"""Módulo responsável pela área administrativa do site."""

from __future__ import annotations

from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from content_store import create_backup, load_content, save_content


admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")


def _get_content_path() -> Path:
    """Retorna o caminho completo do arquivo JSON com o conteúdo público."""

    path = current_app.config.get("PAGE_CONTENT_PATH")
    if path is None:
        raise RuntimeError("PAGE_CONTENT_PATH não está configurado na aplicação.")
    return Path(path)


def _load_page_content() -> Dict[str, Any]:
    """Lê o conteúdo atual do site."""

    path = _get_content_path()
    return load_content(path)


def _save_page_content(data: Dict[str, Any]) -> None:
    """Persiste as alterações realizadas no painel."""

    path = _get_content_path()
    backups_dir = Path(current_app.root_path) / "backups"
    if path.exists():
        create_backup(path, backups_dir)
    save_content(path, data)


def _get_last_modified() -> Optional[datetime]:
    """Retorna a data da última modificação do arquivo de conteúdo."""

    path = _get_content_path()
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def _get_last_backup() -> Optional[Path]:
    """Obtém o backup mais recente disponível."""

    backup_dir = Path(current_app.root_path) / "backups"
    if not backup_dir.exists():
        return None

    backups = sorted(backup_dir.glob("page_content_*.json"), reverse=True)
    return backups[0] if backups else None


def _find_section(sections: List[Dict[str, Any]], section_id: str) -> Optional[Dict[str, Any]]:
    for section in sections:
        if section.get("id") == section_id:
            return section
    return None


def _normalize_sections(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = data.setdefault("sections", [])
    if not isinstance(sections, list):
        raise ValueError("Estrutura inválida: 'sections' deve ser uma lista.")
    return sections


def _create_section(section_type: str) -> Dict[str, Any]:
    base: Dict[str, Any] = {"id": str(uuid4()), "type": section_type}
    if section_type == "hero":
        base.update(
            {
                "title": "Novo destaque",
                "subtitle": "Apresente a principal mensagem da prefeitura.",
                "background_image": "",
                "primary_text": "Saiba mais",
                "primary_url": "#",
                "secondary_text": "",
                "secondary_url": "",
            }
        )
    elif section_type == "text":
        base.update(
            {
                "title": "Título da seção",
                "body": "Descreva as informações importantes para o cidadão.",
                "alignment": "left",
            }
        )
    elif section_type == "image":
        base.update(
            {
                "title": "Imagem em destaque",
                "body": "Explique o contexto da imagem e adicione um link se necessário.",
                "image_url": "",
                "image_alt": "",
                "link_text": "",
                "link_url": "",
                "alignment": "right",
            }
        )
    elif section_type == "cta":
        base.update(
            {
                "title": "Chamada para ação",
                "body": "Convide o cidadão a realizar um procedimento específico.",
                "button_text": "Acessar",
                "button_url": "#",
            }
        )
    elif section_type == "list":
        base.update(
            {
                "title": "Lista de links",
                "body": "Organize atalhos úteis separando um por linha.",
                "items": [],
            }
        )
    elif section_type == "custom":
        base.update(
            {
                "title": "Bloco personalizado",
                "html": "<p>Insira aqui um conteúdo mais avançado.</p>",
            }
        )
    else:
        raise ValueError("Tipo de bloco desconhecido.")
    return base


def _parse_list_items(raw_items: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for line in raw_items.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            items.append({"label": line, "url": "#"})
            continue
        label, url = line.split("|", 1)
        items.append({"label": label.strip(), "url": url.strip()})
    return items


def _is_authenticated() -> bool:
    return bool(session.get("admin_authenticated"))


def login_required(view: Callable) -> Callable:
    """Decorator para restringir acesso às rotas administrativas."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not _is_authenticated():
            next_url = request.url if request.method == "GET" else url_for("admin.dashboard")
            return redirect(url_for("admin.login", next=next_url))
        return view(*args, **kwargs)

    return wrapped_view


@admin_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    """Realiza a autenticação simples dos colaboradores."""

    if _is_authenticated():
        return redirect(url_for("admin.dashboard"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        expected_password = current_app.config.get("ADMIN_PASSWORD", "")

        if password == expected_password:
            session["admin_authenticated"] = True
            session.permanent = True
            flash("Login realizado com sucesso!", "success")
            next_url = request.args.get("next") or url_for("admin.dashboard")
            return redirect(next_url)

        error = "Senha inválida. Tente novamente."
        flash(error, "error")

    return render_template("admin/login.html", error=error)


@admin_bp.route("/admin/logout")
def logout():
    """Encerra a sessão administrativa."""

    session.pop("admin_authenticated", None)
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.route("/admin", methods=["GET", "POST"])
@login_required
def dashboard():
    """Tela principal do painel administrativo."""

    try:
        page_data = _load_page_content()
    except ValueError as error:  # pragma: no cover - apenas para feedback
        flash(str(error), "error")
        page_data = {"title": "Página inicial", "description": "", "sections": []}

    page_data.setdefault("title", "Página inicial")
    page_data.setdefault("description", "")
    sections = _normalize_sections(page_data)
    last_modified = _get_last_modified()
    last_backup = _get_last_backup()

    if request.method == "POST":
        action = request.form.get("action")
        section_id = request.form.get("section_id")

        try:
            if action == "update_page":
                page_data["title"] = request.form.get("page_title", "Página inicial").strip()
                page_data["description"] = request.form.get("page_description", "").strip()
                _save_page_content(page_data)
                flash("Informações gerais atualizadas com sucesso!", "success")
            elif action == "add_section":
                section_type = request.form.get("section_type", "")
                new_section = _create_section(section_type)
                sections.append(new_section)
                _save_page_content(page_data)
                flash("Novo bloco adicionado. Personalize os campos e salve.", "success")
            elif action == "delete_section" and section_id:
                section = _find_section(sections, section_id)
                if not section:
                    raise ValueError("Bloco não encontrado.")
                sections.remove(section)
                _save_page_content(page_data)
                flash("Bloco removido com sucesso.", "success")
            elif action == "move_up" and section_id:
                index = next((i for i, sec in enumerate(sections) if sec.get("id") == section_id), None)
                if index is None or index == 0:
                    raise ValueError("Não é possível mover este bloco para cima.")
                sections[index - 1], sections[index] = sections[index], sections[index - 1]
                _save_page_content(page_data)
                flash("Ordem atualizada.", "success")
            elif action == "move_down" and section_id:
                index = next((i for i, sec in enumerate(sections) if sec.get("id") == section_id), None)
                if index is None or index == len(sections) - 1:
                    raise ValueError("Não é possível mover este bloco para baixo.")
                sections[index + 1], sections[index] = sections[index], sections[index + 1]
                _save_page_content(page_data)
                flash("Ordem atualizada.", "success")
            elif action == "update_section" and section_id:
                section = _find_section(sections, section_id)
                if not section:
                    raise ValueError("Bloco não encontrado.")

                section_type = section.get("type")
                section["title"] = request.form.get("title", "").strip()

                if section_type == "hero":
                    section["subtitle"] = request.form.get("subtitle", "").strip()
                    section["background_image"] = request.form.get("background_image", "").strip()
                    section["primary_text"] = request.form.get("primary_text", "").strip()
                    section["primary_url"] = request.form.get("primary_url", "").strip()
                    section["secondary_text"] = request.form.get("secondary_text", "").strip()
                    section["secondary_url"] = request.form.get("secondary_url", "").strip()
                elif section_type == "text":
                    section["body"] = request.form.get("body", "").strip()
                    section["alignment"] = request.form.get("alignment", "left")
                elif section_type == "image":
                    section["body"] = request.form.get("body", "").strip()
                    section["image_url"] = request.form.get("image_url", "").strip()
                    section["image_alt"] = request.form.get("image_alt", "").strip()
                    section["link_text"] = request.form.get("link_text", "").strip()
                    section["link_url"] = request.form.get("link_url", "").strip()
                    section["alignment"] = request.form.get("alignment", "right")
                elif section_type == "cta":
                    section["body"] = request.form.get("body", "").strip()
                    section["button_text"] = request.form.get("button_text", "").strip()
                    section["button_url"] = request.form.get("button_url", "").strip()
                elif section_type == "list":
                    section["body"] = request.form.get("body", "").strip()
                    raw_items = request.form.get("items", "")
                    section["items"] = _parse_list_items(raw_items)
                elif section_type == "custom":
                    section["html"] = request.form.get("html", "")
                else:
                    raise ValueError("Tipo de bloco desconhecido.")

                _save_page_content(page_data)
                flash("Bloco atualizado com sucesso!", "success")
            else:
                flash("Ação não reconhecida.", "error")

            return redirect(url_for("admin.dashboard"))
        except (ValueError, OSError) as error:  # pragma: no cover - apenas feedback
            current_app.logger.warning("Erro ao atualizar painel: %s", error)
            flash(str(error), "error")

    return render_template(
        "admin/dashboard.html",
        page=page_data,
        sections=sections,
        last_modified=last_modified,
        last_backup=last_backup,
    )
