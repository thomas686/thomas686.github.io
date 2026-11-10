// TS-26 pocket portfolio: the console is a photoreal render (front and back) with a live screen
// and click zones on top; a light Three.js scene animates behind it.
import * as THREE from 'three';

const section = document.getElementById('play');
const host = document.getElementById('stage3d');
const wrap = document.getElementById('tsc');
const card = document.getElementById('tsc-card');
const cv = document.getElementById('tsc-screen');
const hint = document.getElementById('play-hint');
const srText = document.getElementById('screen-text');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;

// ---------- Background scene (no device; just atmosphere) ----------
let renderer = null, scene, camera, cubes = [], particles, grid;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.prepend(renderer.domElement);
  scene = new THREE.Scene();
  { const c = document.createElement('canvas'); c.width = 4; c.height = 512; const x = c.getContext('2d');
    const g = x.createLinearGradient(0, 0, 0, 512); g.addColorStop(0, '#070d0b'); g.addColorStop(0.55, '#0f211c'); g.addColorStop(1, '#16342c');
    x.fillStyle = g; x.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t; }
  scene.fog = new THREE.Fog(0x142d26, 12, 40);
  camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100); camera.position.set(0, 0.4, 14);
  scene.add(new THREE.HemisphereLight(0xdff2e8, 0x0d1714, 0.8));
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(-4, 6, 6); scene.add(key);
  grid = new THREE.GridHelper(90, 90, 0x3fe0a8, 0x1f6b55); grid.position.y = -4.2; grid.material.transparent = true; grid.material.opacity = 0.5; scene.add(grid);
  const cols = [0x9fd8bb, 0x5fa58c, 0x2f6f5e, 0xffd37a];
  for (let i = 0; i < 26; i++) {
    const sz = 0.25 + Math.random() * 0.6, geo = new THREE.BoxGeometry(sz, sz, sz);
    const m = i % 3 === 0
      ? new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: i % 2 ? 0x7dffb0 : 0xffd37a, transparent: true, opacity: 0.85 }))
      : new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: cols[i % 4], roughness: 0.3, metalness: 0.05 }));
    const side = i % 2 ? 1 : -1;
    m.position.set(side * (4 + Math.random() * 10), -3 + Math.random() * 9, -2 - Math.random() * 14);
    m.rotation.set(Math.random() * 3, Math.random() * 3, 0);
    m.userData = { spin: (Math.random() - 0.5) * 0.6, bob: Math.random() * 6, y: m.position.y };
    scene.add(m); cubes.push(m);
  }
  const PN = 140, pos = new Float32Array(PN * 3);
  for (let i = 0; i < PN; i++) { pos[i * 3] = (Math.random() - 0.5) * 34; pos[i * 3 + 1] = -3 + Math.random() * 12; pos[i * 3 + 2] = -1 - Math.random() * 18; }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  particles = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xbff5d6, size: 0.06, transparent: true, opacity: 0.7 })); scene.add(particles);
  const fitBg = () => { const w = host.clientWidth, h = host.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); };
  new ResizeObserver(fitBg).observe(host); fitBg();
} catch { renderer = null; host.style.background = 'radial-gradient(120% 90% at 50% 20%, #16342c, #070d0b)'; }

