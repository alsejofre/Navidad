// Animacions 3D en ASCII per als dies del calendari.
// Al contingut: "animacio": "cor" o bé { "nom": "cotxe", "pluja": true }.
// Totes són fotogrames precalculats amb el motor 3D del taller
// (taller-ascii/animaciones/escenes3d.py i arbre_giratori.py) i desats a anim/<fitxer>.json.
// Cada fitxer només es descarrega quan s'obre el dia que el fa servir.
import { el, movimentReduit } from './util.js';

const FITXERS = {
  arbre3d: 'arbre',
  cor: 'cor',
  cotxe: 'cotxe',
  patins: 'patins',
  cafe: 'cafe',
  avio: 'avio',
  marieta: 'marieta',
  foc: 'foc',
  focs: 'focs',
};

const COLORS = Array.from({ length: 4096 }, (_, i) =>
  `rgb(${((i >> 8) & 15) * 17},${((i >> 4) & 15) * 17},${(i & 15) * 17})`);

const memoria = new Map();                                   // fitxers ja descarregats

function carrega(fitxer) {
  if (!memoria.has(fitxer)) {
    memoria.set(fitxer, fetch(`anim/${fitxer}.json`).then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then((d) => {
      const s = atob(d.dades);
      const bytes = new Uint8Array(s.length);
      for (let k = 0; k < s.length; k++) bytes[k] = s.charCodeAt(k);
      return { ...d, bytes };
    }));
  }
  return memoria.get(fitxer);
}

function reproductor(fitxer, descripcio) {
  const caixa = el('div', { class: 'anim anim-canvas' });
  const canvas = el('canvas', { role: 'img', 'aria-label': descripcio });
  const avis = el('p', { class: 'anim-avis' }, 'Carregant... ✨');
  caixa.append(canvas, avis);
  const ctx = canvas.getContext('2d');

  carrega(fitxer).then((d) => {
    avis.remove();
    let cw, ch, ultim = -1, ampladaActual = 0;
    const mida = () => {
      const w = caixa.clientWidth || 300;
      const dpr = Math.min(devicePixelRatio || 1, 2.5);
      const h = w * (d.H * 2) / d.W;
      canvas.style.height = `${h}px`;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      cw = canvas.width / d.W;
      ch = canvas.height / d.H;
      ctx.font = `bold ${ch * 0.86}px ui-monospace, Menlo, Consolas, monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ampladaActual = w;
      ultim = -1;
    };
    const pinta = (i) => {
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const b = d.bytes;
      for (let k = d.offsets[i] * 5, fi = d.offsets[i + 1] * 5; k < fi; k += 5) {
        const cel = b[k] | (b[k + 1] << 8), car = b[k + 2], col = b[k + 3] | (b[k + 4] << 8);
        const x = cel % d.W, y = (cel / d.W) | 0;
        ctx.fillStyle = COLORS[col];
        if (car === 0) ctx.fillRect(x * cw, y * ch, cw + 0.5, ch + 0.5);
        else ctx.fillText(String.fromCharCode(car), (x + 0.5) * cw, (y + 0.5) * ch);
      }
    };
    mida();
    const quiet = movimentReduit();
    let t = quiet ? (d.bucle ? d.bucle / d.fps + 4 : d.n / d.fps / 2) : 0;
    let abans = null;
    const frame = (ara) => {
      if (!caixa.isConnected) return;                       // s'ha tancat el dia: parem
      if (abans !== null && !quiet) t += Math.min(0.1, (ara - abans) / 1000);
      abans = ara;
      const visible = caixa.offsetParent !== null;
      if (visible && Math.abs(caixa.clientWidth - ampladaActual) > 2) mida();
      const f = Math.floor(t * d.fps);
      const i = f < d.n ? f : d.bucle + ((f - d.bucle) % (d.n - d.bucle));
      if (i !== ultim && visible) { pinta(i); ultim = i; }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }).catch(() => { avis.textContent = 'No s\'ha pogut carregar l\'animació 😢'; });
  return caixa;
}

const DESCRIPCIONS = {
  arbre3d: 'Arbre de Nadal en 3D que creix i gira',
  cor: 'Cor vermell que batega i gira',
  cotxe: 'Cotxe vermell amb un avet al sostre per una carretera nevada',
  'cotxe-pluja': 'Cotxe de nit sota la pluja entre muntanyes',
  patins: 'Patinadora fent voltes en una pista de gel',
  cafe: 'Tassa nadalenca amb un cor de latte i vapor',
  avio: 'Avió de nit entre núvols sota la lluna',
  marieta: 'Marieta passejant per una fulla',
  foc: 'Foc de llar amb flames i espurnes',
  focs: 'Focs artificials i una estrella fugaç amb «Bon Nadal»',
};

export function creaAnimacio(spec) {
  const { nom, pluja } = typeof spec === 'string' ? { nom: spec } : spec;
  const fitxer = nom === 'cotxe' && pluja ? 'cotxe-pluja' : FITXERS[nom];
  if (!fitxer) return el('p', { class: 'buit' }, `(Animació desconeguda: ${nom})`);
  return reproductor(fitxer, DESCRIPCIONS[fitxer === 'cotxe-pluja' ? 'cotxe-pluja' : nom]);
}

export const NOMS_ANIMACIONS = Object.keys(FITXERS);
