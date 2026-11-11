// TS-26 pocket portfolio: the photoreal face render mounted on a real 3D body (Three.js),
// with a live screen, clickable controls, drag to spin, and a light background scene.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
const BG = new URLSearchParams(location.search).get('bg') || 'pixel';

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

// ---------- Background modes: work | studio | bangkok | pixel | cubes ----------
if (BG !== 'cubes') { grid.visible = false; cubes.forEach(c => { c.visible = false; }); particles.visible = false; }
const canvasBg = (w, h, paint, nearest = false) => {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); paint(x, w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  if (nearest) { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; }
  return { tex: t, ctx: x, c };
};
let bgTick = () => {}, workTick = () => {}, pixelTick = () => {};
const floating = [];
const gallery = new THREE.Group(); scene.add(gallery);
let hoverScreen = null, galleryState = null;
window.__tsProject = null;
if (BG === 'work' || BG === 'mix') {
  if (BG === 'work') scene.background = canvasBg(4, 512, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#050b09'); g.addColorStop(0.6, '#0b1a15'); g.addColorStop(1, '#10251f'); x.fillStyle = g; x.fillRect(0, 0, w, h); }).tex;
  scene.fog = BG === 'mix' ? new THREE.Fog(0x2b1b46, 12, 38) : new THREE.Fog(0x0a1612, 12, 34);
  if (BG === 'work') { const floor = new THREE.GridHelper(80, 40, 0x1f6b55, 0x123a30); floor.position.y = -3.3; floor.material.transparent = true; floor.material.opacity = 0.35; scene.add(floor); }
  workTick = bgTick = (t, dt = 0.016) => {
    const st = galleryState; if (!st) return;
    gallery.rotation.y = Math.sin(t * 0.06) * 0.04;
    const shown = id => floating.find(f => (f.userData.pending != null ? st.p[f.userData.pending].id : f.userData.id) === id);
    const want = window.__tsProject;
    if (want && !shown(want)) { const f = floating.find(f => f !== hoverScreen && f.userData.pending == null) || floating[0]; f.userData.pending = st.p.findIndex(q => q.id === want); }
    if (t - st.last > 4.5) {
      st.last = t;
      for (let n = 0; n < floating.length; n++) {
        st.rr = (st.rr + 1) % floating.length; const f = floating[st.rr];
        if (f === hoverScreen || f.userData.id === want || f.userData.pending != null) continue;
        for (let m = 0; m < st.p.length; m++) { st.next = (st.next + 1) % st.p.length; if (!shown(st.p[st.next].id)) { f.userData.pending = st.next; break; } }
        break;
      }
    }
    for (const f of floating) {
      const u = f.userData;
      if (u.pending != null) { u.fade -= dt * 3; if (u.fade <= 0) { u.fade = 0; const q = st.p[u.pending]; u.img.material.map = st.texs[u.pending]; u.label.material.map = st.labels[u.pending]; u.img.material.needsUpdate = true; u.label.material.needsUpdate = true; u.id = q.id; u.pending = null; } }
      else if (u.fade < 1) u.fade = Math.min(1, u.fade + dt * 2.5);
      const playing = u.id === want, hot = f === hoverScreen || playing;
      u.k += ((hot ? 1 : 0) - u.k) * Math.min(1, dt * 6);
      u.q = (u.q || 0) + ((playing ? 1 : 0) - (u.q || 0)) * Math.min(1, dt * 5);
      f.position.y = u.y + Math.sin(t * 0.5 + u.p) * 0.08;
      f.position.z = u.z + u.q * 0.8;
      f.scale.setScalar(1 + u.k * 0.08 + u.q * 0.18);
      u.edge.material.color.setHex(u.q > 0.5 ? 0xffd37a : 0x7dffb0);
      u.edge.material.opacity = Math.min(1, (0.3 + u.k * 0.7) * u.fade * (u.q > 0.5 ? 0.75 + 0.25 * Math.sin(t * 6) : 1));
      u.img.material.color.setScalar((0.6 + u.k * 0.4) * u.fade);
      u.label.material.opacity = u.fade;
      u.tag.material.opacity = u.q * u.fade;
    }
  };
} else if (BG === 'studio') {
  scene.background = canvasBg(512, 512, (x, w, h) => { const g = x.createRadialGradient(w / 2, h * 0.45, 10, w / 2, h * 0.45, w * 0.7); g.addColorStop(0, '#2a2e2c'); g.addColorStop(1, '#070908'); x.fillStyle = g; x.fillRect(0, 0, w, h); }).tex;
  scene.fog = new THREE.Fog(0x0b0d0c, 12, 34);
  const mirror = new Reflector(new THREE.PlaneGeometry(60, 60), { textureWidth: 1024, textureHeight: 1024, color: 0x8a8f8c });
  mirror.rotation.x = -Math.PI / 2; mirror.position.y = -3.32; scene.add(mirror);
  const dim = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshBasicMaterial({ color: 0x070908, transparent: true, opacity: 0.5 }));
  dim.rotation.x = -Math.PI / 2; dim.position.y = -3.31; scene.add(dim);
  const spot = new THREE.SpotLight(0xffffff, 60, 30, 0.45, 0.6, 1.4); spot.position.set(0, 9, 4); spot.target.position.set(0, -1, 0); scene.add(spot, spot.target);
  shadow.material.opacity = 0.9;
} else if (BG === 'bangkok') {
  const b = canvasBg(2048, 1024, (x, w, h) => {
    const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#070a1a'); g.addColorStop(0.55, '#1c1736'); g.addColorStop(0.78, '#5a2d4a'); g.addColorStop(0.9, '#c2643f'); g.addColorStop(1, '#2a1622'); x.fillStyle = g; x.fillRect(0, 0, w, h);
    for (let i = 0; i < 220; i++) { x.fillStyle = 'rgba(255,255,255,' + (Math.random() * 0.6) + ')'; x.fillRect(Math.random() * w, Math.random() * h * 0.5, 2, 2); }
    const base = h * 0.86; let X = 0;
    const tower = (tx, tw, th, col) => { x.fillStyle = col; x.fillRect(tx, base - th, tw, th);
      for (let wy = base - th + 10; wy < base - 6; wy += 14) for (let wx = tx + 6; wx < tx + tw - 6; wx += 12) if (Math.random() < 0.38) { x.fillStyle = Math.random() < 0.8 ? 'rgba(255,214,140,.85)' : 'rgba(170,220,255,.8)'; x.fillRect(wx, wy, 5, 7); } };
    while (X < w) { const tw = 40 + Math.random() * 110, th = 90 + Math.random() * 300; tower(X, tw, th, '#100c1c'); X += tw + Math.random() * 14; }
    tower(w * 0.62, 70, 560, '#120d20'); tower(w * 0.31, 90, 470, '#120d20'); tower(w * 0.8, 60, 420, '#120d20');
    x.fillStyle = '#0b0814'; x.fillRect(0, base, w, h - base);
    x.filter = 'blur(10px)';
    for (let i = 0; i < 120; i++) { const r = 6 + Math.random() * 26; x.beginPath(); x.arc(Math.random() * w, h * 0.7 + Math.random() * h * 0.3, r, 0, 7);
      x.fillStyle = ['rgba(255,170,90,.35)', 'rgba(255,90,120,.28)', 'rgba(120,200,255,.28)', 'rgba(255,230,160,.35)'][i % 4]; x.fill(); }
    x.filter = 'none';
  });
  scene.background = b.tex; scene.fog = null; shadow.material.opacity = 0.5;
}
if (BG === 'pixel' || BG === 'mix') {
  const PW = 480, PH = 270;
  const P = canvasBg(PW, PH, () => {}, true);
  scene.background = P.tex; if (BG === 'pixel') scene.fog = null; shadow.material.opacity = 0.55;
  const rnd = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(7);
  const stars = Array.from({ length: 110 }, () => [rnd() * PW, rnd() * 120, rnd() * 6, rnd() < 0.15 ? 2 : 1]);
  const clouds = Array.from({ length: 6 }, (_, i) => [rnd() * PW, 30 + rnd() * 60, 14 + rnd() * 26, 0.6 + rnd() * 1.2]);
  const birds = Array.from({ length: 4 }, () => [rnd() * PW, 60 + rnd() * 40, 0.6 + rnd() * 0.5]);
  const ridge = (seed, amp, base, len) => Array.from({ length: len }, (_, i) => Math.round(base - amp * (0.55 + 0.45 * Math.sin(i * 0.03 + seed) * Math.cos(i * 0.013 + seed * 1.7))));
  const far = ridge(1.3, 34, 170, 900), mid = ridge(4.1, 26, 188, 900);
  const sky = ['#120d33', '#1e1446', '#33195a', '#4f1f66', '#74265f', '#a3335a', '#d04c4f', '#ef7a4c', '#f8a65a'];
  const dither = (x, y0, y1, c1, c2) => { for (let y = y0; y < y1; y++) for (let xx = (y % 2); xx < PW; xx += 2) { x.fillStyle = (y - y0) / (y1 - y0) > 0.5 ? c2 : c1; x.fillRect(xx, y, 1, 1); } };
  const temple = (x, bx, by, s) => { // a stylised prang silhouette
    const tiers = [[18, 6], [14, 8], [11, 9], [8, 10], [5, 12], [3, 10], [1, 10]];
    let y = by; for (const [hw, hgt] of tiers) { x.fillRect(Math.round(bx - hw * s), Math.round(y - hgt * s), Math.round(hw * 2 * s), Math.round(hgt * s)); y -= hgt * s; }
  };
  const palm = (x, px0, py0, h, sw, lean = 1) => {
    let tx = px0, ty = py0;
    for (let i = 0; i < h; i++) { tx = px0 + Math.round(lean * 6 * (i / h) * (i / h)); ty = py0 - i; x.fillRect(tx, ty, i < h * 0.3 ? 3 : 2, 1); }
    const fronds = [[-1, -0.5], [-0.8, -0.9], [-0.3, -1], [0.3, -1], [0.8, -0.9], [1, -0.5], [-1.1, 0.1], [1.1, 0.1]];
    for (const [fx, fy] of fronds) { for (let s = 0; s < 14; s++) { const k = s / 14, ox = tx + Math.round(fx * s + sw * k), oy = ty + Math.round(fy * s * 0.6 + k * k * 9);
      x.fillRect(ox, oy, 2, 1); if (s % 3 === 1) x.fillRect(ox, oy + 1, 1, 2); } }
    x.fillRect(tx - 1, ty - 1, 4, 3); };
  let shoot = null, skyCache = null;
  pixelTick = (t) => {
    const x = P.ctx, par = tiltY * 40;
    if (!skyCache) { skyCache = document.createElement('canvas'); skyCache.width = PW; skyCache.height = 152; const sc2 = skyCache.getContext('2d'); const band = 150 / sky.length;
      for (let i = 0; i < sky.length; i++) { sc2.fillStyle = sky[i]; sc2.fillRect(0, Math.round(i * band), PW, Math.ceil(band) + 1); }
      for (let i = 0; i < sky.length - 1; i++) dither(sc2, Math.round((i + 1) * band) - 2, Math.round((i + 1) * band) + 2, sky[i], sky[i + 1]); }
    x.drawImage(skyCache, 0, 0);
    for (const [sx0, sy0, ph, sz] of stars) if (Math.sin(t * 2.2 + ph * 3) > -0.2) { x.fillStyle = sz > 1 ? '#fff4d8' : '#c9c2ff'; x.fillRect(Math.round(sx0 - par * 0.05), Math.round(sy0), sz, sz); }
    if (!shoot && Math.random() < 0.004) shoot = { x: 60 + Math.random() * 300, y: 10 + Math.random() * 40, life: 0 };
    if (shoot) { shoot.life++; for (let k = 0; k < 10; k++) { x.fillStyle = 'rgba(255,255,255,' + (1 - k / 10) + ')'; x.fillRect(Math.round(shoot.x + shoot.life * 4 - k * 3), Math.round(shoot.y + shoot.life * 1.5 - k), 2, 1); } if (shoot.life > 24) shoot = null; }
    const sunX = 240 - par * 0.15, sunY = 176, SR = 64;
    for (let y = -SR; y <= 0; y++) { const w = Math.round(Math.sqrt(SR * SR - y * y)); if (y > -26 && Math.floor((y + SR) / 3) % 3 === 2) continue;
      x.fillStyle = y < -40 ? '#ffe28a' : y < -18 ? '#ffc061' : '#ff9a4d'; x.fillRect(Math.round(sunX - w), sunY + y, w * 2, 1); }
    for (const c of clouds) { const cx = ((c[0] + t * c[3] * 4 - par * 0.2) % (PW + 80)) - 40; x.fillStyle = 'rgba(255,190,200,.55)';
      x.fillRect(Math.round(cx), Math.round(c[1]), Math.round(c[2]), 3); x.fillRect(Math.round(cx + 4), Math.round(c[1] - 2), Math.round(c[2] * 0.6), 2); }
    const drawRidge = (pts, col, speed, shift) => { x.fillStyle = col; const off = Math.floor(t * speed + shift);
      for (let i = 0; i < PW; i++) { const y = pts[((i + off) % pts.length + pts.length) % pts.length]; x.fillRect(i, y, 1, 200 - y); } };
    drawRidge(far, '#3a2150', 2, -par * 0.3); drawRidge(mid, '#271a3d', 4, -par * 0.6);
    x.fillStyle = '#1a1230'; temple(x, 330 - par * 0.8, 200, 1.1); temple(x, 300 - par * 0.8, 200, 0.7); temple(x, 362 - par * 0.8, 200, 0.6);
    x.fillStyle = '#1a1230'; x.fillRect(0, 196, PW, 6);
    for (let y = 202; y < PH; y++) { x.fillStyle = y % 3 === 0 ? '#2b1b46' : '#1e1536'; x.fillRect(0, y, PW, 1); }
    for (let y = 204; y < PH; y += 3) { const w = Math.max(2, 60 - (y - 204) * 0.6) * (0.7 + 0.3 * Math.sin(t * 3 + y)); x.fillStyle = 'rgba(255,170,90,.55)'; x.fillRect(Math.round(sunX - w), y, Math.round(w * 2), 1); }
    for (const b of birds) { const bx = ((b[0] + t * 14 * b[2]) % (PW + 20)) - 10, by = b[1] + Math.sin(t * 2 + b[0]) * 3, f = Math.sin(t * 9 + b[0]) > 0 ? 1 : 0;
      x.fillStyle = '#1a1230'; x.fillRect(Math.round(bx - 2), Math.round(by - f), 2, 1); x.fillRect(Math.round(bx), Math.round(by), 1, 1); x.fillRect(Math.round(bx + 1), Math.round(by - f), 2, 1); }
    x.fillStyle = '#0f0b1f'; palm(x, Math.round(60 - par * 1.2), 202, 46, Math.sin(t * 1.3) * 1.5); palm(x, Math.round(88 - par * 1.2), 202, 34, Math.sin(t * 1.1 + 1) * 1.5);
    palm(x, Math.round(420 - par * 1.2), 202, 40, Math.sin(t * 1.2 + 2) * 1.5);
    P.tex.needsUpdate = true;
  };
  bgTick = BG === 'mix' ? (t, dt) => { pixelTick(t, dt); workTick(t, dt); } : pixelTick;
}
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

