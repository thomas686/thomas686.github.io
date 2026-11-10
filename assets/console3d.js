// TS-26 pocket portfolio: a real 3D handheld (Three.js) with a live canvas screen.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const host = document.getElementById('stage3d');
const section = document.getElementById('play');
const hint = document.getElementById('play-hint');
const srText = document.getElementById('screen-text');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;

// ---------- Renderer, scene, camera ----------
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
} catch {
  host.innerHTML = '<p class="no3d">This browser cannot show the 3D console. Scroll down for the normal portfolio.</p>';
  throw new Error('no webgl');
}
let PR = Math.min(devicePixelRatio, 2);
renderer.setPixelRatio(PR);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
host.prepend(renderer.domElement);

const scene = new THREE.Scene();
const BG = 0x0d1714;
{ const c = document.createElement('canvas'); c.width = 4; c.height = 512; const x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, 512); g.addColorStop(0, '#070d0b'); g.addColorStop(0.55, '#0f211c'); g.addColorStop(1, '#16342c');
  x.fillStyle = g; x.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t; }
scene.fog = new THREE.Fog(0x142d26, 14, 42);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.7;
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);

scene.add(new THREE.HemisphereLight(0xdff2e8, 0x0d1714, 0.5));
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(-6, 7, 4.5); key.intensity = 2.5; key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.008;
Object.assign(key.shadow.camera, { left: -3.5, right: 3.5, top: 4, bottom: -4, near: 1, far: 20 });
scene.add(key);
const rim = new THREE.DirectionalLight(0xdff5ea, 0.7); rim.position.set(-5, 2, -4); scene.add(rim);

const grid = new THREE.GridHelper(90, 90, 0x3fe0a8, 0x1f6b55); grid.position.y = -3.26;
grid.material.transparent = true; grid.material.opacity = 0.55; scene.add(grid);
{ const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, 'rgba(0,0,0,.7)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(5.5, 2.2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = -3.24; scene.add(m); }
// Soft glow behind the console
{ const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, 'rgba(125,255,176,.45)'); g.addColorStop(.5, 'rgba(63,143,119,.18)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthWrite: false, fog: false })); s.scale.set(14, 14, 1); s.position.set(0, 0.5, -3); scene.add(s); }
// Drifting cubes
const cubeCols = [0x9fd8bb, 0x5fa58c, 0x2f6f5e, 0xffd37a];
const cubes = [];
for (let i = 0; i < 24; i++) {
  const sz = 0.25 + Math.random() * 0.6, col = cubeCols[i % 4];
  const geo = new THREE.BoxGeometry(sz, sz, sz);
  const m = i % 3 === 0
    ? new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: i % 2 ? 0x7dffb0 : 0xffd37a, transparent: true, opacity: 0.9 }))
    : new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({ color: col, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.2 }));
  const side = i % 2 ? 1 : -1;
  m.position.set(side * (3.2 + Math.random() * 10), -2.5 + Math.random() * 9, -2 - Math.random() * 14);
  m.rotation.set(Math.random() * 3, Math.random() * 3, 0);
  m.userData = { spin: (Math.random() - 0.5) * 0.6, bob: Math.random() * 6, y: m.position.y };
  scene.add(m); cubes.push(m);
}
// Pixel particles floating up
const PN = 140, pPos = new Float32Array(PN * 3);
for (let i = 0; i < PN; i++) { pPos[i * 3] = (Math.random() - 0.5) * 34; pPos[i * 3 + 1] = -3 + Math.random() * 12; pPos[i * 3 + 2] = -1 - Math.random() * 18; }
const pGeo = new THREE.BufferGeometry(); pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0xbff5d6, size: 0.06, transparent: true, opacity: 0.7 }));
scene.add(particles);

// ---------- The device ----------
const W = 3.2, H = 5.4, D = 0.72;
const dev = new THREE.Group(); scene.add(dev);
const grain = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d'); const d = x.createImageData(256, 256);
  for (let i = 0; i < d.data.length; i += 4) { const v = 200 + Math.random() * 55; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  x.putImageData(d, 0, 0); const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(6, 6); return t; })();
const shell = (color, rough = 0.55, extra = {}) => new THREE.MeshPhysicalMaterial({ color, roughness: rough, roughnessMap: grain, bumpMap: grain, bumpScale: 0.004, metalness: 0, clearcoat: 0.2, clearcoatRoughness: 0.5, sheen: 0.25, sheenColor: new THREE.Color(0xffffff), ...extra });
const mat = (color, rough = 0.55, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...extra });
const add = (geo, m, x = 0, y = 0, z = 0, parent = dev) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); parent.add(o); return o; };

