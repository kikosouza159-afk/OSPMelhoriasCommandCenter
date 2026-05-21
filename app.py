from __future__ import annotations

import json
import os
import re
import threading
import uuid
from html import escape
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = Path(os.environ.get("DATA_FILE", DATA_DIR / "demandas.json"))
LOCK = threading.Lock()

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ============================================================
# CADASTRO DE USUÁRIOS
# ============================================================
# Para incluir um usuário novo, adicione apenas uma linha nessa lista.
# Exemplo usuário comum:
#     {"usuario": "aleff.jesus", "senha": "olos123", "pode_excluir": False},
#
# Exemplo usuário com permissão para excluir demandas:
#     {"usuario": "coord.nome", "senha": "olos123", "pode_excluir": True},
#
# Depois é só salvar o app.py, fazer commit/push e redeploy no Render.

USER_ACCESS = [
    {"usuario": "admin", "senha": "olos123", "pode_excluir": True},
    {"usuario": "gerber", "senha": "olos123", "pode_excluir": True},
    {"usuario": "elvis", "senha": "olos123", "pode_excluir": False},
    {"usuario": "michele", "senha": "olos123", "pode_excluir": False},
    {"usuario": "nubia", "senha": "olos123", "pode_excluir": False},
    {"usuario": "marcelo", "senha": "olos123", "pode_excluir": False},
    {"usuario": "hilde", "senha": "olos123", "pode_excluir": False},
    {"usuario": "antonio", "senha": "olos123", "pode_excluir": False},
    {"usuario": "aleff.jesus", "senha": "olos123", "pode_excluir": False},
]


def normalize_login(value: Any) -> str:
    return str(value or "").strip().lower()


def build_users() -> tuple[dict[str, str], set[str]]:
    users: dict[str, str] = {}
    delete_allowed: set[str] = set()

    for item in USER_ACCESS:
        usuario = normalize_login(item.get("usuario"))
        senha = str(item.get("senha") or "").strip()
        if not usuario or not senha:
            continue
        users[usuario] = senha
        if bool(item.get("pode_excluir")):
            delete_allowed.add(usuario)

    # Opcional para Render: permite adicionar usuários sem mexer no código.
    # Formato: EXTRA_USERS="usuario:senha,usuario2:senha:admin"
    extra_users = os.environ.get("EXTRA_USERS", "").strip()
    for raw in [x.strip() for x in extra_users.split(",") if x.strip()]:
        parts = [p.strip() for p in raw.split(":")]
        if len(parts) >= 2:
            usuario = normalize_login(parts[0])
            senha = parts[1]
            perfil = normalize_login(parts[2]) if len(parts) >= 3 else ""
            if usuario and senha:
                users[usuario] = senha
                if perfil in {"admin", "delete", "excluir", "true", "1"}:
                    delete_allowed.add(usuario)

    return users, delete_allowed


def users_footer_text() -> str:
    users, _ = build_users()
    nomes = list(users.keys())
    if not nomes:
        return "Nenhum usuário cadastrado"
    if len(nomes) == 1:
        return f"Usuário liberado: {nomes[0]}"
    return "Usuários liberados: " + ", ".join(nomes[:-1]) + " e " + nomes[-1]


def inject_frontend_auth_config(html: str) -> str:
    users, delete_allowed = build_users()
    users_js = json.dumps(users, ensure_ascii=False, indent=2)
    delete_js = json.dumps(sorted(delete_allowed), ensure_ascii=False)

    html = re.sub(
        r"const\s+USERS\s*=\s*\{.*?\};",
        f"const USERS = {users_js};",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"const\s+DELETE_ALLOWED\s*=\s*\[.*?\];",
        f"const DELETE_ALLOWED = {delete_js};",
        html,
        flags=re.S,
    )
    html = re.sub(
        r'<div class="login-foot">.*?</div>',
        f'<div class="login-foot">{escape(users_footer_text())}.</div>',
        html,
        flags=re.S,
    )
    return html


def get_delete_allowed() -> set[str]:
    _, delete_allowed = build_users()
    return delete_allowed
ALLOWED_STATUS = {"Em Andamento", "Concluído", "Pendentes", "Paralisado"}
STATUS_ALIASES = {"Pendente": "Pendentes", "pendente": "Pendentes", "PENDENTE": "Pendentes"}

DEFAULT_DEMANDAS = []


def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        rows = []
        for item in DEFAULT_DEMANDAS:
            rows.append({"uid": uuid.uuid4().hex, **item})
        save_raw(rows)


