// TS-26 pocket portfolio: the photoreal face render mounted on a real 3D body (Three.js),
// with a live screen, clickable controls, drag to spin, and a light background scene.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const section = document.getElementById('play');
const host = document.getElementById('stage3d');
const hint = document.getElementById('play-hint');
const srText = document.getElementById('screen-text');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;

// ---------- Renderer and background ----------
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' }); }
catch { host.innerHTML = '<p class="no3d">This browser cannot show the 3D console. Scroll down for the normal portfolio.</p>'; throw new Error('no webgl'); }
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
host.prepend(renderer.domElement);

const scene = new THREE.Scene();
{ const c = document.createElement('canvas'); c.width = 4; c.height = 512; const x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, 512); g.addColorStop(0, '#070d0b'); g.addColorStop(0.55, '#0f211c'); g.addColorStop(1, '#16342c');
  x.fillStyle = g; x.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t; }
scene.fog = new THREE.Fog(0x142d26, 14, 42);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.6;
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
scene.add(new THREE.HemisphereLight(0xffffff, 0x1a2a24, 0.7));
const key = new THREE.DirectionalLight(0xffffff, 1.5); key.position.set(-4, 5, 7); scene.add(key);
const rim = new THREE.DirectionalLight(0xdff5ea, 0.6); rim.position.set(5, 2, -4); scene.add(rim);

const grid = new THREE.GridHelper(90, 90, 0x3fe0a8, 0x1f6b55); grid.position.y = -3.3; grid.material.transparent = true; grid.material.opacity = 0.5; scene.add(grid);
const shadow = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, 'rgba(0,0,0,.65)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(5, 2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = -3.28; scene.add(m); return m; })();
const cubes = [];
{ const cols = [0x9fd8bb, 0x5fa58c, 0x2f6f5e, 0xffd37a];
  for (let i = 0; i < 26; i++) {
    const sz = 0.25 + Math.random() * 0.6, geo = new THREE.BoxGeometry(sz, sz, sz);
    const m = i % 3 === 0
      ? new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: i % 2 ? 0x7dffb0 : 0xffd37a, transparent: true, opacity: 0.85 }))
      : new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: cols[i % 4], roughness: 0.3 }));
    const side = i % 2 ? 1 : -1;
    m.position.set(side * (4 + Math.random() * 10), -3 + Math.random() * 9, -2 - Math.random() * 14);
    m.rotation.set(Math.random() * 3, Math.random() * 3, 0);
    m.userData = { spin: (Math.random() - 0.5) * 0.6, bob: Math.random() * 6, y: m.position.y };
    scene.add(m); cubes.push(m);
  } }
const particles = (() => { const N = 140, p = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { p[i * 3] = (Math.random() - 0.5) * 34; p[i * 3 + 1] = -3 + Math.random() * 12; p[i * 3 + 2] = -1 - Math.random() * 18; }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  const m = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xbff5d6, size: 0.06, transparent: true, opacity: 0.7 })); scene.add(m); return m; })();

// ---------- The body: rounded slab with the render on its face ----------
const IMG_W = 457, IMG_H = 612, FACE = { x: 43, y: 28, w: 370, h: 562 };   // face crop inside the full render
const W = 3.2, H = W * FACE.h / FACE.w, D = 0.78, R = 46 / FACE.w * W;
const dev = new THREE.Group(); scene.add(dev);
const loader = new THREE.TextureLoader();
const plastic = new THREE.MeshPhysicalMaterial({ color: 0xc9c4ba, roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.4 });
{ const bt = 0.07, s = new THREE.Shape(), w = W - 2 * bt, h = H - 2 * bt, r = R - bt, x0 = -w / 2, y0 = -h / 2;
  s.moveTo(x0 + r, y0); s.lineTo(x0 + w - r, y0); s.quadraticCurveTo(x0 + w, y0, x0 + w, y0 + r); s.lineTo(x0 + w, y0 + h - r);
  s.quadraticCurveTo(x0 + w, y0 + h, x0 + w - r, y0 + h); s.lineTo(x0 + r, y0 + h); s.quadraticCurveTo(x0, y0 + h, x0, y0 + h - r);
  s.lineTo(x0, y0 + r); s.quadraticCurveTo(x0, y0, x0 + r, y0);
  const geo = new THREE.ExtrudeGeometry(s, { depth: D - 2 * bt, bevelEnabled: true, bevelThickness: bt, bevelSize: bt, bevelSegments: 5, curveSegments: 24 });
  geo.translate(0, 0, -(D - 2 * bt) / 2);
  dev.add(new THREE.Mesh(geo, plastic));
  // seam line around the middle
  const seam = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.012, bevelEnabled: true, bevelThickness: 0, bevelSize: bt + 0.004, bevelSegments: 1, curveSegments: 24 }), new THREE.MeshStandardMaterial({ color: 0x6d685f, roughness: 0.8 }));
  seam.position.z = -0.006; dev.add(seam); }
