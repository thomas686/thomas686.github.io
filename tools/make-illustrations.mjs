// Generates the drawn project illustrations in img/ (1120 x 700 SVG).
// Used for client work, where a real screenshot would show client names or data.
// Run: node tools/make-illustrations.mjs
import { writeFileSync } from 'node:fs';

const F = 'font-family="Geist, Segoe UI, Helvetica, Arial, sans-serif"';
const ink = '#1c2320', muted = '#8a938e', line = '#e6eae5';
const svg = (bg, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 700" ${F}>
<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#1c2320" flood-opacity=".14"/></filter></defs>
<rect width="1120" height="700" fill="${bg}"/>
${body}
</svg>`;
const win = (x, y, w, h, r = 22) => `<g filter="url(#sh)"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="#fff"/></g>`;
const bar = (x, y, w, c = line, h = 14) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${h / 2}" fill="${c}"/>`;
const text = (x, y, s, size = 22, c = ink, w = 500, extra = '') => `<text x="${x}" y="${y}" font-size="${size}" font-weight="${w}" fill="${c}" ${extra}>${s}</text>`;
const check = (x, y, c) => `<circle cx="${x}" cy="${y}" r="14" fill="${c}"/><path d="M${x - 6} ${y} l4 5 l8 -10" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;

const out = {};

// AlphaCRM in English: a language switch over a CRM list
out['english'] = svg('#dcefe8', `
${win(170, 110, 780, 480)}
${text(220, 180, 'Customers', 30, ink, 600)}
<g transform="translate(700,150)"><rect width="200" height="48" rx="24" fill="#eef1ec"/><rect x="100" y="4" width="96" height="40" rx="20" fill="#2f8a74"/>
${text(32, 32, 'DA', 18, muted, 600)}${text(130, 32, 'EN', 18, '#fff', 600)}</g>
${[0, 1, 2, 3].map(i => `<g transform="translate(220,${240 + i * 78})"><circle cx="20" cy="20" r="20" fill="${['#cfe7dd', '#e3e8f6', '#f3e2d8', '#efe6cf'][i]}"/>${bar(60, 6, [220, 180, 240, 200][i], '#d5dad4')}${bar(60, 28, [140, 120, 160, 110][i])}${bar(560, 12, 110, '#e8f1ed', 18)}</g>`).join('')}
`);

// Social post generator: a review queue of drafted posts
out['post-generator'] = svg('#e3e8f6', `
${win(150, 90, 820, 520)}
${text(200, 158, 'Review queue', 30, ink, 600)}${text(200, 192, 'Drafted over the weekend, waiting for a person', 18, muted, 400)}
${[0, 1, 2].map(i => `<g transform="translate(${200 + i * 250},230)"><rect width="220" height="320" rx="16" fill="#f6f7f4" stroke="${line}"/>
<rect x="14" y="14" width="192" height="130" rx="10" fill="${['#c9d3f0', '#d7e9df', '#f1dccf'][i]}"/>
<circle cx="${60 + i * 30}" cy="80" r="${26 - i * 4}" fill="#fff" opacity=".7"/>
${bar(14, 162, 170, '#d5dad4', 12)}${bar(14, 184, 140, line, 12)}${bar(14, 206, 156, line, 12)}
<rect x="14" y="252" width="92" height="40" rx="10" fill="#2f6f5e"/>${text(32, 278, 'Approve', 16, '#fff', 600)}
<rect x="114" y="252" width="92" height="40" rx="10" fill="#fff" stroke="${line}"/>${text(142, 278, 'Edit', 16, ink, 500)}</g>`).join('')}
`);

// Tyre advice chat agent
out['tyre-agent'] = svg('#e3e8f6', `
${win(300, 70, 520, 560, 28)}
<rect x="300" y="70" width="520" height="80" rx="28" fill="#6b7fb8"/><rect x="300" y="120" width="520" height="30" fill="#6b7fb8"/>
<circle cx="350" cy="110" r="20" fill="#fff" opacity=".9"/>${text(385, 118, 'Tyre advice', 22, '#fff', 600)}
<rect x="500" y="185" width="290" height="56" rx="18" fill="#1c2320"/>${text(522, 220, 'Which tyres fit my car?', 19, '#fff', 500)}
<rect x="330" y="265" width="380" height="88" rx="18" fill="#eef1ec"/>${text(352, 300, 'Happy to help. Do you mostly', 19)}${text(352, 330, 'drive in town or on motorways?', 19)}
<rect x="610" y="378" width="180" height="56" rx="18" fill="#1c2320"/>${text(632, 413, 'Mostly town', 19, '#fff', 500)}
<rect x="330" y="458" width="420" height="120" rx="18" fill="#eef1ec"/>${text(352, 493, 'Then an all-season tyre is a', 19)}${text(352, 523, 'good fit. Nearest open dealer:', 19)}
<rect x="352" y="540" width="170" height="26" rx="13" fill="#6b7fb8"/>${text(368, 559, '2.1 km, open now', 15, '#fff', 600)}
`);

// Weekend agents: a week strip with agents on Saturday and Sunday
out['weekend-agents'] = svg('#e3e8f6', `
${win(110, 140, 900, 420)}
${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d, i) => `<g transform="translate(${140 + i * 124},170)"><rect width="110" height="360" rx="14" fill="${i > 4 ? '#eef0fa' : '#f6f7f4'}"/>${text(20, 38, d, 18, i > 4 ? '#6b7fb8' : muted, 600)}</g>`).join('')}
${[['Email check', 0, 230, '#2f6f5e'], ['Post drafts', 0, 300, '#6b7fb8'], ['Post drafts', 1, 230, '#6b7fb8'], ['Content ideas', 1, 300, '#c47a5a']].map(([t, d, y, c]) => `<g transform="translate(${760 + d * 124 - 6},${y})"><rect width="122" height="54" rx="12" fill="#fff" stroke="${c}" stroke-width="2"/>${text(12, 33, t, 15, ink, 600)}</g>`).join('')}
<g transform="translate(150,400)"><rect width="230" height="70" rx="14" fill="#fff" stroke="${line}"/>${check(36, 35, '#2f6f5e')}${text(64, 30, 'Monday 08:00', 15, muted, 500)}${text(64, 52, 'Ready for review', 18, ink, 600)}</g>
`);

// Jewellery brand emails: an email with a ring illustration
out['jewellery-email'] = svg('#f3e2d8', `
${win(340, 50, 440, 600, 18)}
${text(560, 108, 'ATELIER', 22, '#6c6252', 600, 'text-anchor="middle" letter-spacing="8"')}
<rect x="380" y="128" width="360" height="2" fill="#bbc492"/>
<rect x="380" y="150" width="360" height="200" rx="10" fill="#faf6ec"/>
<circle cx="560" cy="255" r="52" fill="none" stroke="#c9a96a" stroke-width="12"/><path d="M548 196 l12 -16 l12 16 l-12 10 z" fill="#e8d9b5" stroke="#c9a96a" stroke-width="3"/>
${text(560, 400, 'Welcome. Here is where we begin.', 21, '#6c6252', 600, 'text-anchor="middle"')}
${bar(410, 425, 300, '#ece5d8', 12)}${bar(440, 447, 240, '#ece5d8', 12)}
<rect x="470" y="485" width="180" height="50" rx="6" fill="#bbc492"/>${text(560, 517, 'See the collection', 17, '#6c6252', 600, 'text-anchor="middle"')}
<rect x="340" y="570" width="440" height="80" rx="0" fill="#bbc492"/><rect x="340" y="632" width="440" height="18" rx="18" fill="#bbc492"/>
${bar(470, 598, 180, '#d4dab6', 10)}${bar(500, 616, 120, '#d4dab6', 10)}
`);

// Own AI brand email: consent box and a newsletter
out['own-email'] = svg('#f3e2d8', `
${win(130, 120, 380, 460)}
${text(170, 185, 'Get monthly AI tips', 24, ink, 600)}
${bar(170, 215, 290, line)}${bar(170, 240, 230, line)}
<rect x="170" y="285" width="300" height="52" rx="10" fill="#f6f7f4" stroke="${line}"/>${text(188, 318, 'name@company.dk', 18, muted, 400)}
<rect x="170" y="360" width="26" height="26" rx="6" fill="#c47a5a"/><path d="M176 373 l5 6 l10 -12" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
${text(208, 380, 'Yes, send me the newsletter', 17, ink, 500)}
<rect x="170" y="420" width="300" height="54" rx="10" fill="#1c2320"/>${text(320, 454, 'Sign up', 18, '#fff', 600, 'text-anchor="middle"')}
${win(590, 80, 400, 540)}
<rect x="590" y="80" width="400" height="120" rx="22" fill="#1c2320"/><rect x="590" y="170" width="400" height="30" fill="#1c2320"/>
${text(630, 150, 'Newsletter', 28, '#fff', 600)}
${[0, 1, 2].map(i => `<g transform="translate(630,${230 + i * 120})"><rect width="90" height="90" rx="12" fill="${['#f1dccf', '#dcefe8', '#e3e8f6'][i]}"/>${bar(110, 16, 190, '#d5dad4', 14)}${bar(110, 44, 200, line, 12)}${bar(110, 64, 150, line, 12)}</g>`).join('')}
`);

// Thai learning app
out['thai-app'] = svg('#efe6cf', `
${win(360, 60, 400, 580, 36)}
${text(400, 120, 'Today', 20, muted, 600)}${text(720, 120, '12 / 20', 18, muted, 500, 'text-anchor="end"')}
<rect x="400" y="138" width="320" height="8" rx="4" fill="#efe6cf"/><rect x="400" y="138" width="192" height="8" rx="4" fill="#b08a3e"/>
<rect x="400" y="180" width="320" height="250" rx="22" fill="#faf7ef"/>
${text(560, 300, 'สวัสดี', 72, ink, 600, 'text-anchor="middle"')}
${text(560, 350, 'sa-wat-dee', 22, muted, 500, 'text-anchor="middle"')}
${[['low', 0], ['mid', 1], ['high', 2]].map(([t, i]) => `<g transform="translate(${430 + i * 90},385)"><circle cx="20" cy="14" r="${8 + i * 2}" fill="${['#d9c79a', '#b08a3e', '#8a6a28'][i]}"/></g>`).join('')}
${text(560, 470, 'Hello', 26, ink, 600, 'text-anchor="middle"')}
<rect x="400" y="510" width="150" height="56" rx="16" fill="#f6f7f4" stroke="${line}"/>${text(475, 545, 'Again', 18, ink, 500, 'text-anchor="middle"')}
<rect x="570" y="510" width="150" height="56" rx="16" fill="#b08a3e"/>${text(645, 545, 'Got it', 18, '#fff', 600, 'text-anchor="middle"')}
`);

// Research journal: coded fieldnote cards
out['research-journal'] = svg('#efe6cf', `
${[[200, 130, -4], [420, 110, 2], [640, 140, -2]].map(([x, y, r], i) => `<g transform="rotate(${r} ${x + 140} ${y + 220})">${win(x, y, 280, 420, 16)}
${text(x + 28, y + 52, ['FN-08-06', 'FN-09-14', 'FN-11-09'][i], 16, muted, 600, 'letter-spacing="1"')}
${bar(x + 28, y + 80, 200, '#d5dad4', 14)}${bar(x + 28, y + 108, 224, line, 12)}${bar(x + 28, y + 130, 190, line, 12)}${bar(x + 28, y + 152, 210, line, 12)}${bar(x + 28, y + 174, 150, line, 12)}
${[['friction', '#f1dccf', '#a65f43'], ['AI work', '#e3e8f6', '#4f62a0'], ['quality check', '#dcefe8', '#2f6f5e']].slice(0, i + 1).map(([t, bg, fg], j) => `<g transform="translate(${x + 28},${y + 220 + j * 46})"><rect width="${t.length * 10 + 30}" height="34" rx="17" fill="${bg}"/>${text(15, 23, t, 15, fg, 600)}</g>`).join('')}
</g>`).join('')}
`);

for (const [name, s] of Object.entries(out)) writeFileSync(`img/${name}.svg`, s);
console.log(Object.keys(out).join(', '));
