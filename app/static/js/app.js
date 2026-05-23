/* ======================================================
   Resume Job Matcher — Frontend JavaScript
   ====================================================== */

const API = '/api/v1';

// ── Utilidades ──────────────────────────────────────────

function qs(sel, ctx = document) { return ctx.querySelector(sel); }
function qsa(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function show(el) { el && el.classList.remove('hidden'); }
function hide(el) { el && el.classList.add('hidden'); }
function toggle(el, condition) { condition ? show(el) : hide(el); }

function showToast(msg, type = 'info') {
  const t = qs('#toast');
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  show(t);
  setTimeout(() => hide(t), 3500);
}

function setLoading(btnText, btnSpinner, loading) {
  btnText.textContent = loading ? 'Aguarde…' : btnText.dataset.original;
  toggle(btnSpinner, loading);
}

async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

// ── Health check ────────────────────────────────────────

async function checkHealth() {
  const badge = qs('#status-badge');
  try {
    const data = await fetch('/health').then(r => r.json());
    badge.textContent = `Online • spaCy ${data.model_language.toUpperCase()}`;
    badge.className = 'status-badge status-ok';
  } catch {
    badge.textContent = 'Offline';
    badge.className = 'status-badge status-error';
  }
}

// ── Navegação por abas ───────────────────────────────────

qsa('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    qsa('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    qsa('.tab-content').forEach(s => {
      toggle(s, s.id === `tab-${tab}`);
      s.classList.toggle('active', s.id === `tab-${tab}`);
    });
    if (tab === 'jobs') loadJobs();
  });
});

// ── Upload + Drag & Drop ─────────────────────────────────

let selectedFile = null;

const dropZone  = qs('#drop-zone');
const fileInput = qs('#file-input');
const fileInfo  = qs('#file-info');
const fileName  = qs('#file-name');
const removeBtn = qs('#remove-file');
const btnAnalyze = qs('#btn-analyze');

function setFile(file) {
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx', 'txt'].includes(ext)) {
    showToast('Formato não suportado. Use PDF, DOCX ou TXT.', 'error');
    return;
  }
  selectedFile = file;
  const icons = { pdf: '📕', docx: '📘', txt: '📄' };
  qs('#file-icon').textContent = icons[ext] || '📄';
  fileName.textContent = file.name;
  hide(dropZone); show(fileInfo);
  btnAnalyze.disabled = false;
}

fileInput.addEventListener('change', e => setFile(e.target.files[0]));
dropZone.addEventListener('click', () => fileInput.click());
removeBtn.addEventListener('click', () => {
  selectedFile = null; fileInput.value = '';
  show(dropZone); hide(fileInfo);
  btnAnalyze.disabled = true;
});

['dragover', 'dragenter'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault(); dropZone.classList.add('drag-over');
  })
);
['dragleave', 'drop'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    if (evt === 'drop') setFile(e.dataTransfer.files[0]);
  })
);

// ── Análise de arquivo ───────────────────────────────────

const btnAnalyzeText    = qs('#btn-analyze-text');
const btnAnalyzeSpinner = qs('#btn-analyze-spinner');
btnAnalyzeText.dataset.original = btnAnalyzeText.textContent;

qs('#btn-analyze').addEventListener('click', async () => {
  if (!selectedFile) return;
  setLoading(btnAnalyzeText, btnAnalyzeSpinner, true);
  btnAnalyze.disabled = true;

  try {
    const topN = parseInt(qs('#top-n').value) || 5;
    const form = new FormData();
    form.append('file', selectedFile);
    form.append('top_n', topN);

    const data = await fetch(API + '/match/upload-and-match', {
      method: 'POST', body: form,
    }).then(async res => {
      if (!res.ok) throw new Error((await res.json()).detail || `Erro ${res.status}`);
      return res.json();
    });

    renderResults(data);
    showToast(`Análise concluída! ${data.total_jobs_analyzed} vagas analisadas.`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setLoading(btnAnalyzeText, btnAnalyzeSpinner, false);
    btnAnalyze.disabled = false;
  }
});

// ── Match rápido ─────────────────────────────────────────

const btnQuickText    = qs('#btn-quick-text');
const btnQuickSpinner = qs('#btn-quick-spinner');
btnQuickText.dataset.original = btnQuickText.textContent;

qs('#btn-quick').addEventListener('click', async () => {
  const resumeText = qs('#quick-resume').value.trim();
  const jobText    = qs('#quick-job').value.trim();
  if (!resumeText || !jobText) {
    showToast('Preencha o texto do currículo e da vaga.', 'error'); return;
  }

  const btn = qs('#btn-quick');
  btn.disabled = true;
  setLoading(btnQuickText, btnQuickSpinner, true);

  try {
    const data = await apiFetch('/match/quick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description: jobText,
        job_title: qs('#quick-title').value.trim() || 'Vaga',
      }),
    });

    renderQuickResult(data.result);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    setLoading(btnQuickText, btnQuickSpinner, false);
  }
});

