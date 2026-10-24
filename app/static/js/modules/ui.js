// ui.js — utilitários de interface
export const qs    = (s, ctx = document) => ctx.querySelector(s);
export const qsa   = (s, ctx = document) => [...ctx.querySelectorAll(s)];
export const show  = el => el && el.classList.remove('hidden');
export const hide  = el => el && el.classList.add('hidden');
export const toggle = (el, c) => c ? show(el) : hide(el);

export function showToast(msg, type = 'info') {
  const t = qs('#toast');
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  show(t);
  setTimeout(() => hide(t), 3800);
}

export function formatarTempo(segundos) {
  if (segundos < 60)   return `${Math.round(segundos)}s`;
  if (segundos < 3600) return `${Math.round(segundos / 60)} min`;
  return `${(segundos / 3600).toFixed(1)} h`;
}
