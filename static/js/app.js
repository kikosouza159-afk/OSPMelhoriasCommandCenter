let demandas = [];
let chartStatus = null;
let chartTipo = null;
let timerBusca = null;

const $ = (id) => document.getElementById(id);

function debouncedLoad() {
  clearTimeout(timerBusca);
  timerBusca = setTimeout(carregarTudo, 300);
}

async function carregarTudo() {
  await carregarResumo();
  await carregarDemandas();
}

async function carregarResumo() {
  const resp = await fetch("/api/resumo");
  const data = await resp.json();

  $("kpiTotal").innerText = data.total;
  $("kpiAltissimo").innerText = data.altissimo;
  $("kpiBacklog").innerText = data.backlog;
  $("kpiConcluidas").innerText = data.concluidas;
  $("kpiScore").innerText = data.score_medio;

  atualizarCardsStatus(data);
  renderChart("chartStatus", data.por_status, "Status", "status");
  renderChart("chartTipo", data.por_tipo, "Tipo", "tipo");
}

async function carregarDemandas() {
  const params = new URLSearchParams({
    status: $("fStatus").value,
    tipo: $("fTipo").value,
    busca: $("fBusca").value
  });

  const resp = await fetch(`/api/demandas?${params}`);
  demandas = await resp.json();
  renderTabela();
}

function atualizarCardsStatus(data) {
  const total = data.total || 0;
  const porStatus = data.por_status || {};
  const filtroAtual = $("fStatus") ? $("fStatus").value : "";

  const allCount = $("statusCountAll");
  if (allCount) allCount.innerText = total;

  document.querySelectorAll(".status-filter-card[data-status]").forEach(card => {
    const status = card.dataset.status || "";
    const countEl = card.querySelector("strong");

    if (countEl) {
      countEl.innerText = status ? (porStatus[status] || 0) : total;
    }

    card.classList.toggle("active", status === filtroAtual);
  });
}

function aplicarFiltroStatusCard(status) {
  if ($("fStatus")) {
    $("fStatus").value = status;
  }

  document.querySelectorAll(".status-filter-card[data-status]").forEach(card => {
    card.classList.toggle("active", (card.dataset.status || "") === status);
  });

  carregarTudo();
}

