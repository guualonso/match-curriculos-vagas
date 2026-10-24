// match.js — análise de currículos e renderização de resultados
import { qs, qsa, show, hide, showToast, formatarTempo } from './ui.js';
import { uploadAndMatch, quickMatch } from './api.js';
import { renderBreakdown, renderSkillsGrid, renderScoreCircle } from './render.js';
import { validarExtensao, ICONS } from './upload.js';
import { state } from './state.js';

// ── Arquivos ────────────────────────────────────────────────

export function adicionarArquivos(novos) {
  for (const f of novos) {
    if (!validarExtensao(f)) { showToast(`${f.name}: formato não suportado.`, 'error'); continue; }
    if (state.arquivosAnlise.find(a => a.name === f.name)) continue;
    state.arquivosAnlise.push(f);
  }
  renderizarListaArquivos();
  qs('#btn-analyze').disabled = state.arquivosAnlise.length === 0;
  atualizarTempoEstimado();
}

export function removerArquivo(nome) {
  state.arquivosAnlise = state.arquivosAnlise.filter(f => f.name !== nome);
  renderizarListaArquivos();
  qs('#btn-analyze').disabled = state.arquivosAnlise.length === 0;
  atualizarTempoEstimado();
}

function renderizarListaArquivos() {
  const dropZone  = qs('#drop-zone');
  const filesList = qs('#files-list');
  if (!state.arquivosAnlise.length) { hide(filesList); show(dropZone); return; }
  hide(dropZone);
  show(filesList);
  filesList.innerHTML = state.arquivosAnlise.map(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return `
      <div class="file-item" id="fi-${f.name.replace(/\W/g, '_')}">
        <span class="file-item-icon">${ICONS[ext] || '📄'}</span>
        <span class="file-item-name">${f.name}</span>
        <span class="file-item-status aguardando">Aguardando</span>
        <button class="file-item-remove" data-nome="${f.name}" title="Remover">✕</button>
      </div>`;
  }).join('');

  filesList.querySelectorAll('.file-item-remove').forEach(btn =>
    btn.addEventListener('click', () => removerArquivo(btn.dataset.nome)));
}

function setStatusArquivo(nome, status) {
  const labels = { aguardando: 'Aguardando', processando: 'Processando…', concluido: 'Concluído', erro: 'Erro' };
  const el = qs(`#fi-${nome.replace(/\W/g, '_')} .file-item-status`);
  if (!el) return;
  el.className = `file-item-status ${status}`;
  el.textContent = labels[status] || status;
}

// ── Tempo estimado ──────────────────────────────────────────

export function atualizarTempoEstimado() {
  const nCurriculos = state.arquivosAnlise.length || 1;
  const escopo      = parseInt(qs('#vagas-escopo')?.value || '0');
  const nVagas      = escopo > 0
    ? Math.min(escopo, state.vagasCadastradas.length)
    : state.vagasCadastradas.length;
  const total = nCurriculos * nVagas;

  // 20 min por candidato triado (Recruiting from Scratch, 2024) — por currículo, não por par
  const tempoManual  = nCurriculos * 20 * 60;
  const tempoSistema = nCurriculos * 2;

  const badgeTempo = qs('#tempo-estimado-badge');
  if (badgeTempo) {
    badgeTempo.innerHTML = total > 0
      ? `Sistema: ~${formatarTempo(tempoSistema)} · Manual: ~${formatarTempo(tempoManual)}`
      : '⏱️ Tempo estimado: —';
  }

  const box = qs('#tempo-manual');
  if (box && total > 0) {
    box.innerHTML = `
      <div class="tempo-linha"><span>📄 Currículos selecionados:</span><strong>${nCurriculos}</strong></div>
      <div class="tempo-linha"><span>📋 Vagas para comparar:</span><strong>${nVagas}</strong></div>
      <div class="tempo-linha"><span>🔢 Total de comparações:</span><strong>${total}</strong></div>
      <div class="tempo-linha"><span>🤖 Tempo estimado (sistema):</span><strong>~${formatarTempo(tempoSistema)}</strong></div>
      <div class="tempo-linha"><span>👤 Tempo estimado (manual, 20 min/currículo):</span><strong>~${formatarTempo(tempoManual)}</strong></div>`;
    show(box);
  }
}

