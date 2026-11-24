// Minijocs: trivia, endevinalla, memory i sopa de lletres.
// Cada joc crida onFet() si es guanya i onPerd() si es perd (aleshores toca càstig).
import { el, barreja, tremola } from './util.js';
import { normalitza } from './xifrat.js';
import * as so from './so.js';

export function creaJoc(d, onFet, onPerd = () => {}) {
  const jocs = { trivia, endevinalla, memory, sopa };
  const crea = jocs[d.joc];
  if (!crea) return el('p', { class: 'buit' }, `(Joc desconegut: ${d.joc})`);
  return el('div', { class: 'joc' }, crea(d, onFet, onPerd));
}

function trivia(d, onFet, onPerd) {
  const caixa = el('div');
  let i = 0;
  let encerts = 0;

  function pregunta() {
    const p = d.preguntes[i];
    const retro = el('p', { class: 'retroaccio' });
    const opcions = p.opcions.map((text, j) => el('button', {
      class: 'opcio',
      onclick: () => {
        opcions.forEach((b) => { b.disabled = true; });
        if (j === p.correcta) {
          encerts++;
          opcions[j].classList.add('be');
          retro.className = 'retroaccio be';
          retro.textContent = p.be || 'Correcte! 🎉';
          so.campaneta();
        } else {
          opcions[j].classList.add('malament');
          opcions[p.correcta].classList.add('be');
          retro.className = 'retroaccio malament';
          retro.textContent = p.malament || 'Ui, no! 🙈';
          so.error();
        }
        setTimeout(() => {
          i++;
          if (i < d.preguntes.length) pregunta();
          else final();
        }, 1500);
      },
    }, text));
    caixa.replaceChildren(
      el('p', { class: 'progres' }, `Pregunta ${i + 1} de ${d.preguntes.length}`),
      el('p', { class: 'enunciat' }, p.q),
      el('div', { class: 'opcions' }, opcions),
      retro,
    );
  }

  function final() {
    const total = d.preguntes.length;
    const aprovat = encerts >= Math.ceil(total / 2);       // cal encertar-ne almenys la meitat
    if (aprovat) so.fanfarria(); else so.error();
    caixa.replaceChildren(el('p', { class: 'enunciat' },
      aprovat ? `Has encertat ${encerts} de ${total}! 🎉` : `Només ${encerts} de ${total}... 😬`));
    if (aprovat) onFet(); else onPerd();
  }

  pregunta();
  return caixa;
}

function endevinalla(d, onFet, onPerd) {
  const caixa = el('div');
  const respostes = (d.respostes || []).map(normalitza);
  const pistes = d.pistes || [];
  let pistesVistes = 0;
  let errors = 0;
  const input = el('input', { type: 'text', placeholder: 'La teva resposta', autocapitalize: 'off', 'aria-label': 'Resposta' });
  const retro = el('p', { class: 'retroaccio' });
  const llistaPistes = el('div');
  const rendicio = el('div', { class: 'accions', hidden: true }, el('button', {
    type: 'button',
    class: 'boto boto-secundari',
    onclick: () => {
      so.error();
      caixa.replaceChildren(el('p', { class: 'retroaccio malament' },
        `Era «${(d.respostes || [''])[0]}»! 🙈`));
      onPerd();
    },
  }, 'Em rendeixo 🏳️'));
  const botoPista = pistes.length ? el('button', {
    type: 'button',
    class: 'boto boto-or',
    onclick: () => {
      llistaPistes.append(el('p', { class: 'text' }, `💡 ${pistes[pistesVistes++]}`));
      if (pistesVistes >= pistes.length) botoPista.remove();
    },
  }, 'Una pista, sisplau') : null;

  const form = el('form', {
    onsubmit: (e) => {
      e.preventDefault();
      if (respostes.includes(normalitza(input.value))) {
        so.fanfarria();
        caixa.replaceChildren(el('p', { class: 'retroaccio be' }, d.be || 'Ho has endevinat! 🥳'));
        onFet();
      } else {
        so.error();
        retro.className = 'retroaccio malament';
        retro.textContent = d.malament || 'Nooo... torna-ho a provar 😜';
        tremola(input);
        if (++errors >= 3) rendicio.hidden = false;          // després de 3 errors, es pot rendir
      }
    },
  }, input, el('button', { class: 'boto', type: 'submit' }, 'Comprovar'));

  caixa.append(el('p', { class: 'enunciat text' }, d.pregunta), form, retro, llistaPistes);
  if (botoPista) caixa.append(el('div', { class: 'accions' }, botoPista));
  caixa.append(rendicio);
  return caixa;
}

