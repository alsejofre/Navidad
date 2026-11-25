// Animacions ASCII per als dies del calendari.
// Al contingut: "animacio": "cotxe" o bé { "nom": "cotxe", "pluja": true }.
// Cada animació és una funció (opcions) → { w, h, pinta(llenç, t, dt) } amb t i dt en segons.
// «arbre3d» és especial: reprodueix fotogrames precalculats (anim/arbre.json) en un canvas.
import { el, movimentReduit } from './util.js';

// ---------------------------------------------------------------- Llenç de caràcters

class Llenc {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.buida();
  }

  buida() {
    this.c = new Array(this.w * this.h).fill(' ');
    this.k = new Array(this.w * this.h).fill('');
  }

  posa(x, y, ch, color = '') {
    x = Math.round(x);
    y = Math.round(y);
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    this.c[y * this.w + x] = ch;
    this.k[y * this.w + x] = color;
  }

  /** Text transparent: els espais no esborren el que hi ha a sota. */
  text(x, y, s, color) {
    [...s].forEach((ch, i) => { if (ch !== ' ') this.posa(x + i, y, ch, color); });
  }

  dibuix(x, y, linies, color) {
    linies.forEach((l, j) => this.text(x, y + j, l, color));
  }

  html() {
    const esc = (ch) => (ch === '<' ? '&lt;' : ch === '>' ? '&gt;' : ch === '&' ? '&amp;' : ch);
    let out = '';
    for (let y = 0; y < this.h; y++) {
      let actual = '';
      for (let x = 0; x < this.w; x++) {
        const i = y * this.w + x;
        const color = this.c[i] === ' ' ? actual : this.k[i];
        if (color !== actual) {
          if (actual) out += '</span>';
          if (color) out += `<span style="color:${color}">`;
          actual = color;
        }
        out += esc(this.c[i]);
      }
      if (actual) out += '</span>';
      out += '\n';
    }
    return out;
  }
}

// Petit generador determinista (per a posicions «aleatòries» estables)
const hash = (n) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};
const mod = (a, n) => ((a % n) + n) % n;

const C = {
  vermell: '#e0574a', crema: '#f4ead6', gris: '#9aa0a6', grisFosc: '#5f6770', verd: '#5fa86e',
  verdFosc: '#3d7a4c', marro: '#9a6b45', or: '#e8c26a', blau: '#8ec3e6', blauFosc: '#5d7ea8',
  rosa: '#f19bb5', neu: '#e8eef5',
};

// ---------------------------------------------------------------- Animacions

