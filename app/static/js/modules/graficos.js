// graficos.js — gráfico da aba Comparativo, desenhado em SVG (sem biblioteca externa)

const SVG = 'http://www.w3.org/2000/svg';

function elemento(tag, atributos = {}, texto = '') {
  const el = document.createElementNS(SVG, tag);
  Object.entries(atributos).forEach(([nome, valor]) => el.setAttribute(nome, valor));
  if (texto) el.textContent = texto;
  return el;
}

function encurtar(texto, limite) {
  return texto.length > limite ? texto.slice(0, limite - 1) + '…' : texto;
}

function classeMudanca(posicaoTfidf, posicaoSbert) {
  if (posicaoSbert < posicaoTfidf) return 'subiu';   // SBERT colocou a vaga mais acima
  if (posicaoSbert > posicaoTfidf) return 'caiu';
  return 'igual';
}

/**
 * Gráfico de inclinação: à esquerda, as top-N vagas do TF-IDF; à direita, as do SBERT.
 * Cada linha liga a mesma vaga nos dois rankings. Vagas fora do top-N de um lado
 * ficam na linha "fora do top". `aoClicar(id)` é chamado ao clicar em uma linha.
 */
export function desenharInclinacao(container, linhas, topN, aoClicar) {
  const largura = 1000, alturaLinha = 34, topo = 46, base = 20;
  const limite = topN + 1;                       // posição usada para "fora do top-N"
  const altura = topo + (limite - 1) * alturaLinha + base;
  const colunaEsquerda = 360, colunaDireita = largura - 360;
  const y = posicao => topo + (Math.min(posicao, limite) - 1) * alturaLinha;
  const limiteTitulo = 34;

  const svg = elemento('svg', { viewBox: `0 0 ${largura} ${altura}`, class: 'grafico', role: 'img',
    'aria-label': `Mudança de posição das vagas do top ${topN} entre o ranking do TF-IDF e o do SBERT` });

  svg.appendChild(elemento('text', { x: colunaEsquerda, y: 22, class: 'cabecalho tfidf', 'text-anchor': 'middle' }, 'Ranking TF-IDF'));
  svg.appendChild(elemento('text', { x: colunaDireita, y: 22, class: 'cabecalho sbert', 'text-anchor': 'middle' }, 'Ranking SBERT'));
  [colunaEsquerda, colunaDireita].forEach(coluna =>
    svg.appendChild(elemento('line', { x1: coluna, y1: y(1) - 10, x2: coluna, y2: y(limite) + 10, class: 'eixo' })));

  // rótulos: posição e título da vaga que ocupa aquela posição em cada ranking
  const porPosicaoTfidf = new Map(linhas.map(l => [l.rankT, l]));
  const porPosicaoSbert = new Map(linhas.map(l => [l.rankS, l]));
  for (let posicao = 1; posicao <= topN; posicao++) {
    const esquerda = porPosicaoTfidf.get(posicao), direita = porPosicaoSbert.get(posicao);
    svg.appendChild(elemento('text', { x: colunaEsquerda - 14, y: y(posicao) + 5, class: 'rotulo', 'text-anchor': 'end' },
      `${esquerda ? encurtar(esquerda.titulo, limiteTitulo) : ''}  #${posicao}`));
    svg.appendChild(elemento('text', { x: colunaDireita + 14, y: y(posicao) + 5, class: 'rotulo' },
      `#${posicao}  ${direita ? encurtar(direita.titulo, limiteTitulo) : ''}`));
  }
  const foraTfidf = linhas.filter(l => l.rankT > topN).length;
  const foraSbert = linhas.filter(l => l.rankS > topN).length;
  svg.appendChild(elemento('text', { x: colunaEsquerda - 14, y: y(limite) + 5, class: 'rotulo fora', 'text-anchor': 'end' },
    `fora do top ${topN} (${foraTfidf})`));
  svg.appendChild(elemento('text', { x: colunaDireita + 14, y: y(limite) + 5, class: 'rotulo fora' },
    `fora do top ${topN} (${foraSbert})`));

  linhas.forEach(linha => {
    const grupo = elemento('g', { class: `inclinacao ${classeMudanca(linha.rankT, linha.rankS)}`, tabindex: '0' });
    grupo.appendChild(elemento('line', { x1: colunaEsquerda, y1: y(linha.rankT), x2: colunaDireita, y2: y(linha.rankS) }));
    // área de clique invisível, mais larga que a linha visível
    grupo.appendChild(elemento('line', { x1: colunaEsquerda, y1: y(linha.rankT), x2: colunaDireita, y2: y(linha.rankS), class: 'alvo' }));
    grupo.appendChild(elemento('circle', { cx: colunaEsquerda, cy: y(linha.rankT), r: 6, class: 'ponta-tfidf' }));
    grupo.appendChild(elemento('circle', { cx: colunaDireita, cy: y(linha.rankS), r: 6, class: 'ponta-sbert' }));
    grupo.appendChild(elemento('title', {}, `${linha.titulo}\nTF-IDF #${linha.rankT} → SBERT #${linha.rankS}`));
    if (aoClicar) {
      grupo.addEventListener('click', () => aoClicar(linha.id));
      grupo.addEventListener('keydown', evento => { if (evento.key === 'Enter') aoClicar(linha.id); });
    }
    svg.appendChild(grupo);
  });

  container.replaceChildren(svg);
}
