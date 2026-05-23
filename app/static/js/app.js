const API = '/api/v1';
let metodoAtivo          = 'tfidf';
let arquivosAnlise       = [];   
let vagasCadastradas     = [];  
let resultadosPorCurriculo = {};

const ITENS_POR_PAGINA = 30;
let paginaAtual = 1;
let nomeAtivo   = null;

const qs  = (s, ctx = document) => ctx.querySelector(s);
const qsa = (s, ctx = document) => [...ctx.querySelectorAll(s)];
const show   = el => el && el.classList.remove('hidden');
const hide   = el => el && el.classList.add('hidden');
const toggle = (el, c) => c ? show(el) : hide(el);

function showToast(msg, type = 'info') {
  const t = qs('#toast');
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  show(t);
  setTimeout(() => hide(t), 3800);
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

function formatarTempo(segundos) {
  if (segundos < 60)   return `${Math.round(segundos)}s`;
  if (segundos < 3600) return `${Math.round(segundos / 60)} min`;
  return `${(segundos / 3600).toFixed(1)} h`;
}

async function checkHealth() {
  const badge = qs('#status-badge');
  try {
    const data = await fetch('/health').then(r => r.json());
    const lang = data.model_language || data.language || 'pt';
    badge.textContent = `Online · spaCy ${lang.toUpperCase()}`;
    badge.className = 'status-badge status-ok';
  } catch (e) {
    badge.textContent = 'Offline';
    badge.className = 'status-badge status-error';
  }
}

async function carregarVagas() {
  try {
    const data = await apiFetch('/jobs?limit=100');
    vagasCadastradas = data.jobs || [];

    const totalReal = data.total || vagasCadastradas.length;
    const txt = `${totalReal} vaga${totalReal !== 1 ? 's' : ''} cadastrada${totalReal !== 1 ? 's' : ''}`;
    const b1 = qs('#total-vagas-badge');
    const b2 = qs('#total-vagas-jobs');
    if (b1) b1.innerHTML = `<strong>${txt}</strong>`;
    if (b2) b2.innerHTML = `<strong>${txt}</strong>`;

    atualizarTempoEstimado();
  } catch { /* -- */ }
}

function atualizarContadorVagas() {
  const total = vagasCadastradas.length;
  const txt = `${total} vaga${total !== 1 ? 's' : ''} cadastrada${total !== 1 ? 's' : ''}`;

  const b1 = qs('#total-vagas-badge');
  const b2 = qs('#total-vagas-jobs');
  if (b1) b1.innerHTML = `<strong>${txt}</strong>`;
  if (b2) b2.innerHTML = `<strong>${txt}</strong>`;

  atualizarTempoEstimado();
}

function atualizarTempoEstimado() {
  const nCurriculos = arquivosAnlise.length || 1;
  const escopo      = parseInt(qs('#vagas-escopo')?.value || '0');
  const nVagas      = escopo > 0
    ? Math.min(escopo, vagasCadastradas.length)
    : vagasCadastradas.length;
  const total = nCurriculos * nVagas;

  const tempoManual  = total * 20 * 60;
  const tempoSistema = nCurriculos * 2; 

  const badgeTempo = qs('#tempo-estimado-badge');
  if (badgeTempo) {
    badgeTempo.innerHTML = total > 0
      ? ` Sistema: ~${formatarTempo(tempoSistema)} · Manual: ~${formatarTempo(tempoManual)}`
      : '⏱️ Tempo estimado: —';
  }

  const box = qs('#tempo-manual');
  if (box && total > 0) {
    box.innerHTML = `
      <div class="tempo-linha"><span>📄 Currículos selecionados:</span><strong>${nCurriculos}</strong></div>
      <div class="tempo-linha"><span>📋 Vagas para comparar:</span><strong>${nVagas}</strong></div>
      <div class="tempo-linha"><span>🔢 Total de comparações:</span><strong>${total}</strong></div>
      <div class="tempo-linha"><span>🤖 Tempo estimado (sistema):</span><strong>~${formatarTempo(tempoSistema)}</strong></div>
      <div class="tempo-linha"><span>👤 Tempo estimado (manual, 20 min/par):</span><strong>~${formatarTempo(tempoManual)}</strong></div>`;
    show(box);
  }
}


qs('#vagas-escopo')?.addEventListener('change', atualizarTempoEstimado);


qsa('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    qsa('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    qsa('.tab-content').forEach(s => {
      s.classList.toggle('active', s.id === `tab-${tab}`);
      toggle(s, s.id === `tab-${tab}`);
    });
    if (tab === 'jobs') loadJobs();
  });
});


