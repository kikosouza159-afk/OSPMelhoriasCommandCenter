from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from pathlib import Path
from datetime import datetime
from functools import wraps

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "demandas.db"

app = Flask(__name__)
app.secret_key = "olos-fraseologia-cockpit-v1-2"

LOGIN_USER = "admin"
LOGIN_PASSWORD = "olos123"

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

STATUS_LIST = ["Backlog", "Em análise", "Em desenvolvimento", "Homologação", "Concluído", "Cancelado"]
TIPO_LIST = ["Fraseologia", "Fluxo", "Validação CPF", "Oferta", "Encerramento", "Correção de lógica"]
RISCO_LIST = ["Baixo", "Médio", "Alto", "Crítico"]
PRIORIDADE_LIST = ["Altíssimo", "Alto", "Médio", "Baixo", "Baixíssimo"]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    """
    Score simplificado:
    Prioridade = (Impacto * 0.30) + (Recorrência * 0.25) + (Urgência * 0.25) + (Risco * 0.20) - (Esforço * 0.10)

    Classificação:
    - Altíssimo
    - Alto
    - Médio
    - Baixo
    - Baixíssimo
    """
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
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demandas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # Migração V1.4: coluna manual para ordenação/prioridade da esteira
        cols = [c["name"] for c in conn.execute("PRAGMA table_info(demandas)").fetchall()]
        if "prioridade_ordem" not in cols:
            conn.execute("ALTER TABLE demandas ADD COLUMN prioridade_ordem INTEGER DEFAULT 0")

        sem_ordem = conn.execute("""
            SELECT id
            FROM demandas
            WHERE COALESCE(prioridade_ordem, 0) = 0
            ORDER BY score_prioridade DESC, id ASC
        """).fetchall()
        for idx, item in enumerate(sem_ordem, start=1):
            conn.execute(
                "UPDATE demandas SET prioridade_ordem = ? WHERE id = ?",
                (idx, item["id"])
            )


        # Migração V1.5.3 cadastro objetivo: usuário que inseriu a demanda
        cols_criado = [c["name"] for c in conn.execute("PRAGMA table_info(demandas)").fetchall()]
        if "criado_por" not in cols_criado:
            conn.execute("ALTER TABLE demandas ADD COLUMN criado_por TEXT DEFAULT ''")
        conn.execute("""
            UPDATE demandas
            SET criado_por = CASE
                WHEN COALESCE(criado_por, '') = '' THEN 'admin'
                ELSE criado_por
            END
        """)


        # Migração V1.5.4: campo Melhoria para demandas que não são de fraseologia
        cols_melhoria = [c["name"] for c in conn.execute("PRAGMA table_info(demandas)").fetchall()]
        if "melhoria" not in cols_melhoria:
            conn.execute("ALTER TABLE demandas ADD COLUMN melhoria TEXT DEFAULT ''")
            conn.execute("""
                UPDATE demandas
                SET melhoria = CASE
                    WHEN tipo <> 'Fraseologia' AND COALESCE(sugestao, '') <> '' THEN sugestao
                    ELSE COALESCE(melhoria, '')
                END
            """)

        total = conn.execute("SELECT COUNT(*) AS qtd FROM demandas").fetchone()["qtd"]
        if total == 0:
            seed = [
                ("0018c1ff2fb47eb8","Alô?","Oi. Aqui é a Isa da Sky, posso falar com THIAGO?","Olá, aqui é a Isa da Sky. Eu falo com Thiago?","","Fraseologia",4,4,4,1,3),
                ("0018c1ff2fb47eb8","Sim.","Eu tenho uma informação importante pra você e sei que os dois últimos dígitos do seu CPF são cinquenta e quatro, pra continuar me fala os três primeiros dígitos do seu CPF, por favor?","Obrigada. Para sua segurança, preciso confirmar uma informação rápida. Os dois últimos dígitos do seu CPF são cinquenta e quatro. Você pode me informar os três primeiros dígitos, por favor?","","Validação CPF",4,3,4,2,4),
                ("0018c1ff2fb47eb8","000.","Obrigado pela confirmação. Este contato é para informar sobre uma pendência na sua conta e te apoiar na regularização. Gostaria de saber se você já pagou a conta em atraso com a Sky no valor total de cento e noventa e oito reais e cinquenta centavos que venceu em treze de março de dois mil e vinte e seis. Você já efetuou o pagamento?","Obrigada pela confirmação. Identificamos uma pendência na sua conta Sky, no valor de cento e noventa e oito reais e cinquenta centavos, com vencimento em <Vencimento aa/mm>. Consegue fazer o pagamento desse valor hoje?","Ofertar o Valor Original","Oferta",5,4,5,2,4),
                ("0018c1ff2fb47eb8","Não.","Certo, e você consegue fazer o pagamento do valor total de cento e noventa e oito reais e cinquenta centavos até hoje?","Retirar","","Correção de lógica",5,5,5,2,5),
                ("0018c1ff2fb47eb8","Também não.","Posso te oferecer o pagamento com desconto para amanhã, no valor de cento e noventa e oito reais e cinquenta centavos. Você consegue pagar nessa data?","Sem problema. Tenho uma opção para pagamento até amanhã com desconto, no valor de cento e noventa e oito reais e cinquenta centavos. Você consegue seguir com essa opção?","2ª Oferta Com Desconto","Oferta",4,4,4,2,3),
                ("0018c1ff2fb47eb8","Não consigo.","Posso te oferecer o pagamento com desconto para o dia quinze de maio de dois mil e vinte e seis, no valor de cento e noventa e oito reais e cinquenta centavos. Você consegue pagar nessa data?","Entendi. Como última opção disponível, consigo ofertar o pagamento até o dia quinze de maio de dois mil e vinte e seis, no valor de cento e noventa e oito reais e cinquenta centavos. Você consegue realizar até essa data?","3ª Oferta com Desconto","Oferta",4,4,4,2,3),
                ("0018c1ff2fb47eb8","Não.","Certo, e que dia você consegue fazer o pagamento?","Retirar","Não faz sentido perguntar qual data que o cliente consegue fazer o pagamento. A última data é D+2.","Correção de lógica",5,5,5,1,5),
                ("0018c1ff2fb47eb8","Só dia 20.","Entendo, eu não consigo te ofertar nessa data, mas vou registrar aqui que você ainda não consegue realizar o pagamento. A Sky agradece a sua atenção, tenha um bom dia.","Entendo. Como o prazo disponível para esta oferta é somente até o dia quinze de maio de dois mil e vinte e seis, não consigo seguir com a data informada. Vou registrar a sua indisponibilidade no momento. A Sky agradece o seu atendimento. Tenha um bom dia.","Em caso de Recusa, finalizar","Encerramento",4,4,4,2,3),
                ("0018c2082fb482e2","Alô?","Oi. Aqui é a Isa da Sky, posso falar com THIAGO?","Olá, aqui é a Isa da Sky. Eu falo com Thiago?","","Fraseologia",4,4,4,1,3),
                ("0018c2082fb482e2","Não conheço.","Tudo bem. Se precisar falar com o THIAGO, pode me informar um horário que eu possa ligar para ele?","Tudo bem. Você teria outro número para eu tentar falar com o Thiago? Se você não conhece ele, sem problema, é só me avisar.","A frase atual está incoerente, pois pede horário mesmo após a pessoa dizer que não conhece o cliente. A sugestão valida a informação e dá chance de correção sem insistir indevidamente.","Correção de lógica",5,4,5,2,5),
                ("0018c2082fb482e2","Mas eu não conheço.","Entendi. Então, não consigo ajudar com essa ligação. A Sky agradece a sua atenção, tenha um bom dia.","Entendi. Vou registrar que este telefone não pertence ao Thiago ou que você não o conhece. A Sky agradece sua atenção. Tenha um bom dia.","O encerramento fica mais correto e operacional. Em vez de dizer não consigo ajudar, o bot registra o motivo real da negativa e encerra com clareza.","Encerramento",4,3,4,2,4),
            ]
            for idx, row in enumerate(seed, start=1):
                score, nivel = calc_prioridade(row[6], row[7], row[8], row[9], row[10])
                conn.execute("""
                    INSERT INTO demandas (
                        call_id, previous_asr, frase_atual, sugestao, melhoria, obs, tipo,
                        impacto, recorrencia, urgencia, esforco, risco,
                        score_prioridade, nivel_prioridade, data_criacao, prioridade_ordem, criado_por
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row[:4] + ("",) + row[4:6] + row[6:] + (score, nivel, datetime.now().strftime("%Y-%m-%d"), idx, "admin"))

        # Migração visual de prioridades antigas para a nova régua simplificada
        antigas = conn.execute("""
            SELECT id, impacto, recorrencia, urgencia, esforco, risco
            FROM demandas
            WHERE nivel_prioridade LIKE 'P%'
        """).fetchall()
        for item in antigas:
            score, nivel = calc_prioridade(
                int(item["impacto"]), int(item["recorrencia"]), int(item["urgencia"]),
                int(item["esforco"]), int(item["risco"])
            )
            conn.execute(
                "UPDATE demandas SET score_prioridade = ?, nivel_prioridade = ? WHERE id = ?",
                (score, nivel, item["id"])
            )
        conn.commit()

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        if usuario == LOGIN_USER and senha == LOGIN_PASSWORD:
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
    return render_template("index.html", status_list=STATUS_LIST, tipo_list=TIPO_LIST, risco_list=RISCO_LIST, prioridade_list=PRIORIDADE_LIST)

@app.route("/api/demandas")
@login_required
def listar_demandas():
    status = request.args.get("status", "")
    tipo = request.args.get("tipo", "")
    busca = request.args.get("busca", "")

    where = []
    params = []

    if status:
        where.append("status = ?")
        params.append(status)
    if tipo:
        where.append("tipo = ?")
        params.append(tipo)
    if busca:
        where.append("(call_id LIKE ? OR previous_asr LIKE ? OR frase_atual LIKE ? OR sugestao LIKE ? OR melhoria LIKE ? OR obs LIKE ?)")
        like = f"%{busca}%"
        params.extend([like, like, like, like, like, like])

    query = "SELECT * FROM demandas"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY COALESCE(prioridade_ordem, 999999) ASC, score_prioridade DESC, id DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/resumo")
@login_required
def resumo():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM demandas").fetchall()
    dados = [dict(r) for r in rows]

    total = len(dados)
    concluidas = sum(1 for d in dados if d["status"] == "Concluído")
    backlog = sum(1 for d in dados if d["status"] == "Backlog")
    altissimo = sum(1 for d in dados if d["nivel_prioridade"] == "Altíssimo")
    score_medio = round(sum(float(d["score_prioridade"]) for d in dados) / total, 2) if total else 0

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

    impacto = int(data.get("impacto", 3))
    recorrencia = int(data.get("recorrencia", 3))
    urgencia = int(data.get("urgencia", 3))
    esforco = int(data.get("esforco", 2))
    risco = int(data.get("risco", 3))
    nivel = data.get("nivel_prioridade", "Médio")
    score = score_from_prioridade(nivel)

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO demandas (
                call_id, previous_asr, frase_atual, sugestao, melhoria, obs, tipo,
                responsavel, status, impacto, recorrencia, urgencia, esforco, risco,
                score_prioridade, nivel_prioridade, data_criacao, data_prevista, prioridade_ordem, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("call_id", ""),
            data.get("previous_asr", ""),
            data.get("frase_atual", ""),
            data.get("sugestao", ""),
            data.get("melhoria", ""),
            data.get("obs", ""),
            data.get("tipo", "Fraseologia"),
            data.get("responsavel", ""),
            data.get("status", "Backlog"),
            impacto, recorrencia, urgencia, esforco, risco,
            score, nivel,
            datetime.now().strftime("%Y-%m-%d"),
            data.get("data_prevista", ""),
            int(data.get("prioridade_ordem") or 999999),
            session.get("usuario", "admin")
        ))
        conn.commit()

    return jsonify({"ok": True})

@app.route("/api/demandas/<int:demanda_id>", methods=["PUT"])
@login_required
def atualizar_demanda(demanda_id):
    data = request.json or {}
    campos = [
        "call_id", "previous_asr", "frase_atual", "sugestao", "melhoria", "obs", "tipo",
        "responsavel", "status", "nivel_prioridade", "impacto", "recorrencia", "urgencia", "esforco",
        "risco", "data_prevista", "data_conclusao", "prioridade_ordem"
    ]

    update = []
    params = []

    impacto = int(data.get("impacto", 3))
    recorrencia = int(data.get("recorrencia", 3))
    urgencia = int(data.get("urgencia", 3))
    esforco = int(data.get("esforco", 2))
    risco = int(data.get("risco", 3))
    nivel = data.get("nivel_prioridade", "Médio")
    score = score_from_prioridade(nivel)

    for c in campos:
        if c in data:
            update.append(f"{c} = ?")
            params.append(data[c])

    update.append("score_prioridade = ?")
    params.append(score)
    update.append("nivel_prioridade = ?")
    params.append(nivel)

    params.append(demanda_id)

    with get_conn() as conn:
        conn.execute(f"UPDATE demandas SET {', '.join(update)} WHERE id = ?", params)
        conn.commit()

    return jsonify({"ok": True})


@app.route("/api/reordenar", methods=["POST"])
@login_required
def reordenar_demandas():
    data = request.json or {}
    ids = data.get("ids", [])

    with get_conn() as conn:
        for idx, demanda_id in enumerate(ids, start=1):
            conn.execute(
                "UPDATE demandas SET prioridade_ordem = ? WHERE id = ?",
                (idx, int(demanda_id))
            )
        conn.commit()

    return jsonify({"ok": True})

@app.route("/api/demandas/<int:demanda_id>", methods=["DELETE"])
@login_required
def deletar_demanda(demanda_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM demandas WHERE id = ?", (demanda_id,))
        conn.commit()
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