// power switch on the right edge: groove + amber knob that slides down when on
const groove = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.8, 0.26), new THREE.MeshStandardMaterial({ color: 0x2a2724, roughness: 0.8 }));
groove.position.set(W / 2 + 0.003, 1.35, 0); dev.add(groove);
const knob = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.26, 0.18), new THREE.MeshStandardMaterial({ color: 0xffd37a, roughness: 0.35, emissive: 0xffb84a, emissiveIntensity: 0.6 }));
knob.position.set(W / 2 + 0.03, 1.6, 0); dev.add(knob);
const callout = document.getElementById('power-callout');
if (coarse && hint) hint.textContent = 'Tap the screen to start';
if (callout) callout.addEventListener('click', () => setPower(true));
const knobWorld = new THREE.Vector3();

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

const MENU = ['ABOUT ME', 'PROJECTS', 'EXPERIENCE', 'CONTACT', 'SNAKE', 'NORMAL VIEW', 'TURN OFF'];
// ---- Snake: an original take on the classic, played on the TS-26 screen ----
const SN = { cols: 20, rows: 13, cell: 30, x0: 20, y0: 56 };
let snake = null;
const hiGet = () => { try { return Number(localStorage.getItem('ts26-snake-hi')) || 0; } catch { return 0; } };
const hiSet = v => { try { localStorage.setItem('ts26-snake-hi', String(v)); } catch { /* storage blocked */ } };
function snakeNew() {
  snake = { body: [[6, 6], [5, 6], [4, 6]], dir: [1, 0], next: [1, 0], food: null, score: 0, alive: true, started: false, acc: 0, step: 0.16, hi: hiGet() };
  snakeFood();
}
function snakeFood() {
  for (;;) { const f = [Math.floor(Math.random() * SN.cols), Math.floor(Math.random() * SN.rows)];
    if (!snake.body.some(([x, y]) => x === f[0] && y === f[1])) { snake.food = f; return; } }
}
function snakeTick(dt) {
  if (!snake || !snake.alive || !snake.started) return;
  snake.acc += dt;
  let moved = false;
  while (snake.acc >= snake.step) {
    snake.acc -= snake.step; snake.dir = snake.next;
    const [hx, hy] = snake.body[0], nx = hx + snake.dir[0], ny = hy + snake.dir[1];
    if (nx < 0 || ny < 0 || nx >= SN.cols || ny >= SN.rows || snake.body.some(([x, y], i) => i < snake.body.length - 1 && x === nx && y === ny)) {
      snake.alive = false; [392, 330, 262, 196].forEach((f, i) => beep(f, 0.14, 'square', i * 0.12));
      if (snake.score > snake.hi) { snake.hi = snake.score; hiSet(snake.hi); }
      break;
    }
    snake.body.unshift([nx, ny]);
    if (nx === snake.food[0] && ny === snake.food[1]) { snake.score++; beep(1046, 0.05); beep(1318, 0.06, 'square', 0.05); snake.step = Math.max(0.07, snake.step - 0.005); snakeFood(); }
    else snake.body.pop();
    moved = true;
  }
  if (moved || !snake.alive) draw();
}
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
    const p = projects[idx]; window.__tsProject = p.id;
    if (p.image) drawContain(img(p.image), 0, 0, 640, 400);
    { const tag = `${idx + 1}/${projects.length}`; sx.font = `12px ${PX}`; const w = sx.measureText(tag).width + 20;
      sx.fillStyle = 'rgba(5,10,16,.85)'; sx.fillRect(640 - w - 14, 14, w, 30); txt(tag, 640 - w - 4, 35, C.amber, 12); }
    const g = sx.createLinearGradient(0, 330, 0, 480); g.addColorStop(0, 'rgba(5,10,16,0)'); g.addColorStop(0.45, 'rgba(5,10,16,.94)');
    sx.fillStyle = g; sx.fillRect(0, 330, 640, 150);
    wrapText(p.title.toUpperCase(), 24, 418, 592, 15, C.amber, 24, 2);
    txt('A: FULL STORY  ◀▶ NEXT  B: MENU', 24, 464, C.dim, 11);
    hits.push({ i: -1, x: 0, y: 0, w: 640, h: 480 }); say.push(`${p.title}. ${p.summary} Press A for the full story.`);
  } else if (view === 'snake') {
    const s = snake;
    txt('SNAKE', 20, 40, C.amber, 16);
    sx.font = `14px ${PX}`; const sc = `SCORE ${s.score}   HI ${Math.max(s.hi, s.score)}`; txt(sc, 620 - sx.measureText(sc).width, 40, C.mint, 14);
    sx.fillStyle = '#081018'; sx.fillRect(SN.x0, SN.y0, SN.cols * SN.cell, SN.rows * SN.cell);
    sx.strokeStyle = 'rgba(125,255,176,.06)'; sx.lineWidth = 1;
    for (let c = 1; c < SN.cols; c++) { sx.beginPath(); sx.moveTo(SN.x0 + c * SN.cell, SN.y0); sx.lineTo(SN.x0 + c * SN.cell, SN.y0 + SN.rows * SN.cell); sx.stroke(); }
    for (let r = 1; r < SN.rows; r++) { sx.beginPath(); sx.moveTo(SN.x0, SN.y0 + r * SN.cell); sx.lineTo(SN.x0 + SN.cols * SN.cell, SN.y0 + r * SN.cell); sx.stroke(); }
    sx.strokeStyle = 'rgba(125,255,176,.35)'; sx.lineWidth = 2; sx.strokeRect(SN.x0, SN.y0, SN.cols * SN.cell, SN.rows * SN.cell);
    const cellAt = (x, y, col, inset = 3) => { sx.fillStyle = col; sx.fillRect(SN.x0 + x * SN.cell + inset, SN.y0 + y * SN.cell + inset, SN.cell - inset * 2, SN.cell - inset * 2); };
    if (s.food) { cellAt(s.food[0], s.food[1], '#ff8f6b', 6); sx.fillStyle = '#7dffb0'; sx.fillRect(SN.x0 + s.food[0] * SN.cell + 13, SN.y0 + s.food[1] * SN.cell + 2, 4, 6); }
    s.body.forEach(([x, y], i) => cellAt(x, y, i === 0 ? '#ffd37a' : (i % 2 ? '#7dffb0' : '#5fe39b')));
    if (!s.started) { sx.fillStyle = 'rgba(5,10,16,.7)'; sx.fillRect(SN.x0, 200, SN.cols * SN.cell, 90); sx.font = `16px ${PX}`;
      const a = 'PRESS A TO PLAY'; txt(a, 320 - sx.measureText(a).width / 2, 240, C.amber, 16); sx.font = `11px ${PX}`; const b = 'STEER WITH THE D-PAD'; txt(b, 320 - sx.measureText(b).width / 2, 272, C.mint, 11); }
    if (!s.alive) { sx.fillStyle = 'rgba(5,10,16,.8)'; sx.fillRect(SN.x0, 180, SN.cols * SN.cell, 130); sx.font = `22px ${PX}`;
      const g = 'GAME OVER'; txt(g, 320 - sx.measureText(g).width / 2, 225, '#ff8f6b', 22); sx.font = `12px ${PX}`;
      const r = s.score >= s.hi && s.score > 0 ? 'NEW HIGH SCORE!' : `SCORE ${s.score}`; txt(r, 320 - sx.measureText(r).width / 2, 258, C.amber, 12);
      const h = 'A: AGAIN   B: MENU'; txt(h, 320 - sx.measureText(h).width / 2, 288, C.mint, 12); }
    foot('\u25B2\u25BC\u25C0\u25B6 STEER', 'B MENU');
    say.push(s.alive ? `Snake. Score ${s.score}. Steer with the arrow keys.` : `Game over. Score ${s.score}. Press A to play again or B for the menu.`);
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
  if (view !== 'project') window.__tsProject = null;
  if (!sound && view !== 'project') txt('MUTED', 532, 60, C.dim, 12);
  scanlines(); screenTex.needsUpdate = true; srText.textContent = say.join(' ') + (sound ? '' : ' Sound is muted.');
}
setInterval(() => { blink = !blink; if (view !== 'boot' && !(view === 'snake' && snake && snake.alive && snake.started)) draw(); }, 500);

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
    hint.innerHTML = coarse ? 'Tap the screen to start' : 'Flip the switch on the right side to start, or press any key';
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
  if (view === 'snake') {
    const d = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[k];
    if (d) { if (snake.alive && !(d[0] === -snake.dir[0] && d[1] === -snake.dir[1])) { snake.next = d; if (!snake.started) snake.started = true; } return; }
    if (k === 'a' || k === 'screen') { if (!snake.alive) snakeNew(); snake.started = true; beep(990, 0.05); draw(); return; }
    if (k === 'b') { beep(330, 0.06); view = 'menu'; idx = MENU.indexOf('SNAKE'); draw(); return; }
    return;
  }
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
    if (choice === 'NORMAL VIEW') { stopMusic(); document.getElementById('to-normal').click(); return; }
    if (choice === 'SNAKE') { snakeNew(); view = 'snake'; draw(); return; }
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
  if (ray.intersectObjects([knob, groove], false)[0]) return { k: 'power' };
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
  const h = hitAt(e);
  hoverScreen = null;
  if (!h && floating.length) { const s = ray.intersectObjects(floating.map(f => f.userData.img), false)[0]; if (s) hoverScreen = s.object.userData.screen; }
  cv.style.cursor = (h && h.k !== 'body') || hoverScreen ? 'pointer' : h ? 'grab' : 'default';
});
cv.addEventListener('pointerup', () => {
  if (!drag) return;
  const d = drag; drag = null;
  if (moved) { spinTarget = Math.round(spinTarget / Math.PI) * Math.PI; return; }
  const h = d.hit;
  if (h && h.k === 'power') { setPower(!on); return; }
  if (!h && hoverScreen && window.openProject) { window.openProject(hoverScreen.userData.id); return; }
  if (!h || h.k === 'body') return;
  if (h.k === 'screen') {
    if (showingBack()) { toFront(); return; }
    if (!on) { setPower(true); return; }
    if (view === 'snake') { press('screen'); return; }
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
  const raw = clock.getDelta(), dt = Math.min(raw, 0.05), rdt = Math.min(raw, 0.5), t = clock.elapsedTime;
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
  camera.position.set(0, THREE.MathUtils.lerp(1.4, 0.3, z), THREE.MathUtils.lerp(dist * 1.35, dist * 1.12, z));
  camera.lookAt(0, THREE.MathUtils.lerp(-0.3, -0.1, z), 0);
  knob.position.y += ((on ? 1.2 : 1.6) - knob.position.y) * Math.min(1, dt * 10);
  knob.material.emissiveIntensity = on ? 0.15 : 0.45 + 0.35 * Math.sin(t * 4);
  if (callout) {
    if (on) callout.classList.add('gone');
    else {
      knob.getWorldPosition(knobWorld); knobWorld.project(camera);
      const r = renderer.domElement.getBoundingClientRect(), kx = (knobWorld.x * 0.5 + 0.5) * r.width, ky = (-knobWorld.y * 0.5 + 0.5) * r.height, cw = callout.offsetWidth;
      const narrow = kx + 26 + cw > r.width - 8;
      if (callout.dataset.mode !== (narrow ? 'tap' : 'switch')) {
        callout.dataset.mode = narrow ? 'tap' : 'switch';
        callout.innerHTML = narrow ? 'TAP THE SCREEN TO START' : '<span class="pc-arrow" aria-hidden="true">&#9664;</span> FLIP THE SWITCH';
      }
      const px = narrow ? (r.width - callout.offsetWidth) / 2 : kx + 26, py = narrow ? r.height * 0.8 : ky - 18;
      callout.style.transform = 'translate(' + px + 'px, ' + py + 'px)';
      callout.classList.remove('gone');
    }
  }
  if (on && view === 'snake') snakeTick(rdt);
  if (!still) bgTick(t, rdt);
  if ((on && view === 'boot') || (!on && offAt && performance.now() - offAt < 400)) draw();
  renderer.render(scene, camera);
}

Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
  .then(([p, e]) => { projects = p; exp = e;
    if (BG !== 'work' && BG !== 'mix') return;
    const texs = p.map(q => { const t = loader.load(q.image); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; });
    const labelTex = title => {
      const lc = document.createElement('canvas'); lc.width = 512; lc.height = 104; const lx = lc.getContext('2d');
      lx.fillStyle = 'rgba(11,10,22,.94)'; lx.fillRect(0, 0, 512, 104); lx.fillStyle = '#ffd37a'; lx.textBaseline = 'middle';
      const words = title.toUpperCase().split(' '); let size = 26, lines;
      for (;;) { lx.font = size + 'px "Press Start 2P", monospace'; lines = [''];
        for (const w of words) { const tl = lines[lines.length - 1] ? lines[lines.length - 1] + ' ' + w : w; if (lx.measureText(tl).width > 492 && lines[lines.length - 1]) lines.push(w); else lines[lines.length - 1] = tl; }
        if (lines.length <= 2 && lines.every(l => lx.measureText(l).width <= 492)) break; if (--size < 9) break; }
      lines.forEach((l, n) => lx.fillText(l, 10, lines.length === 1 ? 52 : 30 + n * 44));
      const t = new THREE.CanvasTexture(lc); t.colorSpace = THREE.SRGBColorSpace; return t;
    };
    const labels = p.map(q => labelTex(q.title));
    const tagTex = (() => { const c = document.createElement('canvas'); c.width = 256; c.height = 48; const x = c.getContext('2d');
      x.fillStyle = '#ffd37a'; x.fillRect(0, 0, 256, 48); x.fillStyle = '#1b1408'; x.font = '18px "Press Start 2P", monospace'; x.textBaseline = 'middle'; x.fillText('\u25B6 NOW PLAYING', 10, 25);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
    const SW = 2.4, SH = SW * 0.625;
    const slots = [];
    for (const side of [-1, 1]) for (const r of [0, 1]) for (const c of [0, 1]) slots.push([side * (4.0 + c * 2.75), r ? 0.45 : 3.25, -7.6 - c * 0.5, side]);
    slots.forEach((s, i) => {
      const g = new THREE.Group();
      const backing = new THREE.Mesh(new THREE.PlaneGeometry(SW + 0.16, SH + 0.7), new THREE.MeshBasicMaterial({ color: 0x0b0a16 }));
      backing.position.set(0, -0.3, -0.02);
      const imgM = new THREE.Mesh(new THREE.PlaneGeometry(SW, SH), new THREE.MeshBasicMaterial({ map: texs[i], color: 0x999999 }));
      const edge = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(SW + 0.16, SH + 0.7)), new THREE.LineBasicMaterial({ color: 0x7dffb0, transparent: true, opacity: 0.3 }));
      edge.position.y = -0.3;
      const label = new THREE.Mesh(new THREE.PlaneGeometry(SW, SW * 104 / 512), new THREE.MeshBasicMaterial({ map: labels[i], transparent: true }));
      label.position.y = -SH / 2 - 0.3;
      const tag = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 0.24), new THREE.MeshBasicMaterial({ map: tagTex, transparent: true, opacity: 0 }));
      tag.position.set(-SW / 2 + 0.65, SH / 2 + 0.2, 0.01);
      g.add(backing, imgM, edge, label, tag);
      g.position.set(s[0], s[1], s[2]); g.rotation.y = -s[3] * 0.2;
      g.userData = { y: s[1], z: s[2], p: i * 1.1, k: 0, q: 0, fade: 1, pending: null, id: p[i].id, img: imgM, label, edge, tag };
      imgM.userData.screen = g;
      gallery.add(g); floating.push(g);
    });
    galleryState = { p, texs, labels, last: 0, rr: -1, next: slots.length - 1 };
  })
  .catch(() => {});
document.fonts.load(`16px ${PX}`).finally(() => draw());
draw(); frame();