qsa('.metodo-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.metodo === 'sbert') {
      showToast('SBERT será implementado na fase 2 do projeto.', 'info');
      return;
    }
    metodoAtivo = btn.dataset.metodo;
    qsa('.metodo-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});


const dropZone   = qs('#drop-zone');
const fileInput  = qs('#file-input');
const filesList  = qs('#files-list');
const btnAnalyze = qs('#btn-analyze');

const EXTS  = ['pdf', 'docx', 'txt'];
const ICONS = { pdf: '📕', docx: '📘', txt: '📄' };

function adicionarArquivos(novos) {
  for (const f of novos) {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!EXTS.includes(ext)) { showToast(`${f.name}: formato não suportado.`, 'error'); continue; }
    if (arquivosAnlise.find(a => a.name === f.name)) continue;
    arquivosAnlise.push(f);
  }
  renderizarListaArquivos();
  btnAnalyze.disabled = arquivosAnlise.length === 0;
  atualizarTempoEstimado();
}

function removerArquivo(nome) {
  arquivosAnlise = arquivosAnlise.filter(f => f.name !== nome);
  renderizarListaArquivos();
  btnAnalyze.disabled = arquivosAnlise.length === 0;
  atualizarTempoEstimado();
}

function renderizarListaArquivos() {
  if (!arquivosAnlise.length) { hide(filesList); show(dropZone); return; }
  hide(dropZone);
  show(filesList);
  filesList.innerHTML = arquivosAnlise.map(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return `<div class="file-item" id="fi-${f.name.replace(/\W/g, '_')}">
      <span class="file-item-icon">${ICONS[ext] || '📄'}</span>
      <span class="file-item-name">${f.name}</span>
      <span class="file-item-status aguardando">Aguardando</span>
      <button class="file-item-remove" onclick="removerArquivo('${f.name}')" title="Remover">✕</button>
    </div>`;
  }).join('');
}

function setStatusArquivo(nome, status) {
  const labels = { aguardando: 'Aguardando', processando: 'Processando…', concluido: 'Concluído', erro: 'Erro' };
  const el = qs(`#fi-${nome.replace(/\W/g, '_')} .file-item-status`);
  if (!el) return;
  el.className = `file-item-status ${status}`;
  el.textContent = labels[status] || status;
}

fileInput?.addEventListener('change', e => adicionarArquivos([...e.target.files]));
dropZone?.addEventListener('click', (e) => {
  if (e.target.closest('label')) return;
  fileInput?.click();
});
['dragover', 'dragenter'].forEach(ev =>
  dropZone?.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add('drag-over'); }));
['dragleave', 'drop'].forEach(ev =>
  dropZone?.addEventListener(ev, e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    if (ev === 'drop') adicionarArquivos([...e.dataTransfer.files]);
  }));

window.removerArquivo = removerArquivo;

const btnAText    = qs('#btn-analyze-text');
const btnASpinner = qs('#btn-analyze-spinner');

btnAnalyze.addEventListener('click', async () => {
  if (!arquivosAnlise.length) return;

  if (!vagasCadastradas.length) {
    showToast('Nenhuma vaga cadastrada para comparar.', 'error'); return;
  }

  const escopo = parseInt(qs('#vagas-escopo').value || '0');
  const topN   = escopo > 0 ? escopo : 9999;

  btnAnalyze.disabled = true;
  btnAText.textContent = 'Analisando…';
  show(btnASpinner);
  resultadosPorCurriculo = {};

  for (const arquivo of arquivosAnlise) {
    setStatusArquivo(arquivo.name, 'processando');
    try {
      const form = new FormData();
      form.append('file', arquivo);
      form.append('top_n', topN);

      const data = await fetch(API + '/match/upload-and-match', {
        method: 'POST', body: form,
      }).then(async res => {
        if (!res.ok) throw new Error((await res.json()).detail || `Erro ${res.status}`);
        return res.json();
      });

      resultadosPorCurriculo[arquivo.name] = data.results;
      setStatusArquivo(arquivo.name, 'concluido');
    } catch (err) {
      setStatusArquivo(arquivo.name, 'erro');
      showToast(`Erro em ${arquivo.name}: ${err.message}`, 'error');
    }
  }

  btnAnalyze.disabled = false;
  btnAText.textContent = 'Analisar';
  hide(btnASpinner);

  const concluidos = Object.keys(resultadosPorCurriculo).length;
  if (concluidos > 0) {
    renderizarResultados();
    showToast(`${concluidos} currículo(s) analisado(s) com sucesso.`, 'success');
  }
});

