// Sons sintetitzats amb Web Audio: no cal cap fitxer ni res amb drets d'autor.
// L'àudio només comença després d'un toc (política dels navegadors).

let ctx;
let mestre;
let sonant = false;
let temporitzador;

function audio() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    mestre = ctx.createGain();
    mestre.gain.value = 0.9;
    mestre.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function nota(freq, inici, durada, { tipus = 'sine', volum = 0.12, desti } = {}) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = tipus;
  o.frequency.value = freq;
  g.gain.setValueAtTime(0.0001, inici);
  g.gain.exponentialRampToValueAtTime(volum, inici + 0.015);
  g.gain.exponentialRampToValueAtTime(0.0001, inici + durada);
  o.connect(g).connect(desti || mestre);
  o.start(inici);
  o.stop(inici + durada + 0.05);
}

/** Campaneta en obrir una casella. */
export function campaneta() {
  if (!audio()) return;
  const t = ctx.currentTime;
  [1318.5, 1760, 2637].forEach((f, i) => nota(f, t + i * 0.08, 1.2, { volum: 0.08 }));
}

/** Fanfàrria curta per a encerts i per a l'aniversari. */
export function fanfarria() {
  if (!audio()) return;
  const t = ctx.currentTime;
  [523.25, 659.25, 783.99, 1046.5].forEach((f, i) =>
    nota(f, t + i * 0.12, 0.6, { tipus: 'triangle', volum: 0.1 }));
}

export function error() {
  if (!audio()) return;
  const t = ctx.currentTime;
  nota(220, t, 0.25, { tipus: 'triangle', volum: 0.08 });
  nota(196, t + 0.12, 0.3, { tipus: 'triangle', volum: 0.08 });
}

export function bufada() {
  if (!audio()) return;
  const t = ctx.currentTime;
  const mostres = ctx.sampleRate * 0.35;
  const buffer = ctx.createBuffer(1, mostres, ctx.sampleRate);
  const d = buffer.getChannelData(0);
  for (let i = 0; i < mostres; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / mostres);
  const font = ctx.createBufferSource();
  const filtre = ctx.createBiquadFilter();
  const g = ctx.createGain();
  filtre.type = 'lowpass'; filtre.frequency.value = 900;
  g.gain.value = 0.25;
  font.buffer = buffer;
  font.connect(filtre).connect(g).connect(mestre);
  font.start(t);
}