function memory(d, onFet, onPerd) {
  const simbols = d.parelles || ['🎄', '🎁', '⛄', '🦌', '🍪', '❄️'];
  const cartes = barreja([...simbols, ...simbols]);
  let girades = [];
  let fetes = 0;
  let bloquejat = false;
  const intents = el('p', { class: 'progres' }, 'Troba les parelles!');
  let comptador = 0;

  const botons = cartes.map((s) => {
    const b = el('button', {
      class: 'carta',
      'aria-label': 'Carta',
      onclick: () => {
        if (bloquejat || b.classList.contains('girada') || b.classList.contains('feta')) return;
        b.classList.add('girada');
        girades.push(b);
        if (girades.length < 2) return;
        comptador++;
        intents.textContent = `Intents: ${comptador}`;
        const [a, c] = girades;
        girades = [];
        if (a.dataset.s === c.dataset.s) {
          a.classList.replace('girada', 'feta');
          c.classList.replace('girada', 'feta');
          so.campaneta();
          fetes++;
          if (fetes === simbols.length) {
            setTimeout(() => {
              const limit = d.maxIntents || simbols.length * 3;
              if (comptador <= limit) {
                so.fanfarria();
                intents.textContent = `Fet en ${comptador} intents! 🎉`;
                onFet();
              } else {
                so.error();
                intents.textContent = `${comptador} intents... massa! (el màxim era ${limit}) 😜`;
                onPerd();
              }
            }, 400);
          }
        } else {
          bloquejat = true;
          setTimeout(() => {
            a.classList.remove('girada');
            c.classList.remove('girada');
            bloquejat = false;
          }, 800);
        }
      },
    }, s);
    b.dataset.s = s;
    return b;
  });
  return el('div', {}, intents, el('div', { class: 'memory' }, botons));
}

// ---------- Sopa de lletres ----------
// Colors pastel nadalencs, mats i suaus, un per paraula trobada.
const PASTELS = [
  '#b9d3b0', // verd sàlvia
  '#e8b9bc', // rosa empolvat
  '#ecd9a6', // daurat mantega
  '#bcd0e0', // blau boira
  '#d2bfdc', // lila
  '#f0cbb0', // préssec
  '#bfdcd2', // menta
  '#dcaeae', // vermell pàl·lid
  '#d8c6aa', // galeta
  '#b3d0cc', // verd aigua
];

