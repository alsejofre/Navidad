// Minijocs: trivia, endevinalla i memory. Cada joc crida onFet() quan s'acaba.
import { el, barreja, tremola } from './util.js';
import { normalitza } from './xifrat.js';
import * as so from './so.js';

export function creaJoc(d, onFet) {
  const jocs = { trivia, endevinalla, memory, sopa };
  const crea = jocs[d.joc];
  if (!crea) return el('p', { class: 'buit' }, `(Joc desconegut: ${d.joc})`);
  return el('div', { class: 'joc' }, crea(d, onFet));
}

function trivia(d, onFet) {
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
    so.fanfarria();
    caixa.replaceChildren(
      el('p', { class: 'enunciat' }, `Has encertat ${encerts} de ${d.preguntes.length}!`),
    );
    onFet();
  }

  pregunta();
  return caixa;
}

function endevinalla(d, onFet) {
  const caixa = el('div');
  const respostes = (d.respostes || []).map(normalitza);
  const pistes = d.pistes || [];
  let pistesVistes = 0;
  const input = el('input', { type: 'text', placeholder: 'La teva resposta', autocapitalize: 'off', 'aria-label': 'Resposta' });
  const retro = el('p', { class: 'retroaccio' });
  const llistaPistes = el('div');
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
      }
    },
  }, input, el('button', { class: 'boto', type: 'submit' }, 'Comprovar'));

  caixa.append(el('p', { class: 'enunciat text' }, d.pregunta), form, retro, llistaPistes);
  if (botoPista) caixa.append(el('div', { class: 'accions' }, botoPista));
  return caixa;
}

function memory(d, onFet) {
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
              so.fanfarria();
              intents.textContent = `Fet en ${comptador} intents! 🎉`;
              onFet();
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
// Paraules en horitzontal, vertical i diagonal (també del revés). Graella fixa per a cada dia
// (llavor = paraules), perquè si es torna a obrir surti igual.
function sopa(d, onFet) {
  const paraules = d.paraules.map((p) => normalitza(p).replace(/[^a-z]/g, '').toUpperCase());
  const mida = Math.max(10, ...paraules.map((p) => p.length + 1));
  let llavor = [...paraules.join('')].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  const atzar = () => ((llavor = (llavor * 1664525 + 1013904223) >>> 0) / 2 ** 32);
  const dirs = [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]];
  let graella;
  let posicions;

  for (let intent = 0; intent < 200; intent++) {
    graella = Array.from({ length: mida }, () => Array(mida).fill(''));
    posicions = {};
    const ordenades = [...paraules].sort((a, b) => b.length - a.length);
    const ok = ordenades.every((p) => {
      for (let k = 0; k < 300; k++) {
        const [dy, dx] = dirs[Math.floor(atzar() * (intent < 100 ? 4 : 8))];
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
    const dy = Math.sign(c - a), dx = Math.sign(e - b);
    for (let i = 0; i < p.length; i++) cel(a + dy * i, b + dx * i).classList.add('trobada');
    llista.querySelector(`[data-p="${p}"]`).classList.add('feta');
    so.campaneta();
    if (trobades.size === paraules.length) {
      so.fanfarria();
      onFet();
    }
  }

  return el('div', {}, el('p', { class: 'progres' }, 'Toca la primera i l\'última lletra de cada paraula.'), taula, llista);
}