function renderScoreBreakdown(r) {
  if (!r.tfidf_score && !r.skills_score) return '';
  const covPct = Math.round((r.skill_coverage || 0) * 100);
  const warn = r.warning
    ? `<div style="margin-top:10px;padding:8px 10px;border-radius:6px;background:rgba(239,68,68,.1);color:var(--danger);font-size:.8rem">⚠️ ${r.warning}</div>`
    : '';
  return `
    <div style="margin-top:10px;display:flex;gap:12px;flex-wrap:wrap">
      <div style="font-size:.78rem;color:var(--text-muted)">
        TF-IDF <strong style="color:var(--text)">${(r.tfidf_score*100).toFixed(0)}%</strong>
      </div>
      <div style="font-size:.78rem;color:var(--text-muted)">
        Skills <strong style="color:var(--text)">${(r.skills_score*100).toFixed(0)}%</strong>
      </div>
      <div style="font-size:.78rem;color:var(--text-muted)">
        Cobertura técnica <strong style="color:var(--text)">${covPct}%</strong>
      </div>
    </div>
    ${warn}
  `;
}

function renderQuickResult(r) {
  const el = qs('#quick-result');
  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px">
      <div class="score-circle level-${r.compatibility_level.toLowerCase()}" style="width:56px;height:56px">
        <span class="score-pct">${r.similarity_percent.toFixed(0)}%</span>
        <span class="score-lbl">${r.compatibility_level}</span>
      </div>
      <div>
        <strong>${r.job_title}</strong>
        <div style="font-size:.82rem;color:var(--text-muted);margin-top:2px">Score final: ${r.similarity_score.toFixed(3)}</div>
        ${renderScoreBreakdown(r)}
      </div>
    </div>
    ${renderSkillsGrid(r)}
  `;
  show(el);
}

// ── Renderização de resultados ───────────────────────────

function renderResults(data) {
  const section = qs('#results-section');
  const list    = qs('#results-list');
  const meta    = qs('#results-meta');

  meta.textContent = `${data.results.length} vagas encontradas de ${data.total_jobs_analyzed} analisadas`;
  list.innerHTML = '';

  if (!data.results.length) {
    list.innerHTML = '<p class="empty-state">Nenhuma vaga cadastrada para comparar. Cadastre vagas na aba "Vagas".</p>';
    show(section); return;
  }

  data.results.forEach((r, i) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const levelClass = `level-${r.compatibility_level.toLowerCase()}`;

    card.innerHTML = `
      <span class="result-rank">#${i + 1}</span>
      <div class="result-header-row">
        <div class="score-circle ${levelClass}">
          <span class="score-pct">${r.similarity_percent.toFixed(0)}%</span>
          <span class="score-lbl">${r.compatibility_level}</span>
        </div>
        <div class="result-info">
          <h3>${r.job_title}</h3>
          <div class="company">Score final: ${r.similarity_score.toFixed(3)}</div>
          ${renderScoreBreakdown(r)}
        </div>
      </div>
      ${renderSkillsGrid(r)}
    `;
    list.appendChild(card);
  });

  show(section);
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderSkillsGrid(r) {
  return `
    <div class="skills-grid">
      <div class="skills-group matching">
        <h4>✅ Em comum (${r.matching_skills.length})</h4>
        <div class="skill-tags">
          ${r.matching_skills.length
            ? r.matching_skills.map(s => `<span class="tag tag-matching">${s}</span>`).join('')
            : '<span class="tag-empty">—</span>'}
        </div>
      </div>
      <div class="skills-group missing">
        <h4>❌ Ausentes (${r.missing_skills.length})</h4>
        <div class="skill-tags">
          ${r.missing_skills.length
            ? r.missing_skills.map(s => `<span class="tag tag-missing">${s}</span>`).join('')
            : '<span class="tag-empty">Nenhuma</span>'}
        </div>
      </div>
      <div class="skills-group extra">
        <h4>➕ Extras (${r.extra_skills.length})</h4>
        <div class="skill-tags">
          ${r.extra_skills.length
            ? r.extra_skills.map(s => `<span class="tag tag-extra">${s}</span>`).join('')
            : '<span class="tag-empty">—</span>'}
        </div>
      </div>
    </div>
  `;
}

// ── Gerenciar vagas ──────────────────────────────────────

async function loadJobs() {
  const container = qs('#jobs-list');
  container.innerHTML = '<p class="empty-state">Carregando…</p>';
  try {
    const data = await apiFetch('/jobs?limit=50');
    if (!data.jobs.length) {
      container.innerHTML = '<p class="empty-state">Nenhuma vaga cadastrada ainda.</p>';
      return;
    }
    container.innerHTML = '';
    data.jobs.forEach(job => {
      const allSkills = Object.values(job.extracted_skills || {}).flat().slice(0, 8);
      const item = document.createElement('div');
      item.className = 'job-item';
      item.innerHTML = `
        <div class="job-item-info" style="flex:1">
          <h4>${job.title}</h4>
          <div class="job-meta">${job.company || '—'} · ${job.source || 'manual'} · ID #${job.id}</div>
          <div class="job-skills skill-tags mt-4" style="margin-top:6px">
            ${allSkills.map(s => `<span class="tag tag-extra">${s}</span>`).join('')}
            ${allSkills.length === 0 ? '<span class="tag-empty">Skills não detectadas</span>' : ''}
          </div>
        </div>
        <button class="btn-icon" onclick="deleteJob(${job.id}, this)" title="Remover">🗑️</button>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    container.innerHTML = `<p class="empty-state">${err.message}</p>`;
  }
}