const ANIMACIONS = {
  // 🚗 Cotxe per la carretera. { pluja: true } → muntanyes i pluja (Andorra).
  cotxe({ pluja = false } = {}) {
    const W = 42, H = 11;
    const cotxe = [
      '    ______',
      '   /|_||_\\`.__',
      '  (   _    _ _\\',
      '  =`-(_)--(_)-\'',
    ];
    const arbre = ['   /\\', '  /  \\', ' /____\\', '   ||'];
    return {
      w: W, h: H,
      pinta(ll, t) {
        if (pluja) {
          // Muntanyes llunyanes (es mouen a poc a poc)
          for (let x = 0; x < W; x++) {
            const u = x + t * 1.5;
            const alt = 2.2 + 1.6 * Math.sin(u * 0.28) + 0.9 * Math.sin(u * 0.11 + 1);
            const seg = 2.2 + 1.6 * Math.sin((u + 1) * 0.28) + 0.9 * Math.sin((u + 1) * 0.11 + 1);
            const y = Math.round(5.5 - alt);
            for (let yy = y + 1; yy <= 5; yy++) ll.posa(x, yy, ':', '#34465c');
            ll.posa(x, y, seg > alt + 0.15 ? '/' : seg < alt - 0.15 ? '\\' : '_', alt > 3.2 ? C.neu : '#7f93ad');
          }
        } else {
          // Arbres al costat de la carretera
          for (let k = 0; k < 5; k++) {
            const x = mod(k * 13 - t * 5, W + 10) - 6;
            ll.dibuix(x, 2, arbre.slice(0, 3), C.verd);
            ll.text(x, 5, arbre[3], C.marro);
          }
        }
        // Carretera
        for (let x = 0; x < W; x++) {
          ll.posa(x, 9, '=', C.grisFosc);
          if (mod(x + Math.floor(t * 14), 6) < 3) ll.posa(x, 10, '-', C.gris);
        }
        // Cotxe (botant una mica) i rodes que giren
        const y = 5 + (Math.sin(t * 9) > 0.92 ? -1 : 0);
        ll.dibuix(12, y, cotxe, C.vermell);
        const roda = Math.floor(t * 10) % 2 ? '(+)' : '(x)';
        ll.text(17, y + 3, roda, C.gris);
        ll.text(22, y + 3, roda, C.gris);
        // Fum del tub d'escapament
        for (let k = 0; k < 3; k++) {
          const fase = mod(t * 1.5 + k / 3, 1);
          ll.posa(13 - fase * 8, y + 3 - fase * 1.5, fase < 0.5 ? 'o' : '.', C.grisFosc);
        }
        if (pluja) {
          for (let i = 0; i < 28; i++) {
            const x = mod(hash(i) * W - t * 6, W);
            const yy = mod(hash(i + 50) * H + t * 15, H);
            ll.posa(x, yy, hash(i + 7) > 0.5 ? "'" : ',', C.blau);
          }
        }
      },
    };
  },

  // ✈️ Avió entre núvols.
  avio() {
    const W = 42, H = 10;
    const avio = ['  __', '  \\ \\_____', '###[==_____>', '  /_/'];
    const nuvol = ['  .-.', ' (   ).', '(___(__)'];
    return {
      w: W, h: H,
      pinta(ll, t) {
        for (let k = 0; k < 4; k++) {
          const x = mod(k * 14 + hash(k) * 6 - t * 3, W + 12) - 9;
          ll.dibuix(x, k % 2 ? 6 : 0, nuvol, C.neu);
        }
        const x = mod(t * 7, W + 16) - 13;
        const y = 3 + Math.round(Math.sin(t * 1.5) * 0.6);
        // Estela
        for (let k = 1; k < 7; k++) {
          if (hash(k + Math.floor(t * 8)) > 0.35) ll.posa(x - k, y + 2, k < 3 ? '~' : '-', C.gris);
        }
        ll.dibuix(x, y, avio, C.crema);
        ll.text(x, y + 2, '###', C.or);
      },
    };
  },

  // ☕ Tassa amb vapor.
  cafe() {
    const W = 30, H = 11;
    const tassa = [
      ' .--------.',
      ' |~~~~~~~~|__',
      ' |        |  )',
      ' |        |_/',
      ' \\        /',
      "  '------'",
    ];
    return {
      w: W, h: H,
      pinta(ll, t) {
        for (let i = 0; i < 3; i++) {
          for (let r = 0; r < 4; r++) {
            const ona = Math.sin(t * 2.4 + r * 0.9 + i * 2.1);
            const x = 11 + i * 3 + Math.round(ona);
            const visible = hash(i * 10 + r + Math.floor(t * 3)) > 0.15;
            if (visible) ll.posa(x, 3 - r, ona > 0 ? '(' : ')', r < 2 ? '#d7d7d7' : '#9b9b9b');
          }
        }
        ll.dibuix(6, 4, tassa, C.crema);
        ll.text(8, 5, '~~~~~~~~', '#a8703f');
        ll.text(3, 10, '~~~~~~~~~~~~~~~~~~~~', '#c9b9a0');
      },
    };
  },

  // 🔥 Llar de foc (foc «à la Doom»).
  foc() {
    const W = 36, H = 12, FW = 26, FH = 8;
    const calor = new Array(FW * FH).fill(0);
    const RAMPA = ' .:-=+*#%@';
    const COLORS = ['#5a1a10', '#7d2412', '#a33a14', '#c75417', '#e0741b', '#f0962a', '#f7b93f', '#fbd66a', '#fde9a6', '#fff6dc'];
    let acumulat = 0;
    const pas = () => {
      for (let x = 0; x < FW; x++) {
        const centre = 1 - Math.abs(x - FW / 2) / (FW / 2);
        calor[(FH - 1) * FW + x] = Math.random() < 0.85 ? Math.round(6 + centre * 30) : 10;
      }
      for (let y = 0; y < FH - 1; y++) {
        for (let x = 0; x < FW; x++) {
          const src = (y + 1) * FW + x;
          const r = Math.floor(Math.random() * 3);
          const dst = y * FW + Math.min(FW - 1, Math.max(0, x - r + 1));
          calor[dst] = Math.max(0, calor[src] - (r & 1) * 2 - (Math.random() < 0.35 ? 1 : 0));
        }
      }
    };
    return {
      w: W, h: H,
      pinta(ll, t, dt) {
        acumulat += dt;
        while (acumulat > 0.07) { pas(); acumulat -= 0.07; }
        ll.text(1, 0, '_'.repeat(34), C.marro);
        ll.text(0, 1, '|' + '_'.repeat(34) + '|', C.marro);
        for (let y = 2; y < 11; y++) { ll.text(1, y, '||', '#7a4a30'); ll.text(33, y, '||', '#7a4a30'); }
        for (let y = 0; y < FH; y++) {
          for (let x = 0; x < FW; x++) {
            const v = Math.min(9, Math.floor(calor[y * FW + x] / 4));
            if (v > 0) ll.posa(5 + x, 2 + y, RAMPA[v], COLORS[v]);
          }
        }
        ll.text(9, 9, '==%%===%%%===%%==', '#7a4a30');
        ll.text(0, 11, "'" + '-'.repeat(34) + "'", C.marro);
      },
    };
  },

  // 🐞 La marieta (el bitxo) passejant.
  marieta() {
    const W = 40, H = 8;
    return {
      w: W, h: H,
      pinta(ll, t) {
        for (let x = 0; x < W; x++) ll.posa(x, 7, ",.'`"[mod(x * 7, 4)], C.verdFosc);
        for (const [fx, color] of [[5, C.rosa], [17, C.or], [30, C.rosa]]) {
          ll.posa(fx, 6, '|', C.verd);
          ll.posa(fx, 5, '*', color);
        }
        const x = mod(t * 4.5, W + 12) - 10;
        const pas = Math.floor(t * 6) % 2;
        ll.text(x + 1, 3, '.---.', C.vermell);
        ll.posa(x + 8, 3, pas ? ',' : "'", C.gris);
        ll.text(x, 4, '/#####\\', C.vermell);
        ll.text(x, 5, '\\#####/', C.vermell);
        for (const [dx, dy] of [[2, 4], [4, 4], [1, 5], [3, 5], [5, 5]]) ll.posa(x + dx, dy, 'o', '#3a1a1a');
        ll.posa(x + 7, 4, '@', '#c9c9c9');
        ll.text(x + 1, 6, pas ? '/ / /' : '\\ \\ \\', C.gris);
        // De tant en tant li surt un cor
        const cicle = mod(t, 3);
        if (cicle < 1.2) ll.text(x + 3, 2 - Math.floor(cicle * 2), '<3', C.rosa);
      },
    };
  },

  // 💓 Cor que batega.
  cor() {
    const W = 34, H = 14;
    const RAMPA = '.:+*#%@';
    return {
      w: W, h: H,
      pinta(ll, t) {
        const f = mod(t, 1.1);
        const batec = Math.exp(-((f - 0.1) ** 2) / 0.003) + 0.6 * Math.exp(-((f - 0.32) ** 2) / 0.003);
        const s = 1 + 0.12 * batec;
        for (let y = 0; y < H; y++) {
          for (let x = 0; x < W; x++) {
            const nx = (x - W / 2 + 0.5) / (W / 2.7) / s;
            const ny = -(y - H / 2 + 0.8) / (H / 2.5) / s;
            const v = (nx * nx + ny * ny - 1) ** 3 - nx * nx * ny ** 3;
            if (v <= 0) {
              const d = Math.min(1, -v * 6);
              const ch = RAMPA[Math.min(RAMPA.length - 1, Math.floor(d * RAMPA.length))];
              ll.posa(x, y, ch, d > 0.5 ? '#e8577a' : '#f3a3b8');
            }
          }
        }
        for (let i = 0; i < 6; i++) {
          if (hash(i + Math.floor(t * 4)) > 0.55) {
            ll.posa(hash(i * 3) * W, hash(i * 7) * H, i % 2 ? '+' : '.', '#f7c6d3');
          }
        }
      },
    };
  },

  // 🎆 Focs artificials.
  focs() {
    const W = 42, H = 13;
    const COLORS = ['#ffd166', '#ef6f8a', '#7ed6a5', '#8ecae6', '#f4a6c0', '#fff3d6'];
    const coets = [];
    const particules = [];
    let proper = 0;
    return {
      w: W, h: H,
      pinta(ll, t, dt) {
        if (t > proper) {
          coets.push({ x: 5 + Math.random() * (W - 10), y: H - 1, alt: 2 + Math.random() * 4, color: COLORS[Math.floor(Math.random() * COLORS.length)] });
          proper = t + 0.3 + Math.random() * 0.5;
        }
        for (let i = coets.length - 1; i >= 0; i--) {
          const c = coets[i];
          c.y -= dt * 12;
          ll.posa(c.x, c.y, '|', c.color);
          ll.posa(c.x, c.y + 1, '.', C.grisFosc);
          if (c.y <= c.alt) {
            for (let k = 0; k < 28; k++) {
              const a = (k / 28) * Math.PI * 2;
              const v = 5 + Math.random() * 4;
              particules.push({ x: c.x, y: c.y, vx: Math.cos(a) * v * 2, vy: Math.sin(a) * v, vida: 1.3, color: c.color });
            }
            coets.splice(i, 1);
          }
        }
        for (let i = particules.length - 1; i >= 0; i--) {
          const p = particules[i];
          p.vida -= dt;
          if (p.vida <= 0) { particules.splice(i, 1); continue; }
          p.vy += 9 * dt;
          p.x += p.vx * dt;
          p.y += p.vy * dt;
          p.vx *= 0.96;
          ll.posa(p.x, p.y, p.vida > 0.9 ? '*' : p.vida > 0.45 ? '+' : '.', p.color);
        }
        ll.text(0, H - 1, '_/\\__|^|___/\\/\\____|^^|__/\\___|^|__/\\___', '#3e4a5a');
      },
    };
  },

  // ⛸️ Patinadora sobre gel.
  patins() {
    const W = 40, H = 8;
    const marques = [];
    let ultimaMarca = 0;
    const mirall = (s) => [...s].reverse().map((c) => (c === '/' ? '\\' : c === '\\' ? '/' : c === '<' ? '>' : c === '>' ? '<' : c)).join('');
    return {
      w: W, h: H,
      pinta(ll, t) {
        for (let x = 0; x < W; x++) ll.posa(x, 7, mod(x, 5) ? '-' : '~', '#9cc9e3');
        const x = W / 2 + Math.sin(t * 0.9) * 15;
        const dreta = Math.cos(t * 0.9) > 0;
        if (t - ultimaMarca > 0.12) { marques.push({ x, t }); ultimaMarca = t; }
        while (marques.length && t - marques[0].t > 1.6) marques.shift();
        for (const m of marques) ll.posa(m.x, 6, t - m.t < 0.8 ? '~' : '.', '#cfe6f3');
        const pas = Math.floor(t * 3) % 2;
        let figura = ['  o', ' /|\\', pas ? ' / >' : ' |\\', '"" ""'];
        if (!dreta) figura = figura.map(mirall);
        ll.dibuix(x - 2, 2, figura.slice(0, 3), C.crema);
        ll.text(x - 2, 5, figura[3], C.gris);
        ll.posa(x + (dreta ? -2 : 2), 3, '~', C.vermell);          // bufanda al vent
        for (let i = 0; i < 12; i++) {
          ll.posa(mod(hash(i) * W + Math.sin(t + i) * 2, W), mod(hash(i + 9) * H + t * 2, 6), '.', C.neu);
        }
      },
    };
  },
};