const faceTex = loader.load('img/ts26-face.png'); faceTex.colorSpace = THREE.SRGBColorSpace; faceTex.anisotropy = 8;
const face = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshStandardMaterial({
  map: faceTex, emissiveMap: faceTex, emissive: 0xffffff, emissiveIntensity: 0.32, roughness: 0.55, bumpMap: faceTex, bumpScale: 0.002, transparent: true, alphaTest: 0.5 }));
face.position.z = D / 2 + 0.003; dev.add(face);

// helpers: full-render pixels -> local units on the face
const ux = px => ((px - FACE.x) / FACE.w - 0.5) * W;
const uy = py => (0.5 - (py - FACE.y) / FACE.h) * H;
const SCR = { x: 84, y: 68, w: 289, h: 210 };
const sc = document.createElement('canvas'); sc.width = 960; sc.height = 720; const sx = sc.getContext('2d');
const screenTex = new THREE.CanvasTexture(sc); screenTex.colorSpace = THREE.SRGBColorSpace; screenTex.anisotropy = 8;
const screen = new THREE.Mesh(new THREE.PlaneGeometry(SCR.w / FACE.w * W, SCR.h / FACE.h * H), new THREE.MeshBasicMaterial({ map: screenTex, color: 0xdedede }));
screen.position.set(ux(SCR.x + SCR.w / 2), uy(SCR.y + SCR.h / 2), D / 2 + 0.006); dev.add(screen);

// press decals over the printed controls
const decal = (px, py, rPx) => { const m = new THREE.Mesh(new THREE.CircleGeometry(rPx / FACE.w * W, 32), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0, depthWrite: false }));
  m.position.set(ux(px), uy(py), D / 2 + 0.007); dev.add(m); return m; };
const CTRL = { dpad: [134, 397, 58], b: [274, 389, 27], a: [350, 388, 27], mute: [228, 471, 21] };
const decals = { a: decal(...CTRL.a), b: decal(...CTRL.b), mute: decal(...CTRL.mute), dpad: decal(134, 397, 20) };

