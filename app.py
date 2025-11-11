"""Aplicação Flask principal da Prefeitura de Orlândia."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Iterable
import uuid
import threading
from types import SimpleNamespace

import click
from flask import (
    abort,
    flash,
    g,
    Flask,
    Blueprint,
    current_app,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_admin import helpers as admin_helpers
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_babel import Babel
from flask_socketio import SocketIO
from sqlalchemy import create_engine, event, func, inspect, or_, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import load_only
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.utils import secure_filename

import storage

from admin import init_admin
from config import Config
from forms import LoginForm, UserProfileForm

from models import (
    db,
    EmergencyService,
    Document,
    FooterColumn,
    HomepageSection,
    Page,
    QuickLink,
    SectionItem,
    User,
)
from models import AuditMixin
from jogo import jogo_bp, init_socketio

# Comentário: extensões globais reutilizadas pela aplicação.
STARTUP_EXTENSION_KEY = "orl_startup_state"


migrate = Migrate()
ckeditor = CKEditor()
login_manager = LoginManager()
babel = Babel()
socketio = SocketIO()


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""

    app = Flask(__name__)
    app.config.from_object(Config)

    def _database_connect_timeout() -> int:
        value = os.getenv("DATABASE_CONNECT_TIMEOUT")
        if not value:
            return 5
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return 5

    def _test_database_connection(database_uri: str) -> None:
        if not database_uri:
            return

        url = make_url(database_uri)
        engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
        connect_args: dict[str, object] = {}

        if url.drivername.startswith("postgresql"):
            connect_args["connect_timeout"] = _database_connect_timeout()

        if connect_args:
            engine_kwargs["connect_args"] = connect_args

        engine = create_engine(database_uri, **engine_kwargs)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        finally:
            engine.dispose()

    def _configure_database() -> None:
        primary_uri = app.config.get("SQLALCHEMY_PRIMARY_DATABASE_URI")
        configured_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
        fallback_uri = app.config.get("SQLALCHEMY_FALLBACK_DATABASE_URI")

        if not primary_uri:
            primary_uri = configured_uri

        if not primary_uri and fallback_uri:
            app.config["SQLALCHEMY_DATABASE_URI"] = fallback_uri
            app.config["SQLALCHEMY_DATABASE_FALLBACK_USED"] = False
            return

        if not primary_uri:
            return

        try:
            _test_database_connection(primary_uri)
        except Exception as exc:  # pragma: no cover - depende de ambiente externo
            if fallback_uri and fallback_uri != primary_uri:
                app.logger.warning(
                    "Não foi possível conectar ao banco configurado. "
                    "Aplicando fallback local.",
                    exc_info=exc,
                )
                app.config["SQLALCHEMY_DATABASE_URI"] = fallback_uri
                app.config["SQLALCHEMY_DATABASE_FALLBACK_USED"] = True
                app.config["SQLALCHEMY_DATABASE_FALLBACK_REASON"] = str(exc)
            else:
                raise
        else:
            app.config["SQLALCHEMY_DATABASE_URI"] = primary_uri
            app.config["SQLALCHEMY_DATABASE_FALLBACK_USED"] = False

    _configure_database()

    storage.init_cloudinary(app)

    # Comentário: inicialização das extensões com as configurações carregadas.
    db.init_app(app)
    migrate.init_app(app, db)
    ckeditor.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Realize o login para acessar o painel."
    login_manager.login_message_category = "error"

    socketio.init_app(app)
    if not getattr(socketio, "_orl_game_initialized", False):
        init_socketio(socketio)
        setattr(socketio, "_orl_game_initialized", True)

    def _select_locale() -> str:
        return app.config.get("BABEL_DEFAULT_LOCALE", "pt_BR")

    def _select_timezone() -> str:
        return app.config.get("BABEL_DEFAULT_TIMEZONE", "America/Sao_Paulo")

    babel.init_app(
        app,
        locale_selector=_select_locale,
        timezone_selector=_select_timezone,
    )

    @app.context_processor
    def inject_admin_helpers() -> dict[str, object]:
        """Disponibiliza utilidades do Flask-Admin para os templates personalizados."""

        admin_blueprint = current_app.blueprints.get("admin")
        admin_static = None
        if admin_blueprint is not None:
            admin_static = getattr(admin_blueprint, "static", None)

        blueprint_name = admin_blueprint.name if admin_blueprint is not None else None

        if admin_static is None:

            def _admin_static_url(filename: str, **kwargs) -> str:
                endpoint = f"{blueprint_name}.static" if blueprint_name else "static"
                return url_for(endpoint, filename=filename, **kwargs)

            admin_static = SimpleNamespace(url=_admin_static_url)

        section_item_upload_endpoint = None
        if current_user.is_authenticated and current_user.is_active:
            try:
                section_item_upload_endpoint = url_for("upload_section_item_image")
            except Exception:  # pragma: no cover - rota indisponível
                section_item_upload_endpoint = None

        return {
            "get_url": admin_helpers.get_url,
            "admin_helpers": admin_helpers,
            "h": admin_helpers,
            "admin_static": admin_static,
            "section_item_image_upload_endpoint": section_item_upload_endpoint,
        }

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    @app.before_request
    def _bind_audit_user() -> None:
        g.current_audit_user = current_user if current_user.is_authenticated else None

    def _audit_before_flush(session, flush_context, instances) -> None:
        if not has_request_context():
            return

        user = getattr(g, "current_audit_user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return

        for instance in session.new:
            if isinstance(instance, AuditMixin):
                if hasattr(instance, "created_by") and getattr(instance, "created_by", None) is None:
                    instance.created_by = user
                if hasattr(instance, "updated_by"):
                    instance.updated_by = user

        for instance in session.dirty:
            if isinstance(instance, AuditMixin) and hasattr(instance, "updated_by"):
                instance.updated_by = user

    if not getattr(db.session, "_audit_listener_configured", False):
        event.listen(db.session, "before_flush", _audit_before_flush)
        db.session._audit_listener_configured = True

    def ensure_database_schema() -> None:
        """Garante a existência das colunas esperadas em instalações antigas."""

        try:
            db.create_all()
        except OperationalError:
            return

        try:
            engine = db.session.get_bind()
        except OperationalError:
            return
        if engine is None:
            return

        inspector = inspect(engine)
        try:
            document_columns = {
                column["name"] for column in inspector.get_columns("document")
            }
        except Exception:  # pragma: no cover - fallback defensivo
            document_columns = set()

        if document_columns and "section_item_id" not in document_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE document ADD COLUMN section_item_id INTEGER")
                )

        try:
            quick_link_columns = {
                column["name"] for column in inspector.get_columns("quick_link")
            }
        except Exception:  # pragma: no cover - tabela inexistente em instalações novas
            quick_link_columns = set()

        if quick_link_columns and "footer_column_id" not in quick_link_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE quick_link ADD COLUMN footer_column_id INTEGER")
                )

        try:
            section_item_columns = {
                column["name"] for column in inspector.get_columns("section_item")
            }
        except Exception:  # pragma: no cover - tabela inexistente em instalações novas
            section_item_columns = set()

        if section_item_columns:
            dialect_name = engine.dialect.name
            transform_columns = {
                "image_scale": {
                    "default": "1.0",
                    "not_null": True,
                    "type": {
                        "postgresql": "DOUBLE PRECISION",
                        "sqlite": "REAL",
                        "default": "FLOAT",
                    },
                },
                "image_rotation": {
                    "default": "0",
                    "not_null": True,
                    "type": {
                        "postgresql": "INTEGER",
                        "sqlite": "INTEGER",
                        "default": "INTEGER",
                    },
                },
            }

            with engine.begin() as connection:
                for column_name, spec in transform_columns.items():
                    if column_name in section_item_columns:
                        continue

                    column_type = spec["type"].get(
                        dialect_name, spec["type"].get("default", "TEXT")
                    )
                    default_value = spec.get("default")

                    alter_statement = (
                        f"ALTER TABLE section_item ADD COLUMN {column_name} {column_type}"
                    )
                    if default_value is not None:
                        alter_statement = f"{alter_statement} DEFAULT {default_value}"

                    connection.execute(text(alter_statement))

                    if default_value is not None:
                        connection.execute(
                            text(
                                f"UPDATE section_item SET {column_name} = {default_value} "
                                f"WHERE {column_name} IS NULL"
                            )
                        )

                        if dialect_name == "postgresql":
                            connection.execute(
                                text(
                                    f"ALTER TABLE section_item ALTER COLUMN {column_name} "
                                    f"SET DEFAULT {default_value}"
                                )
                            )

                    if spec.get("not_null") and dialect_name == "postgresql":
                        connection.execute(
                            text(
                                f"ALTER TABLE section_item ALTER COLUMN {column_name} SET NOT NULL"
                            )
                        )

        audit_tables = (
            "page",
            "homepage_section",
            "section_item",
            "document",
            "footer_column",
            "quick_link",
            "emergency_service",
        )
        audit_columns = {
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
            "created_by_id": "INTEGER",
            "updated_by_id": "INTEGER",
        }

        for table in audit_tables:
            try:
                existing_columns = {
                    column["name"] for column in inspector.get_columns(table)
                }
            except Exception:
                continue

            missing_columns = [
                column_name
                for column_name in audit_columns
                if column_name not in existing_columns
            ]
            if not missing_columns:
                continue

            with engine.begin() as connection:
                for column_name in missing_columns:
                    column_type = audit_columns[column_name]
                    connection.execute(
                        text(
                            f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
                        )
                    )

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

    def ensure_emergency_services() -> None:
        """Popula serviços de emergência padrão em instalações novas."""

        defaults = [
            {
                "name": "SAMU",
                "phone": "192",
                "icon_class": "fas fa-ambulance",
            },
            {
                "name": "Bombeiros",
                "phone": "193",
                "icon_class": "fas fa-fire-extinguisher",
            },
            {
                "name": "Polícia Militar",
                "phone": "190",
                "icon_class": "fas fa-shield-alt",
            },
            {
                "name": "Pronto Socorro",
                "phone": "(16) 3820-2000",
                "icon_class": "fas fa-hospital",
            },
        ]

        try:
            db.create_all()
        except OperationalError:
            return

        try:
            has_services = EmergencyService.query.count() > 0
        except OperationalError:
            return

        if has_services:
            return

        for order, data in enumerate(defaults):
            db.session.add(
                EmergencyService(
                    name=data.get("name", "Serviço"),
                    phone=data.get("phone"),
                    icon_class=data.get("icon_class"),
                    display_order=order,
                    is_active=True,
                )
            )

        db.session.commit()

    def ensure_default_admin_user() -> None:
        """Cria automaticamente o usuário administrador inicial."""

        try:
            db.create_all()
        except OperationalError:
            return

        username = (app.config.get("ADMIN_USERNAME") or "").strip()
        password = app.config.get("ADMIN_PASSWORD")
        if not username or not password:
            return

        try:
            existing_user = User.query.filter(
                func.lower(User.username) == username.lower()
            ).first()
        except OperationalError:
            return

        if existing_user is not None:
            return

        admin_user = User(
            name="Administrador",
            username=username.lower(),
            email=None,
            is_admin=True,
            is_active=True,
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()

    @app.cli.command("ensure-default-data")
    @click.option(
        "--skip-admin",
        is_flag=True,
        default=False,
        help=(
            "Não criar ou atualizar o usuário administrador padrão. "
            "Use quando as credenciais não estiverem configuradas."
        ),
    )
    def ensure_default_data(skip_admin: bool) -> None:
        """Garante a existência de schema e dados iniciais essenciais."""

        ensure_database_schema()
        ensure_homepage_sections()
        ensure_emergency_services()
        if not skip_admin:
            ensure_default_admin_user()

        click.echo("Dados padrão verificados com sucesso.")

    @app.cli.command("restore-database-dump")
    @click.option(
        "--dump-path",
        default="latest.dump",
        show_default=True,
        help=(
            "Caminho para o arquivo de dump gerado pelo Heroku (formato custom do pg_dump)."
        ),
    )
    @click.option(
        "--target",
        type=click.Choice(["auto", "primary", "fallback"]),
        default="auto",
        show_default=True,
        help=(
            "Define qual banco receberá os dados. Em 'auto', utiliza o fallback "
            "quando ele estiver ativo."
        ),
    )
    def restore_database_dump(dump_path: str, target: str) -> None:
        """Restaura um dump do PostgreSQL no banco configurado."""

        path = Path(dump_path)
        if not path.is_absolute():
            path = Path(app.root_path) / path

        if not path.exists():
            raise click.ClickException(
                f"Arquivo de dump não encontrado: {path}"
            )

        primary_uri = app.config.get("SQLALCHEMY_PRIMARY_DATABASE_URI")
        fallback_uri = app.config.get("SQLALCHEMY_FALLBACK_DATABASE_URI")
        current_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

        if target == "primary":
            database_uri = primary_uri or current_uri
        elif target == "fallback":
            database_uri = fallback_uri
        else:  # auto
            if app.config.get("SQLALCHEMY_DATABASE_FALLBACK_USED"):
                database_uri = current_uri
            else:
                database_uri = primary_uri or current_uri

        if not database_uri:
            raise click.ClickException(
                "Nenhuma URL de banco de dados foi configurada para a restauração."
            )

        url = make_url(database_uri)
        if not url.drivername.startswith("postgresql"):
            raise click.ClickException(
                "A restauração automática requer um banco de dados PostgreSQL. "
                "Configure LOCAL_DATABASE_URL para apontar para uma instância local."
            )

        if shutil.which("pg_restore") is None:
            raise click.ClickException(
                "O utilitário 'pg_restore' não foi encontrado no PATH. "
                "Instale o PostgreSQL localmente para continuar."
            )

        env = os.environ.copy()
        if url.password:
            env.setdefault("PGPASSWORD", url.password)

        uri_without_password = url.set(password=None)
        masked_uri = url.render_as_string(hide_password=True)

        click.echo(
            f"Restaurando dump '{path}' em {masked_uri} utilizando pg_restore..."
        )

        command = [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            uri_without_password.render_as_string(hide_password=False),
            str(path),
        ]

        try:
            subprocess.run(command, check=True, env=env)
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(
                "Falha ao restaurar o dump utilizando pg_restore."
            ) from exc

        click.echo("Dump restaurado com sucesso.")

    def _run_startup_tasks_once() -> None:
        """Executa rotinas de inicialização apenas uma vez por instância da app."""

        state = app.extensions.setdefault(STARTUP_EXTENSION_KEY, {})
        if state.get("executed"):
            return

        def _execute_startup_tasks() -> None:
            ensure_database_schema()
            ensure_default_admin_user()
            ensure_homepage_sections()
            ensure_emergency_services()

        init_admin(app)

        if app.config.get("STARTUP_TASKS_ASYNC"):
            def _run_in_background() -> None:
                with app.app_context():
                    try:
                        _execute_startup_tasks()
                    except Exception:  # pragma: no cover - log defensivo
                        app.logger.exception(
                            "Falha ao executar tarefas de inicialização em segundo plano."
                        )

            thread = threading.Thread(
                target=_run_in_background,
                name="orl-startup-tasks",
                daemon=True,
            )
            thread.start()
            state["thread"] = thread
        else:
            _execute_startup_tasks()

        state["executed"] = True

    with app.app_context():
        _run_startup_tasks_once()

    auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

    @auth_bp.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            next_url = request.args.get("next") or url_for("admin.index")
            return redirect(next_url)

        form = LoginForm()
        if form.validate_on_submit():
            username = (form.username.data or "").strip()
            user = None
            if username:
                user = User.query.filter(
                    func.lower(User.username) == username.lower()
                ).first()

            if user and user.is_active and user.check_password(form.password.data):
                login_user(user)
                user.last_login_at = datetime.utcnow()
                db.session.commit()

                next_url = request.args.get("next")
                if not next_url or not next_url.startswith("/"):
                    next_url = url_for("admin.index")
                return redirect(next_url)

            flash("Credenciais inválidas ou usuário inativo.", "error")

        return render_template("auth/login.html", form=form)

    @auth_bp.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Sessão encerrada com sucesso.", "success")
        return redirect(url_for("auth.login"))

    app.register_blueprint(auth_bp)
    app.register_blueprint(jogo_bp)

    @app.route("/admin/perfil", methods=["GET", "POST"])
    @login_required
    def admin_profile():
        form = UserProfileForm(obj=current_user)
        if request.method == "GET":
            form.password.data = ""
            form.confirm_password.data = ""

        if form.validate_on_submit():
            current_user.name = form.name.data
            current_user.email = (form.email.data or "").strip() or None

            if form.password.data:
                current_user.set_password(form.password.data)

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(
                    "Já existe um usuário registrado com este e-mail. Escolha outro endereço.",
                    "error",
                )
            else:
                flash("Perfil atualizado com sucesso!", "success")
                return redirect(url_for("admin_profile"))

        admin_ext = current_app.extensions.get("admin", [])
        admin_view = admin_ext[0].index_view if admin_ext else None
        return render_template("admin/profile.html", form=form, admin_view=admin_view)

    def _resolve_upload_path(config_key: str, default_path: str | Path) -> Path:
        upload_path_value = app.config.get(config_key, default_path)
        upload_path = Path(upload_path_value)
        if not upload_path.is_absolute():
            upload_path = Path(app.root_path) / upload_path
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    def _allowed_file(filename: str, allowed_extensions) -> bool:
        if not filename or "." not in filename:
            return False

        allowed = {ext.lower() for ext in (allowed_extensions or set())}
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in allowed

    @app.route("/admin/ckeditor/uploads/<path:filename>")
    def ckeditor_uploaded_file(filename: str):
        upload_path = _resolve_upload_path(
            "CKEDITOR_UPLOADS_PATH", Path("static") / "uploads"
        )
        return send_from_directory(str(upload_path), filename)

    @app.route("/admin/ckeditor/upload", methods=["POST"])
    def upload_ckeditor_image():
        upload = request.files.get("upload")
        if upload is None or upload.filename == "":
            return (
                jsonify({"uploaded": 0, "error": {"message": "Nenhum arquivo foi enviado."}}),
                400,
            )

        if not _allowed_file(
            upload.filename,
            app.config.get("CKEDITOR_ALLOWED_IMAGE_EXTENSIONS", set()),
        ):
            return (
                jsonify(
                    {
                        "uploaded": 0,
                        "error": {
                            "message": "Formato de arquivo não suportado. Utilize imagens PNG, JPG, JPEG, GIF ou WEBP.",
                        },
                    }
                ),
                400,
            )

        max_size = app.config.get("CKEDITOR_MAX_IMAGE_SIZE")
        if max_size:
            upload.stream.seek(0, os.SEEK_END)
            file_size = upload.stream.tell()
            upload.stream.seek(0)
            if file_size > max_size:
                limit_mb = max_size / (1024 * 1024)
                limit_text = (
                    f"{int(limit_mb)} MB"
                    if float(limit_mb).is_integer()
                    else f"{limit_mb:.1f} MB"
                )
                return (
                    jsonify(
                        {
                            "uploaded": 0,
                            "error": {
                                "message": f"Imagem excede o tamanho máximo permitido de {limit_text}.",
                            },
                        }
                    ),
                    413,
                )

        secure_name = secure_filename(upload.filename)
        if not secure_name:
            return (
                jsonify({"uploaded": 0, "error": {"message": "Nome de arquivo inválido."}}),
                400,
            )

        extension = secure_name.rsplit(".", 1)[1].lower()
        unique_name = f"ckeditor-{uuid.uuid4().hex}.{extension}"

        if storage.is_cloudinary_enabled():
            try:
                file_url = storage.upload_to_cloudinary(
                    upload,
                    filename=unique_name,
                    folder=current_app.config.get("CLOUDINARY_CKEDITOR_FOLDER"),
                    resource_type="image",
                )
            except storage.StorageError:
                current_app.logger.exception(
                    "Falha ao enviar imagem do CKEditor ao Cloudinary."
                )
                return (
                    jsonify(
                        {
                            "uploaded": 0,
                            "error": {
                                "message": "Não foi possível enviar a imagem ao armazenamento externo. Tente novamente.",
                            },
                        }
                    ),
                    502,
                )
        else:
            upload_path = _resolve_upload_path(
                "CKEDITOR_UPLOADS_PATH", Path("static") / "uploads"
            )
            destination = upload_path / unique_name
            upload.save(destination)

            file_url = url_for("ckeditor_uploaded_file", filename=unique_name)
        return jsonify({"uploaded": 1, "fileName": unique_name, "url": file_url})

    @app.route("/admin/section-item/uploads/<path:filename>")
    def section_item_uploaded_image(filename: str):
        upload_path = _resolve_upload_path(
            "SECTION_ITEM_IMAGE_UPLOADS_PATH",
            Path("static") / "uploads" / "section-items",
        )
        return send_from_directory(str(upload_path), filename)

    @app.route("/admin/section-item/upload-image", methods=["POST"])
    @login_required
    def upload_section_item_image():
        upload = request.files.get("upload")
        if upload is None or upload.filename == "":
            return (
                jsonify(
                    {"uploaded": 0, "error": {"message": "Nenhum arquivo foi enviado."}}
                ),
                400,
            )

        allowed_extensions = app.config.get(
            "SECTION_ITEM_ALLOWED_IMAGE_EXTENSIONS",
            app.config.get("CKEDITOR_ALLOWED_IMAGE_EXTENSIONS", set()),
        )
        if not _allowed_file(upload.filename, allowed_extensions):
            return (
                jsonify(
                    {
                        "uploaded": 0,
                        "error": {
                            "message": "Formato de arquivo não suportado. Utilize imagens PNG, JPG, JPEG, GIF ou WEBP.",
                        },
                    }
                ),
                400,
            )

        max_size = app.config.get("SECTION_ITEM_MAX_IMAGE_SIZE")
        if max_size:
            upload.stream.seek(0, os.SEEK_END)
            file_size = upload.stream.tell()
            upload.stream.seek(0)
            if file_size > max_size:
                limit_mb = max_size / (1024 * 1024)
                limit_text = (
                    f"{int(limit_mb)} MB"
                    if float(limit_mb).is_integer()
                    else f"{limit_mb:.1f} MB"
                )
                return (
                    jsonify(
                        {
                            "uploaded": 0,
                            "error": {
                                "message": f"Imagem excede o tamanho máximo permitido de {limit_text}.",
                            },
                        }
                    ),
                    413,
                )

        secure_name = secure_filename(upload.filename)
        if not secure_name:
            return (
                jsonify({"uploaded": 0, "error": {"message": "Nome de arquivo inválido."}}),
                400,
            )

        extension = secure_name.rsplit(".", 1)[1].lower()
        unique_name = f"section-item-{uuid.uuid4().hex}.{extension}"

        if storage.is_cloudinary_enabled():
            try:
                file_url = storage.upload_to_cloudinary(
                    upload,
                    filename=unique_name,
                    folder=current_app.config.get("CLOUDINARY_SECTION_ITEM_FOLDER"),
                    resource_type="image",
                )
            except storage.StorageError:
                current_app.logger.exception(
                    "Falha ao enviar imagem do cartão ao Cloudinary."
                )
                return (
                    jsonify(
                        {
                            "uploaded": 0,
                            "error": {
                                "message": "Não foi possível enviar a imagem ao armazenamento externo. Tente novamente.",
                            },
                        }
                    ),
                    502,
                )
        else:
            upload_path = _resolve_upload_path(
                "SECTION_ITEM_IMAGE_UPLOADS_PATH",
                Path("static") / "uploads" / "section-items",
            )
            destination = upload_path / unique_name
            upload.save(destination)

            file_url = url_for("section_item_uploaded_image", filename=unique_name)

        return jsonify({"uploaded": 1, "fileName": unique_name, "url": file_url})

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
            visible_pages = (
                Page.query.options(
                    # Carrega apenas os campos usados na navegação para evitar
                    # transferir o conteúdo HTML pesado de cada página.
                    load_only(Page.id, Page.slug, Page.title, Page.visible)
                )
                .filter_by(visible=True)
                .order_by(Page.title)
                .all()
            )
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

        try:
            quick_access_links = (
                QuickLink.query.filter(
                    QuickLink.location == QuickLink.LOCATION_QUICK_ACCESS,
                    QuickLink.is_active.isnot(False),
                )
                .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                .all()
            )
            quick_access_configured = (
                QuickLink.query.filter_by(location=QuickLink.LOCATION_QUICK_ACCESS).count()
                > 0
            )
        except OperationalError:
            quick_access_links = []
            quick_access_configured = False

        if not quick_access_links and not quick_access_configured:
            quick_access_links = [
                {"label": "Editais e Licitações", "url": url_for("licitacoes")},
                {"label": "Concursos Públicos", "url": url_for("concursos")},
                {"label": "IPTU Online", "url": url_for("iptu_online")},
                {"label": "Alvarás", "url": url_for("alvaras")},
            ]

        try:
            footer_columns = (
                FooterColumn.query.filter(FooterColumn.is_active.isnot(False))
                .order_by(FooterColumn.display_order.asc(), FooterColumn.id.asc())
                .all()
            )
        except OperationalError:
            footer_columns = []

        footer_columns_payload = []

        if footer_columns:
            column_ids = [column.id for column in footer_columns]

            if column_ids:
                try:
                    footer_links = (
                        QuickLink.query.filter(
                            QuickLink.location == QuickLink.LOCATION_FOOTER,
                            QuickLink.is_active.isnot(False),
                            QuickLink.footer_column_id.in_(column_ids),
                        )
                        .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                        .all()
                    )
                except OperationalError:
                    footer_links = []
            else:
                footer_links = []

            links_by_column: dict[int | None, list[QuickLink]] = {
                column_id: [] for column_id in column_ids
            }
            for link in footer_links:
                links_by_column.setdefault(link.footer_column_id, []).append(link)

            for column in footer_columns:
                footer_columns_payload.append(
                    {
                        "title": column.title,
                        "links": links_by_column.get(column.id, []),
                    }
                )
        else:
            try:
                legacy_footer_links = (
                    QuickLink.query.filter(
                        QuickLink.location == QuickLink.LOCATION_FOOTER,
                        QuickLink.is_active.isnot(False),
                        QuickLink.footer_column_id.is_(None),
                    )
                    .order_by(QuickLink.display_order.asc(), QuickLink.id.asc())
                    .all()
                )
                legacy_configured = (
                    QuickLink.query.filter_by(
                        location=QuickLink.LOCATION_FOOTER
                    ).count()
                    > 0
                )
            except OperationalError:
                legacy_footer_links = []
                legacy_configured = False

            if legacy_footer_links:
                footer_columns_payload = [
                    {"title": "Serviços online", "links": legacy_footer_links}
                ]
            elif not legacy_configured:
                footer_columns_payload = [
                    {
                        "title": "Serviços online",
                        "links": [
                            {"label": "Licitações", "url": url_for("licitacoes")},
                            {"label": "Concursos", "url": url_for("concursos")},
                            {"label": "IPTU Online", "url": url_for("iptu_online")},
                            {"label": "Alvarás", "url": url_for("alvaras")},
                        ],
                    }
                ]
            else:
                footer_columns_payload = [
                    {"title": "Serviços online", "links": []}
                ]

        return {
            "pages": visible_pages,
            "page_columns": _chunk_pages(visible_pages, columns=3),
            "admin_navigation": admin_navigation,
            "admin_index_url": admin_index_url,
            "footer_columns": footer_columns_payload,
            "quick_access_links": quick_access_links,
            "current_year": datetime.utcnow().year,
        }

    @app.route("/")
    def index() -> str:
        """Rota principal que exibe a página inicial estática."""

        try:
            sections = (
                HomepageSection.query.filter_by(is_active=True)
                .order_by(
                    HomepageSection.display_order.asc(),
                    HomepageSection.id.asc(),
                )
                .all()
            )
        except OperationalError:
            sections = []

        try:
            emergency_services = (
                EmergencyService.query.filter_by(is_active=True)
                .order_by(
                    EmergencyService.display_order.asc(),
                    EmergencyService.name.asc(),
                )
                .all()
            )
        except OperationalError:
            emergency_services = []

        return render_template(
            "index.html",
            sections=sections,
            emergency_services=emergency_services,
        )

    @app.route("/buscar")
    def search() -> str:
        """Permite localizar páginas, serviços e documentos pelo termo informado."""

        query = (request.args.get("q", "") or "").strip()
        if not query:
            return redirect(url_for("index"))

        search_pattern = f"%{query}%"

        try:
            page_results = (
                Page.query.filter(Page.visible.is_(True))
                .filter(
                    or_(
                        Page.title.ilike(search_pattern),
                        Page.content.ilike(search_pattern),
                    )
                )
                .order_by(Page.title.asc())
                .all()
            )
        except OperationalError:
            page_results = []

        try:
            section_item_results = (
                SectionItem.query.join(HomepageSection)
                .filter(
                    HomepageSection.is_active.is_(True),
                    SectionItem.is_active.is_(True),
                    or_(
                        SectionItem.title.ilike(search_pattern),
                        SectionItem.summary.ilike(search_pattern),
                        SectionItem.badge.ilike(search_pattern),
                        SectionItem.display_date.ilike(search_pattern),
                    ),
                )
                .order_by(
                    HomepageSection.display_order.asc(),
                    SectionItem.display_order.asc(),
                    SectionItem.id.asc(),
                )
                .all()
            )
        except OperationalError:
            section_item_results = []

        try:
            document_results = (
                Document.query.join(SectionItem)
                .join(HomepageSection)
                .filter(
                    Document.is_active.is_(True),
                    SectionItem.is_active.is_(True),
                    HomepageSection.is_active.is_(True),
                    or_(
                        Document.title.ilike(search_pattern),
                        Document.description.ilike(search_pattern),
                    ),
                )
                .order_by(Document.display_order.asc(), Document.title.asc())
                .all()
            )
        except OperationalError:
            document_results = []

        total_results = (
            len(page_results)
            + len(section_item_results)
            + len(document_results)
        )

        return render_template(
            "search_results.html",
            query=query,
            page_results=page_results,
            section_item_results=section_item_results,
            document_results=document_results,
            total_results=total_results,
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

    @app.route("/transparencia/plano-plurianual")
    def plano_plurianual() -> str:
        """Disponibiliza os principais documentos do Plano Plurianual."""

        return render_template("transparencia/plano_plurianual.html")

    @app.route("/transparencia/relatorios-gestao")
    def relatorios_gestao() -> str:
        """Apresenta os relatórios anuais de gestão do município."""

        return render_template("transparencia/relatorios_gestao.html")

    @app.route("/transparencia/gastos-covid-19")
    def gastos_covid19() -> str:
        """Exibe dados sobre despesas realizadas no enfrentamento à COVID-19."""

        return render_template("transparencia/gastos_covid19.html")

    @app.route("/transparencia/pesquisa-satisfacao")
    def pesquisa_satisfacao() -> str:
        """Disponibiliza formulários e resultados das pesquisas de satisfação."""

        return render_template("transparencia/pesquisa_satisfacao.html")

    @app.route("/transparencia/lista-obras")
    def lista_obras() -> str:
        """Reúne as informações das obras públicas em andamento e concluídas."""

        return render_template("transparencia/lista_obras.html")

    @app.route("/transparencia/iluminacao-publica")
    def iluminacao_publica() -> str:
        """Traz relatórios e canais de atendimento da iluminação pública."""

        return render_template("transparencia/iluminacao_publica.html")

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
            ensure_database_schema()
            click.echo("Banco de dados verificado com sucesso.")
        app.run(host=host, port=port, debug=debug)

    return app


# Comentário: instância utilizada por servidores WSGI ou pelo Flask CLI.
app = create_app()


if __name__ == "__main__":
    # Comentário: execução direta do módulo para ambientes de desenvolvimento.
    socketio.run(app, debug=True)