// Two shells with a seam between them
add(new RoundedBoxGeometry(W, H, D / 2 - 0.01, 3, 0.085), shell(0xd3cfc7, 0.36, { clearcoat: 0.45, clearcoatRoughness: 0.35 }), 0, 0, D / 4 + 0.005);
add(new RoundedBoxGeometry(W - 0.02, H - 0.02, D / 2 - 0.01, 3, 0.085), shell(0xc6c2ba, 0.45), 0, 0, -D / 4 - 0.005);
add(new RoundedBoxGeometry(W - 0.08, H - 0.08, 0.03, 2, 0.12), mat(0x8e8a82, 0.8), 0, 0, 0);
const FZ = D / 2; // front face

// Screen bezel, recessed glass, brand strip
add(new RoundedBoxGeometry(2.76, 2.42, 0.07, 3, 0.1), mat(0x22272c, 0.4), 0, 1.13, FZ + 0.0);
// shape helper: rounded rectangle on a Shape or Path
const rr = (p, w, h, r, cx = 0, cy = 0) => { const x = cx - w / 2, y = cy - h / 2;
  p.moveTo(x + r, y); p.lineTo(x + w - r, y); p.quadraticCurveTo(x + w, y, x + w, y + r); p.lineTo(x + w, y + h - r); p.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  p.lineTo(x + r, y + h); p.quadraticCurveTo(x, y + h, x, y + h - r); p.lineTo(x, y + r); p.quadraticCurveTo(x, y, x + r, y); return p; };
const ring = (rOut, rIn) => { const s = new THREE.Shape(); s.absarc(0, 0, rOut, 0, Math.PI * 2); const h = new THREE.Path(); h.absarc(0, 0, rIn, 0, Math.PI * 2, true); s.holes.push(h); return s; };
const bevel = { bevelEnabled: true, bevelThickness: 0.018, bevelSize: 0.014, bevelSegments: 2, curveSegments: 32 };
{ const s = rr(new THREE.Shape(), 2.96, 2.62, 0.2); s.holes.push(rr(new THREE.Path(), 2.74, 2.4, 0.1));
  add(new THREE.ExtrudeGeometry(s, { depth: 0.03, ...bevel }), mat(0xd0ccc4, 0.55), 0, 1.13, FZ + 0.02); }
const SCR_W = 2.36, SCR_H = 1.77;
add(new RoundedBoxGeometry(SCR_W + 0.12, SCR_H + 0.12, 0.02, 2, 0.03), mat(0x3a4249, 0.35), 0, 1.25, FZ + 0.03);
const sc = document.createElement('canvas'); sc.width = 960; sc.height = 720;
const sx = sc.getContext('2d');
const screenTex = new THREE.CanvasTexture(sc); screenTex.colorSpace = THREE.SRGBColorSpace; screenTex.anisotropy = 4;
const screen = add(new THREE.PlaneGeometry(SCR_W, SCR_H), new THREE.MeshBasicMaterial({ map: screenTex, color: 0xd9d9d9, toneMapped: true }), 0, 1.25, FZ + 0.045);
screen.userData.k = 'screen';

const label = (txt, w, h, size, color, font = '600') => {
  const c = document.createElement('canvas'); c.width = w * 500; c.height = h * 500;
  const x = c.getContext('2d'); x.fillStyle = color; x.font = `${font} ${size * 2.5}px Geist, Segoe UI, Arial, sans-serif`; x.textBaseline = 'middle'; x.letterSpacing = '6px';
  x.fillText(txt, 4, c.height / 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t, transparent: true }));
};
const brand = label('TS-26  ·  POCKET PORTFOLIO', 2.2, 0.14, 15, '#aeb9b4', '600'); brand.position.set(-0.08, 0.13, FZ + 0.037); dev.add(brand);
const led = add(new THREE.CylinderGeometry(0.045, 0.045, 0.03, 20), new THREE.MeshStandardMaterial({ color: 0x3b5446, emissive: 0x000000 }), -1.18, 2.12, FZ + 0.04);
led.rotation.x = Math.PI / 2;