// back: flat render if present, otherwise a drawn plastic back with embossed text
const back = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshStandardMaterial({ roughness: 0.55, transparent: true, alphaTest: 0.5 }));
back.position.z = -D / 2 - 0.003; back.rotation.y = Math.PI; dev.add(back);
{ const c = document.createElement('canvas'); c.width = 740; c.height = Math.round(740 * H / W); const x = c.getContext('2d'), cw = c.width, ch = c.height, rr = R / W * cw;
  const path = (X, Y, w, h, r) => { x.beginPath(); x.moveTo(X + r, Y); x.arcTo(X + w, Y, X + w, Y + h, r); x.arcTo(X + w, Y + h, X, Y + h, r); x.arcTo(X, Y + h, X, Y, r); x.arcTo(X, Y, X + w, Y, r); x.closePath(); };
  path(0, 0, cw, ch, rr); const g = x.createLinearGradient(0, 0, cw, ch); g.addColorStop(0, '#d2cdc3'); g.addColorStop(1, '#bdb8ae'); x.fillStyle = g; x.fill();
  path(70, 120, cw - 140, 300, 40); x.fillStyle = '#c8c3b9'; x.fill(); x.strokeStyle = 'rgba(0,0,0,.12)'; x.lineWidth = 4; x.stroke();
  x.fillStyle = 'rgba(70,66,60,.7)'; x.font = '600 34px Geist, Arial, sans-serif'; x.textAlign = 'center'; x.fillText('TS-26  ·  DESIGNED IN BANGKOK', cw / 2, 285);
  for (let i = 0; i < 16; i++) { const y = ch * 0.5 + i * 30; x.fillStyle = 'rgba(255,255,255,.35)'; x.fillRect(60, y, cw - 120, 6); x.fillStyle = 'rgba(0,0,0,.12)'; x.fillRect(60, y + 6, cw - 120, 6); }
  for (const [X, Y] of [[60, 60], [cw - 60, 60], [60, ch - 60], [cw - 60, ch - 60]]) { x.beginPath(); x.arc(X, Y, 16, 0, 7); x.fillStyle = '#8f8a80'; x.fill(); x.fillStyle = '#5e5a53'; x.fillRect(X - 9, Y - 2, 18, 4); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; back.material.map = t; back.material.needsUpdate = true;
  }

// ---------- Screen drawing (logical 640 x 480, drawn at 1.5x) ----------
const C = { bg: '#0c1620', mint: '#bff5d6', amber: '#ffd37a', dim: '#6f9a87', white: '#ffffff', sel: 'rgba(125,255,176,.14)' };
const PX = '"Press Start 2P", monospace';
let hits = [];
const txt = (s, x, y, col = C.mint, size = 18) => { sx.fillStyle = col; sx.font = `${size}px ${PX}`; sx.fillText(s, x, y); };
function wrapText(s, x, y, maxW, size, col, lh, maxLines = 99) {
  sx.font = `${size}px ${PX}`; const words = s.split(' '); let line = '', n = 0;
  for (const w of words) { const t = line ? line + ' ' + w : w;
    if (sx.measureText(t).width > maxW && line) { txt(line, x, y + n * lh, col, size); line = w; if (++n >= maxLines) return n; } else line = t; }
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
  items.forEach((t, i) => { const y = y0 + i * lh;
    if (i === sel) { sx.fillStyle = C.sel; sx.fillRect(24, y - lh + 10, 592, lh); if (blink) txt('▶', 30, y, C.amber, size); }
    txt(t, 62, y, i === sel ? C.white : C.mint, size); hits.push({ i, x: 24, y: y - lh + 10, w: 592, h: lh }); });
}
const foot = (l, r) => { txt(l, 30, 458, C.dim, 12); sx.font = `12px ${PX}`; txt(r, 610 - sx.measureText(r).width, 458, C.dim, 12); };

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
    screenTex.needsUpdate = true; srText.textContent = 'The console is off. Press A, any key, or tap the screen to start.'; return;
  }
  if (view === 'boot') {
    const t = (performance.now() - bootAt) / 1000;
    if (t < 0.25) { sx.fillStyle = `rgba(233,255,242,${1 - t * 4})`; sx.fillRect(0, 0, 640, 480); }
    const y = Math.min(230, 120 + t * 260);
    sx.font = `56px ${PX}`; txt('TS-26', 320 - sx.measureText('TS-26').width / 2, y, C.mint, 56);
    if (t > 0.8) { sx.font = `16px ${PX}`; const n = 'THOMAS SOKOLOWSKI'; txt(n, 320 - sx.measureText(n).width / 2, 300, C.amber, 16); }
    say.push('TS-26. Thomas Sokolowski.');
  } else if (view === 'menu') {
    txt('MAIN MENU', 30, 60, C.amber, 20); list(MENU, idx, 118, 38, 17);
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
  scanlines(); screenTex.needsUpdate = true; srText.textContent = say.join(' ') + (sound ? '' : ' Sound is muted.');
}
setInterval(() => { blink = !blink; if (view !== 'boot') draw(); }, 500);