function renderizarResultados() {
  const section = qs('#results-section');
  const tabsEl  = qs('#curriculos-tabs');
  const listEl  = qs('#results-list');
  const metaEl  = qs('#results-meta');
  const badgeEl = qs('#results-metodo-badge');
  const nomes   = Object.keys(resultadosPorCurriculo);

  badgeEl.textContent = metodoAtivo.toUpperCase();
  badgeEl.className   = `metodo-tag ${metodoAtivo}`;

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
        paginaAtual = 1;
        nomeAtivo = tab.dataset.nome;
        renderizarListaResultados(nomeAtivo, listEl, metaEl);
      });
    });
  } else {
    hide(tabsEl);
  }

  paginaAtual = 1;
  nomeAtivo   = nomes[0];
  renderizarListaResultados(nomeAtivo, listEl, metaEl);
  show(section);
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderizarListaResultados(nome, listEl, metaEl) {
  const todos     = resultadosPorCurriculo[nome] || [];
  const total     = todos.length;
  const totalPags = Math.ceil(total / ITENS_POR_PAGINA);
  const inicio    = (paginaAtual - 1) * ITENS_POR_PAGINA;
  const pagina    = todos.slice(inicio, inicio + ITENS_POR_PAGINA);

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
        <div class="score-circle level-${(r.compatibility_level || 'baixo').toLowerCase()}">
          <span class="score-pct">${(r.similarity_percent || 0).toFixed(0)}%</span>
          <span class="score-lbl">${r.compatibility_level || '—'}</span>
        </div>
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
        (p >= paginaAtual - vizinhos && p <= paginaAtual + vizinhos)) {
      paginas.push(p);
    }
  }

  const itens = [];
  paginas.forEach((p, idx) => {
    if (idx > 0 && p - paginas[idx - 1] > 1) itens.push('...');
    itens.push(p);
  });

  const btnsPaginas = itens.map(p =>
    p === '...'
      ? `<span class="pag-ellipsis">…</span>`
      : `<button class="pag-btn${p === paginaAtual ? ' active' : ''}" data-p="${p}">${p}</button>`
  ).join('');

  pag.innerHTML = `
    <button class="pag-btn pag-nav" data-p="${paginaAtual - 1}" ${paginaAtual === 1 ? 'disabled' : ''}>‹</button>
    ${btnsPaginas}
    <button class="pag-btn pag-nav" data-p="${paginaAtual + 1}" ${paginaAtual === totalPags ? 'disabled' : ''}>›</button>`;

  pag.querySelectorAll('.pag-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      paginaAtual = parseInt(btn.dataset.p);
      renderizarListaResultados(nome, listEl, metaEl);
      qs('#results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

function renderBreakdown(r) {
  if (!r.tfidf_score && !r.skills_score) return '';
  const cov  = Math.round((r.skill_coverage || 0) * 100);
  const warn = r.warning
    ? `<div style="margin-top:8px;padding:6px 10px;border-radius:6px;background:rgba(239,68,68,.1);color:var(--danger);font-size:.78rem">⚠️ ${r.warning}</div>`
    : '';
  return `
    <div style="margin-top:8px;display:flex;gap:10px;flex-wrap:wrap">
      <span style="font-size:.76rem;color:var(--text-muted)">TF-IDF <strong style="color:var(--text)">${((r.tfidf_score || 0) * 100).toFixed(0)}%</strong></span>
      <span style="font-size:.76rem;color:var(--text-muted)">Skills <strong style="color:var(--text)">${((r.skills_score || 0) * 100).toFixed(0)}%</strong></span>
      <span style="font-size:.76rem;color:var(--text-muted)">Cobertura <strong style="color:var(--text)">${cov}%</strong></span>
    </div>${warn}`;
}

function renderSkillsGrid(r) {
  const ms  = r.matching_skills || [];
  const mis = r.missing_skills  || [];
  const ex  = r.extra_skills    || [];
  return `<div class="skills-grid">
    <div class="skills-group matching">
      <h4>✅ Em comum (${ms.length})</h4>
      <div class="skill-tags">${ms.length ? ms.map(s => `<span class="tag tag-matching">${s}</span>`).join('') : '<span class="tag-empty">—</span>'}</div>
    </div>
    <div class="skills-group missing">
      <h4>❌ Ausentes (${mis.length})</h4>
      <div class="skill-tags">${mis.length ? mis.map(s => `<span class="tag tag-missing">${s}</span>`).join('') : '<span class="tag-empty">Nenhuma</span>'}</div>
    </div>
    <div class="skills-group extra">
      <h4>➕ Extras (${ex.length})</h4>
      <div class="skill-tags">${ex.length ? ex.map(s => `<span class="tag tag-extra">${s}</span>`).join('') : '<span class="tag-empty">—</span>'}</div>
    </div>
  </div>`;
}

const btnQText    = qs('#btn-quick-text');
const btnQSpinner = qs('#btn-quick-spinner');

qs('#btn-quick').addEventListener('click', async () => {
  const resumeText = qs('#quick-resume').value.trim();
  const jobText    = qs('#quick-job').value.trim();
  if (!resumeText || !jobText) { showToast('Preencha os dois campos.', 'error'); return; }
  const btn = qs('#btn-quick');
  btn.disabled = true;
  btnQText.textContent = 'Aguarde…'; show(btnQSpinner);
  try {
    const data = await apiFetch('/match/quick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text:     resumeText,
        job_description: jobText,
        job_title:       qs('#quick-title').value.trim() || 'Vaga',
      }),
    });
    const el = qs('#quick-result');
    const r  = data.result;
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <div class="score-circle level-${(r.compatibility_level || 'baixo').toLowerCase()}" style="width:52px;height:52px">
          <span class="score-pct">${(r.similarity_percent || 0).toFixed(0)}%</span>
          <span class="score-lbl">${r.compatibility_level || '—'}</span>
        </div>
        <div>
          <strong>${r.job_title || 'Vaga'}</strong>
          <div style="font-size:.8rem;color:var(--text-muted);margin-top:2px">Score: ${(r.similarity_score || 0).toFixed(3)}</div>
          ${renderBreakdown(r)}
        </div>
      </div>
      ${renderSkillsGrid(r)}`;
    show(el);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btnQText.textContent = 'Comparar'; hide(btnQSpinner);
  }
});

function setupUploadSimples(dropId, inputId, iconId, nameId, removeId, onFile) {
  const drop   = qs(`#${dropId}`);
  const input  = qs(`#${inputId}`);
  const info   = drop?.nextElementSibling;
  const icon   = qs(`#${iconId}`);
  const name   = qs(`#${nameId}`);
  const remove = qs(`#${removeId}`);
  if (!drop || !input) return;
  let arquivo = null;

  function setFile(f) {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!EXTS.includes(ext)) { showToast('Formato não suportado.', 'error'); return; }
    arquivo = f;
    if (icon) icon.textContent = ICONS[ext] || '📄';
    if (name) name.textContent = f.name;
    hide(drop); if (info) show(info);
    onFile(f);
  }

  input.addEventListener('change', e => setFile(e.target.files[0]));
  drop.addEventListener('click', (e) => {
    if (e.target.closest('label')) return;
    input.click();
  });
  remove?.addEventListener('click', () => {
    arquivo = null; input.value = '';
    if (info) hide(info); show(drop); onFile(null);
  });
  ['dragover', 'dragenter'].forEach(ev =>
    drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('drag-over'); }));
  ['dragleave', 'drop'].forEach(ev =>
    drop.addEventListener(ev, e => {
      e.preventDefault(); drop.classList.remove('drag-over');
      if (ev === 'drop') setFile(e.dataTransfer.files[0]);
    }));

  drop._getArquivo = () => arquivo;
}

