#!/usr/bin/env python3
"""Uso: python3 exporta_web.py [sortida.html] [--mida 84x62] [--segons 32] [--fps 12] [--missatge "Bon Nadal!"]

Graba l'arbre 3D (arbre_giratori.py) i el desa com UN SOL fitxer .html autònom: s'obre al navegador
del mòbil o de l'ordinador sense internet ni res instal·lat. Ideal per enviar per WhatsApp.

Els fotogrames van comprimits (gzip + base64) dins del mateix HTML i es descomprimeixen al
navegador amb DecompressionStream (Chrome/Edge/Firefox moderns, Safari 16.4+).
Per defecte fa un format vertical, pensat per al mòbil.
"""
import argparse
import base64
import gzip
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arbre_giratori import Escena, T_SENSE_INTRO  # noqa: E402

PLANTILLA = r"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#000000">
<title>__TITOL__</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; color: #8a8478; overflow: hidden; }
  [hidden] { display: none !important; }
  body { display: grid; place-items: center; font: 13px ui-monospace, Menlo, Consolas, monospace;
         -webkit-tap-highlight-color: transparent; }
  canvas { display: block; touch-action: manipulation; }
  #avis { position: fixed; inset: 0; display: grid; place-items: center; text-align: center; padding: 24px; }
  #reinicia { position: fixed; right: max(12px, env(safe-area-inset-right)); bottom: max(12px, env(safe-area-inset-bottom));
              background: transparent; color: #6f6a60; border: 1px solid #2a2722; border-radius: 999px;
              font: inherit; padding: 6px 11px; opacity: .7; }
</style>
</head>
<body>
<canvas id="c" aria-label="Arbre de Nadal en 3D fet amb caràcters"></canvas>
<div id="avis">carregant…</div>
<button id="reinicia" type="button" hidden>↺ des del principi</button>
<script>
const W = __W__, H = __H__, FPS = __FPS__, BUCLE = __BUCLE__, N = __N__;
const OFFSETS = [__OFFSETS__];
const DADES = "__DADES__";
(async () => {
  const avis = document.getElementById('avis');
  let bytes;
  try {
    const bin = Uint8Array.from(atob(DADES), (c) => c.charCodeAt(0));
    const flux = new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(flux).arrayBuffer());
  } catch (e) {
    avis.textContent = "El teu navegador no pot obrir l'animació. Prova-ho amb Chrome o Safari actualitzat.";
    return;
  }
  avis.hidden = true;
  const boto = document.getElementById('reinicia');
  boto.hidden = false;
  const c = document.getElementById('c');
  const ctx = c.getContext('2d');
  const colors = Array.from({ length: 4096 }, (_, i) =>
    `rgb(${((i >> 8) & 15) * 17},${((i >> 4) & 15) * 17},${(i & 15) * 17})`);
  let cw, ch;
  function mida() {
    const vw = innerWidth, vh = innerHeight;
    const aspecte = W / (H * 2);                       // cada cel·la és el doble d'alta que d'ampla
    let w = Math.min(vw, vh * aspecte), h = w / aspecte;
    const dpr = Math.min(devicePixelRatio || 1, 3);
    c.style.width = w + 'px'; c.style.height = h + 'px';
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    cw = c.width / W; ch = c.height / H;
    ctx.font = `bold ${ch * 0.86}px ui-monospace, Menlo, Consolas, "Courier New", monospace`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ultim = -1;
  }
  function pinta(i) {
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, c.width, c.height);
    for (let k = OFFSETS[i] * 5, fi = OFFSETS[i + 1] * 5; k < fi; k += 5) {
      const cel = bytes[k] | (bytes[k + 1] << 8), car = bytes[k + 2], col = bytes[k + 3] | (bytes[k + 4] << 8);
      const x = cel % W, y = (cel / W) | 0;
      ctx.fillStyle = colors[col];
      if (car === 0) ctx.fillRect(x * cw, y * ch, cw + 0.5, ch + 0.5);
      else ctx.fillText(String.fromCharCode(car), (x + 0.5) * cw, (y + 0.5) * ch);
    }
  }
  let t = 0, abans = null, ultim = -1, pausa = false;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { t = BUCLE / FPS + 5; pausa = true; }
  function frame(ara) {
    if (abans !== null && !pausa && !document.hidden) t += Math.min(0.1, (ara - abans) / 1000);
    abans = ara;
    const f = Math.floor(t * FPS);
    const i = f < N ? f : BUCLE + ((f - BUCLE) % (N - BUCLE));
    if (i !== ultim) { pinta(i); ultim = i; }
    requestAnimationFrame(frame);
  }
  c.addEventListener('click', () => { pausa = !pausa; });
  boto.addEventListener('click', () => { t = 0; pausa = false; ultim = -1; });
  addEventListener('resize', mida);
  mida();
  requestAnimationFrame(frame);
})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Exporta l'arbre 3D a un .html autònom.")
    ap.add_argument('sortida', nargs='?', default='arbre-de-nadal.html')
    ap.add_argument('--mida', default='84x62', help='AMPLADAxALÇADA en caràcters (84x62 = vertical per al mòbil)')
    ap.add_argument('--segons', type=float, default=32)
    ap.add_argument('--fps', type=float, default=12)
    ap.add_argument('--missatge', default='Bon Nadal!')
    ap.add_argument('--titol', default='Bon Nadal! 🎄')
    args = ap.parse_args()

    W, H = (int(v) for v in args.mida.lower().split('x'))
    escena = Escena(W, H, args.missatge)
    total = int(args.segons * args.fps)
    blocs, offsets = [], [0]
    for i in range(total):
        car, fg, bg = escena.fotograma(i / args.fps)
        regs = []
        for y, x in zip(*np.nonzero(bg.max(-1) >= 8)):
            c = bg[y, x] // 16
            regs.append((y * W + x, 0, (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
        for y, x in zip(*np.nonzero(car != ' ')):
            c = fg[y, x] // 16
            regs.append((y * W + x, ord(car[y, x]), (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
        a = np.zeros(len(regs), dtype=[('cel', '<u2'), ('ch', 'u1'), ('col', '<u2')])
        if regs:
            a['cel'], a['ch'], a['col'] = zip(*regs)
        blocs.append(a.tobytes())
        offsets.append(offsets[-1] + len(regs))
        print(f'\rFotograma {i + 1}/{total}', end='', file=sys.stderr)
    print(file=sys.stderr)

    dades = base64.b64encode(gzip.compress(b''.join(blocs), 9)).decode()
    html = (PLANTILLA.replace('__TITOL__', args.titol)
            .replace('__W__', str(W)).replace('__H__', str(H)).replace('__FPS__', str(args.fps))
            .replace('__BUCLE__', str(int(T_SENSE_INTRO * args.fps))).replace('__N__', str(total))
            .replace('__OFFSETS__', ','.join(map(str, offsets))).replace('__DADES__', dades))
    with open(args.sortida, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✓ {args.sortida} ({len(html) / 1e6:.1f} MB)', file=sys.stderr)


if __name__ == '__main__':
    main()