// ---------- Música: popurri de nadales de domini públic, en capsa de música ----------
// Cada nota és [MIDI, temps]; 0 = silenci. «baix» és la nota greu de cada compàs.
const NADALES = [
  { // Jingle Bells (James Lord Pierpont, 1857) — tornada
    temps: 0.30, compas: 4,
    notes: [
      [76, 1], [76, 1], [76, 2], [76, 1], [76, 1], [76, 2], [76, 1], [79, 1], [72, 1.5], [74, 0.5], [76, 4],
      [77, 1], [77, 1], [77, 1.5], [77, 0.5], [77, 1], [76, 1], [76, 1], [76, 0.5], [76, 0.5],
      [76, 1], [74, 1], [74, 1], [76, 1], [74, 2], [79, 2],
      [76, 1], [76, 1], [76, 2], [76, 1], [76, 1], [76, 2], [76, 1], [79, 1], [72, 1.5], [74, 0.5], [76, 4],
      [77, 1], [77, 1], [77, 1.5], [77, 0.5], [77, 1], [76, 1], [76, 1], [76, 0.5], [76, 0.5],
      [79, 1], [79, 1], [77, 1], [74, 1], [72, 4],
    ],
    baix: [48, 48, 48, 48, 53, 48, 50, 55, 48, 48, 48, 48, 53, 48, 55, 48],
  },
  { // We Wish You a Merry Christmas (tradicional anglesa)
    temps: 0.36, compas: 3, anacrusi: 1,
    notes: [
      [67, 1],
      [72, 1], [72, 0.5], [74, 0.5], [72, 0.5], [71, 0.5], [69, 1], [69, 1], [69, 1],
      [74, 1], [74, 0.5], [76, 0.5], [74, 0.5], [72, 0.5], [71, 1], [67, 1], [67, 1],
      [76, 1], [76, 0.5], [77, 0.5], [76, 0.5], [74, 0.5], [72, 1], [69, 1], [67, 0.5], [67, 0.5],
      [69, 1], [74, 1], [71, 1], [72, 3],
    ],
    baix: [48, 45, 50, 55, 52, 53, 55, 48],
  },
  { // Deck the Halls (tradicional gal·lesa)
    temps: 0.32, compas: 4,
    notes: [
      [79, 1.5], [77, 0.5], [76, 1], [74, 1], [72, 1], [74, 1], [76, 1], [72, 1],
      [74, 0.5], [76, 0.5], [77, 0.5], [74, 0.5], [76, 1.5], [74, 0.5], [72, 1], [71, 1], [72, 2],
      [79, 1.5], [77, 0.5], [76, 1], [74, 1], [72, 1], [74, 1], [76, 1], [72, 1],
      [74, 0.5], [76, 0.5], [77, 0.5], [74, 0.5], [76, 1.5], [74, 0.5], [72, 1], [71, 1], [72, 2],
      [74, 1.5], [76, 0.5], [77, 1], [74, 1], [76, 1.5], [77, 0.5], [79, 1], [74, 1],
      [76, 0.5], [78, 0.5], [79, 1], [81, 0.5], [83, 0.5], [84, 1], [83, 1], [81, 1], [79, 2],
      [79, 1.5], [77, 0.5], [76, 1], [74, 1], [72, 1], [74, 1], [76, 1], [72, 1],
      [81, 0.5], [81, 0.5], [81, 0.5], [81, 0.5], [79, 1.5], [77, 0.5], [76, 1], [74, 1], [72, 2],
    ],
    baix: [48, 48, 55, 48, 48, 48, 55, 48, 55, 48, 50, 55, 48, 48, 53, 48],
  },
];
const midi = (n) => 440 * 2 ** ((n - 69) / 12);

function campanaMusical(freq, inici, durada) {
  nota(freq, inici, Math.max(0.6, durada * 1.6), { volum: 0.055 });
  nota(freq * 2, inici, 0.5, { volum: 0.012 });               // brillantor de capsa de música
}

function programaVolta() {
  let t = ctx.currentTime + 0.1;
  for (const n of NADALES) {
    let tn = t;
    for (const [nt, durada] of n.notes) {
      if (nt) campanaMusical(midi(nt), tn, durada * n.temps);
      tn += durada * n.temps;
    }
    const iniciBaix = t + (n.anacrusi || 0) * n.temps;
    n.baix.forEach((b, i) => nota(midi(b), iniciBaix + i * n.compas * n.temps, n.compas * n.temps * 0.9,
      { tipus: 'triangle', volum: 0.03 }));
    t = tn + n.temps * 2;                                       // petita pausa entre nadales
  }
  temporitzador = setTimeout(() => sonant && programaVolta(), (t - ctx.currentTime - 0.15) * 1000);
}

export function musicaActiva() { return sonant; }

export function canviaMusica() {
  if (!audio()) return false;
  sonant = !sonant;
  if (sonant) {
    programaVolta();
  } else {
    clearTimeout(temporitzador);
    // Les notes ja programades van connectades al «mestre» antic: l'apaguem suaument
    // i en creem un de nou per als efectes.
    const antic = mestre;
    const t = ctx.currentTime;
    antic.gain.setValueAtTime(antic.gain.value, t);
    antic.gain.linearRampToValueAtTime(0.0001, t + 0.3);
    setTimeout(() => antic.disconnect(), 400);
    mestre = ctx.createGain();
    mestre.gain.value = 0.9;
    mestre.connect(ctx.destination);
  }
  return sonant;
}
