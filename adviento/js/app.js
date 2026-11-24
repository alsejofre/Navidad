// Punt d'entrada del calendari.
import { avui, diaObert, diesQueFalten, magatzem, el, avisa, tremola } from './util.js';
import { derivaClau, desxifra, exportaClau, importaClau, deBase64 } from './xifrat.js';
import { iniciaNeu } from './efectes.js';
import { pintaDia, pintaCartera, obreAniversari, iconaDe, cartera } from './vistes.js';
import * as so from './so.js';

// Ordre de les caselles a la graella (barrejat però fix, perquè no canviï cada dia).
const ORDRE = [7, 19, 3, 14, 22, 11, 1, 16, 9, 24, 5, 12, 20, 2, 17, 8, 13, 23, 4, 18, 10, 6, 21, 15];

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const local = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
const modeProva = local && params.has('prova');

let cfg;
let contingut;
let hui;

async function inicia() {
  iniciaNeu($('neu'));
  cfg = await fetch('config.json', { cache: 'no-cache' }).then((r) => r.json());
  hui = avui(cfg.zona);

  if (modeProva) {
    // Només a localhost: ?prova=1 obre-ho tot; ?prova=1&dia=9 simula que avui és el 9.
    const dia = parseInt(params.get('dia'), 10);
    hui = dia ? { any: cfg.any, mes: cfg.mes, dia } : { any: cfg.any, mes: cfg.mes, dia: 31 };
    contingut = await fetch('contingut.exemple.json', { cache: 'no-cache' }).then((r) => r.json());
    return mostraCalendari();
  }

  const paquet = await fetch('contingut.enc.json', { cache: 'no-cache' }).then((r) => r.json());
  const desada = magatzem.llegeix('clau', null);
  if (desada && desada.salt === paquet.salt) {
    try {
      contingut = await desxifra(paquet, await importaClau(desada.clau));
      return mostraCalendari();
    } catch {
      magatzem.esborra('clau');
    }
  }
  mostraBloqueig(paquet);
}

function mostraBloqueig(paquet) {
  $('carregant').hidden = true;
  $('bloqueig').hidden = false;
  $('pregunta').textContent = cfg.pregunta;
  const form = $('form-bloqueig');
  const boto = form.querySelector('button');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    boto.disabled = true;
    boto.textContent = 'Comprovant...';
    $('error-bloqueig').textContent = '';
    try {
      const clau = await derivaClau($('resposta').value, deBase64(paquet.salt), paquet.iteracions);
      contingut = await desxifra(paquet, clau);
      magatzem.escriu('clau', { salt: paquet.salt, clau: await exportaClau(clau) });
      so.campaneta();
      $('bloqueig').hidden = true;
      mostraCalendari();
    } catch {
      so.error();
      $('error-bloqueig').textContent = 'Uix, no és això... 🙈 Torna-ho a provar!';
      tremola($('bloqueig'));
      boto.disabled = false;
      boto.textContent = 'Obrir 🎄';
    }
  });
  $('resposta').focus();
}

function missatgeAvui() {
  const n = hui.dia;
  const desembre = hui.any === cfg.any && hui.mes === cfg.mes;
  if (diesQueFalten(1, cfg, hui) > 0) {
    const f = diesQueFalten(1, cfg, hui);
    return `El calendari comença l'1 de desembre. Falten ${f} ${f === 1 ? 'dia' : 'dies'}! ⏳`;
  }
  if (!desembre || n > cfg.dies) return 'Bon Nadal! 🎄 Pots tornar a obrir totes les caselles.';
  if (n === cfg.diaAniversari) return 'Avui és un dia MOLT especial... 🎂';
  return `Avui és ${n} de desembre: toca obrir la casella ${n}! ✨`;
}

function mostraCalendari() {
  $('carregant').hidden = true;
  $('calendari').hidden = false;
  $('botons').hidden = false;
  if (contingut.nom) $('subtitol').textContent = `per a la ${contingut.nom} 💛`;
  $('missatge-avui').textContent = missatgeAvui();
  pintaGraella();
  actualitzaInsignia();

  $('obre-cartera').addEventListener('click', () => {
    pintaCartera(contingut, actualitzaInsignia);
    $('cartera').showModal();
  });
  $('musica').addEventListener('click', () => {
    const sona = so.canviaMusica();
    $('musica').textContent = sona ? '🎵' : '🔇';
    $('musica').setAttribute('aria-pressed', String(sona));
  });
  document.addEventListener('cartera', actualitzaInsignia);
}

function actualitzaInsignia() {
  const n = cartera.pendents();
  $('insignia').hidden = n === 0;
  $('insignia').textContent = n;
}

function pintaGraella() {
  const obertes = new Set(magatzem.llegeix('obertes', []));
  const graella = $('graella');
  graella.replaceChildren(...ORDRE.filter((n) => n <= cfg.dies).map((n, i) => {
    const potObrir = diaObert(n, cfg, hui);
    const oberta = obertes.has(n) && potObrir;
    const esAvui = n === hui.dia && hui.mes === cfg.mes && hui.any === cfg.any;
    const classes = ['porta', `c${i % 4}`];
    if (n === cfg.diaAniversari) classes.push('gran');
    if (oberta) classes.push('oberta');
    else if (!potObrir) classes.push('tancada');
    if (esAvui && !oberta) classes.push('avui');
    const icona = n === cfg.diaAniversari ? '🎂' : iconaDe(contingut.dies[String(n)]);
    return el('button', {
      class: classes.join(' '),
      'aria-label': `Dia ${n}${oberta ? ', obert' : potObrir ? '' : ', tancat'}`,
      onclick: (e) => obreCasella(n, e.currentTarget),
    }, oberta && el('span', { class: 'icona' }, icona), el('span', { class: 'num' }, n));
  }));
}

function obreCasella(n, boto) {
  if (!diaObert(n, cfg, hui)) {
    so.error();
    tremola(boto);
    const f = diesQueFalten(n, cfg, hui);
    avisa(f === 1 ? 'Paciència! Demà ja la podràs obrir 😉' : `Encara no! Falten ${f} dies ⏳`);
    return;
  }
  const obertes = new Set(magatzem.llegeix('obertes', []));
  const primeraVegada = !obertes.has(n);
  obertes.add(n);
  magatzem.escriu('obertes', [...obertes]);
  so.campaneta();

  if (n === cfg.diaAniversari) {
    obreAniversari(contingut, { repetit: !primeraVegada });
  } else {
    $('modal-contingut').replaceChildren(...pintaDia(n, contingut));
    $('modal').showModal();
    $('modal').scrollTop = 0;
  }
  if (primeraVegada) pintaGraella();
}

inicia().catch((err) => {
  console.error(err);
  $('carregant').textContent = 'Alguna cosa ha fallat carregant el calendari 😢 Torna a carregar la pàgina.';
});
