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
