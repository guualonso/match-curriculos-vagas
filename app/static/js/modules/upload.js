// upload.js — lógica de drag-and-drop e seleção de arquivos
import { show, hide, showToast } from './ui.js';

const EXTS  = ['pdf', 'docx', 'txt'];
export const ICONS = { pdf: '📕', docx: '📘', txt: '📄' };

export function validarExtensao(arquivo) {
  const ext = arquivo.name.split('.').pop().toLowerCase();
  return EXTS.includes(ext) ? ext : null;
}

/**
 * Configura uma zona de upload simples (um arquivo por vez).
 * Retorna getter para o arquivo atual.
 */
export function setupUploadSimples(dropId, inputId, iconId, nameId, removeId, onFile) {
  const drop   = document.querySelector(`#${dropId}`);
  const input  = document.querySelector(`#${inputId}`);
  const info   = drop?.nextElementSibling;
  const icon   = document.querySelector(`#${iconId}`);
  const name   = document.querySelector(`#${nameId}`);
  const remove = document.querySelector(`#${removeId}`);
  if (!drop || !input) return () => null;

  let arquivo = null;

  function setFile(f) {
    if (!f) return;
    const ext = validarExtensao(f);
    if (!ext) { showToast('Formato não suportado.', 'error'); return; }
    arquivo = f;
    if (icon) icon.textContent = ICONS[ext] || '📄';
    if (name) name.textContent = f.name;
    hide(drop);
    if (info) show(info);
    onFile(f);
  }

  input.addEventListener('change', e => setFile(e.target.files[0]));

  drop.addEventListener('click', e => {
    if (e.target.closest('label')) return;
    input.click();
  });

  remove?.addEventListener('click', () => {
    arquivo = null;
    input.value = '';
    if (info) hide(info);
    show(drop);
    onFile(null);
  });

  ['dragover', 'dragenter'].forEach(ev =>
    drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('drag-over'); }));

  ['dragleave', 'drop'].forEach(ev =>
    drop.addEventListener(ev, e => {
      e.preventDefault();
      drop.classList.remove('drag-over');
      if (ev === 'drop') setFile(e.dataTransfer.files[0]);
    }));

  return () => arquivo;
}
