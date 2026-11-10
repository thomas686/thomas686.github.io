// TS-26 pocket portfolio: power, boot, menus, controls, tilt and sound.
(() => {
  const dev = document.getElementById('device'), stage = document.getElementById('stage');
  const scr = document.getElementById('screen'), hint = document.getElementById('play-hint');
  const section = document.getElementById('play');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SHORT = { ai: 'AI', alphacrm: 'CRM', email: 'EMAIL', side: 'SIDE' };
  const MENU = ['ABOUT ME', 'PROJECTS', 'EXPERIENCE', 'CONTACT', 'NORMAL VIEW'];
  let on = false, view = 'off', idx = 0, sub = 0, sound = true, inView = true, projects = [], exp = null, bootTimer;

  // Depth: stack copies of the body shape behind the face
  for (let i = 1; i <= 24; i++) {
    const l = document.createElement('div');
    l.className = 'layer';
    l.style.transform = `translateZ(${-i * 2}px)`;
    l.style.filter = `brightness(${1 - i * 0.01})`;
    dev.prepend(l);
  }

  // Fit to screen width
  function fit() { stage.style.setProperty('--s', Math.min(1, (innerWidth - 32) / 800).toFixed(3)); }
  fit(); addEventListener('resize', fit);

  // Tilt with the pointer
  addEventListener('pointermove', e => {
    if (!inView || still) return;
    stage.style.setProperty('--ry', `${((e.clientX / innerWidth) - 0.5) * 34}deg`);
    stage.style.setProperty('--rx', `${(0.5 - e.clientY / innerHeight) * 20 + 10}deg`);
  });
  new IntersectionObserver(([en]) => { inView = en.intersectionRatio > 0.5; }, { threshold: [0, 0.5, 1] }).observe(section);
  if (!still) dev.classList.add('idle');

  // Sound: tiny square-wave beeps, created on first interaction
  let ac;
  function beep(f = 660, d = 0.06, type = 'square', when = 0) {
    if (!sound) return;
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      const o = ac.createOscillator(), g = ac.createGain();
      o.type = type; o.frequency.value = f;
      g.gain.setValueAtTime(0.05, ac.currentTime + when);
      g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + when + d);
      o.connect(g).connect(ac.destination); o.start(ac.currentTime + when); o.stop(ac.currentTime + when + d + 0.02);
    } catch { /* no audio, fine */ }
  }
  const chime = () => { [523, 659, 784, 1047].forEach((f, i) => beep(f, 0.12, 'square', i * 0.09)); };

  const page = (title, body, foot) => `<div class="scr"><h4>${title}</h4>${body}<div class="foot">${foot}</div></div>`;

  function render() {
    if (!on) { scr.innerHTML = `<div class="off-msg">FLIP THE SWITCH<br><br>&#9650;</div>`; return; }
    if (view === 'boot') {
      scr.innerHTML = `<div class="flash"></div><div class="boot"><div class="big">TS-26</div><div class="who">THOMAS SOKOLOWSKI</div></div>`;
      return;
    }
    if (view === 'menu') {
      scr.innerHTML = page('MAIN MENU', `<ul class="menu">${MENU.map((m, i) => `<li class="${i === idx ? 'sel' : ''}">${m}</li>`).join('')}</ul>`,
        `<span>&#9650;&#9660; MOVE</span><span>A SELECT</span>`);
      return;
    }
    if (view === 'about') {
      const stats = [['SALES', 90], ['BUILD W/ AI', 85], ['EMAIL', 80], ['MARKETING', 78], ['THAI', 55]];
      scr.innerHTML = page('ABOUT ME', `<div class="who-row"><img src="img/thomas.png" alt=""><div>THOMAS SOKOLOWSKI<br>SALES + MARKETING<br>WHO BUILDS WITH AI<br>BANGKOK</div></div>
        <div class="stats">${stats.map(([k, v]) => `<span>${k}</span><i><b style="width:${v}%"></b></i>`).join('')}</div>`,
        `<span>SELF-RATED</span><span>B BACK</span>`);
      return;
    }
    if (view === 'projects') {
      const top = Math.max(0, Math.min(idx - 3, projects.length - 7));
      scr.innerHTML = page(`PROJECTS ${idx + 1}/${projects.length}`, `<ul class="menu">${projects.slice(top, top + 7).map((p, i) =>
        `<li class="${top + i === idx ? 'sel' : ''}"><span class="cat">${SHORT[p.category]}</span> ${esc(p.title.toUpperCase())}</li>`).join('')}</ul>`,
        `<span>A OPEN</span><span>B BACK</span>`);
      return;
    }
    if (view === 'project') {
      const p = projects[idx];
      scr.innerHTML = page(esc(p.title.toUpperCase()), `${p.image ? `<img class="proj-img" src="${p.image}" alt="">` : ''}<div class="small">${esc(p.summary)}</div>`,
        `<span>A FULL STORY${p.demo ? ' / START DEMO' : ''}</span><span>B BACK</span>`);
      return;
    }
    if (view === 'exp') {
      const all = [...exp.work, ...exp.education];
      const e = all[sub];
      scr.innerHTML = page(`EXPERIENCE ${sub + 1}/${all.length}`, `<div class="small" style="color:#ffd37a">${esc(e.when.toUpperCase())}</div>
        <div class="small" style="color:#fff;margin:6px 0">${esc(e.role.toUpperCase())}</div><div class="small">${esc(e.org.toUpperCase())} &middot; ${esc(e.place.toUpperCase())}</div>
        <div class="small" style="margin-top:8px;color:#9fd8bb">${esc(e.text)}</div>`,
        `<span>&#9664;&#9654; FLIP</span><span>B BACK</span>`);
      return;
    }
    if (view === 'contact') {
      scr.innerHTML = page('CONTACT', `<div class="small">EMAIL</div><div class="small" style="color:#fff;margin-bottom:12px">thomas.s686@gmail.com</div>
        <div class="small">LINKEDIN</div><div class="small" style="color:#fff">in/ts0kolowski</div>
        <div class="small" style="margin-top:14px;color:#ffd37a" id="c-msg">A COPY EMAIL<br>START OPEN LINKEDIN</div>`,
        `<span>SELECT SOUND ${sound ? 'ON' : 'OFF'}</span><span>B BACK</span>`);
    }
  }

  function setPower(v) {
    if (v === on) return;
    on = v; dev.classList.toggle('on', on); clearTimeout(bootTimer);
    if (on) {
      view = 'boot'; idx = 0; render(); chime();
      hint.innerHTML = matchMedia('(pointer: coarse)').matches ? 'Tap the d-pad, A to open, B to go back'
        : 'Use the d-pad and A/B, or <kbd>&#8593;</kbd><kbd>&#8595;</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd>';
      bootTimer = setTimeout(() => { view = 'menu'; render(); }, still ? 300 : 1900);
    } else {
      beep(220, 0.15, 'sawtooth'); scr.classList.add('power-off');
      setTimeout(() => { scr.classList.remove('power-off'); view = 'off'; render(); }, 350);
      hint.innerHTML = 'Flip the power switch, or press any key';
    }
  }

  function press(k) {
    const btn = dev.querySelector(`[data-k="${k}"]`);
    if (btn) { btn.classList.add('down'); setTimeout(() => btn.classList.remove('down'), 120); }
    if (!on) { setPower(true); return; }
    if (view === 'boot') return;
    const n = { menu: MENU.length, projects: projects.length }[view];
    if ((k === 'up' || k === 'down') && n) { idx = (idx + (k === 'up' ? -1 : 1) + n) % n; beep(880, 0.04); render(); return; }
    if (view === 'exp' && ['left', 'right', 'up', 'down'].includes(k)) {
      const len = exp.work.length + exp.education.length;
      sub = (sub + (k === 'left' || k === 'up' ? -1 : 1) + len) % len; beep(880, 0.04); render(); return;
    }
    if (view === 'project' && (k === 'left' || k === 'right')) { idx = (idx + (k === 'left' ? -1 : 1) + projects.length) % projects.length; beep(880, 0.04); render(); return; }
    if (k === 'select') { sound = !sound; beep(1200, 0.05); render(); return; }
    if (k === 'b') {
      beep(330, 0.06);
      if (view === 'project') view = 'projects';
      else if (view !== 'menu') { idx = Math.max(0, ['about', 'projects', 'exp', 'contact'].indexOf(view)); view = 'menu'; }
      render(); return;
    }
    if (k === 'a' || k === 'start') {
      beep(990, 0.06);
      if (view === 'menu') {
        const choice = MENU[idx];
        if (choice === 'NORMAL VIEW') { document.getElementById('about').scrollIntoView({ behavior: still ? 'auto' : 'smooth' }); return; }
        view = { 'ABOUT ME': 'about', PROJECTS: 'projects', EXPERIENCE: 'exp', CONTACT: 'contact' }[choice];
        idx = 0; sub = 0;
        if ((view === 'projects' && !projects.length) || (view === 'exp' && !exp)) { view = 'menu'; }
      } else if (view === 'projects') view = 'project';
      else if (view === 'project') {
        const p = projects[idx];
        if (k === 'start' && p.demo) { location.href = p.demo; return; }
        window.openProject && window.openProject(p.id); return;
      } else if (view === 'contact') {
        if (k === 'start') { window.open('https://www.linkedin.com/in/ts0kolowski', '_blank', 'noopener'); return; }
        navigator.clipboard?.writeText('thomas.s686@gmail.com').then(() => { const m = document.getElementById('c-msg'); if (m) m.textContent = 'COPIED!'; }).catch(() => {});
        return;
      }
      render();
    }
  }

  dev.querySelectorAll('[data-k]').forEach(b => b.addEventListener('click', e => { e.preventDefault(); press(b.dataset.k); }));
  document.getElementById('power').addEventListener('click', () => setPower(!on));
  addEventListener('keydown', e => {
    if (!inView || e.target.closest('input,textarea,select,dialog') || e.metaKey || e.ctrlKey || e.altKey) return;
    if (document.querySelector('dialog[open]')) return;
    const map = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'a', z: 'a', Z: 'a', x: 'b', X: 'b', Backspace: 'b', Escape: 'b', ' ': 'start', Shift: 'select' };
    const k = map[e.key];
    if (!on) { if (k || e.key.length === 1) { e.preventDefault(); setPower(true); } return; }
    if (k) { e.preventDefault(); press(k); }
  });

  Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
    .then(([p, e]) => { projects = p; exp = e; }).catch(() => {});
  render();
})();