// D-pad in a shallow well
add(new THREE.CylinderGeometry(0.62, 0.62, 0.02, 48), mat(0xc0bcb3, 0.7), -0.8, -0.95, FZ + 0.005).rotation.x = Math.PI / 2;
add(new THREE.ExtrudeGeometry(ring(0.68, 0.6), { depth: 0.02, ...bevel }), mat(0xd0ccc4, 0.55), -0.8, -0.95, FZ - 0.005);
const arm = 0.15, len = 0.5, s = new THREE.Shape();
s.moveTo(-arm, len); s.lineTo(arm, len); s.lineTo(arm, arm); s.lineTo(len, arm); s.lineTo(len, -arm); s.lineTo(arm, -arm); s.lineTo(arm, -len);
s.lineTo(-arm, -len); s.lineTo(-arm, -arm); s.lineTo(-len, -arm); s.lineTo(-len, arm); s.lineTo(-arm, arm); s.closePath();
const dpad = add(new THREE.ExtrudeGeometry(s, { depth: 0.1, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.025, bevelSegments: 3 }), shell(0x2b3034, 0.38, { clearcoat: 0.3, roughnessMap: null, bumpMap: null }), -0.8, -0.95, FZ + 0.01);
dpad.userData.k = 'dpad'; dpad.userData.z = dpad.position.z;
const nub = add(new THREE.SphereGeometry(0.06, 16, 12), mat(0x1f2326, 0.4), 0, 0, 0.13, dpad); nub.scale.z = 0.3;

// A and B
const btn = (k, color, x, y, letter) => {
  const g = new THREE.Group(); g.position.set(x, y, FZ + 0.01); dev.add(g);
  add(new THREE.CylinderGeometry(0.33, 0.33, 0.02, 48), mat(0xc0bcb3, 0.7), 0, 0, -0.005, g).rotation.x = Math.PI / 2;
  add(new THREE.ExtrudeGeometry(ring(0.37, 0.32), { depth: 0.015, ...bevel }), mat(0xd0ccc4, 0.55), 0, 0, -0.015, g);
  const b = add(new THREE.CylinderGeometry(0.26, 0.27, 0.14, 48), shell(color, 0.22, { clearcoat: 0.9, clearcoatRoughness: 0.15, roughnessMap: null, bumpMap: null }), 0, 0, 0.07, g); b.rotation.x = Math.PI / 2;
  const l = label(letter, 0.24, 0.24, 30, 'rgba(255,255,255,.92)', '700'); l.position.set(0.035, 0, 0.142); g.add(l);
  g.userData.k = k; b.userData.k = k; l.userData.k = k; g.userData.z = g.position.z; return g;
};
const bA = btn('a', 0xe0795a, 0.95, -0.7, 'A');
const bB = btn('b', 0xe9b44c, 0.3, -1.16, 'B');

// Mute button with a speaker icon
const muteBtn = new THREE.Group(); muteBtn.position.set(0, -1.7, FZ + 0.01); dev.add(muteBtn);
add(new THREE.CylinderGeometry(0.17, 0.17, 0.02, 32), mat(0xc0bcb3, 0.7), 0, 0, -0.005, muteBtn).rotation.x = Math.PI / 2;
add(new THREE.CylinderGeometry(0.13, 0.13, 0.08, 32), mat(0x3a4146, 0.45), 0, 0, 0.04, muteBtn).rotation.x = Math.PI / 2;
const iconCanvas = document.createElement('canvas'); iconCanvas.width = iconCanvas.height = 128;
const iconTex = new THREE.CanvasTexture(iconCanvas); iconTex.colorSpace = THREE.SRGBColorSpace;
const icon = new THREE.Mesh(new THREE.CircleGeometry(0.12, 32), new THREE.MeshBasicMaterial({ map: iconTex, transparent: true }));
icon.position.z = 0.082; muteBtn.add(icon);
muteBtn.userData.k = 'mute'; muteBtn.userData.z = muteBtn.position.z;
function drawIcon(muted) {
  const x = iconCanvas.getContext('2d'); x.clearRect(0, 0, 128, 128); x.fillStyle = '#e9efe9'; x.strokeStyle = '#e9efe9'; x.lineWidth = 9; x.lineCap = 'round';
  x.beginPath(); x.moveTo(28, 50); x.lineTo(46, 50); x.lineTo(68, 30); x.lineTo(68, 98); x.lineTo(46, 78); x.lineTo(28, 78); x.closePath(); x.fill();
  if (muted) { x.beginPath(); x.moveTo(82, 48); x.lineTo(108, 80); x.moveTo(108, 48); x.lineTo(82, 80); x.stroke(); }
  else { x.beginPath(); x.arc(70, 64, 22, -0.8, 0.8); x.stroke(); x.beginPath(); x.arc(70, 64, 38, -0.8, 0.8); x.stroke(); }
  iconTex.needsUpdate = true;
}