setupUploadSimples('drop-zone-cmp', 'file-input-cmp', 'file-icon-cmp', 'file-name-cmp', 'remove-file-cmp',
  f => { qs('#btn-comparar').disabled = !f; });

const btnCText    = qs('#btn-comparar-text');
const btnCSpinner = qs('#btn-comparar-spinner');

qs('#btn-comparar')?.addEventListener('click', async () => {
  const dropCmp = qs('#drop-zone-cmp');
  const arquivo = dropCmp?._getArquivo?.();
  if (!arquivo) return;

  qs('#btn-comparar').disabled = true;
  btnCText.textContent = 'Aguarde…'; show(btnCSpinner);

  try {
    const topN = parseInt(qs('#top-n-cmp').value) || 5;
    const form = new FormData();
    form.append('file', arquivo);
    form.append('top_n', topN);

    const dataTfidf = await fetch(API + '/match/upload-and-match', {
      method: 'POST', body: form,
    }).then(async res => {
      if (!res.ok) throw new Error((await res.json()).detail || `Erro ${res.status}`);
      return res.json();
    });

    const dataSbert = simularSbert(dataTfidf.results);
    renderComparativo(dataTfidf.results, dataSbert, topN);
    showToast('Comparativo gerado. SBERT simulado — fase 2 em desenvolvimento.', 'info');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    qs('#btn-comparar').disabled = false;
    btnCText.textContent = 'Comparar TF-IDF vs SBERT'; hide(btnCSpinner);
  }
});

