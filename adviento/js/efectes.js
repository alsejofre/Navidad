// Neu de fons i confeti. Tot es desactiva si el mòbil demana moviment reduït.
import { movimentReduit } from './util.js';

export function iniciaNeu(canvas) {
  if (movimentReduit()) return;
  const ctx = canvas.getContext('2d');
  let flocs = [];
  let w, h;

  function mida() {
    const r = devicePixelRatio || 1;
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * r; canvas.height = h * r;
    ctx.setTransform(r, 0, 0, r, 0, 0);
    const quants = Math.min(90, Math.round(w * h / 9000));
    flocs = Array.from({ length: quants }, () => nouFloc(true));
  }
  function nouFloc(onSigui) {
    return {
      x: Math.random() * w,
      y: onSigui ? Math.random() * h : -10,
      r: 1 + Math.random() * 2.6,
      v: 0.3 + Math.random() * 0.8,
      fase: Math.random() * Math.PI * 2,
    };
  }
  function pas() {
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(255,255,255,0.8)';
    for (const f of flocs) {
      f.y += f.v;
      f.fase += 0.01;
      f.x += Math.sin(f.fase) * 0.4;
      if (f.y > h + 10) Object.assign(f, nouFloc(false));
      ctx.beginPath();
      ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(pas);
  }
  addEventListener('resize', mida);
  mida();
  pas();
}

const COLORS = ['#d8b25a', '#8c2433', '#2b5e47', '#fbf3e4', '#e46a7d', '#7fb3d5'];

export function confeti(canvas, durada = 3500) {
  if (movimentReduit()) return;
  const ctx = canvas.getContext('2d');
  const r = devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * r; canvas.height = h * r;
  ctx.setTransform(r, 0, 0, r, 0, 0);

  const peces = Array.from({ length: 160 }, () => ({
    x: w / 2 + (Math.random() - 0.5) * w * 0.4,
    y: h * 0.35,
    vx: (Math.random() - 0.5) * 12,
    vy: -6 - Math.random() * 9,
    gir: Math.random() * Math.PI,
    vg: (Math.random() - 0.5) * 0.3,
    mida: 6 + Math.random() * 6,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
  }));
  const inici = performance.now();

  function pas(ara) {
    ctx.clearRect(0, 0, w, h);
    for (const p of peces) {
      p.vy += 0.25; p.vx *= 0.99;
      p.x += p.vx; p.y += p.vy; p.gir += p.vg;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.gir);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.mida / 2, -p.mida / 4, p.mida, p.mida / 2);
      ctx.restore();
    }
    if (ara - inici < durada) requestAnimationFrame(pas);
    else ctx.clearRect(0, 0, w, h);
  }
  requestAnimationFrame(pas);
}
