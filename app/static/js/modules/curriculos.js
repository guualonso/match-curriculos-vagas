import { qs, show, hide, showToast } from './ui.js';
import { fetchResumes, uploadResume, deleteResumeApi } from './api.js';
import { abrirHistoricoDoCurriculo } from './historico.js';

let curriculos = [];

function formatarData(dataTexto) {
  const data = new Date(dataTexto);
  return Number.isNaN(data.getTime()) ? '—' : data.toLocaleDateString('pt-BR');
}

function atualizarContador() {
  const total = curriculos.length;
  qs('#total-curriculos').innerHTML =
    `<strong>${total} currículo${total !== 1 ? 's' : ''} cadastrado${total !== 1 ? 's' : ''}</strong>`;
}

function renderLista() {
  const container = qs('#resumes-list');
  const termo = qs('#filtro-curriculos').value.trim().toLowerCase();
  const visiveis = curriculos.filter(curriculo =>
    `${curriculo.filename} ${curriculo.id}`.toLowerCase().includes(termo));

  if (!visiveis.length) {
    container.innerHTML = `<p class="empty-state">${curriculos.length ? 'Nenhum currículo encontrado.' : 'Nenhum currículo cadastrado.'}</p>`;
    return;
  }

  container.innerHTML = visiveis.map(curriculo => {
    const skills = Object.values(curriculo.extracted_skills || {}).flat();
    return `
      <div class="job-item">
        <div class="job-item-info">
          <h4>${curriculo.filename}</h4>
          <div class="job-meta">ID #${curriculo.id} · cadastrado em ${formatarData(curriculo.created_at)} · ${skills.length} habilidades</div>
          <div class="skill-tags" style="margin-top:6px">
            ${skills.slice(0, 8).map(skill => `<span class="tag tag-extra">${skill}</span>`).join('')}
            ${!skills.length ? '<span class="tag-empty">Skills não detectadas</span>' : ''}
          </div>
        </div>
        <div class="acoes-item">
          <button class="btn-icon btn-historico-curriculo" data-id="${curriculo.id}" title="Ver histórico de análises">🕘</button>
          <button class="btn-icon btn-delete-curriculo" data-id="${curriculo.id}" title="Remover">🗑️</button>
        </div>
      </div>`;
  }).join('');

  container.querySelectorAll('.btn-historico-curriculo').forEach(botao =>
    botao.addEventListener('click', () => abrirHistoricoDoCurriculo(botao.dataset.id)));
  container.querySelectorAll('.btn-delete-curriculo').forEach(botao =>
    botao.addEventListener('click', () => removerCurriculo(Number(botao.dataset.id))));
}

export async function carregarCurriculos() {
  try {
    curriculos = await fetchResumes();
    atualizarContador();
    renderLista();
  } catch (erro) {
    qs('#resumes-list').innerHTML = `<p class="empty-state">${erro.message}</p>`;
  }
}

async function removerCurriculo(id) {
  if (!confirm('Remover este currículo? O histórico de análises dele também será apagado.')) return;
  try {
    await deleteResumeApi(id);
    curriculos = curriculos.filter(curriculo => curriculo.id !== id);
    atualizarContador();
    renderLista();
    showToast('Currículo removido.', 'success');
  } catch (erro) {
    showToast(erro.message, 'error');
  }
}

async function cadastrarCurriculo() {
  const arquivo = qs('#resume-file').files[0];
  const mensagem = qs('#resume-msg');
  if (!arquivo) {
    mensagem.textContent = 'Escolha um arquivo PDF, DOCX ou TXT.';
    mensagem.className = 'msg msg-error';
    show(mensagem);
    return;
  }

  const botao = qs('#btn-save-resume');
  botao.disabled = true;
  hide(mensagem);
  try {
    const idsAntes = new Set(curriculos.map(curriculo => curriculo.id));
    const curriculo = await uploadResume(arquivo);
    mensagem.textContent = idsAntes.has(curriculo.id)
      ? `Este currículo já estava cadastrado (ID #${curriculo.id}).`
      : `✅ Currículo cadastrado com o ID #${curriculo.id}.`;
    mensagem.className = 'msg msg-success';
    show(mensagem);
    qs('#resume-file').value = '';
    qs('#resume-file-name').textContent = 'PDF, DOCX ou TXT. As habilidades são extraídas no cadastro.';
    carregarCurriculos();
  } catch (erro) {
    mensagem.textContent = erro.message;
    mensagem.className = 'msg msg-error';
    show(mensagem);
  } finally {
    botao.disabled = false;
  }
}

export function setupCurriculos() {
  qs('#btn-save-resume')?.addEventListener('click', cadastrarCurriculo);
  qs('#btn-refresh-resumes')?.addEventListener('click', carregarCurriculos);
  qs('#filtro-curriculos')?.addEventListener('input', renderLista);
  qs('#resume-file')?.addEventListener('change', evento => {
    const arquivo = evento.target.files[0];
    if (arquivo) qs('#resume-file-name').textContent = `Selecionado: ${arquivo.name}`;
  });
}
