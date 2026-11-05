const API = '/api/v1';

export async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

export async function uploadAndMatch(arquivo, limiteVagas = 0) {
  const form = new FormData();
  form.append('file', arquivo);
  form.append('limite_vagas', limiteVagas);
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

export async function fetchJobOptions() {
  return apiFetch('/jobs/opcoes');
}

export async function fetchResumesForJob(jobId) {
  return apiFetch(`/match/job/${jobId}/resumes`);
}

export async function fetchResumes() {
  return apiFetch('/resumes');
}

export async function uploadResume(arquivo) {
  const form = new FormData();
  form.append('file', arquivo);
  return apiFetch('/resumes/upload', { method: 'POST', body: form });
}

export async function deleteResumeApi(id) {
  const res = await fetch(`${API}/resumes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Erro ao remover currículo.');
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
