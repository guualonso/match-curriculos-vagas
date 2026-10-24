// api.js — comunicação com o backend
const API = '/api/v1';

export async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

export async function uploadAndMatch(arquivo, topN, metodo = 'tfidf') {
  const form = new FormData();
  form.append('file', arquivo);
  form.append('top_n', topN);
  form.append('metodo', metodo);
  const res = await fetch(API + '/match/upload-and-match', { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || `Erro ${res.status}`);
  return res.json();
}

export async function quickMatch(payload) {
  return apiFetch('/match/quick', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function fetchJobs(limit = 100) {
  return apiFetch(`/jobs?limit=${limit}`);
}

export async function saveJob(payload) {
  return apiFetch('/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteJobApi(id) {
  const res = await fetch(`${API}/jobs/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Erro ao remover vaga.');
}

export async function fetchHistory(resumeId) {
  return apiFetch(`/history/resume/${resumeId}`);
}

export async function checkHealth() {
  const { qs } = await import('./ui.js');
  const badge = qs('#status-badge');
  try {
    const data = await fetch('/health').then(r => r.json());
    const lang = data.model_language || data.language || 'pt';
    badge.textContent = `Online · spaCy ${lang.toUpperCase()}`;
    badge.className = 'status-badge status-ok';
  } catch {
    badge.textContent = 'Offline';
    badge.className = 'status-badge status-error';
  }
}

export async function compareMethods(arquivo, topN) {
  const form = new FormData();
  form.append('file', arquivo);
  form.append('top_n', topN);
  const res = await fetch('/api/v1/match/compare', { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || `Erro ${res.status}`);
  return res.json();
}
