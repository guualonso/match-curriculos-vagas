// comparativo.js — aba Comparativo TF-IDF vs SBERT (interativo, com reordenação animada)
import { qs, show, hide, showToast } from './ui.js';
import { compareMethods } from './api.js';
import { setupUploadSimples } from './upload.js';

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
    montar(data.tfidf, data.sbert, topN);
    showToast('Comparativo gerado. Clique em TF-IDF / SBERT para ver a reordenação.', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; text.textContent = 'Comparar TF-IDF vs SBERT'; hide(spin);
  }
}

// ── Montagem ────────────────────────────────────────────────
function montar(tfidf, sbert, topN) {
  // ranks globais (as listas já vêm ordenadas por cada método)
  const rankT = Object.fromEntries(tfidf.map((r, i) => [String(r.job_id), i + 1]));
  const rankS = Object.fromEntries(sbert.map((r, i) => [String(r.job_id), i + 1]));
  const mapT  = Object.fromEntries(tfidf.map(r => [String(r.job_id), r]));
  const mapS  = Object.fromEntries(sbert.map(r => [String(r.job_id), r]));
  const totalVagas = tfidf.length;

  // exibe só a UNIÃO do top-N de cada método
  const ids = [...new Set([...tfidf, ...sbert].map(r => String(r.job_id)))]
    .filter(id => rankT[id] <= topN || rankS[id] <= topN);

  const list = qs('#comparativo-list');
  list.innerHTML = '';
  const linhas = ids.map(id => {
    const t = mapT[id], s = mapS[id];
    const linha = {
      id, titulo: t.job_title || '—',
      pctT: t.similarity_percent, pctS: s.similarity_percent,
      rankT: rankT[id], rankS: rankS[id],
      nivelT: (t.compatibility_level || '').toLowerCase(),
      nivelS: (s.compatibility_level || '').toLowerCase(),
      skills: (t.matching_skills || []).slice(0, 5),
    };
    linha.el = criarCard(linha);
    return linha;
  });

  estado = { linhas, ordem: null, total: totalVagas };
  aplicarOrdem('tfidf', false);   // começa no TF-IDF, sem animar
  renderBanner();
  renderStats(tfidf, sbert, rankT, rankS, totalVagas);
  qs('#cmp-subtitle').textContent =
    `Exibindo ${linhas.length} vagas (top ${topN} de cada método) de ${totalVagas} avaliadas.`;
  show(qs('#comparativo-section'));
  show(qs('#comparativo-stats'));
  qs('#comparativo-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function criarCard(l) {
  const el = document.createElement('div');
  el.className = 'cmp-card';
  el.dataset.id = l.id;
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
      <div class="cmp-move">Posição: TF-IDF <strong>#${l.rankT}</strong> → SBERT <strong>#${l.rankS}</strong></div>
      <div class="skill-tags cmp-skills">
        ${l.skills.map(s => `<span class="tag tag-matching">${s}</span>`).join('')}
      </div>
    </div>`;
  return el;
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
function renderBanner() {
  const topo = estado.linhas;
  const concordamNivel = topo.filter(l => l.nivelT === l.nivelS).length;
  const banner = qs('#comparativo-banner');
  banner.innerHTML = `
    <div class="cmp-veredito">
      <strong>Como ler</strong>
      <p>Cada cartão mostra o score dos <em>dois</em> métodos e sua posição em cada ranking.
         Clique em <strong>TF-IDF</strong> ou <strong>SBERT</strong> acima para reordenar a lista
         com animação: os cartões que <span style="color:var(--secondary)">sobem</span> ficaram melhor
         ranqueados pelo SBERT; os que <span style="color:var(--danger)">descem</span>, pior.
         Entre as vagas exibidas, os dois métodos deram o mesmo nível de compatibilidade em
         <strong>${concordamNivel} de ${topo.length}</strong>.</p>
    </div>`;
}

function renderStats(tfidf, sbert, rankT, rankS, total) {
  const ids = Object.keys(rankT);
  const st = ids.map(id => (tfidf.find(r => String(r.job_id) === id) || {}).similarity_score || 0);
  const ss = ids.map(id => (sbert.find(r => String(r.job_id) === id) || {}).similarity_score || 0);
  const n = ids.length;
  if (n < 2) { hide(qs('#comparativo-stats')); return; }

  const mt = st.reduce((a, b) => a + b, 0) / n, ms = ss.reduce((a, b) => a + b, 0) / n;
  const num  = st.reduce((a, t, i) => a + (t - mt) * (ss[i] - ms), 0);
  const denT = Math.sqrt(st.reduce((a, t) => a + (t - mt) ** 2, 0));
  const denS = Math.sqrt(ss.reduce((a, s) => a + (s - ms) ** 2, 0));
  const corr = denT && denS ? num / (denT * denS) : 0;
  const maior = Math.max(...ids.map(id => Math.abs(
    ((tfidf.find(r => String(r.job_id) === id) || {}).similarity_score || 0) -
    ((sbert.find(r => String(r.job_id) === id) || {}).similarity_score || 0)))) * 100;
  const top3T = new Set(ids.filter(id => rankT[id] <= 3));
  const top3S = new Set(ids.filter(id => rankS[id] <= 3));
  const conc = [...top3T].filter(id => top3S.has(id)).length;

  qs('#stat-correlacao').textContent   = corr.toFixed(2);
  qs('#stat-maior-diff').textContent   = `${maior.toFixed(1)}%`;
  qs('#stat-concordancia').textContent = `${conc}/3`;
}
