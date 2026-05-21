from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:  # keeps local JSON fallback working if psycopg2 is not installed
    psycopg2 = None
    RealDictCursor = None

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = Path(os.environ.get("DATA_FILE", DATA_DIR / "demandas.json"))

# Render/Postgres: configure a variável DATABASE_URL no Web Service.
# Exemplo: DATABASE_URL=postgresql://usuario:senha@host:5432/banco
DATABASE_URL = os.getenv("DATABASE_URL")
FORCE_POSTGRES = os.getenv("FORCE_POSTGRES", "1").strip() != "0"
USE_POSTGRES = bool(DATABASE_URL)

LOCK = threading.Lock()


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Para incluir usuários, altere apenas este bloco.
# pode_excluir=True libera exclusão de demandas.
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


def build_users() -> dict[str, str]:
    return {str(u["usuario"]).strip().lower(): str(u["senha"]) for u in USER_ACCESS}


def build_delete_allowed() -> set[str]:
    return {
        str(u["usuario"]).strip().lower()
        for u in USER_ACCESS
        if bool(u.get("pode_excluir"))
    }


USERS = build_users()
DELETE_ALLOWED = build_delete_allowed()

ALLOWED_STATUS = {"Em Andamento", "Concluído", "Pendentes", "Paralisado"}
STATUS_ALIASES = {
    "Pendente": "Pendentes",
    "pendente": "Pendentes",
    "PENDENTE": "Pendentes",
    "pendentes": "Pendentes",
    "PENDENTES": "Pendentes",
}

# Não popular mais com demandas antigas do código.
# Com Postgres, se não houver dados, o painel abre vazio.
DEFAULT_DEMANDAS: list[dict[str, Any]] = []


def get_db_connection():
    if not USE_POSTGRES:
        return None
    if psycopg2 is None:
        raise RuntimeError("psycopg2-binary não está instalado. Inclua no requirements.txt.")
    return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
    if not USE_POSTGRES:
        return
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS demandas (
                    uid TEXT PRIMARY KEY,
                    prioridade INTEGER NOT NULL,
                    cliente TEXT NOT NULL DEFAULT 'Geral',
                    data TEXT NOT NULL DEFAULT '',
                    melhoria TEXT NOT NULL DEFAULT '',
                    observacao TEXT NOT NULL DEFAULT '',
                    responsavel TEXT NOT NULL DEFAULT '',
                    prazo TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Em Andamento',
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_demandas_prioridade ON demandas(prioridade);")
        conn.commit()


def ensure_data_file() -> None:
    if USE_POSTGRES:
        init_db()
        return

    # Segurança para produção no Render:
    # se DATABASE_URL não estiver configurada, NÃO volta para JSON antigo nem dados mockados.
    # Isso evita o efeito "voltou tudo" após sleep/redeploy do Render.
    if FORCE_POSTGRES:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        rows = [{"uid": uuid.uuid4().hex, **item} for item in DEFAULT_DEMANDAS]
        save_raw(rows)


def load_raw() -> list[dict[str, Any]]:
    ensure_data_file()

    if USE_POSTGRES:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT uid, cliente, data, melhoria, observacao, responsavel, prazo, status
                    FROM demandas
                    ORDER BY prioridade ASC, criado_em ASC;
                    """
                )
                rows = [dict(row) for row in cur.fetchall()]
        return normalize_rows(rows, persist=False)

    if FORCE_POSTGRES:
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = []
    if not isinstance(data, list):
        data = []

    return normalize_rows(data, persist=True)


def normalize_rows(rows: list[dict[str, Any]], persist: bool = False) -> list[dict[str, Any]]:
    changed = False
    cleaned_rows = []

    for item in rows:
        if not isinstance(item, dict):
            changed = True
            continue
        clean = dict(item)
        if "uid" not in clean or not clean.get("uid"):
            clean["uid"] = uuid.uuid4().hex
            changed = True
        if "cliente" not in clean or not clean.get("cliente"):
            clean["cliente"] = "Geral"
            changed = True
        clean["status"] = STATUS_ALIASES.get(str(clean.get("status", "")).strip(), clean.get("status", "Em Andamento"))
        if clean["status"] not in ALLOWED_STATUS:
            clean["status"] = "Em Andamento"
            changed = True
        cleaned_rows.append(clean)

    if changed and persist:
        save_raw(cleaned_rows)
    return cleaned_rows


def save_raw(rows: list[dict[str, Any]]) -> None:
    if USE_POSTGRES:
        init_db()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM demandas;")
                for prioridade, row in enumerate(rows, start=1):
                    cur.execute(
                        """
                        INSERT INTO demandas
                            (uid, prioridade, cliente, data, melhoria, observacao, responsavel, prazo, status, atualizado_em)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                        """,
                        (
                            str(row.get("uid") or uuid.uuid4().hex),
                            prioridade,
                            str(row.get("cliente") or "Geral"),
                            str(row.get("data") or ""),
                            str(row.get("melhoria") or ""),
                            str(row.get("observacao") or ""),
                            str(row.get("responsavel") or ""),
                            str(row.get("prazo") or ""),
                            str(row.get("status") or "Em Andamento"),
                        ),
                    )
            conn.commit()
        return

    if FORCE_POSTGRES:
        # Em produção, não gravar fallback local. O painel deve usar DATABASE_URL.
        return

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


def users_text() -> str:
    nomes = list(USERS.keys())
    if not nomes:
        return "Nenhum usuário configurado."
    if len(nomes) == 1:
        return nomes[0]
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


@app.get("/")
def index():
    return render_template(
        "index.html",
        users=USERS,
        delete_allowed=sorted(DELETE_ALLOWED),
        users_text=users_text(),
        storage_mode="Postgres" if USE_POSTGRES else "DATABASE_URL ausente",
    )


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "storage": "postgres" if USE_POSTGRES else "sem_database_url",
        "database_url_configurada": bool(DATABASE_URL),
        "force_postgres": FORCE_POSTGRES,
        "aviso": "DATABASE_URL ausente. O painel não vai usar JSON local." if not USE_POSTGRES else "Postgres ativo."
    })


@app.get("/api/demandas")
def listar_demandas():
    with LOCK:
        rows = load_raw()
        return jsonify({"demandas": with_priority(rows), "storage": "postgres" if USE_POSTGRES else "json"})


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
    if user not in DELETE_ALLOWED:
        return jsonify({"error": "Exclusão liberada apenas para usuários autorizados."}), 403
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