// Speaker holes
const holeGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.02, 14), holeMat = mat(0x4f6f5d, 0.9);
{ const slot = new THREE.CapsuleGeometry(0.04, 0.3, 4, 12);
  for (let c = 0; c < 6; c++) { const m = add(slot, mat(0x0d1110, 0.9), -0.5 + c * 0.2, -2.2, FZ - 0.01); m.scale.z = 0.4; } }

// Power slider on the top edge
add(new THREE.BoxGeometry(0.7, 0.05, 0.22), mat(0x8a867d, 0.8), -0.8, H / 2 + 0.005, 0);
const knob = add(new RoundedBoxGeometry(0.26, 0.12, 0.17, 2, 0.04), mat(0xeef1ea, 0.5), -0.97, H / 2 + 0.06, 0);
knob.userData.k = 'power';
// Volume wheel on the right side
{ const wheel = add(new THREE.CylinderGeometry(0.22, 0.22, 0.12, 36), mat(0x8e8a82, 0.6), W / 2 - 0.02, 0.9, 0); wheel.rotation.z = Math.PI / 2;
  for (let i = 0; i < 18; i++) { const a = i / 18 * Math.PI * 2; const r = add(new THREE.BoxGeometry(0.13, 0.02, 0.02), mat(0x8a867d, 0.6), W / 2 - 0.02, 0.9 + Math.sin(a) * 0.22, Math.cos(a) * 0.22); r.rotation.x = -a; } }
// Link port on the left side, headphone jack on the bottom
add(new RoundedBoxGeometry(0.06, 0.42, 0.22, 2, 0.025), mat(0x1f2427, 0.6), -W / 2 + 0.01, 1.35, 0);
{ const jack = add(new THREE.CylinderGeometry(0.06, 0.06, 0.06, 20), mat(0x1f2427, 0.6), 0.9, -H / 2 + 0.01, 0); }
add(new RoundedBoxGeometry(0.5, 0.05, 0.18, 2, 0.02), mat(0x8a867d, 0.7), -0.6, -H / 2 + 0.005, 0);
// ---- Back: stepped plateau, embossed panel, ribbed grip, battery door with latch
const BZ = -D / 2; // back face
const backMat = shell(0xc6c2ba, 0.42, { clearcoat: 0.35 });
const ribMat = shell(0xbdb9b0, 0.4, { clearcoat: 0.35 });
{ // raised plateau on the upper back
  const s = rr(new THREE.Shape(), 2.7, 2.3, 0.16);
  const m = add(new THREE.ExtrudeGeometry(s, { depth: 0.06, ...bevel }), backMat, 0, 1.15, BZ + 0.01); m.rotation.y = Math.PI; }
{ // recessed text panel
  const s = rr(new THREE.Shape(), 1.9, 0.9, 0.06);
  add(new THREE.ExtrudeGeometry(s, { depth: 0.01, ...bevel, bevelThickness: 0.006, bevelSize: 0.006 }), shell(0xc4c0b8, 0.5), 0, 1.25, BZ - 0.075).rotation.y = Math.PI;
  const c = document.createElement('canvas'); c.width = 1140; c.height = 540; const x = c.getContext('2d');
  x.fillStyle = 'rgba(70,67,62,.75)'; x.font = '700 64px Geist, Arial, sans-serif'; x.fillText('TS-26', 40, 110);
  x.font = '500 34px Geist, Arial, sans-serif';
  ['POCKET PORTFOLIO', 'DESIGNED IN BANGKOK', 'BY THOMAS SOKOLOWSKI', 'BUILT WITH AI  ·  2026'].forEach((l, i) => x.fillText(l, 40, 190 + i * 70));
  x.strokeStyle = 'rgba(70,67,62,.6)'; x.lineWidth = 4; x.strokeRect(860, 60, 220, 120); x.font = '600 30px Geist, Arial'; x.fillText('MODEL', 905, 108); x.fillText('TS-26', 905, 152);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  const p = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 0.85), new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.6 }));
  p.position.set(0, 1.25, BZ - 0.098); p.rotation.y = Math.PI; dev.add(p); }
{ // ribbed grip across the lower back
  for (let i = 0; i < 14; i++) add(new RoundedBoxGeometry(2.9, 0.055, 0.05, 2, 0.02), ribMat, 0, -0.15 - i * 0.13, BZ - 0.02);
}
{ // battery door over the ribs, with its own ribs and a latch
  const s = rr(new THREE.Shape(), 2.2, 1.55, 0.1);
  add(new THREE.ExtrudeGeometry(s, { depth: 0.04, ...bevel }), backMat, 0, -1.3, BZ - 0.02).rotation.y = Math.PI;
  for (let i = 0; i < 9; i++) add(new RoundedBoxGeometry(1.9, 0.04, 0.03, 2, 0.012), ribMat, 0, -0.75 - i * 0.14, BZ - 0.09);
  add(new RoundedBoxGeometry(0.42, 0.2, 0.06, 2, 0.03), shell(0xb5b1a8, 0.4), 0, -0.47, BZ - 0.1);
  add(new THREE.BoxGeometry(0.22, 0.06, 0.03), mat(0x1f2427, 0.6), 0, -0.47, BZ - 0.13);
}
// ribbed side grips near the bottom
for (const sx of [-1, 1]) for (let i = 0; i < 10; i++) add(new RoundedBoxGeometry(0.04, 0.05, 0.42, 2, 0.015), ribMat, sx * (W / 2 + 0.005), -0.6 - i * 0.16, 0);
// card slot on the top edge
add(new RoundedBoxGeometry(0.9, 0.04, 0.08, 2, 0.015), mat(0x161a1c, 0.7), 0.55, H / 2 + 0.002, -0.08);
// LINK label and frame around the side port
{ const c = document.createElement('canvas'); c.width = 256; c.height = 64; const x = c.getContext('2d');
  x.fillStyle = 'rgba(70,67,62,.8)'; x.font = '700 40px Geist, Arial'; x.fillText('LINK', 70, 46);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const p = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.125), new THREE.MeshBasicMaterial({ map: t, transparent: true }));
  p.position.set(-W / 2 - 0.006, 1.8, 0); p.rotation.y = -Math.PI / 2; p.rotation.z = Math.PI / 2; dev.add(p);
  add(new RoundedBoxGeometry(0.03, 0.56, 0.3, 2, 0.04), shell(0xcac6be, 0.4), -W / 2 - 0.002, 1.35, 0); }
