"""Utilitários para leitura e escrita do conteúdo público do site."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_content(path: Path) -> Dict[str, Any]:
    """Carrega o arquivo JSON com os blocos da página inicial."""

    if not path.exists():
        return {"title": "Página inicial", "description": "", "sections": []}

    data = path.read_text(encoding="utf-8")
    try:
        return json.loads(data)
    except json.JSONDecodeError as error:  # pragma: no cover - feedback para admin
        raise ValueError(f"Conteúdo inválido no arquivo {path}: {error}") from error


def save_content(path: Path, data: Dict[str, Any]) -> None:
    """Persiste o conteúdo da página inicial em disco."""

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(serialized + "\n", encoding="utf-8")


def create_backup(source: Path, destination: Path) -> Path:
    """Cria uma cópia de segurança do ``source`` dentro de ``destination``."""

    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = destination / f"page_content_{timestamp}.json"
    backup_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path