// ---------- Sound ----------
let ac, music = null;
const audio = () => (ac = ac || new (window.AudioContext || window.webkitAudioContext)());
function beep(f = 660, d = 0.06, type = 'square', when = 0) {
  if (!sound) return;
  try { const a = audio(), o = a.createOscillator(), g = a.createGain();
    o.type = type; o.frequency.value = f; g.gain.setValueAtTime(0.05, a.currentTime + when);
    g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + when + d);
    o.connect(g).connect(a.destination); o.start(a.currentTime + when); o.stop(a.currentTime + when + d + 0.02); } catch { }
}
const chime = () => [523, 659, 784, 1047].forEach((f, i) => beep(f, 0.12, 'square', i * 0.09));
const hz = m => 440 * Math.pow(2, (m - 69) / 12);
const LEAD = [69, 0, 72, 0, 76, 74, 72, 0, 69, 0, 67, 69, 72, 0, 0, 0, 74, 0, 76, 0, 79, 76, 74, 0, 72, 0, 74, 72, 69, 0, 0, 0,
  69, 0, 72, 0, 76, 74, 72, 0, 77, 0, 76, 74, 72, 0, 74, 0, 76, 0, 74, 72, 69, 0, 67, 0, 69, 0, 0, 0, 0, 0, 0, 0];
