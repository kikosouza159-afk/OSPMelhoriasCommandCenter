# Esteira de Demandas - Postgres Forçado

Esta versão foi ajustada para evitar que o painel volte para dados antigos quando o Render dormir, reiniciar ou fizer deploy.

## Variáveis obrigatórias no Render

Configure no Web Service:

```text
DATABASE_URL=<Internal Database URL do Postgres>
FORCE_POSTGRES=1
```

`FORCE_POSTGRES=1` é o padrão. Com ele ativo, o app não usa `data/demandas.json` como fallback.

## Comandos Render

```text
Build command: pip install -r requirements.txt
Start command: gunicorn app:app
```

## Teste rápido

Acesse:

```text
/sapi/health
```

ou:

```text
/api/health
```

O retorno precisa mostrar:

```json
{"storage":"postgres","database_url_configurada":true}
```
