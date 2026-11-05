import { qs, show, hide, showToast } from './ui.js';
import { fetchJobOptions, fetchResumesForJob } from './api.js';
import { renderResultadosUnificados, resumoDosResultados } from './resultados.js';

let opcoesVagas = [];
let ultimaBusca = null;

function preencherSelecao(filtro = '') {
  const termo = filtro.trim().toLowerCase();
  const visiveis = opcoesVagas.filter(vaga =>
    `${vaga.title} ${vaga.company || ''}`.toLowerCase().includes(termo));
  qs('#vaga-escolhida').innerHTML = visiveis.length
    ? visiveis.map(vaga =>
        `<option value="${vaga.id}">#${vaga.id} · ${vaga.title}${vaga.company ? ` — ${vaga.company}` : ''}</option>`).join('')
    : '<option value="">Nenhuma vaga encontrada</option>';
}

export async function carregarOpcoesVagas() {
  try {
    opcoesVagas = await fetchJobOptions();
    preencherSelecao(qs('#filtro-vagas').value);
  } catch (erro) {
    showToast(`Erro ao carregar as vagas: ${erro.message}`, 'error');
  }
}

function renderizar() {
  if (!ultimaBusca) return;
  const { job_id, job_title, total_resumes_analyzed, results } = ultimaBusca;
  const { compativeis, pelosDois } = resumoDosResultados(results);
  qs('#vaga-resultados-meta').textContent =
    `${compativeis} currículos compatíveis de ${total_resumes_analyzed} analisados (${pelosDois} pelos dois métodos) · vaga #${job_id} ${job_title}`;
  renderResultadosUnificados(
    qs('#vaga-resultados-list'), results, parseInt(qs('#top-n-vaga').value, 10),
    item => `${item.resume_filename} <span class="id-curriculo">ID #${item.resume_id}</span>`,
    'currículos', 'Nenhum currículo com nível Médio ou Alto para esta vaga.',
  );
}

async function buscarCurriculos() {
  const idVaga = qs('#vaga-escolhida').value;
  if (!idVaga) { showToast('Escolha uma vaga.', 'error'); return; }

  const botao = qs('#btn-buscar-curriculos');
  const texto = qs('#btn-buscar-curriculos-text');
  const spinner = qs('#btn-buscar-curriculos-spinner');
  botao.disabled = true;
  texto.textContent = 'Comparando…';
  show(spinner);

  try {
    ultimaBusca = await fetchResumesForJob(idVaga);
    if (!ultimaBusca.total_resumes_analyzed) {
      showToast('Nenhum currículo cadastrado. Envie currículos na aba Currículo → Vagas.', 'error');
    }
    renderizar();
    const secao = qs('#vaga-resultados-section');
    show(secao);
    secao.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (erro) {
    showToast(erro.message, 'error');
  } finally {
    botao.disabled = false;
    texto.textContent = 'Buscar currículos compatíveis';
    hide(spinner);
  }
}

export function setupVagaCurriculos() {
  qs('#filtro-vagas')?.addEventListener('input', evento => preencherSelecao(evento.target.value));
  qs('#btn-buscar-curriculos')?.addEventListener('click', buscarCurriculos);
  qs('#top-n-vaga')?.addEventListener('change', renderizar);
}