function simularSbert(resultsTfidf) {
  return resultsTfidf.map(r => {
    const v = (Math.random() - 0.4) * 0.15;
    const s = Math.max(0.05, Math.min(0.98, r.similarity_score + v));
    return { ...r, similarity_score: +s.toFixed(4), similarity_percent: +(s * 100).toFixed(2),
      compatibility_level: s >= 0.7 ? 'Alto' : s >= 0.4 ? 'Médio' : 'Baixo' };
  }).sort((a, b) => b.similarity_score - a.similarity_score);
}

function renderComparativo(tfidf, sbert, topN) {
  const section = qs('#comparativo-section');
  const list    = qs('#comparativo-list');
  list.innerHTML = '';

  const mapT = Object.fromEntries(tfidf.map(r => [r.job_id, r]));
  const mapS = Object.fromEntries(sbert.map(r => [r.job_id, r]));
  const ids  = [...new Set([...tfidf.map(r => r.job_id)])].slice(0, topN);

  ids.forEach(id => {
    const t = mapT[id]; const s = mapS[id];
    if (!t || !s) return;
    const diff = s.similarity_score - t.similarity_score;
    const dPct = (diff * 100).toFixed(1);
    const dCls = diff > 0.01 ? 'diff-pos' : diff < -0.01 ? 'diff-neg' : 'diff-neu';
    const dLbl = diff > 0.01 ? `▲ +${dPct}%` : diff < -0.01 ? `▼ ${dPct}%` : `≈ ${dPct}%`;
    const rankT = tfidf.findIndex(r => r.job_id === id) + 1;
    const rankS = sbert.findIndex(r => r.job_id === id) + 1;

    const row = document.createElement('div');
    row.innerHTML = `
      <div class="cmp-vaga-label">${t.job_title}</div>
      <div class="comparativo-row">
        <div class="comparativo-cell tfidf-cell">
          <div class="cmp-header">
            <div class="score-circle level-${(t.compatibility_level || 'baixo').toLowerCase()}" style="width:52px;height:52px">
              <span class="score-pct">${t.similarity_percent.toFixed(0)}%</span>
              <span class="score-lbl">${t.compatibility_level}</span>
            </div>
            <div>
              <div style="font-size:.8rem;color:var(--text-muted)">Score: ${t.similarity_score.toFixed(3)}</div>
              ${renderBreakdown(t)}
            </div>
            <span class="cmp-rank">#${rankT}</span>
          </div>
          <div class="cmp-score-bar"><div class="cmp-score-fill tfidf-fill" style="width:${t.similarity_percent}%"></div></div>
          ${renderSkillsMini(t)}
        </div>
        <div class="comparativo-cell sbert-cell">
          <div class="cmp-header">
            <div class="score-circle level-${(s.compatibility_level || 'baixo').toLowerCase()}" style="width:52px;height:52px">
              <span class="score-pct">${s.similarity_percent.toFixed(0)}%</span>
              <span class="score-lbl">${s.compatibility_level}</span>
            </div>
            <div>
              <div style="font-size:.8rem;color:var(--text-muted)">Score: ${s.similarity_score.toFixed(3)}</div>
              <span class="cmp-diff ${dCls}">${dLbl} vs TF-IDF</span>
            </div>
            <span class="cmp-rank">#${rankS}</span>
          </div>
          <div class="cmp-score-bar"><div class="cmp-score-fill sbert-fill" style="width:${s.similarity_percent}%"></div></div>
          <div style="font-size:.75rem;color:var(--text-muted);margin-top:6px;font-style:italic">🧠 Embeddings semânticos — fase 2</div>
        </div>
      </div>`;
    list.appendChild(row);
  });

  renderStats(tfidf, sbert);
  show(section); show(qs('#comparativo-stats'));
}

