// Petites utilitats: dates en hora de Madrid, localStorage segur i creació d'elements.

export function avui(zona) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zona, year: 'numeric', month: 'numeric', day: 'numeric',
  }).formatToParts(new Date());
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return { any: +p.year, mes: +p.month, dia: +p.day };
}

/** Un dia s'obre a partir de la seva data (i els dies passats queden oberts). */
export function diaObert(n, cfg, hui) {
  const clau = (a, m, d) => a * 10000 + m * 100 + d;
  return clau(hui.any, hui.mes, hui.dia) >= clau(cfg.any, cfg.mes, n);
}

export function diesQueFalten(n, cfg, hui) {
  const dia = 24 * 3600 * 1000;
  return Math.round((Date.UTC(cfg.any, cfg.mes - 1, n) - Date.UTC(hui.any, hui.mes - 1, hui.dia)) / dia);
}

export const magatzem = {
  llegeix(clau, perDefecte) {
    try {
      const v = localStorage.getItem(clau);
      return v === null ? perDefecte : JSON.parse(v);
    } catch {
      return perDefecte;
    }
  },
  escriu(clau, valor) {
    try { localStorage.setItem(clau, JSON.stringify(valor)); } catch { /* mode privat */ }
  },
  esborra(clau) {
    try { localStorage.removeItem(clau); } catch { /* res */ }
  },
};

/** el('p', { class: 'text' }, 'Hola') — el text sempre va com a textContent (segur). */
export function el(etiqueta, atributs = {}, ...fills) {
  const node = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(atributs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const f of fills.flat()) {
    if (f === undefined || f === null || f === false) continue;
    node.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return node;
}

export const movimentReduit = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

let temporitzadorAvis;
export function avisa(text) {
  const avis = document.getElementById('avis');
  avis.textContent = text;
  avis.classList.add('visible');
  clearTimeout(temporitzadorAvis);
  temporitzadorAvis = setTimeout(() => avis.classList.remove('visible'), 2600);
}

export function tremola(node) {
  node.classList.remove('tremola');
  void node.offsetWidth;
  node.classList.add('tremola');
}

export function barreja(llista) {
  const a = [...llista];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