const ROOTS = [45, 41, 48, 43], STEP = 60 / 132 / 4;
function voice(t, f, d, type, vol, dest) { const o = ac.createOscillator(), g = ac.createGain(); o.type = type; o.frequency.setValueAtTime(f, t);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d); o.connect(g).connect(dest); o.start(t); o.stop(t + d + 0.02); }
function hat(t, dest) { const n = ac.createBufferSource(), b = ac.createBuffer(1, ac.sampleRate * 0.04, ac.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
  const f = ac.createBiquadFilter(), g = ac.createGain(); f.type = 'highpass'; f.frequency.value = 6000; g.gain.value = 0.25;
  n.buffer = b; n.connect(f).connect(g).connect(dest); n.start(t); }
function startMusic(delay = 0) {
  if (!sound || music || !on) return;
  try { audio().resume();
    const out = ac.createGain(); out.connect(ac.destination);
    out.gain.setValueAtTime(0, ac.currentTime + delay); out.gain.linearRampToValueAtTime(0.09, ac.currentTime + delay + 1.5);
    let step = 0, next = ac.currentTime + delay;
    const timer = setInterval(() => { while (next < ac.currentTime + 0.15) { const s = step % 64, l = LEAD[s];
      if (l) voice(next, hz(l), STEP * 1.8, 'square', 0.32, out);
      if (s % 2 === 0) voice(next, hz(ROOTS[Math.floor(s / 16)] + (s % 8 === 4 ? 12 : 0)), STEP * 1.6, 'triangle', 0.6, out);
      if (s % 4 === 2) hat(next, out); next += STEP; step++; } }, 25);
    music = { out, timer }; } catch { music = null; }
}
function stopMusic() { if (!music) return; const m = music; music = null;
  try { m.out.gain.cancelScheduledValues(ac.currentTime); m.out.gain.setValueAtTime(m.out.gain.value, ac.currentTime); m.out.gain.linearRampToValueAtTime(0, ac.currentTime + 0.4); } catch { }
  setTimeout(() => { clearInterval(m.timer); m.out.disconnect(); }, 450); }
document.addEventListener('visibilitychange', () => { if (document.hidden) stopMusic(); else if (on && inView) startMusic(); });
new IntersectionObserver(([en]) => { inView = en.intersectionRatio > 0.4; if (!inView) stopMusic(); else if (on) startMusic(); }, { threshold: [0, 0.4, 1] }).observe(section);

// ---------- Behaviour ----------
let bootTimer, zoomTarget = 0, zoom = 0, spin = 0, spinTarget = 0;
const showingBack = () => Math.abs(Math.round(spinTarget / Math.PI)) % 2 === 1;
const toFront = () => { spinTarget = Math.round(spinTarget / (Math.PI * 2)) * Math.PI * 2; };
function setPower(v) {
  if (v === on) return;
  on = v; clearTimeout(bootTimer); zoomTarget = on ? 1 : 0;
  if (on) {
    view = 'boot'; idx = 0; bootAt = performance.now(); chime(); startMusic(0.6); toFront();
    hint.innerHTML = coarse ? 'Tap the d-pad, A to open, B to go back, or tap the screen'
      : 'Click the buttons or the screen, or use <kbd>&#8593;</kbd><kbd>&#8595;</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd> <kbd>M</kbd> mute. Drag to spin it.';
    bootTimer = setTimeout(() => { view = 'menu'; draw(); }, still ? 300 : 1900);
  } else {
    stopMusic(); beep(220, 0.15, 'sawtooth'); offAt = performance.now(); view = 'off';
    hint.innerHTML = coarse ? 'Tap the screen or A to start, drag to spin it' : 'Press A or any key to start, drag to spin it';
  }
}
function flash(k) {
  const d = decals[['up', 'down', 'left', 'right'].includes(k) ? 'dpad' : k]; if (!d) return;
  if (d === decals.dpad) { const o = { up: [0, 38], down: [0, -38], left: [-38, 0], right: [38, 0] }[k] || [0, 0];
    d.position.x = ux(134 + o[0]); d.position.y = uy(397 - o[1]); }
  d.material.opacity = 0.32; setTimeout(() => { d.material.opacity = 0; }, 140);
}
function toggleMute() { sound = !sound; flash('mute'); if (sound) { beep(1200, 0.05); startMusic(); } else stopMusic(); draw(); }
function press(k) {
  if (k === 'mute') { toggleMute(); return; }
  if (showingBack()) { toFront(); return; }
  flash(k);
  if (!on) { if (k === 'a' || k === 'screen') setPower(true); return; }
  if (view === 'boot') return;
  const n = { menu: MENU.length, contact: CONTACT.length }[view];
  if ((k === 'up' || k === 'down') && n) { idx = (idx + (k === 'up' ? -1 : 1) + n) % n; msg = ''; beep(880, 0.04); draw(); return; }
  if (view === 'exp' && ['left', 'right', 'up', 'down'].includes(k)) {
    const len = exp.work.length + exp.education.length; sub = (sub + (k === 'left' || k === 'up' ? -1 : 1) + len) % len; beep(880, 0.04); draw(); return; }
  if (view === 'project' && ['left', 'right', 'up', 'down'].includes(k)) { idx = (idx + (k === 'left' || k === 'up' ? -1 : 1) + projects.length) % projects.length; beep(880, 0.04); draw(); return; }
  if (k === 'b') { beep(330, 0.06);
    if (view === 'project') { idx = 1; view = 'menu'; }
    else if (view !== 'menu') { idx = Math.max(0, ['about', 'project', 'exp', 'contact'].indexOf(view)); view = 'menu'; }
    draw(); return; }
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
    return; }
  draw();
}