// ── Análise ─────────────────────────────────────────────────

export function setupMatch() {
  const dropZone  = qs('#drop-zone');
  const fileInput = qs('#file-input');
  const btnAnalyze = qs('#btn-analyze');

  fileInput?.addEventListener('change', e => adicionarArquivos([...e.target.files]));

  dropZone?.addEventListener('click', e => {
    if (e.target.closest('label')) return;
    fileInput?.click();
  });

  ['dragover', 'dragenter'].forEach(ev =>
    dropZone?.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add('drag-over'); }));

  ['dragleave', 'drop'].forEach(ev =>
    dropZone?.addEventListener(ev, e => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      if (ev === 'drop') adicionarArquivos([...e.dataTransfer.files]);
    }));

  qs('#vagas-escopo')?.addEventListener('change', atualizarTempoEstimado);

  btnAnalyze.addEventListener('click', handleAnalyze);
  qs('#btn-quick').addEventListener('click', handleQuickMatch);
}

async function handleAnalyze() {
  if (!state.arquivosAnlise.length) return;
  if (!state.vagasCadastradas.length) {
    showToast('Nenhuma vaga cadastrada para comparar.', 'error'); return;
  }

  const escopo = parseInt(qs('#vagas-escopo').value || '0');
  const topN   = escopo > 0 ? escopo : 9999;
  const btn    = qs('#btn-analyze');
  const text   = qs('#btn-analyze-text');
  const spin   = qs('#btn-analyze-spinner');

  btn.disabled = true;
  text.textContent = 'Analisando…';
  show(spin);
  state.resultadosPorCurriculo = {};

  for (const arquivo of state.arquivosAnlise) {
    setStatusArquivo(arquivo.name, 'processando');
    try {
      const data = await uploadAndMatch(arquivo, topN, state.metodoAtivo);
      state.resultadosPorCurriculo[arquivo.name] = data.results;

      const id = data.resume_id || data.curriculo_id;
      const el = document.querySelector(`#fi-${arquivo.name.replace(/\W/g, '_')} .file-item-status`);
      if (el) el.textContent = id ? `Concluído · ID #${id}` : 'Concluído';
      if (el) el.className = 'file-item-status concluido';

    } catch (err) {
      setStatusArquivo(arquivo.name, 'erro');
      showToast(`Erro em ${arquivo.name}: ${err.message}`, 'error');
    }
  }

  btn.disabled = false;
  text.textContent = 'Analisar';
  hide(spin);

  const concluidos = Object.keys(state.resultadosPorCurriculo).length;
  if (concluidos > 0) {
    renderizarResultados();
    showToast(`${concluidos} currículo(s) analisado(s) com sucesso.`, 'success');
  }
}

async function handleQuickMatch() {
  const resumeText = qs('#quick-resume').value.trim();
  const jobText    = qs('#quick-job').value.trim();
  if (!resumeText || !jobText) { showToast('Preencha os dois campos.', 'error'); return; }

  const btn  = qs('#btn-quick');
  const text = qs('#btn-quick-text');
  const spin = qs('#btn-quick-spinner');

  btn.disabled = true;
  text.textContent = 'Aguarde…';
  show(spin);

  try {
    const data = await quickMatch({
      resume_text:     resumeText,
      job_description: jobText,
      job_title:       qs('#quick-title').value.trim() || 'Vaga',
      metodo:          state.metodoAtivo,
    });
    const r  = data.result;
    const el = qs('#quick-result');
    el.innerHTML = `
      <div class="quick-result-header">
        ${renderScoreCircle(r, '52px')}
        <div>
          <strong>${r.job_title || 'Vaga'}</strong>
          <div class="score-meta">Score: ${(r.similarity_score || 0).toFixed(3)}</div>
          ${renderBreakdown(r)}
        </div>
      </div>
      ${renderSkillsGrid(r)}`;
    show(el);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    text.textContent = 'Comparar';
    hide(spin);
  }
}

// ── Resultados ──────────────────────────────────────────────

