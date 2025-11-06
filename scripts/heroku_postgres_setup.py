#!/usr/bin/env python3
"""Automatiza os passos para habilitar o Heroku Postgres na aplicação."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import Iterable


def run(command: Iterable[str] | str, description: str) -> None:
    """Executa um comando do Heroku CLI exibindo logs amigáveis."""

    if isinstance(command, str):
        printable = command
        cmd_list = command
        shell = True
    else:
        printable = " ".join(shlex.quote(part) for part in command)
        cmd_list = list(command)
        shell = False

    print(f"\n▶ {description}\n$ {printable}")
    try:
        subprocess.run(cmd_list, check=True, text=True, shell=shell)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Falha ao executar: {printable}")
        raise SystemExit(exc.returncode) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Configura credenciais, executa migrações e valida dados "
            "iniciais após adicionar o Heroku Postgres."
        )
    )
    parser.add_argument(
        "--app",
        required=True,
        help="Nome da aplicação no Heroku (parâmetro --app do CLI).",
    )
    parser.add_argument(
        "--admin-username",
        help="Usuário administrador a ser configurado (ADMIN_USERNAME).",
    )
    parser.add_argument(
        "--admin-password",
        help="Senha do usuário administrador (ADMIN_PASSWORD).",
    )
    parser.add_argument(
        "--skip-admin",
        action="store_true",
        help="Ignora a configuração de credenciais administrativas.",
    )
    parser.add_argument(
        "--database-url-normalize",
        choices={"0", "1"},
        help=(
            "Define DATABASE_URL_NORMALIZE quando necessário. "
            "Use 0 apenas se quiser desativar a normalização."
        ),
    )

    args = parser.parse_args()

    if not args.skip_admin and (not args.admin_username or not args.admin_password):
        parser.error(
            "Informe --admin-username e --admin-password ou utilize --skip-admin."
        )

    # Passo 1: garantir variáveis de ambiente essenciais.
    config_parts = []
    if not args.skip_admin:
        config_parts.extend(
            [
                f"ADMIN_USERNAME={args.admin_username}",
                f"ADMIN_PASSWORD={args.admin_password}",
            ]
        )
    if args.database_url_normalize:
        config_parts.append(f"DATABASE_URL_NORMALIZE={args.database_url_normalize}")

    if config_parts:
        run(
            [
                "heroku",
                "config:set",
                *config_parts,
                "--app",
                args.app,
            ],
            "Definindo variáveis de ambiente no Heroku",
        )
    else:
        print("\n▶ Nenhuma variável de ambiente adicional para configurar.")

    run(
        ["heroku", "config:get", "DATABASE_URL", "--app", args.app],
        "Verificando se o DATABASE_URL foi provisionado pelo add-on",
    )

    # Passo 2: executar migrações do banco de dados.
    run(
        ["heroku", "run", "flask db upgrade", "--app", args.app],
        "Executando migrações com Flask-Migrate",
    )

    # Passo 3: reiniciar os dynos para recarregar a aplicação.
    run(
        ["heroku", "ps:restart", "--app", args.app],
        "Reiniciando a aplicação no Heroku",
    )

    # Passo 4: garantir dados iniciais utilizando o comando Flask recém-criado.
    ensure_command = "flask ensure-default-data"
    if args.skip_admin:
        ensure_command += " --skip-admin"

    run(
        ["heroku", "run", ensure_command, "--app", args.app],
        "Garantindo schema e dados iniciais",
    )

    print("\n✅ Integração com Heroku Postgres concluída!")


if __name__ == "__main__":  # pragma: no cover - script de utilidade
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
