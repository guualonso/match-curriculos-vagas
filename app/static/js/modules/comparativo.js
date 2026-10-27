// comparativo.js — aba Comparativo TF-IDF vs SBERT (interativo, com reordenação animada)
import { qs, show, hide, showToast } from './ui.js';
import { compareMethods } from './api.js';
import { setupUploadSimples } from './upload.js';
import { desenharInclinacao } from './graficos.js';

let estado = null;   // { linhas:[{id,el,titulo,pctT,pctS,rankT,rankS,nivelT,nivelS,skills}], ordem:'tfidf'|'sbert', total }

export function setupComparativo() {
  const getArquivo = setupUploadSimples(
    'drop-zone-cmp', 'file-input-cmp',
    'file-icon-cmp', 'file-name-cmp', 'remove-file-cmp',
    f => { qs('#btn-comparar').disabled = !f; }
  );
  qs('#btn-comparar')?.addEventListener('click', () => handleComparar(getArquivo));
  qs('#btn-ord-tfidf')?.addEventListener('click', () => reordenar('tfidf'));
  qs('#btn-ord-sbert')?.addEventListener('click', () => reordenar('sbert'));
}

async function handleComparar(getArquivo) {
  const arquivo = getArquivo();
  if (!arquivo) return;
  const btn = qs('#btn-comparar'), text = qs('#btn-comparar-text'), spin = qs('#btn-comparar-spinner');
  btn.disabled = true; text.textContent = 'Comparando…'; show(spin);
  try {
    const topN = parseInt(qs('#top-n-cmp').value) || 10;
    const data = await compareMethods(arquivo, topN);
    if (!data.tfidf?.length) { showToast('Nenhuma vaga cadastrada para comparar.', 'error'); return; }
    if (!Array.isArray(data.pontos)) {
      showToast('O servidor respondeu sem as posições das vagas: ele está rodando uma versão antiga do código. Reinicie o uvicorn.', 'error');
      return;
    }
    montar(data, topN);
    showToast('Comparativo gerado. Clique em uma vaga para ver as habilidades.', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; text.textContent = 'Comparar TF-IDF vs SBERT'; hide(spin);
  }
}

// ── Montagem ────────────────────────────────────────────────
const nivelDoScore = score => (score >= 0.7 ? 'alto' : score >= 0.4 ? 'médio' : 'baixo');

function montar({ tfidf, sbert, pontos }, topN) {
  // `pontos` traz score e posição de TODAS as vagas nos dois métodos; as listas
  // `tfidf` e `sbert` (top 50 de cada) só fornecem os detalhes, como as habilidades.
  const detalhes = Object.fromEntries([...sbert, ...tfidf].map(r => [String(r.job_id), r]));
  const totalVagas = pontos.length;

  // exibe só a UNIÃO do top-N de cada método
  const exibidos = pontos.filter(p => p.posicao_tfidf <= topN || p.posicao_sbert <= topN);

  const list = qs('#comparativo-list');
  list.innerHTML = '';
  const linhas = exibidos.map(p => {
    const id = String(p.job_id);
    const linha = {
      id, titulo: p.job_title || '—',
      pctT: p.score_tfidf * 100, pctS: p.score_sbert * 100,
      rankT: p.posicao_tfidf, rankS: p.posicao_sbert,
      nivelT: nivelDoScore(p.score_tfidf), nivelS: nivelDoScore(p.score_sbert),
      comuns: detalhes[id]?.matching_skills || [],
      ausentes: detalhes[id]?.missing_skills || [],
      extras: detalhes[id]?.extra_skills || [],
    };
    linha.el = criarCard(linha);
    return linha;
  });

  estado = { linhas, ordem: null, total: totalVagas };
  aplicarOrdem('tfidf', false);   // começa no TF-IDF, sem animar
  renderStats(pontos, linhas);
  desenharInclinacao(qs('#grafico-inclinacao'), linhas, topN, abrirVaga);
  qs('#cmp-total-vagas').textContent = totalVagas;
  qs('#cmp-subtitle').textContent =
    `Exibindo ${linhas.length} vagas (top ${topN} de cada método) de ${totalVagas} avaliadas.`;
  show(qs('#comparativo-section'));
  show(qs('#comparativo-stats'));
  qs('#comparativo-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function tags(lista, classe) {
  return lista.length
    ? lista.map(skill => `<span class="tag ${classe}">${skill}</span>`).join('')
    : '<span class="tag-empty">—</span>';
}

function criarCard(l) {
  const el = document.createElement('div');
  el.className = 'cmp-card';
  el.dataset.id = l.id;
  el.tabIndex = 0;
  el.setAttribute('role', 'button');
  el.setAttribute('aria-expanded', 'false');
  el.innerHTML = `
    <div class="cmp-pos">#${l.rankT}</div>
    <div class="cmp-body">
      <div class="cmp-title">${l.titulo}</div>
      <div class="cmp-bars">
        <div class="cmp-bar-row">
          <span class="cmp-tag tfidf">TF-IDF</span>
          <div class="cmp-track"><div class="cmp-fill tfidf" style="width:${l.pctT}%"></div></div>
          <span class="cmp-val">${l.pctT.toFixed(0)}%</span>
        </div>
        <div class="cmp-bar-row">
          <span class="cmp-tag sbert">SBERT</span>
          <div class="cmp-track"><div class="cmp-fill sbert" style="width:${l.pctS}%"></div></div>
          <span class="cmp-val">${l.pctS.toFixed(0)}%</span>
        </div>
      </div>
      <div class="cmp-move">Posição: TF-IDF <strong>#${l.rankT}</strong> → SBERT <strong>#${l.rankS}</strong>
        <span class="cmp-abrir">ver habilidades ▾</span></div>
      <div class="cmp-detalhe" hidden>
        <div class="skills-group matching">
          <h4>✅ Em comum (${l.comuns.length})</h4>
          <div class="skill-tags">${tags(l.comuns, 'tag-matching')}</div>
        </div>
        <div class="skills-group missing">
          <h4>❌ Pedidas pela vaga e ausentes no currículo (${l.ausentes.length})</h4>
          <div class="skill-tags">${tags(l.ausentes, 'tag-missing')}</div>
        </div>
        <div class="skills-group extra">
          <h4>➕ Extras do currículo (${l.extras.length})</h4>
          <div class="skill-tags">${tags(l.extras, 'tag-extra')}</div>
        </div>
      </div>
    </div>`;
  const alternar = () => {
    const detalhe = el.querySelector('.cmp-detalhe');
    detalhe.hidden = !detalhe.hidden;
    el.classList.toggle('aberto', !detalhe.hidden);
    el.setAttribute('aria-expanded', String(!detalhe.hidden));
  };
  el.addEventListener('click', evento => {
    if (!evento.target.closest('.cmp-detalhe')) alternar();   // clicar nas habilidades não fecha
  });
  el.addEventListener('keydown', evento => { if (evento.key === 'Enter') alternar(); });
  return el;
}

// Chamado ao clicar em uma linha do gráfico: rola até a vaga, abre e destaca.
function abrirVaga(id) {
  const linha = estado?.linhas.find(l => l.id === id);
  if (!linha) return;
  const detalhe = linha.el.querySelector('.cmp-detalhe');
  if (detalhe.hidden) linha.el.click();
  linha.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  linha.el.classList.add('destacado');
  setTimeout(() => linha.el.classList.remove('destacado'), 1600);
}

// ── Reordenação com animação (FLIP) ─────────────────────────
function reordenar(ordem) {
  if (!estado || estado.ordem === ordem) return;
  aplicarOrdem(ordem, true);
}

function aplicarOrdem(ordem, animar) {
  const list = qs('#comparativo-list');
  const key  = ordem === 'tfidf' ? 'rankT' : 'rankS';

  // posições iniciais (First)
  const first = animar
    ? new Map(estado.linhas.map(l => [l.el, l.el.getBoundingClientRect().top]))
    : null;

  // reordena DOM e atualiza o número de posição exibido
  estado.linhas.slice().sort((a, b) => a[key] - b[key]).forEach(l => {
    list.appendChild(l.el);
    l.el.querySelector('.cmp-pos').textContent = '#' + (ordem === 'tfidf' ? l.rankT : l.rankS);
  });

  // botões
  qs('#btn-ord-tfidf').classList.toggle('active', ordem === 'tfidf');
  qs('#btn-ord-sbert').classList.toggle('active', ordem === 'sbert');
  estado.ordem = ordem;

  if (!animar) return;

  // Invert + Play
  estado.linhas.forEach(l => {
    const c = l.el;
    const dy = first.get(c) - c.getBoundingClientRect().top;
    if (!dy) return;
    c.style.transition = 'none';
    c.style.transform = `translateY(${dy}px)`;
    c.classList.add(dy > 0 ? 'subiu' : 'caiu');
    setTimeout(() => c.classList.remove('subiu', 'caiu'), 900);
  });
  requestAnimationFrame(() => {
    estado.linhas.forEach(l => {
      l.el.style.transition = 'transform .6s cubic-bezier(.2,.8,.2,1)';
      l.el.style.transform = '';
    });
  });
}

// ── Resumo e estatísticas ───────────────────────────────────
function leituraSpearman(valor) {
  const intensidade = Math.abs(valor);
  if (intensidade >= 0.7) return valor > 0 ? 'Ordens muito parecidas' : 'Ordens quase invertidas';
  if (intensidade >= 0.4) return valor > 0 ? 'Ordens moderadamente parecidas' : 'Ordens parcialmente invertidas';
  if (intensidade >= 0.2) return 'Ordens pouco parecidas: os métodos priorizam vagas diferentes';
  return 'Sem relação: os métodos ordenam as vagas de formas independentes';
}

function renderStats(pontos, linhas) {
  const n = pontos.length;
  if (n < 2) { hide(qs('#comparativo-stats')); return; }

  // Spearman sobre as posições de todas as vagas (posições únicas, sem empates)
  const somaDiferencas = pontos.reduce((soma, p) => soma + (p.posicao_tfidf - p.posicao_sbert) ** 2, 0);
  const spearman = 1 - (6 * somaDiferencas) / (n * (n * n - 1));

  const maisMudou = linhas.reduce((maior, l) =>
    Math.abs(l.rankT - l.rankS) > Math.abs(maior.rankT - maior.rankS) ? l : maior, linhas[0]);
  const maiorMudanca = Math.abs(maisMudou.rankT - maisMudou.rankS);
  const top3Tfidf = new Set(pontos.filter(p => p.posicao_tfidf <= 3).map(p => p.job_id));
  const concordancia = pontos.filter(p => p.posicao_sbert <= 3 && top3Tfidf.has(p.job_id)).length;

  qs('#stat-correlacao').textContent = spearman.toFixed(2).replace('.', ',');
  qs('#stat-correlacao-leitura').textContent = `${leituraSpearman(spearman)} (${n} vagas)`;
  qs('#stat-maior-diff').textContent = `${maiorMudanca} ${maiorMudanca === 1 ? 'posição' : 'posições'}`;
  qs('#stat-maior-diff-leitura').textContent =
    `${maisMudou.titulo}: #${maisMudou.rankT} no TF-IDF → #${maisMudou.rankS} no SBERT`;
  qs('#stat-concordancia').textContent = `${concordancia} de 3`;
  qs('#stat-concordancia-leitura').textContent = [
    'Os métodos discordam totalmente sobre as melhores vagas',
    'Concordam em 1 das 3 melhores vagas',
    'Concordam em 2 das 3 melhores vagas',
    'Concordam nas 3 melhores vagas',
  ][concordancia];
}
