// app.js — ponto de entrada principal
import { qs, qsa, show, hide } from './modules/ui.js';
import { state } from './modules/state.js';
import { checkHealth } from './modules/api.js';
import { carregarVagas, loadJobs, setupVagas } from './modules/vagas.js';
import { setupMatch } from './modules/match.js';
import { setupComparativo } from './modules/comparativo.js';
import { setupHistorico } from './modules/historico.js';

// ── Navegação entre abas ────────────────────────────────────
function setupNavegacao() {
  qsa('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      qsa('.nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      qsa('.tab-content').forEach(s => {
        const ativo = s.id === `tab-${tab}`;
        s.classList.toggle('active', ativo);
        ativo ? show(s) : hide(s);
      });
      if (tab === 'jobs') loadJobs();
    });
  });
}

// ── Seletor de método (TF-IDF / SBERT) ─────────────────────
function setupMetodoSelector() {
  qsa('.metodo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.metodoAtivo = btn.dataset.metodo;
      qsa('.metodo-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

// ── Inicialização ───────────────────────────────────────────
async function init() {
  setupNavegacao();
  setupMetodoSelector();
  setupMatch();
  setupVagas();
  setupComparativo();
  setupHistorico();
  checkHealth();
  carregarVagas();
}

init();