function renderSkillsMini(r) {
  const ms = (r.matching_skills || []).slice(0, 4);
  if (!ms.length) return '';
  return `<div class="skill-tags" style="margin-top:6px">
    ${ms.map(s => `<span class="tag tag-matching">${s}</span>`).join('')}
    ${(r.matching_skills || []).length > 4 ? `<span class="tag tag-extra">+${r.matching_skills.length - 4}</span>` : ''}
  </div>`;
}

function renderStats(tfidf, sbert) {
  const st = tfidf.map(r => r.similarity_score);
  const ss = sbert.map(r => r.similarity_score);
  const n  = Math.min(st.length, ss.length);
  if (n < 2) return;
  const mt  = st.reduce((a, b) => a + b, 0) / n;
  const ms  = ss.reduce((a, b) => a + b, 0) / n;
  const num  = st.slice(0, n).reduce((a, t, i) => a + (t - mt) * (ss[i] - ms), 0);
  const denT = Math.sqrt(st.slice(0, n).reduce((a, t) => a + (t - mt) ** 2, 0));
  const denS = Math.sqrt(ss.reduce((a, s) => a + (s - ms) ** 2, 0));
  const corr = denT && denS ? num / (denT * denS) : 0;
  const diffs = st.map((t, i) => Math.abs(t - (ss[i] || t)));
  const maior = Math.max(...diffs) * 100;
  const top3T = new Set(tfidf.slice(0, 3).map(r => r.job_id));
  const top3S = new Set(sbert.slice(0, 3).map(r => r.job_id));
  const conc  = [...top3T].filter(id => top3S.has(id)).length;
  qs('#stat-correlacao').textContent   = corr.toFixed(2);
  qs('#stat-maior-diff').textContent   = `${maior.toFixed(1)}%`;
  qs('#stat-concordancia').textContent = `${conc}/3`;
}

// ── Vagas (aba) ───────────────────────────────────────────
async function loadJobs() {
  const container = qs('#jobs-list');
  container.innerHTML = '<p class="empty-state">Carregando…</p>';
  try {
    const data = await apiFetch('/jobs?limit=100');
    vagasCadastradas = data.jobs || [];
    const totalReal = data.total || vagasCadastradas.length;
    const txt = `${totalReal} vaga${totalReal !== 1 ? 's' : ''} cadastrada${totalReal !== 1 ? 's' : ''}`;
    const b2 = qs('#total-vagas-jobs');
    if (b2) b2.innerHTML = `<strong>${txt}</strong>`;
    atualizarTempoEstimado();

    if (!vagasCadastradas.length) {
      container.innerHTML = '<p class="empty-state">Nenhuma vaga cadastrada.</p>'; return;
    }
    container.innerHTML = '';
    vagasCadastradas.forEach(job => {
      const skills = Object.values(job.extracted_skills || {}).flat().slice(0, 8);
      const item   = document.createElement('div');
      item.className = 'job-item';
      item.innerHTML = `
        <div class="job-item-info" style="flex:1">
          <h4>${job.title}</h4>
          <div class="job-meta">${job.company || '—'} · ${job.source || 'manual'} · ID #${job.id}</div>
          <div class="skill-tags" style="margin-top:6px">
            ${skills.map(s => `<span class="tag tag-extra">${s}</span>`).join('')}
            ${!skills.length ? '<span class="tag-empty">Skills não detectadas</span>' : ''}
          </div>
        </div>
        <button class="btn-icon" onclick="deleteJob(${job.id},this)" title="Remover">🗑️</button>`;
      container.appendChild(item);
    });
  } catch (err) { container.innerHTML = `<p class="empty-state">${err.message}</p>`; }
}