// ---------------------------------------------------------------- Arbre 3D (fotogrames precalculats)

function arbre3d() {
  const caixa = el('div', { class: 'anim anim-canvas' });
  const canvas = el('canvas', { 'aria-label': 'Arbre de Nadal en 3D fet amb caràcters' });
  const avis = el('p', { class: 'anim-avis' }, 'Carregant l\'arbre... 🎄');
  caixa.append(canvas, avis);
  const ctx = canvas.getContext('2d');
  const colors = Array.from({ length: 4096 }, (_, i) =>
    `rgb(${((i >> 8) & 15) * 17},${((i >> 4) & 15) * 17},${(i & 15) * 17})`);

  fetch('anim/arbre.json').then((r) => r.json()).then((d) => {
    const s = atob(d.dades);
    const bytes = new Uint8Array(s.length);
    for (let k = 0; k < s.length; k++) bytes[k] = s.charCodeAt(k);
    avis.remove();
    let cw, ch, ultim = -1;
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
      ultim = -1;
    };
    const pinta = (i) => {
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      for (let k = d.offsets[i] * 5, fi = d.offsets[i + 1] * 5; k < fi; k += 5) {
        const cel = bytes[k] | (bytes[k + 1] << 8), car = bytes[k + 2], col = bytes[k + 3] | (bytes[k + 4] << 8);
        const x = cel % d.W, y = (cel / d.W) | 0;
        ctx.fillStyle = colors[col];
        if (car === 0) ctx.fillRect(x * cw, y * ch, cw + 0.5, ch + 0.5);
        else ctx.fillText(String.fromCharCode(car), (x + 0.5) * cw, (y + 0.5) * ch);
      }
    };
    mida();
    let t = movimentReduit() ? d.bucle / d.fps + 4 : 0;
    let abans = null;
    const frame = (ara) => {
      if (!caixa.isConnected) return;                    // s'ha tancat el dia: parem
      if (abans !== null && !movimentReduit()) t += Math.min(0.1, (ara - abans) / 1000);
      abans = ara;
      if (caixa.clientWidth && Math.abs(canvas.width / (devicePixelRatio || 1) - caixa.clientWidth) > 2) mida();
      const f = Math.floor(t * d.fps);
      const i = f < d.n ? f : d.bucle + ((f - d.bucle) % (d.n - d.bucle));
      if (i !== ultim && caixa.offsetParent !== null) { pinta(i); ultim = i; }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }).catch(() => { avis.textContent = 'No s\'ha pogut carregar l\'arbre 😢'; });
  return caixa;
}