// ---------- Pointer: what was hit on the face ----------
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
function hitAt(e) {
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const h = ray.intersectObjects([screen, face], false)[0];
  if (!h) return ray.intersectObject(dev, true)[0] ? { k: 'body' } : null;
  if (h.object === screen) return { k: 'screen', x: h.uv.x * 640, y: (1 - h.uv.y) * 480 };
  const px = FACE.x + h.uv.x * FACE.w, py = FACE.y + (1 - h.uv.y) * FACE.h;
  for (const [k, [cx, cy, rad]] of Object.entries(CTRL)) {
    const dx = px - cx, dy = py - cy;
    if (dx * dx + dy * dy <= rad * rad) {
      if (k !== 'dpad') return { k };
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 12) return { k: 'body' };
      return { k: Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up') };
    }
  }
  return { k: 'body' };
}
let tiltX = 0, tiltY = 0, drag = null, moved = false;
const cv = renderer.domElement;
cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, spin: spinTarget, hit: hitAt(e) }; moved = false; cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointermove', e => {
  if (drag) { const dx = e.clientX - drag.x; if (Math.abs(dx) > 6) moved = true; if (moved) { spinTarget = drag.spin + dx * 0.012; cv.style.cursor = 'grabbing'; } return; }
  const h = hitAt(e); cv.style.cursor = h && h.k !== 'body' ? 'pointer' : h ? 'grab' : 'default';
});
cv.addEventListener('pointerup', () => {
  if (!drag) return;
  const d = drag; drag = null;
  if (moved) { spinTarget = Math.round(spinTarget / Math.PI) * Math.PI; return; }
  const h = d.hit; if (!h || h.k === 'body') return;
  if (h.k === 'screen') {
    if (showingBack()) { toFront(); return; }
    if (!on) { setPower(true); return; }
    const t = hits.find(t => h.x >= t.x && h.x <= t.x + t.w && h.y >= t.y && h.y <= t.y + t.h);
    if (!t) return; if (t.i >= 0) idx = t.i; press('screen'); return;
  }
  press(h.k);
});
addEventListener('pointermove', e => {
  if (!inView || still || drag) return;
  tiltY = ((e.clientX / innerWidth) - 0.5) * 0.5; tiltX = (e.clientY / innerHeight - 0.5) * 0.3;
});
addEventListener('keydown', e => {
  if (!inView || e.target.closest('input,textarea,select,dialog,a,button') || e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.querySelector('dialog[open]')) return;
  const k = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'a', z: 'a', Z: 'a', x: 'b', X: 'b', Backspace: 'b', Escape: 'b', m: 'mute', M: 'mute' }[e.key];
  if (k === 'mute') { e.preventDefault(); toggleMute(); return; }
  if (!on) { if (k || e.key.length === 1) { e.preventDefault(); setPower(true); } return; }
  if (k) { e.preventDefault(); press(k); }
});

// ---------- Layout and loop ----------
let dist = 13;
function fit() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  dist = Math.max((H * 1.5) / (2 * t), (W * 1.5) / (2 * t * camera.aspect));
}
new ResizeObserver(fit).observe(host); fit();
const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  if (document.hidden || !inView) { clock.getDelta(); return; }
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  zoom += (zoomTarget - zoom) * Math.min(1, dt * 1.8);
  spin += (spinTarget - spin) * Math.min(1, dt * 7);
  const z = zoom;
  const rx = THREE.MathUtils.lerp(tiltX + 0.22, tiltX * 0.4, z), ry = THREE.MathUtils.lerp(tiltY - 0.35, tiltY * 0.4, z);
  dev.rotation.x += (rx - dev.rotation.x) * Math.min(1, dt * 5);
  dev.rotation.y += (ry + spin - dev.rotation.y) * Math.min(1, dt * 5);
  dev.position.y = still ? 0 : Math.sin(t * 1.1) * 0.06;
  shadow.scale.setScalar(1 - dev.position.y * 0.3);
  if (!still) {
    for (const c of cubes) { c.rotation.x += c.userData.spin * dt; c.rotation.y += c.userData.spin * 0.7 * dt; c.position.y = c.userData.y + Math.sin(t * 0.6 + c.userData.bob) * 0.3; }
    particles.position.y = (t * 0.25) % 12; if (particles.position.y > 6) particles.position.y -= 12;
    grid.position.z = (t * 0.4) % 1;
  }
  camera.position.set(0, THREE.MathUtils.lerp(1.4, 0.15, z), THREE.MathUtils.lerp(dist * 1.35, dist * 0.92, z));
  camera.lookAt(0, THREE.MathUtils.lerp(-0.3, -0.1, z), 0);
  if ((on && view === 'boot') || (!on && offAt && performance.now() - offAt < 400)) draw();
  renderer.render(scene, camera);
}

Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
  .then(([p, e]) => { projects = p; exp = e; }).catch(() => {});
document.fonts.load(`16px ${PX}`).finally(() => draw());
draw(); frame();