window.deleteJob = async (id, btn) => {
  if (!confirm('Remover esta vaga?')) return;
  try {
    await fetch(`${API}/jobs/${id}`, { method: 'DELETE' });
    btn.closest('.job-item').remove();
    vagasCadastradas = vagasCadastradas.filter(v => v.id !== id);
    atualizarContadorVagas();
    showToast('Vaga removida.', 'success');
  } catch { showToast('Erro ao remover.', 'error'); }
};

const btnJobText    = qs('#btn-job-text');
const btnJobSpinner = qs('#btn-job-spinner');

qs('#btn-save-job').addEventListener('click', async () => {
  const title = qs('#job-title').value.trim();
  const desc  = qs('#job-desc').value.trim();
  const msg   = qs('#job-msg');
  if (!title || !desc) {
    msg.textContent = 'Preencha título e descrição.'; msg.className = 'msg msg-error'; show(msg); return;
  }
  const btn = qs('#btn-save-job');
  btn.disabled = true; btnJobText.textContent = 'Aguarde…'; show(btnJobSpinner); hide(msg);
  try {
    await apiFetch('/jobs', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, company: qs('#job-company').value.trim() || null,
        description: desc, source: qs('#job-source').value }),
    });
    msg.textContent = '✅ Vaga salva!'; msg.className = 'msg msg-success'; show(msg);
    qs('#job-title').value = ''; qs('#job-company').value = ''; qs('#job-desc').value = '';
    loadJobs();
  } catch (err) {
    msg.textContent = err.message; msg.className = 'msg msg-error'; show(msg);
  } finally {
    btn.disabled = false; btnJobText.textContent = 'Salvar Vaga'; hide(btnJobSpinner);
  }
});

qs('#btn-refresh-jobs')?.addEventListener('click', loadJobs);

qs('#btn-load-history')?.addEventListener('click', async () => {
  const id = qs('#history-resume-id').value.trim();
  if (!id) { showToast('Informe o ID do currículo.', 'error'); return; }
  const container = qs('#history-list');
  container.innerHTML = '<p class="empty-state">Buscando…</p>';
  try {
    const data = await apiFetch(`/history/resume/${id}`);
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">Nenhum histórico encontrado.</p>'; return;
    }
    container.innerHTML = '';
    data.forEach(h => {
      const item = document.createElement('div');
      item.className = 'history-item';
      const metodo = h.metodo || 'tfidf';
      item.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
          <strong>Vaga #${h.job_id}</strong>
          <span class="metodo-tag ${metodo}">${metodo.toUpperCase()}</span>
          <span class="tag tag-${h.compatibility_level === 'Alto' ? 'matching' : h.compatibility_level === 'Médio' ? 'extra' : 'missing'}">
            ${(h.similarity_percent || 0).toFixed(1)}% · ${h.compatibility_level}
          </span>
        </div>
        <div style="font-size:.78rem;color:var(--text-muted);margin-top:4px">
          ${new Date(h.created_at).toLocaleString('pt-BR')}
        </div>
        <div class="skill-tags" style="margin-top:8px">
          ${(h.matching_skills || []).slice(0, 6).map(s => `<span class="tag tag-matching">${s}</span>`).join('')}
        </div>`;
      container.appendChild(item);
    });
  } catch (err) { container.innerHTML = `<p class="empty-state">${err.message}</p>`; }
});

checkHealth();
carregarVagas();