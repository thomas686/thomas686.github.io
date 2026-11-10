// TS-26 pocket portfolio: power, boot, menus, controls, tilt and sound.
(() => {
  const dev = document.getElementById('device'), stage = document.getElementById('stage');
  const scr = document.getElementById('screen'), hint = document.getElementById('play-hint');
  const section = document.getElementById('play');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SHORT = { ai: 'AI', alphacrm: 'CRM', email: 'EMAIL', side: 'SIDE' };
  const MENU = ['ABOUT ME', 'PROJECTS', 'EXPERIENCE', 'CONTACT', 'NORMAL VIEW', 'SOUND'];
  const CONTACT = ['COPY EMAIL', 'OPEN LINKEDIN'];
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
  function fit() { stage.style.setProperty('--s', Math.max(0.55, Math.min(1, (innerWidth - 32) / 420, (innerHeight - 180) / 700)).toFixed(3)); }
  fit(); addEventListener('resize', fit);

  // Tilt with the pointer
  addEventListener('pointermove', e => {
    if (!inView || still || dev.classList.contains('zoom')) return;
    stage.style.setProperty('--ry', `${((e.clientX / innerWidth) - 0.5) * 34}deg`);
    stage.style.setProperty('--rx', `${(0.5 - e.clientY / innerHeight) * 20 + 10}deg`);
  });
  new IntersectionObserver(([en]) => {
    inView = en.intersectionRatio > 0.5;
    if (typeof stopMusic === 'function') { if (!inView) stopMusic(); else if (on) startMusic(); }
  }, { threshold: [0, 0.5, 1] }).observe(section);
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

  // Background chiptune: an original 4-bar loop (lead, bass, hi-hat), scheduled ahead in time
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);
  const LEAD = [69, 0, 72, 0, 76, 74, 72, 0, 69, 0, 67, 69, 72, 0, 0, 0, 74, 0, 76, 0, 79, 76, 74, 0, 72, 0, 74, 72, 69, 0, 0, 0,
    69, 0, 72, 0, 76, 74, 72, 0, 77, 0, 76, 74, 72, 0, 74, 0, 76, 0, 74, 72, 69, 0, 67, 0, 69, 0, 0, 0, 0, 0, 0, 0];
  const ROOTS = [45, 41, 48, 43];
  const STEP = 60 / 132 / 4;
  let music = null;
  function voice(t, f, d, type, vol, dest) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.connect(g).connect(dest); o.start(t); o.stop(t + d + 0.02);
  }
  function hat(t, dest) {
    const n = ac.createBufferSource(), b = ac.createBuffer(1, ac.sampleRate * 0.04, ac.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    const f = ac.createBiquadFilter(), g = ac.createGain();
    f.type = 'highpass'; f.frequency.value = 6000; g.gain.value = 0.25;
    n.buffer = b; n.connect(f).connect(g).connect(dest); n.start(t);
  }
  function startMusic(delay = 0) {
    if (!sound || music) return;
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      ac.resume();
      const out = ac.createGain(); out.gain.value = 0; out.connect(ac.destination);
      out.gain.setValueAtTime(0, ac.currentTime + delay); out.gain.linearRampToValueAtTime(0.09, ac.currentTime + delay + 1.5);
      let step = 0, next = ac.currentTime + delay;
      const timer = setInterval(() => {
        while (next < ac.currentTime + 0.15) {
          const s = step % 64, lead = LEAD[s];
          if (lead) voice(next, hz(lead), STEP * 1.8, 'square', 0.32, out);
          if (s % 2 === 0) voice(next, hz(ROOTS[Math.floor(s / 16)] + (s % 8 === 4 ? 12 : 0)), STEP * 1.6, 'triangle', 0.6, out);
          if (s % 4 === 2) hat(next, out);
          next += STEP; step++;
        }
      }, 25);
      music = { out, timer };
    } catch { music = null; }
  }
  function stopMusic() {
    if (!music) return;
    const m = music; music = null;
    try { m.out.gain.cancelScheduledValues(ac.currentTime); m.out.gain.setValueAtTime(m.out.gain.value, ac.currentTime); m.out.gain.linearRampToValueAtTime(0, ac.currentTime + 0.4); } catch { }
    setTimeout(() => { clearInterval(m.timer); m.out.disconnect(); }, 450);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopMusic(); else if (on && inView) startMusic(); });

  const page = (title, body, foot) => `<div class="scr"><h4>${title}</h4>${body}<div class="foot">${foot}</div></div>`;

  function render() {
    if (!on) { scr.innerHTML = `<div class="off-msg">FLIP THE SWITCH<br><br>&#9650;</div>`; return; }
    if (view === 'boot') {
      scr.innerHTML = `<div class="flash"></div><div class="boot"><div class="big">TS-26</div><div class="who">THOMAS SOKOLOWSKI</div></div>`;
      return;
    }
    if (view === 'menu') {
      scr.innerHTML = page('MAIN MENU', `<ul class="menu">${MENU.map((m, i) => `<li data-i="${i}" class="${i === idx ? 'sel' : ''}">${m === 'SOUND' ? `SOUND: ${sound ? 'ON' : 'OFF'}` : m}</li>`).join('')}</ul>`,
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
        `<li data-i="${top + i}" class="${top + i === idx ? 'sel' : ''}"><span class="cat">${SHORT[p.category]}</span> ${esc(p.title.toUpperCase())}</li>`).join('')}</ul>`,
        `<span>A OPEN</span><span>B BACK</span>`);
      return;
    }
    if (view === 'project') {
      const p = projects[idx];
      scr.innerHTML = `<div class="shot">${p.image ? `<img src="${p.image}" alt="">` : ''}<div class="cap"><b>${esc(p.title.toUpperCase())}</b>
        <span>TAP OR A: FULL STORY &middot; &#9664;&#9654; NEXT</span></div></div>`;
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
      scr.innerHTML = page('CONTACT', `<div class="small">EMAIL</div><div class="small" style="color:#fff;margin-bottom:10px">thomas.s686@gmail.com</div>
        <div class="small">LINKEDIN</div><div class="small" style="color:#fff;margin-bottom:14px">in/ts0kolowski</div>
        <ul class="menu">${CONTACT.map((m, i) => `<li data-i="${i}" class="${i === idx ? 'sel' : ''}">${m}</li>`).join('')}</ul>
        <div class="small" style="color:#ffd37a;margin-top:6px" id="c-msg"></div>`,
        `<span>A DO IT</span><span>B BACK</span>`);
    }
  }

  function setPower(v) {
    if (v === on) return;
    on = v; dev.classList.toggle('on', on); clearTimeout(bootTimer);
    if (on) {
      view = 'boot'; idx = 0; render(); chime(); startMusic(0.6);
      if (!still) {
        dev.classList.remove('unzoom'); dev.classList.add('zoom');
        stage.style.setProperty('--rx', '0deg'); stage.style.setProperty('--ry', '0deg');
        setTimeout(() => { dev.classList.remove('zoom'); dev.classList.add('unzoom'); stage.style.setProperty('--rx', '8deg'); stage.style.setProperty('--ry', '-12deg'); }, 2300);
      }
      hint.innerHTML = matchMedia('(pointer: coarse)').matches ? 'Tap the d-pad, A to open, B to go back'
        : 'Use the d-pad and A/B, or <kbd>&#8593;</kbd><kbd>&#8595;</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd>';
      bootTimer = setTimeout(() => { view = 'menu'; render(); }, still ? 300 : 1900);
    } else {
      stopMusic(); dev.classList.remove('zoom');
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
    const n = { menu: MENU.length, projects: projects.length, contact: CONTACT.length }[view];
    if ((k === 'up' || k === 'down') && n) { idx = (idx + (k === 'up' ? -1 : 1) + n) % n; beep(880, 0.04); render(); return; }
    if (view === 'exp' && ['left', 'right', 'up', 'down'].includes(k)) {
      const len = exp.work.length + exp.education.length;
      sub = (sub + (k === 'left' || k === 'up' ? -1 : 1) + len) % len; beep(880, 0.04); render(); return;
    }
    if (view === 'project' && (k === 'left' || k === 'right')) { idx = (idx + (k === 'left' ? -1 : 1) + projects.length) % projects.length; beep(880, 0.04); render(); return; }
    if (k === 'b') {
      beep(330, 0.06);
      if (view === 'project') view = 'projects';
      else if (view !== 'menu') { idx = Math.max(0, ['about', 'projects', 'exp', 'contact'].indexOf(view)); view = 'menu'; }
      render(); return;
    }
    if (k === 'a') {
      beep(990, 0.06);
      if (view === 'menu') {
        const choice = MENU[idx];
        if (choice === 'SOUND') { sound = !sound; if (sound) { beep(1200, 0.05); startMusic(); } else stopMusic(); render(); return; }
        if (choice === 'NORMAL VIEW') { document.getElementById('about').scrollIntoView({ behavior: still ? 'auto' : 'smooth' }); return; }
        view = { 'ABOUT ME': 'about', PROJECTS: 'projects', EXPERIENCE: 'exp', CONTACT: 'contact' }[choice];
        idx = 0; sub = 0;
        if ((view === 'projects' && !projects.length) || (view === 'exp' && !exp)) { view = 'menu'; }
      } else if (view === 'projects') view = 'project';
      else if (view === 'project') {
        window.openProject && window.openProject(projects[idx].id); return;
      } else if (view === 'contact') {
        if (idx === 1) { window.open('https://www.linkedin.com/in/ts0kolowski', '_blank', 'noopener'); return; }
        navigator.clipboard?.writeText('thomas.s686@gmail.com').then(() => { const m = document.getElementById('c-msg'); if (m) m.textContent = 'COPIED!'; }).catch(() => {});
        return;
      }
      render();
    }
  }

  dev.querySelectorAll('[data-k]').forEach(b => b.addEventListener('click', e => { e.preventDefault(); press(b.dataset.k); }));
  document.getElementById('power').addEventListener('click', () => setPower(!on));
  // Tap the screen: open the tapped item, or the full story of the project shown
  scr.addEventListener('click', e => {
    if (!on) { setPower(true); return; }
    const li = e.target.closest('li[data-i]');
    if (li) { idx = Number(li.dataset.i); press('a'); return; }
    if (view === 'project') press('a');
  });
  addEventListener('keydown', e => {
    if (!inView || e.target.closest('input,textarea,select,dialog') || e.metaKey || e.ctrlKey || e.altKey) return;
    if (document.querySelector('dialog[open]')) return;
    const map = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'a', z: 'a', Z: 'a', x: 'b', X: 'b', Backspace: 'b', Escape: 'b' };
    const k = map[e.key];
    if (!on) { if (k || e.key.length === 1) { e.preventDefault(); setPower(true); } return; }
    if (k) { e.preventDefault(); press(k); }
  });

  Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
    .then(([p, e]) => { projects = p; exp = e; }).catch(() => {});
  render();
})();
