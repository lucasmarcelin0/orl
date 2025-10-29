"""Módulo responsável pela área administrativa do site."""

from __future__ import annotations

from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

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


admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")


def _get_index_path() -> Path:
    """Retorna o caminho completo do template index.html."""

    path = current_app.config.get("INDEX_TEMPLATE_PATH")
    if path is None:
        raise RuntimeError("INDEX_TEMPLATE_PATH não está configurado na aplicação.")
    return Path(path)


def _read_index_content() -> str:
    """Lê o conteúdo atual do index.html."""

    path = _get_index_path()
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_index_content(content: str) -> None:
    """Atualiza o arquivo index.html com o conteúdo fornecido."""

    path = _get_index_path()
    path.write_text(content, encoding="utf-8")


def _create_backup(original_content: str) -> Optional[Path]:
    """Gera um backup do conteúdo anterior do index.html."""

    if not original_content:
        return None

    backup_dir = Path(current_app.root_path) / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"index_{timestamp}.html"
    backup_path.write_text(original_content, encoding="utf-8")
    return backup_path


def _get_last_modified() -> Optional[datetime]:
    """Retorna a data da última modificação do index.html."""

    path = _get_index_path()
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def _get_last_backup() -> Optional[Path]:
    """Obtém o backup mais recente disponível."""

    backup_dir = Path(current_app.root_path) / "backups"
    if not backup_dir.exists():
        return None

    backups = sorted(backup_dir.glob("index_*.html"), reverse=True)
    return backups[0] if backups else None


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

    current_content = _read_index_content()
    last_modified = _get_last_modified()
    last_backup = _get_last_backup()

    if request.method == "POST":
        new_content = request.form.get("content", "")

        if not new_content.strip():
            flash("O conteúdo não pode ficar vazio.", "error")
        else:
            try:
                _create_backup(current_content)
                _write_index_content(new_content)
            except OSError as error:  # pragma: no cover - apenas para feedback ao usuário
                current_app.logger.exception("Erro ao salvar conteúdo do index.html")
                flash(f"Não foi possível salvar o arquivo: {error}", "error")
            else:
                flash("Página inicial atualizada com sucesso!", "success")
                return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/dashboard.html",
        content=current_content,
        last_modified=last_modified,
        last_backup=last_backup,
    )