// ---------------------------------------------------------------- Muntatge

export function creaAnimacio(spec) {
  const { nom, ...opcions } = typeof spec === 'string' ? { nom: spec } : spec;
  if (nom === 'arbre3d') return arbre3d();
  const fabrica = ANIMACIONS[nom];
  if (!fabrica) return el('p', { class: 'buit' }, `(Animació desconeguda: ${nom})`);
  const anim = fabrica(opcions);
  const ll = new Llenc(anim.w, anim.h);
  const pre = el('pre', { class: 'ascii anim', 'aria-hidden': 'true' });
  const dibuixa = (t, dt) => {
    ll.buida();
    anim.pinta(ll, t, dt);
    pre.innerHTML = ll.html();                            // només caràcters escapats i colors fixos
  };
  if (movimentReduit()) {
    dibuixa(2.5, 0.05);
    return pre;
  }
  let t = 0, abans = null, ultimDibuix = -1;
  const frame = (ara) => {
    if (!pre.isConnected) return;                         // s'ha tancat el dia: parem
    const dt = abans === null ? 0 : Math.min(0.1, (ara - abans) / 1000);
    abans = ara;
    t += dt;
    if (t - ultimDibuix >= 1 / 15 && pre.offsetParent !== null) {
      dibuixa(t, t - Math.max(0, ultimDibuix));
      ultimDibuix = t;
    }
    requestAnimationFrame(frame);
  };
  dibuixa(0, 0.05);
  requestAnimationFrame(frame);
  return pre;
}

export const NOMS_ANIMACIONS = ['arbre3d', ...Object.keys(ANIMACIONS)];