function renderizarResultados() {
  const section = qs('#results-section');
  const tabsEl  = qs('#curriculos-tabs');
  const listEl  = qs('#results-list');
  const metaEl  = qs('#results-meta');
  const badgeEl = qs('#results-metodo-badge');
  const nomes   = Object.keys(state.resultadosPorCurriculo);

  badgeEl.textContent = state.metodoAtivo.toUpperCase();
  badgeEl.className   = `metodo-tag ${state.metodoAtivo}`;

  if (nomes.length > 1) {
    show(tabsEl);
    tabsEl.innerHTML = nomes.map((nome, i) =>
      `<button class="curriculo-tab${i === 0 ? ' active' : ''}" data-nome="${nome}">
        ${nome.replace(/\.[^.]+$/, '')}
      </button>`
    ).join('');
    tabsEl.querySelectorAll('.curriculo-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        tabsEl.querySelectorAll('.curriculo-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        state.paginaAtual = 1;
        state.nomeAtivo = tab.dataset.nome;
        renderizarListaResultados(state.nomeAtivo, listEl, metaEl);
      });
    });
  } else {
    hide(tabsEl);
  }

  state.paginaAtual = 1;
  state.nomeAtivo   = nomes[0];
  renderizarListaResultados(state.nomeAtivo, listEl, metaEl);
  show(section);
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderizarListaResultados(nome, listEl, metaEl) {
  const todos     = state.resultadosPorCurriculo[nome] || [];
  const total     = todos.length;
  const totalPags = Math.ceil(total / state.ITENS_POR_PAGINA);
  const inicio    = (state.paginaAtual - 1) * state.ITENS_POR_PAGINA;
  const pagina    = todos.slice(inicio, inicio + state.ITENS_POR_PAGINA);

  metaEl.textContent = `${total} vagas · ${nome}`;
  listEl.innerHTML = '';

  if (!total) {
    listEl.innerHTML = '<p class="empty-state">Sem resultados para este currículo.</p>';
    hide(qs('#pagination'));
    return;
  }

  pagina.forEach((r, i) => {
    const rankGlobal = inicio + i + 1;
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
      <span class="result-rank">#${rankGlobal}</span>
      <div class="result-header-row">
        ${renderScoreCircle(r)}
        <div class="result-info">
          <h3>${r.job_title || '—'}</h3>
          <div class="company">Score: ${(r.similarity_score || 0).toFixed(3)}</div>
          ${renderBreakdown(r)}
        </div>
      </div>
      ${renderSkillsGrid(r)}`;
    listEl.appendChild(card);
  });

  renderizarPaginacao(totalPags, listEl, metaEl, nome);
}

function renderizarPaginacao(totalPags, listEl, metaEl, nome) {
  const pag = qs('#pagination');
  if (totalPags <= 1) { hide(pag); return; }

  show(pag);
  const vizinhos = 2;
  const paginas  = [];

  for (let p = 1; p <= totalPags; p++) {
    if (p === 1 || p === totalPags ||
        (p >= state.paginaAtual - vizinhos && p <= state.paginaAtual + vizinhos)) {
      paginas.push(p);
    }
  }

  const itens = [];
  paginas.forEach((p, idx) => {
    if (idx > 0 && p - paginas[idx - 1] > 1) itens.push('...');
    itens.push(p);
  });

  pag.innerHTML = `
    <button class="pag-btn pag-nav" data-p="${state.paginaAtual - 1}" ${state.paginaAtual === 1 ? 'disabled' : ''}>‹</button>
    ${itens.map(p =>
      p === '...'
        ? `<span class="pag-ellipsis">…</span>`
        : `<button class="pag-btn${p === state.paginaAtual ? ' active' : ''}" data-p="${p}">${p}</button>`
    ).join('')}
    <button class="pag-btn pag-nav" data-p="${state.paginaAtual + 1}" ${state.paginaAtual === totalPags ? 'disabled' : ''}>›</button>`;

  pag.querySelectorAll('.pag-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      state.paginaAtual = parseInt(btn.dataset.p);
      renderizarListaResultados(nome, listEl, metaEl);
      qs('#results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}
