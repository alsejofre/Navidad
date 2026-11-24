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

// ---------- Música de capsa de música (melodia original) ----------
// Notes MIDI; 0 = silenci. Cada pas dura un temps.
const MELODIA = [
  76, 74, 72, 74, 76, 76, 76, 0,
  74, 74, 76, 79, 77, 76, 74, 0,
  72, 76, 79, 81, 79, 77, 76, 74,
  72, 74, 76, 74, 72, 0, 67, 0,
];
const BAIX = [48, 55, 53, 55, 48, 53, 55, 48];
const TEMPS = 0.42;
const midi = (n) => 440 * 2 ** ((n - 69) / 12);

function programaVolta() {
  const t0 = ctx.currentTime + 0.05;
  MELODIA.forEach((n, i) => {
    if (n) nota(midi(n), t0 + i * TEMPS, 1.4, { volum: 0.05 });
  });
  BAIX.forEach((n, i) => nota(midi(n), t0 + i * TEMPS * 4, TEMPS * 4, { tipus: 'triangle', volum: 0.025 }));
  temporitzador = setTimeout(() => sonant && programaVolta(), (MELODIA.length * TEMPS - 0.1) * 1000);
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
