# Cockpit V1.5

Login animado + menu executivo de clientes + painel TALENTOS integrado.

## O que mudou na V1.5
- O card TALENTOS agora abre o projeto `locator_dashboard_flask_v30_tabulacao` dentro do Cockpit.
- Rotas internas da TALENTOS:
  - `/cliente/talentos/painel`
  - `/cliente/talentos/painel/comparativo`
  - `/cliente/talentos/painel/tabulacao`
- Visual do painel TALENTOS ajustado para combinar com o fundo tecnológico do Cockpit.
- Botão de retorno para o menu principal.

## Login padrão
- Usuário: admin
- Senha: 123456

## Base de dados
Coloque o arquivo Excel em:

```bash
data/base.xlsx
```

Ou configure uma variável de ambiente:

```bash
EXCEL_PATH=C:\caminho\base.xlsx
```

## Rodar localmente
```bash
pip install -r requirements.txt
python app.py
```

Acesse:

```bash
http://127.0.0.1:5000
```

## Render
Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app
```


## Ajuste V1.5
- Corrigido conflito CSS da classe `.grid` que deformava os gráficos.
- Containers de gráficos e tabelas travados para evitar estouro visual.
