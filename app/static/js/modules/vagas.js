// vagas.js — gerenciamento da aba Vagas
import { qs, show, hide, showToast } from './ui.js';
import { fetchJobs, saveJob, deleteJobApi } from './api.js';
import { state } from './state.js';
import { atualizarTempoEstimado } from './match.js';

export function atualizarContadorVagas() {
  const total = state.vagasCadastradas.length;
  const txt = `${total} vaga${total !== 1 ? 's' : ''} cadastrada${total !== 1 ? 's' : ''}`;
  const b1 = qs('#total-vagas-badge');
  const b2 = qs('#total-vagas-jobs');
  if (b1) b1.innerHTML = `<strong>${txt}</strong>`;
  if (b2) b2.innerHTML = `<strong>${txt}</strong>`;
  atualizarTempoEstimado();
}

export async function carregarVagas() {
  try {
    const data = await fetchJobs(100);
    state.vagasCadastradas = data.jobs || [];
    const totalReal = data.total || state.vagasCadastradas.length;
    const txt = `${totalReal} vaga${totalReal !== 1 ? 's' : ''} cadastrada${totalReal !== 1 ? 's' : ''}`;
    const b1 = qs('#total-vagas-badge');
    const b2 = qs('#total-vagas-jobs');
    if (b1) b1.innerHTML = `<strong>${txt}</strong>`;
    if (b2) b2.innerHTML = `<strong>${txt}</strong>`;
    atualizarTempoEstimado();
  } catch { /* silencioso */ }
}

export async function loadJobs() {
  const container = qs('#jobs-list');
  container.innerHTML = '<p class="empty-state">Carregando…</p>';
  try {
    const data = await fetchJobs(100);
    state.vagasCadastradas = data.jobs || [];
    const totalReal = data.total || state.vagasCadastradas.length;
    const txt = `${totalReal} vaga${totalReal !== 1 ? 's' : ''} cadastrada${totalReal !== 1 ? 's' : ''}`;
    const b2 = qs('#total-vagas-jobs');
    if (b2) b2.innerHTML = `<strong>${txt}</strong>`;
    atualizarTempoEstimado();

    if (!state.vagasCadastradas.length) {
      container.innerHTML = '<p class="empty-state">Nenhuma vaga cadastrada.</p>'; return;
    }

    container.innerHTML = '';
    state.vagasCadastradas.forEach(job => {
      const skills = Object.values(job.extracted_skills || {}).flat().slice(0, 8);
      const item   = document.createElement('div');
      item.className = 'job-item';
      item.innerHTML = `
        <div class="job-item-info">
          <h4>${job.title}</h4>
          <div class="job-meta">${job.company || '—'} · ${job.source || 'manual'} · ID #${job.id}</div>
          <div class="skill-tags" style="margin-top:6px">
            ${skills.map(s => `<span class="tag tag-extra">${s}</span>`).join('')}
            ${!skills.length ? '<span class="tag-empty">Skills não detectadas</span>' : ''}
          </div>
        </div>
        <button class="btn-icon btn-delete-job" data-id="${job.id}" title="Remover">🗑️</button>`;
      container.appendChild(item);
    });

    container.querySelectorAll('.btn-delete-job').forEach(btn =>
      btn.addEventListener('click', () => handleDeleteJob(parseInt(btn.dataset.id), btn)));

  } catch (err) {
    container.innerHTML = `<p class="empty-state">${err.message}</p>`;
  }
}

async function handleDeleteJob(id, btn) {
  if (!confirm('Remover esta vaga?')) return;
  try {
    await deleteJobApi(id);
    btn.closest('.job-item').remove();
    state.vagasCadastradas = state.vagasCadastradas.filter(v => v.id !== id);
    atualizarContadorVagas();
    showToast('Vaga removida.', 'success');
  } catch {
    showToast('Erro ao remover.', 'error');
  }
}

export function setupVagas() {
  qs('#btn-save-job').addEventListener('click', handleSaveJob);
  qs('#btn-refresh-jobs')?.addEventListener('click', loadJobs);
}

async function handleSaveJob() {
  const title = qs('#job-title').value.trim();
  const desc  = qs('#job-desc').value.trim();
  const msg   = qs('#job-msg');
  const btn   = qs('#btn-save-job');
  const text  = qs('#btn-job-text');
  const spin  = qs('#btn-job-spinner');

  if (!title || !desc) {
    msg.textContent = 'Preencha título e descrição.';
    msg.className = 'msg msg-error';
    show(msg); return;
  }

  btn.disabled = true;
  text.textContent = 'Aguarde…';
  show(spin);
  hide(msg);

  try {
    await saveJob({
      title,
      company:     qs('#job-company').value.trim() || null,
      description: desc,
      source:      qs('#job-source').value,
    });
    msg.textContent = '✅ Vaga salva!';
    msg.className = 'msg msg-success';
    show(msg);
    qs('#job-title').value   = '';
    qs('#job-company').value = '';
    qs('#job-desc').value    = '';
    loadJobs();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = 'msg msg-error';
    show(msg);
  } finally {
    btn.disabled = false;
    text.textContent = 'Salvar Vaga';
    hide(spin);
  }
}
