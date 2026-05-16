# Painel Gestão de Demandas de Fraseologia Bot - V1

Painel em Flask para controlar melhorias solicitadas ao time de desenvolvimento.

## O que tem nesta versão

- Cards executivos: total, P1 críticas, backlog, concluídas e score médio
- Filtros por status, tipo e busca livre
- Gráficos por status e tipo
- Tabela com as demandas priorizadas
- Cadastro, edição e exclusão de demandas
- Banco SQLite local
- Score de prioridade ponderado

## Fórmula de prioridade

Prioridade = (Impacto * 0.35) + (Recorrência * 0.25) + (Urgência * 0.25) + (Risco * 0.15) - (Esforço * 0.10)

Campos de 1 a 5.

Classificação:
- P1 - Crítica: score >= 4.0
- P2 - Alta: score >= 3.2
- P3 - Média: score >= 2.4
- P4 - Baixa: score < 2.4

## Como rodar

1. Instale o Python 3.10 ou superior
2. Abra o terminal dentro da pasta do projeto
3. Rode:

```bash
pip install -r requirements.txt
python app.py
```

4. Acesse no navegador:

```bash
http://127.0.0.1:5000
```

## Arquivo principal

- `app.py`: backend Flask e APIs
- `templates/index.html`: layout principal
- `static/css/style.css`: visual do cockpit
- `static/js/app.js`: filtros, gráficos e CRUD
- `data/demandas.db`: banco SQLite criado automaticamente ao rodar


## Correção V1.1

Correção aplicada no comportamento dos gráficos do Chart.js.

Problema:
- O canvas dos gráficos ficava recalculando a altura continuamente e expandia sem parar.

Ajuste:
- Altura fixa no bloco `.chart-panel`
- Altura máxima fixa para os elementos `canvas`
- `resizeDelay` no Chart.js
- Animação desativada para evitar loop visual em alguns navegadores/layouts


## Atualização V1.2

Incluída página inicial de login com identidade visual inspirada na Olos Tecnologia:
- Azul tecnológico
- Laranja de destaque
- Fundo animado com grid e partículas
- Botão de sair no cockpit
- Proteção das rotas principais e APIs por sessão

Acesso inicial:
- Usuário: admin
- Senha: olos123

Para alterar o usuário e senha, edite no `app.py`:

```python
LOGIN_USER = "admin"
LOGIN_PASSWORD = "olos123"
```


## Atualização V1.3

Prioridade simplificada para leitura mais executiva.

Nova classificação:
- Altíssimo
- Alto
- Médio
- Baixo
- Baixíssimo

O painel continua calculando um score interno, mas a tabela exibe apenas a classificação final para facilitar a gestão com o time de desenvolvimento.


## Atualização V1.4

Ajustes aplicados:
- Fundo com mais vida, usando linhas tecnológicas, partículas em movimento e gradientes azul/laranja.
- Paleta reforçada com tons de azul e laranja.
- Incluído `Id Prioridade`, editável no cadastro da demanda.
- A esteira agora permite arrastar e soltar linhas para alterar a prioridade manualmente.
- A ordem arrastada é salva no SQLite pela rota `/api/reordenar`.


## Atualização V1.5

Ajuste visual na esteira:
- Área principal ampliada para ocupar melhor a tela.
- Tabela com layout fixo e colunas proporcionais.
- Removida a barra horizontal em telas largas.
- Melhor quebra de texto para exibir todos os campos.
- Altura da esteira ajustada para rolagem vertical quando necessário.


## Atualização V1.5.1

Correção visual na coluna de ações:
- Botões Editar e Excluir corrigidos.
- Removido o efeito de quebra vertical das letras.
- Coluna de ações recebeu mais espaço.
- Redistribuição das larguras da esteira para manter boa leitura dos demais campos.


## Atualização V1.5.2

Ajuste visual da coluna de ações:
- Botões Editar e Excluir posicionados lado a lado.
- Mais espaço para a coluna de ações.
- Pequena redistribuição das colunas para preservar a leitura da esteira.


## Atualização V1.5.3