function renderTabela() {
  const tbody = $("tbody");
  tbody.innerHTML = "";

  demandas.forEach(d => {
    const tr = document.createElement("tr");
    tr.draggable = true;
    tr.dataset.id = d.id;
    tr.className = "draggable-row";

    const melhoriaOuSugestao = d.tipo === "Fraseologia"
      ? (d.sugestao || "")
      : (d.melhoria || d.sugestao || "");

    tr.innerHTML = `
      <td class="drag-cell" title="Arraste para reordenar">⋮⋮</td>
      <td><span class="priority-id">${escapeHtml(d.prioridade_ordem || "")}</span></td>
      <td><span class="badge ${classePrioridade(d.nivel_prioridade)}">${escapeHtml(d.nivel_prioridade || "")}</span></td>
      <td><span class="badge status">${escapeHtml(d.status || "")}</span></td>
      <td>${escapeHtml(d.tipo || "")}</td>
      <td>${escapeHtml(d.call_id || "")}</td>
      <td><div class="truncate">${escapeHtml(d.frase_atual || "")}</div></td>
      <td><div class="truncate">${escapeHtml(melhoriaOuSugestao)}</div></td>
      <td><div class="truncate">${escapeHtml(d.obs || "")}</div></td>
      <td>${escapeHtml(d.criado_por || "")}</td>
      <td>${escapeHtml(d.responsavel || "")}</td>
      <td>
        <div class="actions">
          <button type="button" class="ghost btn-edit" onclick="editar(${d.id})">Editar</button>
          <button type="button" class="ghost btn-delete" onclick="excluir(${d.id})">Excluir</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  ativarDragAndDrop();
}

function ativarDragAndDrop() {
  const tbody = $("tbody");
  let draggingRow = null;

  tbody.querySelectorAll("tr").forEach(row => {
    row.addEventListener("dragstart", () => {
      draggingRow = row;
      row.classList.add("dragging");
    });

    row.addEventListener("dragend", async () => {
      row.classList.remove("dragging");
      draggingRow = null;
      await salvarNovaOrdem();
    });

    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      const afterElement = getDragAfterElement(tbody, event.clientY);
      if (!draggingRow) return;

      if (afterElement == null) {
        tbody.appendChild(draggingRow);
      } else {
        tbody.insertBefore(draggingRow, afterElement);
      }
    });
  });
}

function getDragAfterElement(container, y) {
  const rows = [...container.querySelectorAll("tr:not(.dragging)")];

  return rows.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;

    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    }

    return closest;
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

async function salvarNovaOrdem() {
  const ids = [...$("tbody").querySelectorAll("tr")].map(row => Number(row.dataset.id));

  await fetch("/api/reordenar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids })
  });

  await carregarDemandas();
}

function classePrioridade(nivel) {
  if (nivel === "Altíssimo") return "prio-altissimo";
  if (nivel === "Alto") return "prio-alto";
  if (nivel === "Médio") return "prio-medio";
  if (nivel === "Baixo") return "prio-baixo";
  return "prio-baixissimo";
}

function renderChart(canvasId, obj, label, tipo) {
  const ctx = $(canvasId);
  if (!ctx) return;

  const labels = Object.keys(obj || {});
  const values = Object.values(obj || {});

  const current = tipo === "status" ? chartStatus : chartTipo;
  if (current) current.destroy();

  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderWidth: 1
      }]
    },
    options: {
      plugins: {
        legend: { display: false }
      },
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 200,
      animation: false,
      scales: {
        x: { ticks: { color: "#cfe2f7" }, grid: { color: "rgba(255,255,255,.06)" } },
        y: { ticks: { color: "#cfe2f7", precision: 0 }, grid: { color: "rgba(255,255,255,.06)" } }
      }
    }
  });

  if (tipo === "status") chartStatus = chart;
  else chartTipo = chart;
}

function abrirModal() {
  $("modalTitle").innerText = "Nova demanda";
  limparForm();
  $("modal").showModal();
}

function fecharModal() {
  $("modal").close();
}

function limparForm() {
  ["id", "call_id", "previous_asr", "frase_atual", "sugestao", "melhoria", "obs", "responsavel", "data_prevista", "prioridade_ordem"].forEach(id => {
    if ($(id)) $(id).value = "";
  });

  $("tipo").value = "Fraseologia";
  $("status").value = "Backlog";
  $("nivel_prioridade").value = "Médio";
  $("impacto").value = 3;
  $("recorrencia").value = 3;
  $("urgencia").value = 3;
  $("esforco").value = 2;
  $("risco").value = 3;

  if ($("criado_por_view")) {
    $("criado_por_view").value = $("criado_por_view").defaultValue || "";
  }

  toggleFraseologiaFields();
}

function editar(id) {
  const d = demandas.find(x => x.id === id);
  if (!d) return;

  $("modalTitle").innerText = `Editar demanda #${id}`;

  Object.keys(d).forEach(k => {
    if ($(k)) $(k).value = d[k] ?? "";
  });

  $("id").value = d.id;

  if ($("criado_por_view")) {
    $("criado_por_view").value = d.criado_por || "";
  }

  toggleFraseologiaFields();
  $("modal").showModal();
}

async function salvarDemanda(event) {
  event.preventDefault();

  const id = $("id").value;
  const payload = {
    call_id: $("call_id").value,
    previous_asr: $("previous_asr").value,
    frase_atual: $("frase_atual").value,
    sugestao: $("sugestao").value,
    melhoria: $("melhoria").value,
    obs: $("obs").value,
    tipo: $("tipo").value,
    status: $("status").value,
    nivel_prioridade: $("nivel_prioridade").value,
    responsavel: $("responsavel").value,
    data_prevista: $("data_prevista").value,
    prioridade_ordem: Number($("prioridade_ordem").value || 999999),
    impacto: Number($("impacto").value),
    recorrencia: Number($("recorrencia").value),
    urgencia: Number($("urgencia").value),
    esforco: Number($("esforco").value),
    risco: Number($("risco").value)
  };

  const url = id ? `/api/demandas/${id}` : "/api/demandas";
  const method = id ? "PUT" : "POST";

  await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  fecharModal();
  await carregarTudo();
}

async function excluir(id) {
  if (!confirm("Deseja excluir esta demanda?")) return;

  await fetch(`/api/demandas/${id}`, { method: "DELETE" });
  await carregarTudo();
}

function toggleFraseologiaFields() {
  const fraseologiaBox = $("fraseologiaBox");
  const melhoriaBox = $("melhoriaBox");
  if (!fraseologiaBox || !melhoriaBox) return;

  const tipo = $("tipo").value;
  const isFraseologia = tipo === "Fraseologia";

  fraseologiaBox.style.display = isFraseologia ? "block" : "none";
  melhoriaBox.style.display = isFraseologia ? "none" : "block";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

carregarTudo();