// ---------- Screen drawing (logical 640 x 480, drawn at 1.5x) ----------
cv.width = 960; cv.height = 720;
const sx = cv.getContext('2d');
const C = { bg: '#0c1620', mint: '#bff5d6', amber: '#ffd37a', dim: '#6f9a87', white: '#ffffff', sel: 'rgba(125,255,176,.14)' };
const PX = '"Press Start 2P", monospace';
let hits = [];
const txt = (s, x, y, col = C.mint, size = 18) => { sx.fillStyle = col; sx.font = `${size}px ${PX}`; sx.fillText(s, x, y); };
function wrapText(s, x, y, maxW, size, col, lh, maxLines = 99) {
  sx.font = `${size}px ${PX}`; const words = s.split(' '); let line = '', n = 0;
  for (const w of words) {
    const t = line ? line + ' ' + w : w;
    if (sx.measureText(t).width > maxW && line) { txt(line, x, y + n * lh, col, size); line = w; if (++n >= maxLines) return n; } else line = t;
  }
  if (line) txt(line, x, y + n * lh, col, size);
  return n + 1;
}
function scanlines() {
  sx.fillStyle = 'rgba(255,255,255,.03)'; for (let y = 0; y < 480; y += 4) sx.fillRect(0, y, 640, 2);
  const g = sx.createRadialGradient(320, 220, 180, 320, 240, 460); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.5)');
  sx.fillStyle = g; sx.fillRect(0, 0, 640, 480);
}
const imgs = {};
const img = src => { if (!imgs[src]) { imgs[src] = new Image(); imgs[src].onload = () => draw(); imgs[src].src = src; } return imgs[src]; };
function drawContain(im, x, y, w, h) {
  if (!im.complete || !im.naturalWidth) return;
  const r = Math.min(w / im.naturalWidth, h / im.naturalHeight), dw = im.naturalWidth * r, dh = im.naturalHeight * r;
  sx.drawImage(im, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
}
function list(items, sel, y0, lh = 34, size = 17) {
  items.forEach((t, i) => {
    const y = y0 + i * lh;
    if (i === sel) { sx.fillStyle = C.sel; sx.fillRect(24, y - lh + 10, 592, lh); if (blink) txt('▶', 30, y, C.amber, size); }
    txt(t, 62, y, i === sel ? C.white : C.mint, size);
    hits.push({ i, x: 24, y: y - lh + 10, w: 592, h: lh });
  });
}
const foot = (l, r) => { txt(l, 30, 458, C.dim, 12); sx.font = `12px ${PX}`; txt(r, 610 - sx.measureText(r).width, 458, C.dim, 12); };

// ---------- State ----------
const MENU = ['ABOUT ME', 'PROJECTS', 'EXPERIENCE', 'CONTACT', 'NORMAL VIEW', 'TURN OFF'];
const CONTACT = ['COPY EMAIL', 'OPEN LINKEDIN'];
let on = false, view = 'off', idx = 0, sub = 0, sound = true, inView = true, blink = true, msg = '';
let projects = [], exp = null, bootAt = 0, offAt = 0;

function draw() {
  hits = [];
  sx.setTransform(1.5, 0, 0, 1.5, 0, 0);
  sx.fillStyle = C.bg; sx.fillRect(0, 0, 640, 480); sx.textBaseline = 'alphabetic';
  const say = [];
  if (!on) {
    sx.fillStyle = '#050807'; sx.fillRect(0, 0, 640, 480);
    if (offAt && performance.now() - offAt < 350) { const k = 1 - (performance.now() - offAt) / 350; sx.fillStyle = '#e9fff2'; sx.fillRect(320 - 300 * k, 238, 600 * k, 4); }
    else if (blink) { sx.font = `16px ${PX}`; const s = coarse ? 'TAP TO START' : 'PRESS A TO START'; txt(s, 320 - sx.measureText(s).width / 2, 250, '#4f7766', 16); }
    srText.textContent = 'The console is off. Press A, any key, or tap the screen to start.'; return;
  }
  if (view === 'boot') {
    const t = (performance.now() - bootAt) / 1000;
    if (t < 0.25) { sx.fillStyle = `rgba(233,255,242,${1 - t * 4})`; sx.fillRect(0, 0, 640, 480); }
    const y = Math.min(230, 120 + t * 260);
    sx.font = `56px ${PX}`; txt('TS-26', 320 - sx.measureText('TS-26').width / 2, y, C.mint, 56);
    if (t > 0.8) { sx.font = `16px ${PX}`; const n = 'THOMAS SOKOLOWSKI'; txt(n, 320 - sx.measureText(n).width / 2, 300, C.amber, 16); }
    say.push('TS-26. Thomas Sokolowski.');
  } else if (view === 'menu') {
    txt('MAIN MENU', 30, 60, C.amber, 20);
    list(MENU, idx, 118, 38, 17);
    foot('▲▼ MOVE', 'A OPEN'); say.push('Main menu. Selected: ' + MENU[idx]);
  } else if (view === 'about') {
    txt('ABOUT ME', 30, 60, C.amber, 20);
    const ph = img('img/thomas.png');
    if (ph.complete && ph.naturalWidth) {
      const t = document.createElement('canvas'); t.width = t.height = 34; t.getContext('2d').drawImage(ph, 0, 0, 34, 34);
      sx.imageSmoothingEnabled = false; sx.drawImage(t, 30, 82, 102, 102); sx.imageSmoothingEnabled = true;
      sx.strokeStyle = C.amber; sx.lineWidth = 3; sx.strokeRect(30, 82, 102, 102);
    }
    ['THOMAS SOKOLOWSKI', 'SALES + MARKETING', 'WHO BUILDS WITH AI', 'BANGKOK'].forEach((l, i) => txt(l, 156, 106 + i * 24, i ? C.mint : C.white, 13));
    [['SALES', 90], ['BUILD W/ AI', 85], ['EMAIL', 80], ['MARKETING', 78], ['THAI', 55]].forEach(([k, v], i) => {
      const y = 232 + i * 38; txt(k, 30, y, C.mint, 13);
      sx.fillStyle = '#21323f'; sx.fillRect(230, y - 14, 370, 16);
      const g = sx.createLinearGradient(230, 0, 600, 0); g.addColorStop(0, '#7dffb0'); g.addColorStop(1, C.amber);
      sx.fillStyle = g; sx.fillRect(230, y - 14, 370 * v / 100, 16);
    });
    foot('SELF-RATED', 'B BACK'); say.push('About me. Sales and marketing person who builds with AI, Bangkok.');
  } else if (view === 'project') {
    const p = projects[idx];
    if (p.image) drawContain(img(p.image), 0, 0, 640, 400);
    { const tag = `${idx + 1}/${projects.length}`; sx.font = `12px ${PX}`; const w = sx.measureText(tag).width + 20;
      sx.fillStyle = 'rgba(5,10,16,.85)'; sx.fillRect(640 - w - 14, 14, w, 30); txt(tag, 640 - w - 4, 35, C.amber, 12); }
    const g = sx.createLinearGradient(0, 330, 0, 480); g.addColorStop(0, 'rgba(5,10,16,0)'); g.addColorStop(0.45, 'rgba(5,10,16,.94)');
    sx.fillStyle = g; sx.fillRect(0, 330, 640, 150);
    wrapText(p.title.toUpperCase(), 24, 418, 592, 15, C.amber, 24, 2);
    txt('A: FULL STORY  ◀▶ NEXT  B: MENU', 24, 464, C.dim, 11);
    hits.push({ i: -1, x: 0, y: 0, w: 640, h: 480 }); say.push(`${p.title}. ${p.summary} Press A for the full story.`);
  } else if (view === 'exp') {
    const all = [...exp.work, ...exp.education], e = all[sub];
    txt(`EXPERIENCE ${sub + 1}/${all.length}`, 30, 60, C.amber, 20);
    txt(e.when.toUpperCase(), 30, 112, C.amber, 13);
    const n = wrapText(e.role.toUpperCase(), 30, 150, 580, 15, C.white, 26, 2);
    wrapText(`${e.org} · ${e.place}`.toUpperCase(), 30, 150 + n * 26 + 10, 580, 12, C.mint, 22, 2);
    wrapText(e.text, 30, 270, 580, 12, '#9fd8bb', 24, 6);
    foot('◀▶ FLIP', 'B BACK'); say.push(`${e.role}, ${e.org}, ${e.when}. ${e.text}`);
  } else if (view === 'contact') {
    txt('CONTACT', 30, 60, C.amber, 20);
    txt('EMAIL', 30, 112, C.dim, 12); txt('thomas.s686@gmail.com', 30, 142, C.white, 15);
    txt('LINKEDIN', 30, 184, C.dim, 12); txt('in/ts0kolowski', 30, 214, C.white, 15);
    list(CONTACT, idx, 290); if (msg) txt(msg, 62, 380, C.amber, 14);
    foot('A DO IT', 'B BACK'); say.push('Contact. Email thomas.s686@gmail.com. LinkedIn in slash ts0kolowski.');
  }
  if (!sound && view !== 'project') txt('MUTED', 532, 60, C.dim, 12);
  scanlines(); srText.textContent = say.join(' ') + (sound ? '' : ' Sound is muted.');
}
setInterval(() => { blink = !blink; if (view !== 'boot') draw(); }, 500);

// ---------- Sound ----------
let ac, music = null;
const audio = () => (ac = ac || new (window.AudioContext || window.webkitAudioContext)());
function beep(f = 660, d = 0.06, type = 'square', when = 0) {
  if (!sound) return;
  try {
    const a = audio(), o = a.createOscillator(), g = a.createGain();
    o.type = type; o.frequency.value = f; g.gain.setValueAtTime(0.05, a.currentTime + when);
    g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + when + d);
    o.connect(g).connect(a.destination); o.start(a.currentTime + when); o.stop(a.currentTime + when + d + 0.02);
  } catch { /* no audio */ }
}
const chime = () => [523, 659, 784, 1047].forEach((f, i) => beep(f, 0.12, 'square', i * 0.09));
const hz = m => 440 * Math.pow(2, (m - 69) / 12);
const LEAD = [69, 0, 72, 0, 76, 74, 72, 0, 69, 0, 67, 69, 72, 0, 0, 0, 74, 0, 76, 0, 79, 76, 74, 0, 72, 0, 74, 72, 69, 0, 0, 0,
  69, 0, 72, 0, 76, 74, 72, 0, 77, 0, 76, 74, 72, 0, 74, 0, 76, 0, 74, 72, 69, 0, 67, 0, 69, 0, 0, 0, 0, 0, 0, 0];
