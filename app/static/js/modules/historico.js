// historico.js
import { qs, showToast } from './ui.js';
import { apiFetch, fetchHistory } from './api.js';

const LIMITE_PREVIA_SKILLS = 8;

const ICONE_SETA = `
  <svg class="hr-arrow" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>`;

const ICONE_CHEVRON = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 9l6 6 6-6" />
  </svg>`;

export function setupHistorico() {
  qs('#btn-load-history')?.addEventListener('click', handleLoadHistory);
  qs('#history-resume-id')?.addEventListener('keydown', evento => {
    if (evento.key === 'Enter') handleLoadHistory();
  });
  carregarUltimosHistoricos();
}

// Carrega automaticamente os últimos 10 ao abrir a aba
async function carregarUltimosHistoricos() {
  try {
    const registros = await apiFetch('/history/recent?limit=10');
    if (registros?.length) {
      renderHistorico(registros, qs('#history-list'), 'Últimas análises');
    }
  } catch {
    // endpoint pode não existir ainda — silencioso
  }
}

async function handleLoadHistory() {
  const idCurriculo = qs('#history-resume-id').value.trim();
  if (!idCurriculo) { showToast('Informe o ID do currículo.', 'error'); return; }

  const metodoFiltro = qs('#history-metodo').value;
  const container = qs('#history-list');
  container.innerHTML = '<p class="empty-state">Buscando…</p>';

  try {
    const registros = await fetchHistory(idCurriculo);
    const registrosFiltrados = metodoFiltro
      ? registros.filter(registro => normalizarMetodo(registro.metodo) === metodoFiltro)
      : registros;

    if (!registrosFiltrados.length) {
      container.innerHTML = '<p class="empty-state">Nenhum histórico encontrado.</p>';
      return;
    }
    renderHistorico(registrosFiltrados, container, `Currículo #${idCurriculo}`);
  } catch (erro) {
    container.innerHTML = `<p class="empty-state">${erro.message}</p>`;
  }
}

// ── Helpers ─────────────────────────────────────────────

function normalizarMetodo(metodo) {
  return (metodo || 'tfidf').toLowerCase();
}

function classeDoNivel(nivel) {
  if (nivel === 'Alto') return 'alto';
  if (nivel === 'Médio') return 'medio';
  return 'baixo';
}

function formatarData(dataTexto) {
  const data = new Date(dataTexto);
  if (Number.isNaN(data.getTime())) return { dia: '—', hora: '' };
  return {
    dia: data.toLocaleDateString('pt-BR'),
    hora: data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
  };
}

function renderTags(skills, classeTag) {
  if (!skills.length) return '<span class="tag-empty">—</span>';
  return skills.map(skill => `<span class="tag ${classeTag}">${skill}</span>`).join('');
}

// ── Render ──────────────────────────────────────────────

function renderHistorico(registros, container, titulo) {
  container.innerHTML = '';

  const cabecalho = document.createElement('div');
  cabecalho.className = 'history-list-header';
  cabecalho.innerHTML = `
    <h2>${titulo}</h2>
    <span>${registros.length} ${registros.length === 1 ? 'análise' : 'análises'}</span>`;
  container.appendChild(cabecalho);

  registros.forEach(registro => container.appendChild(criarLinha(registro)));
}

function criarLinha(registro) {
  const metodo = normalizarMetodo(registro.metodo);
  const nivel = registro.compatibility_level || '—';
  const percentual = Number(registro.similarity_percent) || 0;
  const { dia, hora } = formatarData(registro.created_at);

  const skillsEmComum = registro.matching_skills || [];
  const skillsAusentes = registro.missing_skills || [];
  const skillsExtras = registro.extra_skills || [];

  const quantidadeRestante = Math.max(skillsEmComum.length - LIMITE_PREVIA_SKILLS, 0);
  const previaSkills = skillsEmComum.length
    ? `<div class="hr-skills">
         ${renderTags(skillsEmComum.slice(0, LIMITE_PREVIA_SKILLS), 'tag-matching')}
         ${quantidadeRestante > 0 ? `<span class="tag tag-extra">+${quantidadeRestante}</span>` : ''}
       </div>`
    : '';

  const linha = document.createElement('article');
  linha.className = `history-row nivel-${classeDoNivel(nivel)}`;
  linha.innerHTML = `
    <div class="hr-main">
      <div class="hr-ids">
        <span class="hr-id">
          <span class="hr-id-label">Currículo</span>
          <strong>#${registro.resume_id}</strong>
        </span>
        ${ICONE_SETA}
        <span class="hr-id">
          <span class="hr-id-label">Vaga</span>
          <strong>#${registro.job_id}</strong>
        </span>
        <span class="metodo-tag ${metodo}">${metodo.toUpperCase()}</span>
      </div>

      <div class="hr-score-block" title="${percentual.toFixed(1)}%">
        <div class="hr-score-top">
          <span class="hr-score">${percentual.toFixed(1)}%</span>
          <span class="hr-nivel">${nivel}</span>
        </div>
        <div class="hr-bar">
          <div class="hr-bar-fill" style="width:${Math.min(percentual, 100)}%"></div>
        </div>
      </div>

      <div class="hr-date">
        <span class="hr-date-dia">${dia}</span>
        <span>${hora}</span>
      </div>

      <button class="hr-toggle" type="button" aria-expanded="false" aria-label="Ver detalhes">
        ${ICONE_CHEVRON}
      </button>
    </div>

    ${previaSkills}

    <div class="hr-detail" hidden>
      <div class="skills-group matching">
        <h4>✅ Em comum (${skillsEmComum.length})</h4>
        <div class="skill-tags">${renderTags(skillsEmComum, 'tag-matching')}</div>
      </div>
      <div class="skills-group missing">
        <h4>❌ Ausentes na vaga (${skillsAusentes.length})</h4>
        <div class="skill-tags">${renderTags(skillsAusentes, 'tag-missing')}</div>
      </div>
      <div class="skills-group extra">
        <h4>➕ Extras no currículo (${skillsExtras.length})</h4>
        <div class="skill-tags">${renderTags(skillsExtras, 'tag-extra')}</div>
      </div>
    </div>`;

  // Clique em qualquer ponto da linha expande; o botão garante acesso via teclado
  const botaoExpandir = linha.querySelector('.hr-toggle');
  const detalhe = linha.querySelector('.hr-detail');

  linha.querySelector('.hr-main').addEventListener('click', () => {
    const estaAberta = linha.classList.toggle('open');
    detalhe.hidden = !estaAberta;
    botaoExpandir.setAttribute('aria-expanded', String(estaAberta));
  });

  return linha;
}