// Screws on the back
for (const [x, y] of [[-1.25, 2.3], [1.25, 2.3], [-1.25, -2.3], [1.25, -2.3]]) add(new THREE.CylinderGeometry(0.11, 0.11, 0.02, 24), mat(0x5c5953, 0.8), x, y, -D / 2 - 0.002).rotation.x = Math.PI / 2;
for (const [x, y] of [[-1.25, 2.3], [1.25, 2.3], [-1.25, -2.3], [1.25, -2.3]]) add(new THREE.CylinderGeometry(0.07, 0.07, 0.02, 16), mat(0x9aa39e, 0.3, { metalness: 0.8 }), x, y, -D / 2 - 0.005).rotation.x = Math.PI / 2;

const clickables = [screen, dpad, bA, bB, knob, muteBtn];
dev.traverse(o => { if (o.isMesh && o !== screen && !o.material.transparent) { o.castShadow = true; o.receiveShadow = true; } });

// ---------- Post-processing ----------
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.32, 0.5, 0.95);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---------- Layout ----------
let dist = 13;
function fit() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h, false); composer.setPixelRatio(PR); composer.setSize(w, h); bloom.resolution.set(w / 2, h / 2); camera.aspect = w / h; camera.updateProjectionMatrix();
  const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  dist = Math.max((H * 1.42) / (2 * t), (W * 1.5) / (2 * t * camera.aspect));
  scene.fog.near = dist * 1.7; scene.fog.far = dist * 4.2;
}
new ResizeObserver(fit).observe(host); fit();

