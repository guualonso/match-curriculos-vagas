import { qs, qsa, show, hide, showToast, formatarTempo } from './ui.js';
import { uploadAndMatch, quickMatch } from './api.js';
import { renderSkillsGrid } from './render.js';
import {
  renderComposicaoTfidf, renderResultadosUnificados, renderScoresDuplos, renderSeloMetodos, resumoDosResultados,
} from './resultados.js';
import { validarExtensao, ICONS } from './upload.js';
import { state } from './state.js';

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

export function atualizarTempoEstimado() {
  const nCurriculos = state.arquivosAnlise.length || 1;
  const escopo      = parseInt(qs('#vagas-escopo')?.value || '0');
  const nVagas      = escopo > 0 ? Math.min(escopo, state.totalVagas) : state.totalVagas;
  const total = nCurriculos * nVagas;

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
  qs('#top-n-analise')?.addEventListener('change', renderizarListaResultados);

  btnAnalyze.addEventListener('click', handleAnalyze);
  qs('#btn-quick').addEventListener('click', handleQuickMatch);
}

async function handleAnalyze() {
  if (!state.arquivosAnlise.length) return;
  if (!state.vagasCadastradas.length) {
    showToast('Nenhuma vaga cadastrada para comparar.', 'error'); return;
  }

  const limiteVagas = parseInt(qs('#vagas-escopo').value || '0');
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
      const data = await uploadAndMatch(arquivo, limiteVagas);
      state.resultadosPorCurriculo[arquivo.name] = { resultados: data.results, totalVagas: data.total_jobs_analyzed };

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
    });
    const el = qs('#quick-result');
    el.innerHTML = `
      <div class="quick-result-header">
        ${renderScoresDuplos(data, '52px')}
        <div>
          <strong>${data.tfidf.job_title || 'Vaga'}</strong>
          ${renderSeloMetodos(data.metodos)}
          ${renderComposicaoTfidf(data.tfidf)}
        </div>
      </div>
      ${renderSkillsGrid(data.tfidf)}`;
    show(el);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    text.textContent = 'Comparar';
    hide(spin);
  }
}

function renderizarResultados() {
  const section = qs('#results-section');
  const tabsEl  = qs('#curriculos-tabs');
  const nomes   = Object.keys(state.resultadosPorCurriculo);

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
        state.nomeAtivo = tab.dataset.nome;
        renderizarListaResultados();
      });
    });
  } else {
    hide(tabsEl);
  }

  state.nomeAtivo = nomes[0];
  renderizarListaResultados();
  show(section);
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderizarListaResultados() {
  const nome = state.nomeAtivo;
  if (!nome) return;
  const { resultados = [], totalVagas = 0 } = state.resultadosPorCurriculo[nome] || {};
  const topN = parseInt(qs('#top-n-analise').value, 10);
  const { compativeis, pelosDois } = resumoDosResultados(resultados);

  qs('#results-meta').textContent =
    `${compativeis} vagas compatíveis de ${totalVagas} analisadas (${pelosDois} pelos dois métodos) · ${nome}`;
  renderResultadosUnificados(
    qs('#results-list'), resultados, topN,
    item => item.job_title || '—',
    'vagas', 'Nenhuma vaga com nível Médio ou Alto para este currículo.',
  );
}