Ajuste na esteira de demandas:
- Removida a coluna ASR da tabela principal.
- O campo PreviousAsrTranscription permanece no cadastro/edição para consulta e registro.
- Redistribuição das colunas para melhorar a visualização da frase atual, sugestão e observações.


## Atualização V1.5.4

Correção para deploy no Render:
- Incluído `gunicorn==22.0.0` no `requirements.txt`.
- Incluído `Procfile` com `web: gunicorn app:app`.

Configuração recomendada no Render:

Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app
```


## Atualização V1.5.3 - Cadastro objetivo

Ajustes aplicados:
- Cadastro simplificado para gestão.
- Removidos da tela de cadastro:
  - PreviousAsrTranscription
  - Observação / justificativa
  - Impacto
  - Recorrência
  - Urgência
  - Esforço
  - Risco
- Campo de classificação virou seleção direta:
  - Altíssimo
  - Alto
  - Médio
  - Baixo
  - Baixíssimo
- Frase atual do bot e Sugestão aparecem apenas quando o tipo for `Fraseologia`.
- Incluído `Inserido por`, preenchido automaticamente de acordo com o login.
- Mantida a correção para deploy com Gunicorn no Render.


## Atualização V1.5.4 - Melhoria e Observação

Ajustes aplicados:
- Para tipo `Fraseologia`, aparecem:
  - Frase atual do bot
  - Sugestão de fraseologia / ajuste
- Para os demais tipos, aparecem:
  - Melhoria
  - Observação
- Incluído campo `melhoria` no banco SQLite.
- A esteira passa a exibir `Sugestão / Melhoria` e `Obs`.


## Atualização V1.5.5 - Múltiplos logins

Correção aplicada:
- O login agora usa um dicionário `USERS`.
- Isso permite cadastrar vários usuários com suas respectivas senhas.

Exemplo:

```python
USERS = {
    "admin": "olos123",
    "elvis": "olos123",
    "michele": "olos123",
    "nubia": "olos123"
}
```

Validação usada:

```python
if usuario in USERS and USERS[usuario] == senha:
    session["logged_in"] = True
    session["usuario"] = usuario
```


## Atualização V1.5.6 - Cards de status e botões corrigidos

Ajustes aplicados neste pacote:
- Incluídos cards de status dentro da esteira para filtrar a lista abaixo.
- Cards disponíveis: Todos, Backlog, Em análise, Em desenvolvimento, Homologação, Concluído e Cancelado.
- Os cards exibem a quantidade por status.
- Ao clicar no card, o filtro de status é aplicado automaticamente.
- Corrigido o `app.js`, removendo duplicidades de função e chamadas quebradas.
- Botões Editar e Excluir mantidos lado a lado e com largura estável.


## Atualização V1.5.8 - Persistência compartilhada no Render

Esta versão corrige o problema de uma pessoa salvar uma demanda e ela não aparecer para outra pessoa.

### Ponto principal

Para os dados serem compartilhados entre usuários, o Render precisa usar um banco PostgreSQL comum.  
Se a variável `DATABASE_URL` não estiver configurada no Render, o app usa SQLite local e os dados não ficam compartilhados/persistentes.

### O que mudou

- Suporte a PostgreSQL via variável `DATABASE_URL`.
- Localmente, sem `DATABASE_URL`, continua usando SQLite.
- Banner no painel mostrando se o banco está em:
  - `PostgreSQL compartilhado`
  - `SQLite local`
- Endpoint técnico: `/api/db-status`
- A carga das 11 demandas de exemplo fica desativada por padrão.
- Se quiser carregar exemplos, use `LOAD_DEMO_DATA=true`.

### Configuração obrigatória no Render

1. Crie um banco PostgreSQL no Render.
2. Copie a `Internal Database URL`.
3. No Web Service do painel, abra **Environment**.
4. Adicione:

```text
DATABASE_URL=<cole aqui a Internal Database URL>
```

5. Faça novo deploy.

### Configuração do serviço

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

Quando o painel estiver correto, aparecerá um banner com:

```text
PostgreSQL compartilhado - Dados compartilhados e persistentes.
```