// ---------- Screen drawing ----------
const C = { bg: '#0c1620', mint: '#bff5d6', amber: '#ffd37a', dim: '#6f9a87', white: '#ffffff', sel: 'rgba(125,255,176,.14)' };
const PX = '"Press Start 2P", monospace';
let hits = [];
const txt = (s, x, y, col = C.mint, size = 18) => { sx.fillStyle = col; sx.font = `${size}px ${PX}`; sx.fillText(s, x, y); };
function wrap(s, x, y, maxW, size, col, lh, maxLines = 99) {
  sx.font = `${size}px ${PX}`; const words = s.split(' '); let line = '', n = 0;
  for (const w of words) {
    const t = line ? line + ' ' + w : w;
    if (sx.measureText(t).width > maxW && line) { txt(line, x, y + n * lh, col, size); line = w; if (++n >= maxLines) return n; }
    else line = t;
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
const SHORT = { ai: 'AI', alphacrm: 'CRM', email: 'EMAIL', side: 'SIDE' };
const MENU = ['ABOUT ME', 'PROJECTS', 'EXPERIENCE', 'CONTACT', 'NORMAL VIEW'];
const CONTACT = ['COPY EMAIL', 'OPEN LINKEDIN'];
let on = false, view = 'off', idx = 0, sub = 0, sound = true, inView = true, blink = true, msg = '';
let projects = [], exp = null, bootAt = 0, offAt = 0;

function draw() {
  hits = [];
  sx.setTransform(1.5, 0, 0, 1.5, 0, 0);
  sx.fillStyle = C.bg; sx.fillRect(0, 0, 640, 480); sx.textBaseline = 'alphabetic';
  const say = [];
  if (!on) {
    if (offAt && performance.now() - offAt < 350) { const k = 1 - (performance.now() - offAt) / 350; sx.fillStyle = '#e9fff2'; sx.fillRect(320 - 300 * k, 238, 600 * k, 4); }
    else { txt('FLIP THE SWITCH', 185, 230, '#6f9a87', 16); txt('▲ ON TOP', 245, 270, '#4f7766', 14); }
    screenTex.needsUpdate = true; srText.textContent = 'The console is off. Press any key or the power switch.'; return;
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
    const items = MENU; list(items, idx, 125, 40, 18);
    foot('▲▼ MOVE', 'A OPEN'); say.push('Main menu. Selected: ' + items[idx]);
  } else if (view === 'about') {
    txt('ABOUT ME', 30, 60, C.amber, 20);
    const ph = img('img/thomas.png');
    if (ph.complete && ph.naturalWidth) {
      const t = document.createElement('canvas'); t.width = t.height = 34; const tx = t.getContext('2d'); tx.drawImage(ph, 0, 0, 34, 34);
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
  } else if (view === 'projects') {
    txt(`PROJECTS ${idx + 1}/${projects.length}`, 30, 60, C.amber, 20);
    const top = Math.max(0, Math.min(idx - 4, projects.length - 9));
    const items = projects.slice(top, top + 9).map(p => `${SHORT[p.category].padEnd(5)} ${p.title.toUpperCase()}`.slice(0, 30));
    list(items, idx - top, 104, 37, 14); hits.forEach(h => { h.i += top; });
    foot('▲▼ MOVE  A OPEN', 'B BACK'); say.push(`Projects. Selected: ${projects[idx]?.title}`);
  } else if (view === 'project') {
    const p = projects[idx];
    if (p.image) drawContain(img(p.image), 0, 0, 640, 400);
    const g = sx.createLinearGradient(0, 330, 0, 480); g.addColorStop(0, 'rgba(5,10,16,0)'); g.addColorStop(0.45, 'rgba(5,10,16,.94)');
    sx.fillStyle = g; sx.fillRect(0, 330, 640, 150);
    wrap(p.title.toUpperCase(), 24, 418, 592, 15, C.amber, 24, 2);
    txt('TAP OR A: FULL STORY   ◀▶ NEXT', 24, 464, C.dim, 11);
    hits.push({ i: -1, x: 0, y: 0, w: 640, h: 480 }); say.push(`${p.title}. ${p.summary} Press A for the full story.`);
  } else if (view === 'exp') {
    const all = [...exp.work, ...exp.education], e = all[sub];
    txt(`EXPERIENCE ${sub + 1}/${all.length}`, 30, 60, C.amber, 20);
    txt(e.when.toUpperCase(), 30, 112, C.amber, 13);
    let n = wrap(e.role.toUpperCase(), 30, 150, 580, 15, C.white, 26, 2);
    wrap(`${e.org} · ${e.place}`.toUpperCase(), 30, 150 + n * 26 + 10, 580, 12, C.mint, 22, 2);
    wrap(e.text, 30, 270, 580, 12, '#9fd8bb', 24, 6);
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
setInterval(() => { blink = !blink; if (on && view !== 'boot') draw(); }, 500);

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
let zoomTarget = 0, zoom = 0, bootTimer, zoomTimer;
function setPower(v) {
  if (v === on) return;
  on = v; clearTimeout(bootTimer); clearTimeout(zoomTimer);
  led.material.emissive.set(on ? 0x5dff9e : 0x000000); led.material.color.set(on ? 0x7dffb0 : 0x3b5446);
  if (on) {
    view = 'boot'; idx = 0; bootAt = performance.now(); chime(); startMusic(0.6);
    zoomTarget = 1;
    hint.innerHTML = coarse ? 'Tap the d-pad, A to open, B to go back, or tap the screen'
      : 'Click the buttons or the screen, or use <kbd>&#8593;</kbd><kbd>&#8595;</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd>';
    bootTimer = setTimeout(() => { view = 'menu'; draw(); }, still ? 300 : 1900);
  } else {
    stopMusic(); zoomTarget = 0; beep(220, 0.15, 'sawtooth'); offAt = performance.now(); view = 'off';
    hint.innerHTML = 'Flip the power switch, or press any key';
  }
}
function pressAnim(k) {
  const o = { a: bA, b: bB, up: dpad, down: dpad, left: dpad, right: dpad }[k];
  if (!o) return;
  if (o === dpad) {
    const tilt = 0.12; dpad.rotation.set({ up: -tilt, down: tilt }[k] || 0, { left: -tilt, right: tilt }[k] || 0, 0);
    setTimeout(() => dpad.rotation.set(0, 0, 0), 130);
  } else { o.position.z = o.userData.z - 0.05; setTimeout(() => { o.position.z = o.userData.z; }, 130); }
}
function toggleMute() {
  sound = !sound; drawIcon(!sound);
  if (sound) { beep(1200, 0.05); startMusic(); } else stopMusic();
  muteBtn.position.z = muteBtn.userData.z - 0.04; setTimeout(() => { muteBtn.position.z = muteBtn.userData.z; }, 130);
  if (on) draw();
}
function press(k) {
  if (k === 'mute') { toggleMute(); return; }
  pressAnim(k);
  if (!on) { setPower(true); return; }
  if (view === 'boot') return;
  const n = { menu: MENU.length, projects: projects.length, contact: CONTACT.length }[view];
  if ((k === 'up' || k === 'down') && n) { idx = (idx + (k === 'up' ? -1 : 1) + n) % n; msg = ''; beep(880, 0.04); draw(); return; }
  if (view === 'exp' && ['left', 'right', 'up', 'down'].includes(k)) {
    const len = exp.work.length + exp.education.length; sub = (sub + (k === 'left' || k === 'up' ? -1 : 1) + len) % len; beep(880, 0.04); draw(); return;
  }
  if (view === 'project' && (k === 'left' || k === 'right')) { idx = (idx + (k === 'left' ? -1 : 1) + projects.length) % projects.length; beep(880, 0.04); draw(); return; }
  if (k === 'b') {
    beep(330, 0.06);
    if (view === 'project') view = 'projects';
    else if (view !== 'menu') { idx = Math.max(0, ['about', 'projects', 'exp', 'contact'].indexOf(view)); view = 'menu'; }
    draw(); return;
  }
  if (k !== 'a') return;
  beep(990, 0.06);
  if (view === 'menu') {
    const choice = MENU[idx];
    if (choice === 'NORMAL VIEW') { document.getElementById('about').scrollIntoView({ behavior: still ? 'auto' : 'smooth' }); return; }
    const next = { 'ABOUT ME': 'about', PROJECTS: 'projects', EXPERIENCE: 'exp', CONTACT: 'contact' }[choice];
    if ((next === 'projects' && !projects.length) || (next === 'exp' && !exp)) return;
    view = next; idx = 0; sub = 0; msg = '';
  } else if (view === 'projects') view = 'project';
  else if (view === 'project') { window.openProject && window.openProject(projects[idx].id); return; }
  else if (view === 'contact') {
    if (idx === 1) { window.open('https://www.linkedin.com/in/ts0kolowski', '_blank', 'noopener'); return; }
    navigator.clipboard?.writeText('thomas.s686@gmail.com').then(() => { msg = 'COPIED!'; draw(); }).catch(() => { msg = 'SEE THE ADDRESS ABOVE'; draw(); });
    return;
  }
  draw();
}

// ---------- Pointer: tilt, hover, click ----------
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let tiltX = 0.12, tiltY = -0.25, spin = 0, dragging = null;
function pick(e) {
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(clickables, true)[0];
  if (!hit) return null;
  let o = hit.object; while (o && !o.userData.k) o = o.parent;
  return o ? { k: o.userData.k, hit } : null;
}
renderer.domElement.addEventListener('pointerup', () => { dragging = null; });
renderer.domElement.addEventListener('pointercancel', () => { dragging = null; });
addEventListener('pointermove', e => {
  if (dragging) { spin = dragging.spin + (e.clientX - dragging.x) * 0.012; renderer.domElement.style.cursor = 'grabbing'; return; }
  if (!inView) return;
  if (!still) { tiltY = ((e.clientX / innerWidth) - 0.5) * 0.7; tiltX = (e.clientY / innerHeight - 0.5) * 0.4 + 0.08; }
  if (e.target === renderer.domElement) renderer.domElement.style.cursor = pick(e) ? 'pointer' : 'grab';
});
renderer.domElement.addEventListener('pointerdown', e => {
  const p = pick(e);
  if (!p || Math.abs(Math.sin(spin / 2)) > 0.5) { dragging = { x: e.clientX, spin }; renderer.domElement.setPointerCapture(e.pointerId); return; }
  e.preventDefault();
  if (p.k === 'power') { setPower(!on); return; }
  if (p.k === 'dpad') {
    const l = dpad.worldToLocal(p.hit.point.clone());
    if (Math.max(Math.abs(l.x), Math.abs(l.y)) < 0.1) return;
    press(Math.abs(l.x) > Math.abs(l.y) ? (l.x > 0 ? 'right' : 'left') : (l.y > 0 ? 'up' : 'down')); return;
  }
  if (p.k === 'screen') {
    if (!on) { setPower(true); return; }
    const u = p.hit.uv, x = u.x * 640, y = (1 - u.y) * 480;
    const h = hits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
    if (!h) return;
    if (h.i >= 0) idx = h.i;
    press('a'); return;
  }
  press(p.k);
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
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
let slow = 0, useBloom = false, checked = 0;
function frame() {
  requestAnimationFrame(frame);
  if (document.hidden || !inView) { clock.getDelta(); return; }
  const raw = clock.getDelta(), dt = Math.min(raw, 0.05), t = clock.elapsedTime;
  if (checked < 240) {
    checked++; if (raw > 1 / 40) slow++;
    if (checked === 120 && slow > 60) { PR = 1.25; renderer.setPixelRatio(PR); renderer.shadowMap.enabled = false; fit(); }
  }
  zoom = still ? zoomTarget : zoom + (zoomTarget - zoom) * Math.min(1, dt * 1.6);
  const z = ease(Math.min(1, Math.max(0, zoom)));
  const rx = THREE.MathUtils.lerp(tiltX + 0.28, tiltX * 0.35, z), ry = THREE.MathUtils.lerp(tiltY - 0.35, tiltY * 0.35, z);
  dev.rotation.x += (rx - dev.rotation.x) * Math.min(1, dt * 5);
  if (on && !dragging) spin += (Math.round(spin / (Math.PI * 2)) * Math.PI * 2 - spin) * Math.min(1, dt * 3);
  dev.rotation.y += (ry + spin - dev.rotation.y) * Math.min(1, dt * 5);
  dev.position.y = still ? 0 : Math.sin(t * 1.1) * 0.06;
  if (!still) {
    for (const c of cubes) { c.rotation.x += c.userData.spin * dt; c.rotation.y += c.userData.spin * 0.7 * dt; c.position.y = c.userData.y + Math.sin(t * 0.6 + c.userData.bob) * 0.3; }
    particles.position.y = (t * 0.25) % 12; if (particles.position.y > 6) particles.position.y -= 12;
    grid.position.z = (t * 0.4) % 1;
  }
  knob.position.x += ((on ? -0.63 : -0.97) - knob.position.x) * Math.min(1, dt * 12);
  camera.position.set(0, THREE.MathUtils.lerp(1.6, 0.2, z), THREE.MathUtils.lerp(dist * 1.55, dist, z));
  camera.lookAt(0, THREE.MathUtils.lerp(-0.4, -0.35, z), 0);
  if ((on && view === 'boot') || (!on && offAt && performance.now() - offAt < 400)) draw();
  if (useBloom) composer.render(); else renderer.render(scene, camera);
}

Promise.all([fetch('data/projects.json').then(r => r.json()), fetch('data/experience.json').then(r => r.json())])
  .then(([p, e]) => { projects = p; exp = e; }).catch(() => {});
document.fonts.load(`16px ${PX}`).finally(() => draw());
drawIcon(false); draw(); frame();
