from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from functools import wraps

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "demandas.db"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_RENDER = bool(os.environ.get("RENDER"))
USE_POSTGRES = bool(DATABASE_URL)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "olos-fraseologia-cockpit-v1-8")

USERS = {
    "admin": "olos123",
    "elvis": "olos123",
    "michele": "olos123",
    "nubia": "olos123",
    "marcelo": "olos123",
    "hilde": "olos123",
    "antonio": "olos123"
}

STATUS_LIST = ["Backlog", "Em análise", "Em desenvolvimento", "Homologação", "Concluído", "Cancelado"]
TIPO_LIST = ["Fraseologia", "Fluxo", "Validação CPF", "Oferta", "Encerramento", "Correção de lógica"]
RISCO_LIST = ["Baixo", "Médio", "Alto", "Crítico"]
PRIORIDADE_LIST = ["Altíssimo", "Alto", "Médio", "Baixo", "Baixíssimo"]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def db_mode_name():
    return "PostgreSQL compartilhado" if USE_POSTGRES else "SQLite local"


def placeholder():
    return "%s" if USE_POSTGRES else "?"


def get_conn():
    if USE_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError("psycopg2-binary não está instalado. Verifique o requirements.txt.")
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetchall(sql, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def fetchone(sql, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
    return dict(row) if row else None


def execute(sql, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()


def execute_many(sql, params_list):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executemany(sql, params_list)
        conn.commit()


def column_exists(table_name, column_name):
    if USE_POSTGRES:
        row = fetchone(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            [table_name, column_name]
        )
        return row is not None

    rows = fetchall(f"PRAGMA table_info({table_name})")
    return any(r["name"] == column_name for r in rows)


def score_from_prioridade(nivel):
    mapa = {
        "Altíssimo": 5.0,
        "Alto": 4.0,
        "Médio": 3.0,
        "Baixo": 2.0,
        "Baixíssimo": 1.0
    }
    return mapa.get(nivel or "Médio", 3.0)


def calc_prioridade(impacto, recorrencia, urgencia, esforco, risco):
    score = (impacto * 0.30) + (recorrencia * 0.25) + (urgencia * 0.25) + (risco * 0.20) - (esforco * 0.10)
    score = round(max(score, 0), 2)

    if score >= 4.2:
        nivel = "Altíssimo"
    elif score >= 3.4:
        nivel = "Alto"
    elif score >= 2.6:
        nivel = "Médio"
    elif score >= 1.8:
        nivel = "Baixo"
    else:
        nivel = "Baixíssimo"

    return score, nivel


def init_db():
    id_definition = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

    execute(f"""
        CREATE TABLE IF NOT EXISTS demandas (
            id {id_definition},
            call_id TEXT,
            previous_asr TEXT,
            frase_atual TEXT,
            sugestao TEXT,
            melhoria TEXT DEFAULT '',
            obs TEXT,
            tipo TEXT DEFAULT 'Fraseologia',
            responsavel TEXT DEFAULT '',
            status TEXT DEFAULT 'Backlog',
            impacto INTEGER DEFAULT 3,
            recorrencia INTEGER DEFAULT 3,
            urgencia INTEGER DEFAULT 3,
            esforco INTEGER DEFAULT 2,
            risco INTEGER DEFAULT 3,
            score_prioridade REAL DEFAULT 0,
            nivel_prioridade TEXT DEFAULT 'Médio',
            data_criacao TEXT,
            data_prevista TEXT DEFAULT '',
            data_conclusao TEXT DEFAULT '',
            prioridade_ordem INTEGER DEFAULT 0,
            criado_por TEXT DEFAULT ''
        )
    """)

    migrations = {
        "prioridade_ordem": "INTEGER DEFAULT 0",
        "criado_por": "TEXT DEFAULT ''",
        "melhoria": "TEXT DEFAULT ''"
    }

    for col, definition in migrations.items():
        if not column_exists("demandas", col):
            execute(f"ALTER TABLE demandas ADD COLUMN {col} {definition}")

    execute("""
        UPDATE demandas
        SET criado_por = CASE
            WHEN COALESCE(criado_por, '') = '' THEN 'admin'
            ELSE criado_por
        END
    """)

    execute("""
        UPDATE demandas
        SET melhoria = CASE
            WHEN tipo <> 'Fraseologia' AND COALESCE(melhoria, '') = '' AND COALESCE(sugestao, '') <> '' THEN sugestao
            ELSE COALESCE(melhoria, '')
        END
    """)

    sem_ordem = fetchall("""
        SELECT id
        FROM demandas
        WHERE COALESCE(prioridade_ordem, 0) = 0
        ORDER BY score_prioridade DESC, id ASC
    """)

    ph = placeholder()
    for idx, item in enumerate(sem_ordem, start=1):
        execute(f"UPDATE demandas SET prioridade_ordem = {ph} WHERE id = {ph}", [idx, item["id"]])

    antigas = fetchall("""
        SELECT id, impacto, recorrencia, urgencia, esforco, risco
        FROM demandas
        WHERE nivel_prioridade LIKE 'P%'
    """)

    for item in antigas:
        score, nivel = calc_prioridade(
            int(item["impacto"]), int(item["recorrencia"]), int(item["urgencia"]),
            int(item["esforco"]), int(item["risco"])
        )
        execute(
            f"UPDATE demandas SET score_prioridade = {ph}, nivel_prioridade = {ph} WHERE id = {ph}",
            [score, nivel, item["id"]]
        )

    load_demo_data = os.environ.get("LOAD_DEMO_DATA", "false").lower() == "true"
    total = fetchone("SELECT COUNT(*) AS qtd FROM demandas")["qtd"]

    if total == 0 and load_demo_data:
        seed_demo_data()


def seed_demo_data():
    seed = [
        ("0018c1ff2fb47eb8", "Alô?", "Oi. Aqui é a Isa da Sky, posso falar com THIAGO?", "Olá, aqui é a Isa da Sky. Eu falo com Thiago?", "", "Fraseologia", 4, 4, 4, 1, 3),
        ("0018c1ff2fb47eb8", "Sim.", "Eu tenho uma informação importante pra você e sei que os dois últimos dígitos do seu CPF são cinquenta e quatro, pra continuar me fala os três primeiros dígitos do seu CPF, por favor?", "Obrigada. Para sua segurança, preciso confirmar uma informação rápida. Os dois últimos dígitos do seu CPF são cinquenta e quatro. Você pode me informar os três primeiros dígitos, por favor?", "", "Validação CPF", 4, 3, 4, 2, 4),
        ("0018c1ff2fb47eb8", "000.", "Obrigado pela confirmação. Este contato é para informar sobre uma pendência na sua conta e te apoiar na regularização. Gostaria de saber se você já pagou a conta em atraso com a Sky no valor total de cento e noventa e oito reais e cinquenta centavos que venceu em treze de março de dois mil e vinte e seis. Você já efetuou o pagamento?", "Obrigada pela confirmação. Identificamos uma pendência na sua conta Sky, no valor de cento e noventa e oito reais e cinquenta centavos, com vencimento em <Vencimento aa/mm>. Consegue fazer o pagamento desse valor hoje?", "Ofertar o Valor Original", "Oferta", 5, 4, 5, 2, 4),
    ]

    ph = placeholder()
    sql = f"""
        INSERT INTO demandas (
            call_id, previous_asr, frase_atual, sugestao, melhoria, obs, tipo,
            impacto, recorrencia, urgencia, esforco, risco,
            score_prioridade, nivel_prioridade, data_criacao, prioridade_ordem, criado_por
        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """

    params = []
    for idx, row in enumerate(seed, start=1):
        score, nivel = calc_prioridade(row[6], row[7], row[8], row[9], row[10])
        params.append(row[:4] + ("",) + row[4:6] + row[6:] + (score, nivel, datetime.now().strftime("%Y-%m-%d"), idx, "admin"))

    execute_many(sql, params)


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        if usuario in USERS and USERS[usuario] == senha:
            session["logged_in"] = True
            session["usuario"] = usuario
            return redirect(url_for("index"))

        erro = "Usuário ou senha inválidos."

    return render_template("login.html", erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        status_list=STATUS_LIST,
        tipo_list=TIPO_LIST,
        risco_list=RISCO_LIST,
        prioridade_list=PRIORIDADE_LIST
    )


@app.route("/api/db-status")
@login_required
def db_status():
    return jsonify({
        "mode": db_mode_name(),
        "using_postgres": USE_POSTGRES,
        "database_url_configured": bool(DATABASE_URL),
        "render": IS_RENDER,
        "warning": "" if USE_POSTGRES else "ATENÇÃO: usando SQLite local. Em Render, os dados não são compartilhados entre usuários e podem sumir após restart/deploy."
    })


@app.route("/api/demandas")
@login_required
def listar_demandas():
    status = request.args.get("status", "")
    tipo = request.args.get("tipo", "")
    busca = request.args.get("busca", "")
    ph = placeholder()

    where = []
    params = []

    if status:
        where.append(f"status = {ph}")
        params.append(status)

    if tipo:
        where.append(f"tipo = {ph}")
        params.append(tipo)

    if busca:
        where.append(f"(call_id LIKE {ph} OR previous_asr LIKE {ph} OR frase_atual LIKE {ph} OR sugestao LIKE {ph} OR melhoria LIKE {ph} OR obs LIKE {ph})")
        like = f"%{busca}%"
        params.extend([like, like, like, like, like, like])

    query = "SELECT * FROM demandas"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY COALESCE(prioridade_ordem, 999999) ASC, score_prioridade DESC, id DESC"

    rows = fetchall(query, params)
    return jsonify(rows)


@app.route("/api/resumo")
@login_required
def resumo():
    dados = fetchall("SELECT * FROM demandas")

    total = len(dados)
    concluidas = sum(1 for d in dados if d["status"] == "Concluído")
    backlog = sum(1 for d in dados if d["status"] == "Backlog")
    altissimo = sum(1 for d in dados if d["nivel_prioridade"] == "Altíssimo")
    score_medio = round(sum(float(d["score_prioridade"] or 0) for d in dados) / total, 2) if total else 0

    por_status = {}
    por_tipo = {}

    for d in dados:
        por_status[d["status"]] = por_status.get(d["status"], 0) + 1
        por_tipo[d["tipo"]] = por_tipo.get(d["tipo"], 0) + 1

    return jsonify({
        "total": total,
        "concluidas": concluidas,
        "backlog": backlog,
        "altissimo": altissimo,
        "score_medio": score_medio,
        "por_status": por_status,
        "por_tipo": por_tipo
    })


@app.route("/api/demandas", methods=["POST"])
@login_required
def criar_demanda():
    data = request.json or {}
    nivel = data.get("nivel_prioridade", "Médio")
    score = score_from_prioridade(nivel)
    ph = placeholder()

    sql = f"""
        INSERT INTO demandas (
            call_id, previous_asr, frase_atual, sugestao, melhoria, obs, tipo,
            responsavel, status, impacto, recorrencia, urgencia, esforco, risco,
            score_prioridade, nivel_prioridade, data_criacao, data_prevista, prioridade_ordem, criado_por
        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """

    params = [
        data.get("call_id", ""),
        data.get("previous_asr", ""),
        data.get("frase_atual", ""),
        data.get("sugestao", ""),
        data.get("melhoria", ""),
        data.get("obs", ""),
        data.get("tipo", "Fraseologia"),
        data.get("responsavel", ""),
        data.get("status", "Backlog"),
        int(data.get("impacto", 3)),
        int(data.get("recorrencia", 3)),
        int(data.get("urgencia", 3)),
        int(data.get("esforco", 2)),
        int(data.get("risco", 3)),
        score,
        nivel,
        datetime.now().strftime("%Y-%m-%d"),
        data.get("data_prevista", ""),
        int(data.get("prioridade_ordem") or 999999),
        session.get("usuario", "admin")
    ]

    execute(sql, params)
    return jsonify({"ok": True})


@app.route("/api/demandas/<int:demanda_id>", methods=["PUT"])
@login_required
def atualizar_demanda(demanda_id):
    data = request.json or {}
    nivel = data.get("nivel_prioridade", "Médio")
    score = score_from_prioridade(nivel)
    ph = placeholder()

    campos = [
        "call_id", "previous_asr", "frase_atual", "sugestao", "melhoria", "obs", "tipo",
        "responsavel", "status", "nivel_prioridade", "impacto", "recorrencia", "urgencia",
        "esforco", "risco", "data_prevista", "data_conclusao", "prioridade_ordem"
    ]

    update = []
    params = []

    for c in campos:
        if c in data:
            update.append(f"{c} = {ph}")
            params.append(data[c])

    update.append(f"score_prioridade = {ph}")
    params.append(score)
    update.append(f"nivel_prioridade = {ph}")
    params.append(nivel)

    params.append(demanda_id)

    execute(f"UPDATE demandas SET {', '.join(update)} WHERE id = {ph}", params)
    return jsonify({"ok": True})


@app.route("/api/reordenar", methods=["POST"])
@login_required
def reordenar_demandas():
    data = request.json or {}
    ids = data.get("ids", [])
    ph = placeholder()

    for idx, demanda_id in enumerate(ids, start=1):
        execute(f"UPDATE demandas SET prioridade_ordem = {ph} WHERE id = {ph}", [idx, int(demanda_id)])

    return jsonify({"ok": True})


@app.route("/api/demandas/<int:demanda_id>", methods=["DELETE"])
@login_required
def deletar_demanda(demanda_id):
    ph = placeholder()
    execute(f"DELETE FROM demandas WHERE id = {ph}", [demanda_id])
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
