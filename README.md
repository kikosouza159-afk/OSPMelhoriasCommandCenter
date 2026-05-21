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


## Correção de persistência aplicada

Esta versão não usa `localStorage` para salvar demandas. O navegador guarda apenas o usuário logado.
Todas as demandas são lidas e gravadas no arquivo único do servidor:

```text
data/demandas.json
```

Também foi aplicado `cache: no-store` no front-end e cabeçalhos `no-cache` no Flask, para evitar que a página recarregue dados antigos após salvar.

### Importante no Render

Se o serviço reiniciar ou se você fizer novo deploy, o disco padrão do Render pode voltar para os arquivos do repositório. Para manter as demandas mesmo após reinício/deploy, crie um **Persistent Disk** no Render e configure a variável de ambiente abaixo apontando para esse disco:

```text
DATA_FILE=/var/data/demandas.json
```

Sem persistent disk, as demandas ficam salvas entre atualizações da página, mas podem ser perdidas em redeploy/restart do serviço.

## Persistência com Postgres no Render

Configure no Web Service do Render a variável de ambiente:

```text
DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

Com `DATABASE_URL` configurada, o painel salva e lê as demandas no Postgres. Sem essa variável, ele usa JSON local apenas para testes.

Para incluir usuários, edite apenas o bloco `USER_ACCESS` no `app.py`.