def load_raw() -> list[dict[str, Any]]:
    ensure_data_file()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    if not isinstance(data, list):
        data = []
    changed = False
    for item in data:
        if "uid" not in item or not item.get("uid"):
            item["uid"] = uuid.uuid4().hex
            changed = True
        if "cliente" not in item or not item.get("cliente"):
            item["cliente"] = "Geral"
            changed = True
    if changed:
        save_raw(data)
    return data


def save_raw(rows: list[dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            DATA_FILE.with_suffix(".bak.json").write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
    tmp = DATA_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA_FILE)


def with_priority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for idx, item in enumerate(rows, start=1):
        clean = dict(item)
        clean["id"] = idx
        result.append(clean)
    return result


def clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "Em Andamento").strip()
    status = STATUS_ALIASES.get(status, status)
    if status not in ALLOWED_STATUS:
        status = "Em Andamento"
    return {
        "cliente": str(payload.get("cliente") or "Geral").strip() or "Geral",
        "data": str(payload.get("data") or "").strip(),
        "melhoria": str(payload.get("melhoria") or "").strip(),
        "observacao": str(payload.get("observacao") or "").strip(),
        "responsavel": str(payload.get("responsavel") or "").strip(),
        "prazo": str(payload.get("prazo") or "").strip(),
        "status": status,
    }


def current_user(payload: dict[str, Any]) -> str:
    return str(payload.get("user") or "").strip().lower()


def find_index_by_uid(rows: list[dict[str, Any]], uid: str) -> int:
    uid = str(uid or "").strip()
    for idx, row in enumerate(rows):
        if str(row.get("uid")) == uid:
            return idx
    return -1


@app.get("/")
def index():
    template_path = BASE_DIR / "templates" / "index.html"
    html = template_path.read_text(encoding="utf-8")
    return inject_frontend_auth_config(html)


@app.get("/api/demandas")
def listar_demandas():
    with LOCK:
        rows = load_raw()
        return jsonify({"demandas": with_priority(rows)})


@app.post("/api/demandas")
def criar_demanda():
    payload = request.get_json(silent=True) or {}
    clean = clean_payload(payload)
    if not clean["melhoria"] or not clean["responsavel"]:
        return jsonify({"error": "Preencha pelo menos Melhoria e Responsável."}), 400
    with LOCK:
        rows = load_raw()
        rows.append({"uid": uuid.uuid4().hex, **clean})
        save_raw(rows)
        return jsonify({"ok": True, "demandas": with_priority(rows)})


@app.put("/api/demandas/<uid>")
def editar_demanda(uid: str):
    payload = request.get_json(silent=True) or {}
    clean = clean_payload(payload)
    if not clean["melhoria"] or not clean["responsavel"]:
        return jsonify({"error": "Preencha pelo menos Melhoria e Responsável."}), 400
    with LOCK:
        rows = load_raw()
        idx = find_index_by_uid(rows, uid)
        if idx < 0 and uid.isdigit():
            idx = int(uid) - 1
        if idx < 0 or idx >= len(rows):
            return jsonify({"error": "Demanda não encontrada."}), 404
        rows[idx].update(clean)
        save_raw(rows)
        return jsonify({"ok": True, "demandas": with_priority(rows)})


@app.delete("/api/demandas/<uid>")
def excluir_demanda(uid: str):
    payload = request.get_json(silent=True) or {}
    user = current_user(payload)
    if user not in get_delete_allowed():
        return jsonify({"error": "Exclusão liberada apenas para usuários com permissão de exclusão."}), 403
    with LOCK:
        rows = load_raw()
        idx = find_index_by_uid(rows, uid)
        if idx < 0 and uid.isdigit():
            idx = int(uid) - 1
        if idx < 0 or idx >= len(rows):
            return jsonify({"error": "Demanda não encontrada."}), 404
        rows.pop(idx)
        save_raw(rows)
        return jsonify({"ok": True, "demandas": with_priority(rows)})


@app.post("/api/reorder")
def reordenar_demandas():
    payload = request.get_json(silent=True) or {}
    uid_order = [str(x) for x in payload.get("ids", [])]
    with LOCK:
        rows = load_raw()
        by_uid = {str(row.get("uid")): row for row in rows}
        if set(uid_order) != set(by_uid.keys()):
            return jsonify({"error": "A lista de prioridades ficou desatualizada. Atualize a página e tente novamente."}), 409
        rows = [by_uid[uid] for uid in uid_order]
        save_raw(rows)
        return jsonify({"ok": True, "demandas": with_priority(rows)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
