// ------------------------------------------------------------------
// Site Brasil - Liberados x Montados
// ------------------------------------------------------------------

const state = {
  estadoAtual: null,
  linhas: [],       // todas as linhas do histórico do estado atual
  snapshots: [],     // lista de timestamps de extração distintos, ordenados
};

const el = {
  estadoSelect: document.getElementById("estado-select"),
  status: document.getElementById("status"),
  snapshotSection: document.getElementById("snapshot-section"),
  snapshotSelect: document.getElementById("snapshot-select"),
  snapshotResumo: document.getElementById("snapshot-resumo"),
  snapshotTabela: document.getElementById("snapshot-tabela"),
  compareSection: document.getElementById("compare-section"),
  compareAntes: document.getElementById("compare-antes"),
  compareDepois: document.getElementById("compare-depois"),
  compareBtn: document.getElementById("compare-btn"),
  compareResumo: document.getElementById("compare-resumo"),
  compareTabelas: document.getElementById("compare-tabelas"),
};

function init() {
  Object.entries(CONFIG_ESTADOS).forEach(([sigla, info]) => {
    const opt = document.createElement("option");
    opt.value = sigla;
    opt.textContent = `${sigla} — ${info.nome}`;
    if (!info.csvUrl) opt.textContent += " (sem URL configurada)";
    el.estadoSelect.appendChild(opt);
  });

  el.estadoSelect.addEventListener("change", onEstadoChange);
  el.snapshotSelect.addEventListener("change", onSnapshotChange);
  el.compareBtn.addEventListener("click", onCompareClick);
}

async function onEstadoChange() {
  const sigla = el.estadoSelect.value;
  if (!sigla) return;

  const info = CONFIG_ESTADOS[sigla];
  if (!info.csvUrl) {
    setStatus(`Nenhuma URL configurada para ${sigla} ainda. Edite config.js.`, true);
    resetSections();
    return;
  }

  setStatus(`Carregando dados de ${sigla}...`);
  resetSections();

  try {
    const linhas = await carregarCsv(info.csvUrl);
    state.estadoAtual = sigla;
    state.linhas = linhas;
    state.snapshots = extrairSnapshots(linhas);

    if (state.snapshots.length === 0) {
      setStatus(`Nenhum snapshot encontrado para ${sigla}. Rode o snapshot na planilha primeiro.`, true);
      return;
    }

    setStatus(`${linhas.length} linhas carregadas · ${state.snapshots.length} snapshot(s) disponível(is).`);
    popularSnapshotSelects();
    el.snapshotSection.hidden = false;
    el.compareSection.hidden = state.snapshots.length < 2;
  } catch (err) {
    console.error(err);
    setStatus(`Erro ao carregar dados de ${sigla}: ${err.message}`, true);
  }
}

function carregarCsv(url) {
  return new Promise((resolve, reject) => {
    Papa.parse(url, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const linhas = results.data.filter(l => l.NUMPED && l.EXTRACAO_TS);
        resolve(linhas);
      },
      error: (err) => reject(err),
    });
  });
}

function extrairSnapshots(linhas) {
  const unicos = [...new Set(linhas.map(l => l.EXTRACAO_TS))];
  return unicos.sort((a, b) => new Date(a) - new Date(b));
}

function popularSnapshotSelects() {
  [el.snapshotSelect, el.compareAntes, el.compareDepois].forEach(select => {
    select.innerHTML = "";
    state.snapshots.forEach(ts => {
      const opt = document.createElement("option");
      opt.value = ts;
      opt.textContent = formatarData(ts);
      select.appendChild(opt);
    });
  });
  // por padrão: comparar o primeiro com o último snapshot do dia
  el.compareAntes.value = state.snapshots[0];
  el.compareDepois.value = state.snapshots[state.snapshots.length - 1];
  el.snapshotSelect.value = state.snapshots[state.snapshots.length - 1];
  onSnapshotChange();
}