window.deleteJob = async (id, btn) => {
  if (!confirm('Remover esta vaga?')) return;
  try {
    await fetch(`${API}/jobs/${id}`, { method: 'DELETE' });
    btn.closest('.job-item').remove();
    showToast('Vaga removida.', 'success');
  } catch { showToast('Erro ao remover vaga.', 'error'); }
};

const btnJobText    = qs('#btn-job-text');
const btnJobSpinner = qs('#btn-job-spinner');
btnJobText.dataset.original = btnJobText.textContent;

qs('#btn-save-job').addEventListener('click', async () => {
  const title = qs('#job-title').value.trim();
  const desc  = qs('#job-desc').value.trim();
  const msg   = qs('#job-msg');

  if (!title || !desc) {
    msg.textContent = 'Preencha o título e a descrição da vaga.';
    msg.className = 'msg msg-error'; show(msg); return;
  }

  const btn = qs('#btn-save-job');
  btn.disabled = true;
  setLoading(btnJobText, btnJobSpinner, true);
  hide(msg);

  try {
    await apiFetch('/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        company: qs('#job-company').value.trim() || null,
        description: desc,
        source: qs('#job-source').value,
      }),
    });

    msg.textContent = '✅ Vaga salva com sucesso!';
    msg.className = 'msg msg-success'; show(msg);
    qs('#job-title').value = '';
    qs('#job-company').value = '';
    qs('#job-desc').value = '';
    loadJobs();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = 'msg msg-error'; show(msg);
  } finally {
    btn.disabled = false;
    setLoading(btnJobText, btnJobSpinner, false);
  }
});

qs('#btn-refresh-jobs').addEventListener('click', loadJobs);

// ── Histórico ────────────────────────────────────────────

qs('#btn-load-history').addEventListener('click', async () => {
  const id = qs('#history-resume-id').value.trim();
  if (!id) { showToast('Informe o ID do currículo.', 'error'); return; }

  const container = qs('#history-list');
  container.innerHTML = '<p class="empty-state">Buscando…</p>';

  try {
    const data = await apiFetch(`/history/resume/${id}`);
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">Nenhum histórico encontrado para este currículo.</p>';
      return;
    }
    container.innerHTML = '';
    data.forEach(h => {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center">
          <strong>Vaga #${h.job_id}</strong>
          <span class="tag tag-${h.compatibility_level === 'Alto' ? 'matching' : h.compatibility_level === 'Médio' ? 'extra' : 'missing'}">
            ${h.similarity_percent.toFixed(1)}% · ${h.compatibility_level}
          </span>
        </div>
        <div style="font-size:.8rem;color:var(--text-muted);margin-top:4px">
          ${new Date(h.created_at).toLocaleString('pt-BR')}
        </div>
        <div class="skill-tags mt-4" style="margin-top:8px">
          ${h.matching_skills.slice(0, 6).map(s => `<span class="tag tag-matching">${s}</span>`).join('')}
        </div>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    container.innerHTML = `<p class="empty-state">${err.message}</p>`;
  }
});

// ── Init ─────────────────────────────────────────────────

checkHealth();
