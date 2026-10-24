// render.js — funções de renderização de cards e skills

export function renderBreakdown(r) {
  if (!r.tfidf_score && !r.skills_score) return '';
  const cov  = Math.round((r.skill_coverage || 0) * 100);
  const warn = r.warning
    ? `<div class="breakdown-warn">⚠️ ${r.warning}</div>`
    : '';
  return `
    <div class="breakdown-row">
      <span class="breakdown-item">TF-IDF <strong>${((r.tfidf_score  || 0) * 100).toFixed(0)}%</strong></span>
      <span class="breakdown-item">Skills <strong>${((r.skills_score || 0) * 100).toFixed(0)}%</strong></span>
      <span class="breakdown-item">Cobertura <strong>${cov}%</strong></span>
    </div>${warn}`;
}

export function renderSkillsGrid(r) {
  const ms  = r.matching_skills || [];
  const mis = r.missing_skills  || [];
  const ex  = r.extra_skills    || [];
  return `
    <div class="skills-grid">
      <div class="skills-group matching">
        <h4>✅ Em comum (${ms.length})</h4>
        <div class="skill-tags">
          ${ms.length ? ms.map(s => `<span class="tag tag-matching">${s}</span>`).join('') : '<span class="tag-empty">—</span>'}
        </div>
      </div>
      <div class="skills-group missing">
        <h4>❌ Ausentes (${mis.length})</h4>
        <div class="skill-tags">
          ${mis.length ? mis.map(s => `<span class="tag tag-missing">${s}</span>`).join('') : '<span class="tag-empty">Nenhuma</span>'}
        </div>
      </div>
      <div class="skills-group extra">
        <h4>➕ Extras (${ex.length})</h4>
        <div class="skill-tags">
          ${ex.length ? ex.map(s => `<span class="tag tag-extra">${s}</span>`).join('') : '<span class="tag-empty">—</span>'}
        </div>
      </div>
    </div>`;
}

export function renderSkillsMini(r) {
  const ms = (r.matching_skills || []).slice(0, 4);
  if (!ms.length) return '';
  const extra = (r.matching_skills || []).length - 4;
  return `
    <div class="skill-tags" style="margin-top:6px">
      ${ms.map(s => `<span class="tag tag-matching">${s}</span>`).join('')}
      ${extra > 0 ? `<span class="tag tag-extra">+${extra}</span>` : ''}
    </div>`;
}

export function renderScoreCircle(r, size = '') {
  const level = (r.compatibility_level || 'baixo').toLowerCase();
  const style = size ? `style="width:${size};height:${size}"` : '';
  return `
    <div class="score-circle level-${level}" ${style}>
      <span class="score-pct">${(r.similarity_percent || 0).toFixed(0)}%</span>
      <span class="score-lbl">${r.compatibility_level || '—'}</span>
    </div>`;
}