function onSnapshotChange() {
  const ts = el.snapshotSelect.value;
  const linhasDoSnapshot = state.linhas.filter(l => l.EXTRACAO_TS === ts);

  const liberados = linhasDoSnapshot.filter(l => (l.POSICAO || "").trim().toUpperCase() === "L");
  const montados = linhasDoSnapshot.filter(l => (l.POSICAO || "").trim().toUpperCase() === "M");

  el.snapshotResumo.innerHTML = `
    <div class="card">
      <span class="card-numero">${liberados.length}</span>
      <span class="card-label">Liberados (L)</span>
    </div>
    <div class="card">
      <span class="card-numero">${montados.length}</span>
      <span class="card-label">Montados (M)</span>
    </div>
    <div class="card">
      <span class="card-numero">${linhasDoSnapshot.length}</span>
      <span class="card-label">Total no snapshot</span>
    </div>
  `;

  el.snapshotTabela.innerHTML = montarTabela(
    ["NUMPED", "NOMECLIENTE", "POSICAO", "PRACA", "DESTINO"],
    linhasDoSnapshot
  );
}

function onCompareClick() {
  const tsAntes = el.compareAntes.value;
  const tsDepois = el.compareDepois.value;

  if (tsAntes === tsDepois) {
    el.compareResumo.innerHTML = `<p class="aviso">Escolha dois snapshots diferentes para comparar.</p>`;
    el.compareTabelas.innerHTML = "";
    return;
  }

  const mapaAntes = new Map();
  const mapaDepois = new Map();

  state.linhas.filter(l => l.EXTRACAO_TS === tsAntes).forEach(l => mapaAntes.set(l.NUMPED, l));
  state.linhas.filter(l => l.EXTRACAO_TS === tsDepois).forEach(l => mapaDepois.set(l.NUMPED, l));

  const transicaoLM = [];
  const permaneceramL = [];
  const cancelados = [];
  const novos = [];

  mapaAntes.forEach((linhaAntes, numped) => {
    const posAntes = (linhaAntes.POSICAO || "").trim().toUpperCase();
    const linhaDepois = mapaDepois.get(numped);

    if (!linhaDepois) {
      cancelados.push(linhaAntes);
      return;
    }
    const posDepois = (linhaDepois.POSICAO || "").trim().toUpperCase();

    if (posAntes === "L" && posDepois === "M") {
      transicaoLM.push(linhaDepois);
    } else if (posAntes === "L" && posDepois === "L") {
      permaneceramL.push(linhaDepois);
    }
  });

  mapaDepois.forEach((linhaDepois, numped) => {
    if (!mapaAntes.has(numped)) novos.push(linhaDepois);
  });

  el.compareResumo.innerHTML = `
    <div class="card">
      <span class="card-numero">${transicaoLM.length}</span>
      <span class="card-label">Saíram de L → M</span>
    </div>
    <div class="card">
      <span class="card-numero">${permaneceramL.length}</span>
      <span class="card-label">Continuam em L</span>
    </div>
    <div class="card card-alerta">
      <span class="card-numero">${cancelados.length}</span>
      <span class="card-label">Cancelados (sumiram)</span>
    </div>
    <div class="card">
      <span class="card-numero">${novos.length}</span>
      <span class="card-label">Novos pedidos</span>
    </div>
  `;

  el.compareTabelas.innerHTML = `
    <h3>Cancelados</h3>
    ${montarTabela(["NUMPED", "NOMECLIENTE", "POSICAO", "PRACA"], cancelados)}
    <h3>Saíram de L → M</h3>
    ${montarTabela(["NUMPED", "NOMECLIENTE", "PRACA", "DESTINO"], transicaoLM)}
  `;
}

function montarTabela(colunas, linhas) {
  if (linhas.length === 0) return `<p class="aviso">Nenhum registro.</p>`;
  const head = colunas.map(c => `<th>${c}</th>`).join("");
  const body = linhas.map(l => `<tr>${colunas.map(c => `<td>${l[c] ?? ""}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function formatarData(ts) {
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function setStatus(msg, isErro = false) {
  el.status.textContent = msg;
  el.status.classList.toggle("erro", isErro);
}

function resetSections() {
  el.snapshotSection.hidden = true;
  el.compareSection.hidden = true;
  el.snapshotResumo.innerHTML = "";
  el.snapshotTabela.innerHTML = "";
  el.compareResumo.innerHTML = "";
  el.compareTabelas.innerHTML = "";
}

init();
