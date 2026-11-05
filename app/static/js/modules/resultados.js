import { renderBreakdown, renderSkillsGrid, renderScoreCircle } from './render.js';

export function renderScoresDuplos(item, tamanho = '') {
  return `
    <div class="scores-duplos">
      <div class="score-metodo">${renderScoreCircle(item.tfidf, tamanho)}<span class="metodo-tag tfidf">TF-IDF</span></div>
      <div class="score-metodo">${renderScoreCircle(item.sbert, tamanho)}<span class="metodo-tag sbert">SBERT</span></div>
    </div>`;
}

export function renderSeloMetodos(metodos = []) {
  if (metodos.length === 2) return '<span class="selo-metodos ambos">✔ Compatível pelos dois métodos</span>';
  if (metodos.includes('tfidf')) return '<span class="selo-metodos tfidf">Compatível só pelo TF-IDF</span>';
  if (metodos.includes('sbert')) return '<span class="selo-metodos sbert">Compatível só pelo SBERT</span>';
  return '<span class="selo-metodos nenhum">Não compatível</span>';
}

export function renderComposicaoTfidf(resultado) {
  return `<div class="composicao-tfidf"><span class="composicao-titulo">Composição do score TF-IDF:</span>${renderBreakdown(resultado)}</div>`;
}

function cartao(item, posicao, titulo) {
  const card = document.createElement('div');
  card.className = 'result-card';
  card.innerHTML = `
    <span class="result-rank">#${posicao}</span>
    <div class="result-header-row">
      ${renderScoresDuplos(item)}
      <div class="result-info">
        <h3>${titulo}</h3>
        ${renderSeloMetodos(item.metodos)}
        ${renderComposicaoTfidf(item.tfidf)}
      </div>
    </div>
    ${renderSkillsGrid(item.tfidf)}`;
  return card;
}

function nota(resultado, metodo) {
  return `<span class="nota-metodo ${metodo}">${metodo === 'tfidf' ? 'TF-IDF' : 'SBERT'}
    <strong>${(resultado.similarity_percent || 0).toFixed(0)}%</strong> · ${resultado.compatibility_level}</span>`;
}

function linhaCompacta(item, posicao, titulo) {
  return `
    <div class="linha-demais">
      <span class="linha-posicao">#${posicao}</span>
      <span class="linha-titulo">${titulo}</span>
      ${nota(item.tfidf, 'tfidf')}
      ${nota(item.sbert, 'sbert')}
      ${renderSeloMetodos(item.metodos)}
    </div>`;
}

export function renderResultadosUnificados(container, itens, topN, tituloDe, nomeItens, mensagemVazia) {
  const top = itens.slice(0, topN).filter(item => item.metodos.length);
  const demais = itens.slice(top.length);

  container.innerHTML = '';
  if (!top.length) container.innerHTML = `<p class="empty-state">${mensagemVazia}</p>`;
  top.forEach((item, indice) => container.appendChild(cartao(item, indice + 1, tituloDe(item))));

  if (demais.length) {
    const detalhes = document.createElement('details');
    detalhes.className = 'demais';
    detalhes.innerHTML = `
      <summary>Ver as demais ${demais.length} ${nomeItens} e suas posições</summary>
      <div class="demais-lista">
        ${demais.map((item, indice) => linhaCompacta(item, top.length + indice + 1, tituloDe(item))).join('')}
      </div>`;
    container.appendChild(detalhes);
  }
}

export function resumoDosResultados(itens) {
  const compativeis = itens.filter(item => item.metodos.length).length;
  const pelosDois = itens.filter(item => item.metodos.length === 2).length;
  return { compativeis, pelosDois };
}
