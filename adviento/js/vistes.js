// Contingut de cada dia, cartera de vals i pantalla d'aniversari.
import { el, magatzem } from './util.js';
import { creaJoc } from './jocs.js';
import * as so from './so.js';
import { confeti } from './efectes.js';

const ICONES = { missatge: '💌', joc: '🎲', cupo: '🎟️', humor: '😂' };
export const iconaDe = (d) => (d && ICONES[d.tipus]) || '🎁';

// ---------- Cartera ----------
export const cartera = {
  llegeix: () => magatzem.llegeix('cartera', {}),
  guarda(n) {
    const c = this.llegeix();
    if (!c[n]) c[n] = { guardat: new Date().toISOString(), bescanviat: null };
    magatzem.escriu('cartera', c);
  },
  bescanvia(n) {
    const c = this.llegeix();
    if (c[n]) c[n].bescanviat = new Date().toISOString();
    magatzem.escriu('cartera', c);
  },
  pendents() {
    return Object.values(this.llegeix()).filter((v) => !v.bescanviat).length;
  },
};

const dataCurta = (iso) => new Date(iso).toLocaleDateString('ca-ES', { day: 'numeric', month: 'long' });

function targetaVal(n, d, estat) {
  const bescanviat = estat && estat.bescanviat;
  return el('div', { class: `val${bescanviat ? ' bescanviat' : ''}` },
    bescanviat && el('span', { class: 'segell' }, 'Bescanviat'),
    el('p', { class: 'titol-val' }, d.titol || 'Val'),
    d.text && el('p', { class: 'text' }, d.text),
    d.condicions && el('p', { class: 'condicions' }, d.condicions),
    bescanviat && el('p', { class: 'condicions' }, `Gastat el ${dataCurta(bescanviat)}`),
  );
}

export function pintaCartera(contingut, onCanvi) {
  const llista = document.getElementById('cartera-llista');
  const c = cartera.llegeix();
  const dies = Object.keys(c).sort((a, b) => a - b);
  if (!dies.length) {
    llista.replaceChildren(el('p', { class: 'buit' }, 'Encara no tens cap val. Ja n\'aniran sortint... 😏'));
    return;
  }
  llista.replaceChildren(...dies.map((n) => {
    const d = contingut.dies[n] || {};
    const estat = c[n];
    return el('div', {},
      targetaVal(n, d, estat),
      !estat.bescanviat && el('div', { class: 'accions' }, el('button', {
        class: 'boto boto-or',
        onclick: () => {
          if (!confirm(`Vols gastar ara el val «${d.titol}»?`)) return;
          cartera.bescanvia(n);
          so.fanfarria();
          pintaCartera(contingut, onCanvi);
          onCanvi();
        },
      }, 'Bescanviar ara')),
    );
  }));
}

