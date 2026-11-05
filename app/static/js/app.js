import { qs, qsa, show, hide } from './modules/ui.js';
import { checkHealth } from './modules/api.js';
import { carregarVagas, loadJobs, setupVagas } from './modules/vagas.js';
import { setupMatch } from './modules/match.js';
import { carregarOpcoesVagas, setupVagaCurriculos } from './modules/vaga_curriculos.js';
import { carregarUltimosHistoricos, setupHistorico } from './modules/historico.js';
import { carregarCurriculos, setupCurriculos } from './modules/curriculos.js';

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
      if (tab === 'vaga-curriculos') carregarOpcoesVagas();
      if (tab === 'resumes') carregarCurriculos();
      if (tab === 'history') carregarUltimosHistoricos();
    });
  });
}

async function init() {
  setupNavegacao();
  setupMatch();
  setupVagas();
  setupVagaCurriculos();
  setupCurriculos();
  setupHistorico();
  checkHealth();
  carregarVagas();
}

init();