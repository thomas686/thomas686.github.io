const CATS = { ai: 'AI and automation', alphacrm: 'AlphaCRM', email: 'Email', side: 'Side project' };
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let projects = [];

function renderCards(cat) {
  const list = cat === 'all' ? projects : projects.filter(p => p.category === cat);
  $('cards').innerHTML = list.map(p => `
    <button type="button" class="card c-${p.category}${cat === 'all' && p.featured ? ' wide' : ''}" data-id="${p.id}">
      ${p.image ? `<img class="thumb" src="${p.image}" alt="" loading="lazy" width="1120" height="700">` : ''}
      <span class="tag">${CATS[p.category]}</span>
      <h3>${esc(p.title)}</h3>
      <p>${esc(p.summary)}</p>
      <span class="more">Read the story ${p.demo ? '<span class="live">Live demo</span>' : ''}</span>
    </button>`).join('');
  document.querySelectorAll('.card').forEach(b => b.addEventListener("click", () => openProject(b.dataset.id)));
}

function openProject(id) {
  const p = projects.find(x => x.id === id);
  const d = $('detail');
  d.className = `c-${p.category}`;
  $('d-cat').textContent = `${CATS[p.category]} · ${p.year}`;
  $('d-title').textContent = p.title;
  const img = $('d-img');
  img.hidden = !p.image;
  if (p.image) { img.src = p.image; img.alt = `Screenshot: ${p.title}`; }
  $('d-imgnote').textContent = p.imageKind === 'blurred' ? 'Real screenshot. Client names and logos are blurred.' : '';
  $('d-summary').textContent = p.summary;
  $('d-problem').textContent = p.problem;
  $('d-built').textContent = p.built;
  $('d-result').textContent = p.result;
  $('d-tools').innerHTML = p.tools.map(t => `<li>${esc(t)}</li>`).join('');
  const demo = $('d-demo');
  demo.hidden = !p.demo;
  if (p.demo) demo.href = p.demo;
  d.showModal();
  d.scrollTop = 0;
}

window.openProject = openProject;
window.portfolioData = () => projects;

function renderTimeline(id, items) {
  $(id).innerHTML = items.map(i => `
    <li><div class="t-when">${esc(i.when)} · ${esc(i.place)}</div>
      <div class="t-role">${esc(i.role)}</div>
      <div class="t-org">${esc(i.org)}</div>
      <p class="t-text">${esc(i.text)}</p></li>`).join('');
}

document.querySelectorAll('.filters button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.filters button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  renderCards(b.dataset.cat);
}));
$('d-close').addEventListener('click', () => $('detail').close());
$('detail').addEventListener('click', e => { if (e.target === $('detail')) $('detail').close(); });
$('copy').addEventListener('click', async () => {
  const btn = $('copy');
  try { await navigator.clipboard.writeText($('email').textContent); btn.textContent = 'Copied'; }
  catch { getSelection().selectAllChildren($('email')); btn.textContent = 'Selected, press Ctrl+C'; }
  setTimeout(() => { btn.textContent = 'Copy email'; }, 2500);
});

function tick() {
  const t = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Bangkok', hour: '2-digit', minute: '2-digit' }).format(new Date());
  $('clock').textContent = `${t} local time`;
}
tick();
setInterval(tick, 30000);

Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
  .then(([p, e]) => {
    projects = p;
    renderCards('all');
    renderTimeline('work-list', e.work);
    renderTimeline('edu-list', e.education);
  })
  .catch(() => { $('cards').innerHTML = '<p>The projects did not load. Reload the page to try again.</p>'; });

// "Players visited": a public visit counter (abacus.jasoncameron.dev). Each browser counts once;
// local testing only reads the number. The badge stays hidden if the service does not answer.
(() => {
  const box = document.getElementById('visits'), num = document.getElementById('v-num');
  if (!box || !num) return;
  const API = 'https://abacus.jasoncameron.dev', NS = 'thomas686-portfolio', KEY = 'players';
  const local = /^(localhost|127\.|0\.0\.0\.0)/.test(location.hostname);
  let counted = false;
  try { counted = localStorage.getItem('ts26-counted') === '1'; } catch { /* storage blocked */ }
  const url = `${API}/${counted ? 'get' : 'hit'}/${NS}/${KEY}`;
  (local ? Promise.resolve({ ok: true, json: () => ({ value: 0 }) }) : fetch(url)).then(r => r.ok ? r.json() : r.status === 404 ? { value: 0 } : Promise.reject())
    .then(({ value }) => {
      if (!local && !counted) { try { localStorage.setItem('ts26-counted', '1'); } catch { } }
      box.hidden = false;
      const end = Number(value) || 0, t0 = performance.now(), dur = 1200;
      const step = now => { const k = Math.min(1, (now - t0) / dur), v = Math.round(end * (1 - Math.pow(1 - k, 3)));
        num.textContent = String(v).padStart(6, '0'); if (k < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    })
    .catch(() => { box.hidden = true; });
})();