// Paraules en horitzontal, vertical i diagonal (també del revés). Graella fixa per a cada dia
// (llavor = paraules), perquè si es torna a obrir surti igual.
function sopa(d, onFet) {
  const paraules = d.paraules.map((p) => normalitza(p).replace(/[^a-z]/g, '').toUpperCase());
  const mida = Math.max(10, ...paraules.map((p) => p.length + 1));
  let llavor = [...paraules.join('')].reduce((a, c) => (Math.imul(a, 31) + c.charCodeAt(0)) >>> 0, 7);
  const atzar = () => {                                        // mulberry32
    llavor = (llavor + 0x6D2B79F5) >>> 0;
    let t = llavor;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const H = [[0, 1]], V = [[1, 0]], D = [[1, 1], [-1, 1]];
  // Repartiment: sobretot horitzontals, algunes verticals i un parell de diagonals
  const PATRO = [H, H, V, D, H, V, D, H, H, V];
  const totes = [...H, ...V, ...D];
  let graella;
  let posicions;

  for (let intent = 0; intent < 200; intent++) {
    graella = Array.from({ length: mida }, () => Array(mida).fill(''));
    posicions = {};
    const ordenades = [...paraules].sort((a, b) => b.length - a.length);
    const ok = ordenades.every((p, n) => {
      const permeses = intent < 150 ? PATRO[n % PATRO.length] : totes;
      for (let k = 0; k < 300; k++) {
        const [dy, dx] = permeses[Math.floor(atzar() * permeses.length)];
        const y0 = Math.floor(atzar() * mida);
        const x0 = Math.floor(atzar() * mida);
        const y1 = y0 + dy * (p.length - 1);
        const x1 = x0 + dx * (p.length - 1);
        if (y1 < 0 || y1 >= mida || x1 < 0 || x1 >= mida) continue;
        let cap = true;
        for (let i = 0; i < p.length; i++) {
          const c = graella[y0 + dy * i][x0 + dx * i];
          if (c && c !== p[i]) { cap = false; break; }
        }
        if (!cap) continue;
        for (let i = 0; i < p.length; i++) graella[y0 + dy * i][x0 + dx * i] = p[i];
        posicions[p] = [y0, x0, y1, x1];
        return true;
      }
      return false;
    });
    if (ok) break;
  }
  const abc = 'ABCDEFGHIJLMNOPRSTUVXYZ';
  for (const fila of graella) for (let x = 0; x < mida; x++) if (!fila[x]) fila[x] = abc[Math.floor(atzar() * abc.length)];

  const trobades = new Set();
  let inici = null;
  const caselles = [];
  const taula = el('div', { class: 'sopa', style: `--mida:${mida}` });
  graella.forEach((fila, y) => fila.forEach((c, x) => {
    const b = el('button', { class: 'lletra', type: 'button', 'aria-label': `${c}, fila ${y + 1}, columna ${x + 1}`, onclick: () => tria(y, x) }, c);
    caselles.push(b);
    taula.append(b);
  }));
  const llista = el('ul', { class: 'paraules-sopa' }, d.paraules.map((p, i) => el('li', { 'data-p': paraules[i] }, p)));
  const cel = (y, x) => caselles[y * mida + x];

  function tria(y, x) {
    if (!inici) {
      inici = [y, x];
      cel(y, x).classList.add('marcada');
      return;
    }
    const [y0, x0] = inici;
    cel(y0, x0).classList.remove('marcada');
    inici = null;
    const trobada = Object.entries(posicions).find(([p, [a, b, c, e]]) =>
      !trobades.has(p) && ((a === y0 && b === x0 && c === y && e === x) || (c === y0 && e === x0 && a === y && b === x)));
    if (!trobada) {
      if (y !== y0 || x !== x0) { so.error(); tremola(taula); }
      return;
    }
    const [p, [a, b, c, e]] = trobada;
    trobades.add(p);
    const color = PASTELS[paraules.indexOf(p) % PASTELS.length];
    const dy = Math.sign(c - a), dx = Math.sign(e - b);
    for (let i = 0; i < p.length; i++) {
      const lletra = cel(a + dy * i, b + dx * i);
      lletra.classList.add('trobada');
      lletra.style.setProperty('--c', color);
    }
    const li = llista.querySelector(`[data-p="${p}"]`);
    li.classList.add('feta');
    li.style.setProperty('--c', color);
    so.campaneta();
    if (trobades.size === paraules.length) {
      so.fanfarria();
      onFet();
    }
  }

  return el('div', {}, el('p', { class: 'progres' }, 'Toca la primera i l\'última lletra de cada paraula.'), taula, llista);
}
