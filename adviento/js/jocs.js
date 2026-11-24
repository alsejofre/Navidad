// Minijocs: trivia, endevinalla i memory. Cada joc crida onFet() quan s'acaba.
import { el, barreja, tremola } from './util.js';
import { normalitza } from './xifrat.js';
import * as so from './so.js';

export function creaJoc(d, onFet) {
  const jocs = { trivia, endevinalla, memory };
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