const ROOTS = [45, 41, 48, 43], STEP = 60 / 132 / 4;
function voice(t, f, d, type, vol, dest) {
  const o = ac.createOscillator(), g = ac.createGain(); o.type = type; o.frequency.setValueAtTime(f, t);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d); o.connect(g).connect(dest); o.start(t); o.stop(t + d + 0.02);
}
function hat(t, dest) {
  const n = ac.createBufferSource(), b = ac.createBuffer(1, ac.sampleRate * 0.04, ac.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
  const f = ac.createBiquadFilter(), g = ac.createGain(); f.type = 'highpass'; f.frequency.value = 6000; g.gain.value = 0.25;
  n.buffer = b; n.connect(f).connect(g).connect(dest); n.start(t);
}
function startMusic(delay = 0) {
  if (!sound || music || !on) return;
  try {
    audio().resume();
    const out = ac.createGain(); out.connect(ac.destination);
    out.gain.setValueAtTime(0, ac.currentTime + delay); out.gain.linearRampToValueAtTime(0.09, ac.currentTime + delay + 1.5);
    let step = 0, next = ac.currentTime + delay;
    const timer = setInterval(() => {
      while (next < ac.currentTime + 0.15) {
        const s = step % 64, l = LEAD[s];
        if (l) voice(next, hz(l), STEP * 1.8, 'square', 0.32, out);
        if (s % 2 === 0) voice(next, hz(ROOTS[Math.floor(s / 16)] + (s % 8 === 4 ? 12 : 0)), STEP * 1.6, 'triangle', 0.6, out);
        if (s % 4 === 2) hat(next, out);
        next += STEP; step++;
      }
    }, 25);
    music = { out, timer };
  } catch { music = null; }
}
function stopMusic() {
  if (!music) return; const m = music; music = null;
  try { m.out.gain.cancelScheduledValues(ac.currentTime); m.out.gain.setValueAtTime(m.out.gain.value, ac.currentTime); m.out.gain.linearRampToValueAtTime(0, ac.currentTime + 0.4); } catch { }
  setTimeout(() => { clearInterval(m.timer); m.out.disconnect(); }, 450);
}
document.addEventListener('visibilitychange', () => { if (document.hidden) stopMusic(); else if (on && inView) startMusic(); });
new IntersectionObserver(([en]) => { inView = en.intersectionRatio > 0.4; if (!inView) stopMusic(); else if (on) startMusic(); }, { threshold: [0, 0.4, 1] }).observe(section);

// ---------- Behaviour ----------
let bootTimer;
function setPower(v) {
  if (v === on) return;
  on = v; clearTimeout(bootTimer); wrap.classList.toggle('on', on);
  if (on) {
    view = 'boot'; idx = 0; bootAt = performance.now(); chime(); startMusic(0.6); toFront();
    hint.innerHTML = coarse ? 'Tap the d-pad, A to open, B to go back, or tap the screen'
      : 'Click the buttons or the screen, or use <kbd>&#8593;</kbd><kbd>&#8595;</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd> <kbd>M</kbd> mute';
    bootTimer = setTimeout(() => { view = 'menu'; draw(); }, still ? 300 : 1900);
  } else {
    stopMusic(); beep(220, 0.15, 'sawtooth'); offAt = performance.now(); view = 'off';
    hint.innerHTML = coarse ? 'Tap the screen or A to start, drag to turn it over' : 'Press A or any key to start, drag to turn it over';
  }
}
function flash(k) {
  const el = wrap.querySelector(`[data-k="${k}"]`) || (['up', 'down', 'left', 'right'].includes(k) && wrap.querySelector(`[data-k="dpad"]`));
  if (!el) return;
  el.classList.remove('down'); void el.offsetWidth; el.classList.add('down');
  if (el.dataset.k === 'dpad') el.dataset.dir = k;
  setTimeout(() => el.classList.remove('down'), 140);
}
function toggleMute() {
  sound = !sound; flash('mute');
  if (sound) { beep(1200, 0.05); startMusic(); } else stopMusic();
  draw();
}
function press(k) {
  if (k === 'mute') { toggleMute(); return; }
  if (showingBack()) { toFront(); return; }
  flash(k);
  if (!on) { if (k === 'a' || k === 'screen') setPower(true); return; }
  if (view === 'boot') return;
  const n = { menu: MENU.length, contact: CONTACT.length }[view];
  if ((k === 'up' || k === 'down') && n) { idx = (idx + (k === 'up' ? -1 : 1) + n) % n; msg = ''; beep(880, 0.04); draw(); return; }
  if (view === 'exp' && ['left', 'right', 'up', 'down'].includes(k)) {
    const len = exp.work.length + exp.education.length; sub = (sub + (k === 'left' || k === 'up' ? -1 : 1) + len) % len; beep(880, 0.04); draw(); return;
  }
  if (view === 'project' && ['left', 'right', 'up', 'down'].includes(k)) { idx = (idx + (k === 'left' || k === 'up' ? -1 : 1) + projects.length) % projects.length; beep(880, 0.04); draw(); return; }
  if (k === 'b') {
    beep(330, 0.06);
    if (view === 'project') { idx = 1; view = 'menu'; }
    else if (view !== 'menu') { idx = Math.max(0, ['about', 'project', 'exp', 'contact'].indexOf(view)); view = 'menu'; }
    draw(); return;
  }
  if (k !== 'a' && k !== 'screen') return;
  beep(990, 0.06);
  if (view === 'menu') {
    const choice = MENU[idx];
    if (choice === 'TURN OFF') { setPower(false); return; }
    if (choice === 'NORMAL VIEW') { document.getElementById('about').scrollIntoView({ behavior: still ? 'auto' : 'smooth' }); return; }
    const next = { 'ABOUT ME': 'about', PROJECTS: 'project', EXPERIENCE: 'exp', CONTACT: 'contact' }[choice];
    if ((next === 'project' && !projects.length) || (next === 'exp' && !exp)) return;
    view = next; idx = 0; sub = 0; msg = '';
  } else if (view === 'project') { window.openProject && window.openProject(projects[idx].id); return; }
  else if (view === 'contact') {
    if (idx === 1) { window.open('https://www.linkedin.com/in/ts0kolowski', '_blank', 'noopener'); return; }
    navigator.clipboard?.writeText('thomas.s686@gmail.com').then(() => { msg = 'COPIED!'; draw(); }).catch(() => { msg = 'SEE THE ADDRESS ABOVE'; draw(); });
    return;
  }
  draw();
}

// ---------- Click zones ----------
wrap.querySelectorAll('[data-k]').forEach(el => el.addEventListener('click', e => {
  e.stopPropagation();
  if (moved) return;
  const k = el.dataset.k;
  if (k === 'dpad') {
    const r = el.getBoundingClientRect(), dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    if (Math.max(Math.abs(dx), Math.abs(dy)) < r.width * 0.08) return;
    press(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up')); return;
  }
  press(k);
}));
cv.addEventListener('click', e => {
  e.stopPropagation();
  if (moved) return;
  if (!on) { setPower(true); return; }
  const r = cv.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * 640, y = (e.clientY - r.top) / r.height * 480;
  const h = hits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
  if (!h) return;
  if (h.i >= 0) idx = h.i;
  press('screen');
});

// ---------- Tilt, flip by dragging ----------
let rx = 0, ry = 0, tx = 0, ty = 0, flip = 0, flipTarget = 0, drag = null, moved = false;
function flipTo(v) { flipTarget = v; }
const showingBack = () => Math.abs(Math.round(flipTarget / 180)) % 2 === 1;
const toFront = () => { flipTarget = Math.round(flipTarget / 360) * 360 + (Math.round(flipTarget / 180) % 2 ? 0 : 0); if (showingBack()) flipTarget += flipTarget > 0 ? -180 : 180; };
addEventListener('pointermove', e => {
  if (drag) {
    const dx = e.clientX - drag.x; if (Math.abs(dx) > 6) moved = true;
    flipTarget = drag.flip + dx * 0.6; return;
  }
  if (!inView || still) return;
  ty = ((e.clientX / innerWidth) - 0.5) * 16; tx = (0.5 - e.clientY / innerHeight) * 10;
  card.style.setProperty('--lx', `${(e.clientX / innerWidth) * 100}%`); card.style.setProperty('--ly', `${(e.clientY / innerHeight) * 100}%`);
});
wrap.addEventListener('pointerdown', e => { drag = { x: e.clientX, flip: flipTarget }; moved = false; });
addEventListener('pointerup', () => {
  if (!drag) return; drag = null;
  flipTarget = Math.round(flipTarget / 180) * 180;
  setTimeout(() => { moved = false; }, 0);
});

addEventListener('keydown', e => {
  if (!inView || e.target.closest('input,textarea,select,dialog,a,button') || e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.querySelector('dialog[open]')) return;
  const k = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'a', z: 'a', Z: 'a', x: 'b', X: 'b', Backspace: 'b', Escape: 'b', m: 'mute', M: 'mute' }[e.key];
  if (k === 'mute') { e.preventDefault(); toggleMute(); return; }
  if (!on) { if (k || e.key.length === 1) { e.preventDefault(); setPower(true); } return; }
  if (k) { e.preventDefault(); press(k); }
});

// ---------- Loop ----------
const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  if (document.hidden || !inView) { clock.getDelta(); return; }
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  flip += (flipTarget - flip) * Math.min(1, dt * 8);
  rx += (tx * (on ? 0.4 : 1) - rx) * Math.min(1, dt * 5); ry += (ty * (on ? 0.4 : 1) - ry) * Math.min(1, dt * 5);
  const float = still ? 0 : Math.sin(t * 1.1) * 6;
  card.style.transform = `translateY(${float}px) rotateX(${rx}deg) rotateY(${ry + flip}deg)`;
  if (renderer) {
    if (!still) {
      for (const c of cubes) { c.rotation.x += c.userData.spin * dt; c.rotation.y += c.userData.spin * 0.7 * dt; c.position.y = c.userData.y + Math.sin(t * 0.6 + c.userData.bob) * 0.3; }
      particles.position.y = (t * 0.25) % 12; if (particles.position.y > 6) particles.position.y -= 12;
      grid.position.z = (t * 0.4) % 1;
      camera.position.x += (ry * 0.05 - camera.position.x) * Math.min(1, dt * 2);
    }
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }
  if ((on && view === 'boot') || (!on && offAt && performance.now() - offAt < 400)) draw();
}

Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
  .then(([p, e]) => { projects = p; exp = e; }).catch(() => {});
document.fonts.load(`16px ${PX}`).finally(() => draw());
draw(); frame();
