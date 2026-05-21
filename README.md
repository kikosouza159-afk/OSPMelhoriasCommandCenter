# Esteira Executiva de Demandas

Painel Flask para gestão compartilhada de demandas por cliente.

## Recursos

- Login com usuários pré-definidos.
- Fundo animado e interativo também na tela de login.
- Salvamento compartilhado em `data/demandas.json`.
- Campo **Cliente** por demanda.
- Filtro de cliente para organizar a esteira por carteira/cliente.
- Cards superiores clicáveis para filtrar por status.
- Drag and drop para reordenar prioridade.
- Status **Concluído** com destaque verde.
- Exclusão liberada somente para `admin` e `gerber`.
- Exportação CSV.

## Usuários

Todos usam a senha `olos123`:

- admin
- gerber
- elvis
- michele
- nubia
- marcelo
- hilde
- antonio

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py
```

Acesse:

```text
http://localhost:5000
```

## Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```