// ---------- Dia normal ----------
export function pintaDia(n, contingut) {
  const d = contingut.dies[String(n)];
  const parts = [el('span', { class: 'etiqueta-dia' }, `${n} de desembre`)];

  if (!d) {
    parts.push(el('h2', {}, 'Ups!'), el('p', { class: 'text' }, 'Aquest regal encara s\'està embolicant... 🎀'));
  } else {
    if (d.titol && d.tipus !== 'cupo') parts.push(el('h2', {}, d.titol));
    if (d.tipus === 'cupo') parts.push(el('h2', {}, 'Has guanyat un val! 🎟️'));
    if (d.foto) parts.push(el('img', { class: 'foto', src: d.foto, alt: d.peuFoto || '' }));

    if (d.tipus === 'cupo') {
      const estat = cartera.llegeix()[n];
      parts.push(targetaVal(n, d, estat));
      const boto = el('button', {
        class: 'boto boto-or',
        disabled: !!estat,
        onclick: () => {
          cartera.guarda(n);
          boto.disabled = true;
          boto.textContent = 'Guardat a la cartera ✓';
          so.campaneta();
          document.dispatchEvent(new Event('cartera'));
        },
      }, estat ? 'Ja és a la cartera ✓' : 'Guardar a la cartera');
      parts.push(el('div', { class: 'accions' }, boto));
    } else if (d.text) {
      parts.push(el('p', { class: 'text' }, d.text));
    }

    if (d.ascii) parts.push(el('pre', { class: 'ascii' }, d.ascii));

    if (d.tipus === 'joc') {
      const jocs = magatzem.llegeix('jocs', {});
      const premi = el('div', { class: 'premi', hidden: !jocs[n] }, d.premi || 'Molt bé! 🏆');
      const joc = creaJoc(d, () => {
        magatzem.escriu('jocs', { ...magatzem.llegeix('jocs', {}), [n]: true });
        premi.hidden = false;
        premi.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
      parts.push(joc, premi);
    }
  }

  const regal = contingut.regal || {};
  const index = (regal.diesPista || []).indexOf(n);
  if (index >= 0 && regal.pistes && regal.pistes[index]) {
    parts.push(el('div', { class: 'pista' },
      el('h3', {}, `🔍 Pista ${index + 1} de ${regal.diesPista.length}`),
      el('p', {}, regal.pistes[index]),
      el('p', { class: 'peu-pista' }, 'Sobre el teu regal d\'aniversari... 🎂'),
    ));
  }
  return parts;
}

// ---------- Dia 14: aniversari ----------
export function obreAniversari(contingut, { repetit }) {
  const capa = document.getElementById('aniversari');
  const regal = contingut.regal || {};
  const nom = contingut.nom || '';
  const quantes = regal.espelmes || 5;
  let bufades = 0;

  const instruccio = el('p', { class: 'instruccio' }, 'Bufa les espelmes! (toca-les) 🕯️');
  const espelmes = Array.from({ length: quantes }, () => {
    const e = el('button', {
      class: 'espelma',
      'aria-label': 'Espelma',
      onclick: () => {
        if (e.classList.contains('bufada')) return;
        e.classList.add('bufada');
        so.bufada();
        bufades++;
        if (bufades === quantes) celebra();
        else instruccio.textContent = `Encara en queden ${quantes - bufades}... 💨`;
      },
    });
    return e;
  });

  const carta = el('div', { class: 'carta-aniversari targeta', hidden: true });
  const tanca = el('button', { class: 'boto boto-secundari', onclick: () => { capa.hidden = true; } }, 'Tornar al calendari');

  function celebra() {
    so.fanfarria();
    confeti(document.getElementById('confeti'));
    instruccio.textContent = 'Desitja\'t alguna cosa... ✨';
    const pistes = (regal.pistes || []).filter(Boolean);
    carta.replaceChildren(
      el('p', { class: 'text' }, regal.missatgeAniversari || 'Per molts anys!'),
      pistes.length && el('div', { class: 'recull-pistes' },
        el('p', { class: 'text' }, 'Recordes les pistes?'),
        el('ol', {}, pistes.map((p) => el('li', {}, p))),
      ),
      el('p', { class: 'tancament' }, regal.tancament || 'La sorpresa final te la dono jo 🎁'),
    );
    carta.hidden = false;
    setTimeout(() => carta.scrollIntoView({ behavior: 'smooth', block: 'start' }), 600);
  }

  capa.replaceChildren(el('div', { class: 'dins' },
    el('span', { class: 'etiqueta-dia' }, '14 de desembre'),
    el('h2', {}, `Per molts anys${nom ? `, ${nom}` : ''}! 🎂`),
    instruccio,
    el('div', { class: 'pastis', 'aria-hidden': 'false' },
      el('div', { class: 'espelmes' }, espelmes),
      el('div', { class: 'pis dalt' }),
      el('div', { class: 'pis' }),
      el('div', { class: 'plat' }),
    ),
    carta,
    el('div', { class: 'accions' }, tanca),
  ));
  capa.hidden = false;
  capa.scrollTop = 0;
  if (!repetit) confeti(document.getElementById('confeti'), 1800);
}
