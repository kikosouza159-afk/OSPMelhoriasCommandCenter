from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

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

USERS = {
    "admin": "olos123",
    "gerber": "olos123",
    "elvis": "olos123",
    "michele": "olos123",
    "nubia": "olos123",
    "marcelo": "olos123",
    "hilde": "olos123",
    "antonio": "olos123",
    "aleff.jesus": "olos123",
}
DELETE_ALLOWED = {"admin", "gerber"}
ALLOWED_STATUS = {"Em Andamento", "Concluído", "Pendentes", "Paralisado"}
STATUS_ALIASES = {"Pendente": "Pendentes", "pendente": "Pendentes", "PENDENTE": "Pendentes"}

DEFAULT_DEMANDAS = [
    {
        "cliente": "Sky",
        "data": "2026-05-20",
        "melhoria": "Retirar pergunta de nova data após negativa",
        "observacao": "Cliente informou que só consegue pagar dia 20. Bot não deve perguntar nova data fora da regra.",
        "responsavel": "Hildebrando",
        "prazo": "2026-05-22",
        "status": "Em Andamento",
    },
    {
        "cliente": "Sky",
        "data": "2026-05-20",
        "melhoria": "Corrigir fluxo de terceiro desconhecido",
        "observacao": "Quando a pessoa informar que não conhece o cliente, o fluxo deve validar telefone incorreto ou solicitar outro contato.",
        "responsavel": "Elvis",
        "prazo": "2026-05-23",
        "status": "Pendentes",
    },
    {
        "cliente": "Energisa",
        "data": "2026-05-21",
        "melhoria": "Normalizar nomes antes da vocalização",
        "observacao": "Padronizar nomes com acentuação e pronúncia para melhorar naturalidade e assertividade do atendimento.",
        "responsavel": "Hildebrando",
        "prazo": "2026-05-27",
        "status": "Em Andamento",
    },
    {
        "cliente": "Energisa",
        "data": "2026-05-21",
        "melhoria": "Revisar regra de encerramento por WhatsApp",
        "observacao": "Criar frase de encerramento com orientação objetiva para continuidade do atendimento via WhatsApp.",
        "responsavel": "Gerber",
        "prazo": "2026-05-29",
        "status": "Paralisado",
    },
    {
        "cliente": "Energisa",
        "data": "2026-05-22",
        "melhoria": "Homologar frase padrão de encerramento",
        "observacao": "Aplicar comunicação final: A Energisa agradece. Tenha um bom dia.",
        "responsavel": "Michele",
        "prazo": "2026-05-30",
        "status": "Concluído",
    },
]


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
    return render_template("index.html")


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
    if user not in DELETE_ALLOWED:
        return jsonify({"error": "Exclusão liberada apenas para Admin e Gerber."}), 403
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
