import { qs, showToast } from './ui.js';
import { apiFetch, fetchHistory } from './api.js';
import { renderSeloMetodos } from './resultados.js';

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
}

export function abrirHistoricoDoCurriculo(idCurriculo) {
  qs('#history-resume-id').value = idCurriculo;
  qs('.nav-btn[data-tab="history"]').click();
  handleLoadHistory();
}

export async function carregarUltimosHistoricos() {
  if (qs('#history-resume-id').value.trim()) return;
  const container = qs('#history-list');
  try {
    const pares = await apiFetch('/history/recent?limit=10');
    if (pares?.length) {
      renderHistorico(pares, container, 'Últimas análises');
    } else {
      container.innerHTML = '<p class="empty-state">Nenhuma análise registrada ainda.</p>';
    }
  } catch (erro) {
    container.innerHTML = `<p class="empty-state">${erro.message}</p>`;
  }
}

async function handleLoadHistory() {
  const idCurriculo = qs('#history-resume-id').value.trim();
  if (!idCurriculo) { showToast('Informe o ID do currículo.', 'error'); return; }

  const container = qs('#history-list');
  container.innerHTML = '<p class="empty-state">Buscando…</p>';

  try {
    const pares = await fetchHistory(idCurriculo);
    if (!pares.length) {
      container.innerHTML = '<p class="empty-state">Nenhum histórico encontrado.</p>';
      return;
    }
    renderHistorico(pares, container, `Currículo #${idCurriculo}`);
  } catch (erro) {
    container.innerHTML = `<p class="empty-state">${erro.message}</p>`;
  }
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

function renderHistorico(pares, container, titulo) {
  container.innerHTML = '';

  const cabecalho = document.createElement('div');
  cabecalho.className = 'history-list-header';
  cabecalho.innerHTML = `
    <h2>${titulo}</h2>
    <span>${pares.length} ${pares.length === 1 ? 'par analisado' : 'pares analisados'}</span>`;
  container.appendChild(cabecalho);

  pares.forEach(par => container.appendChild(criarLinha(par)));
}

function blocoMetodo(registro, metodo) {
  const rotulo = metodo === 'tfidf' ? 'TF-IDF' : 'SBERT';
  if (!registro) {
    return `<div class="hr-metodo"><div class="hr-score-top"><span class="metodo-tag ${metodo}">${rotulo}</span><span class="hr-nivel">—</span></div></div>`;
  }
  const nivel = registro.compatibility_level || '—';
  const percentual = Number(registro.similarity_percent) || 0;
  return `
    <div class="hr-metodo nivel-${classeDoNivel(nivel)}" title="${rotulo}: ${percentual.toFixed(1)}%">
      <div class="hr-score-top">
        <span class="metodo-tag ${metodo}">${rotulo}</span>
        <span class="hr-score">${percentual.toFixed(1)}%</span>
        <span class="hr-nivel">${nivel}</span>
      </div>
      <div class="hr-bar"><div class="hr-bar-fill" style="width:${Math.min(percentual, 100)}%"></div></div>
    </div>`;
}

const NIVEL_DA_LINHA = ['baixo', 'medio', 'alto'];

function criarLinha(par) {
  const registro = par.tfidf || par.sbert;
  const { dia, hora } = formatarData(par.created_at);

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
  linha.className = `history-row nivel-${NIVEL_DA_LINHA[par.metodos.length]}`;
  linha.innerHTML = `
    <div class="hr-main">
      <div class="hr-ids">
        <span class="hr-id">
          <span class="hr-id-label">Currículo</span>
          <strong>#${par.resume_id}</strong>
        </span>
        ${ICONE_SETA}
        <span class="hr-id">
          <span class="hr-id-label">Vaga</span>
          <strong>#${par.job_id}</strong>
        </span>
        ${renderSeloMetodos(par.metodos)}
      </div>

      <div class="hr-score-block">
        ${blocoMetodo(par.tfidf, 'tfidf')}
        ${blocoMetodo(par.sbert, 'sbert')}
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

  const botaoExpandir = linha.querySelector('.hr-toggle');
  const detalhe = linha.querySelector('.hr-detail');

  linha.querySelector('.hr-main').addEventListener('click', () => {
    const estaAberta = linha.classList.toggle('open');
    detalhe.hidden = !estaAberta;
    botaoExpandir.setAttribute('aria-expanded', String(estaAberta));
  });

  return linha;
}