#!/usr/bin/env node
// Ús:
//   node herramientas/xifrar.mjs                 → xifra privado/contingut.json
//   node herramientas/xifrar.mjs --exemple       → xifra adviento/contingut.exemple.json amb la clau «prova»
//   NAVIDAD_CLAU="resposta" node herramientas/xifrar.mjs   → sense pregunta interactiva
//   --nou-salt   → genera un salt nou (ella haurà de tornar a escriure la resposta)
//
// Abans de xifrar:
//   · "ascii": "dibujos/x.txt"  → s'hi posa el contingut de taller-ascii/dibujos/x.txt
//   · "foto": "fotos/x.jpg"     → s'hi incrusta privado/fotos/x.jpg com a data: URL
// Resultat: adviento/contingut.enc.json (és l'únic fitxer amb contingut que es puja).

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline/promises';
import { xifra, desxifra, derivaClau, deBase64 } from '../adviento/js/xifrat.js';

const arrel = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = new Set(process.argv.slice(2));
const exemple = args.has('--exemple');
const entrada = exemple ? join(arrel, 'adviento/contingut.exemple.json') : join(arrel, 'privado/contingut.json');
const sortida = join(arrel, 'adviento/contingut.enc.json');
const TIPUS = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif' };

if (!existsSync(entrada)) {
  console.error(`No trobo ${entrada}. Copia adviento/contingut.exemple.json a privado/contingut.json i edita'l.`);
  process.exit(1);
}

const contingut = JSON.parse(readFileSync(entrada, 'utf8'));
let mida = 0;
for (const [n, d] of Object.entries(contingut.dies || {})) {
  if (typeof d.ascii === 'string' && d.ascii.endsWith('.txt')) {
    d.ascii = readFileSync(join(arrel, 'taller-ascii', d.ascii), 'utf8').replace(/\n$/, '');
  }
  if (typeof d.foto === 'string' && !d.foto.startsWith('data:')) {
    const ruta = join(arrel, 'privado', d.foto);
    const tipus = TIPUS[extname(ruta).toLowerCase()];
    if (!tipus) throw new Error(`Dia ${n}: format de foto no suportat (${d.foto})`);
    const bytes = readFileSync(ruta);
    mida += bytes.length;
    d.foto = `data:${tipus};base64,${bytes.toString('base64')}`;
  }
}
if (mida > 8e6) console.warn(`⚠️  Les fotos ocupen ${(mida / 1e6).toFixed(1)} MB: redueix-les (≈1200 px d'ample) perquè carregui ràpid al mòbil.`);

let resposta = exemple ? 'prova' : process.env.NAVIDAD_CLAU;
if (!resposta) {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  resposta = await rl.question('Resposta a la pregunta (la clau): ');
  rl.close();
}
if (!resposta.trim()) { console.error('Resposta buida.'); process.exit(1); }

// Si ja existeix un fitxer xifrat, reaprofitem el salt: així, si la resposta no canvia,
// ella no ha de tornar a escriure-la cada vegada que actualitzem el contingut.
let salt;
if (!args.has('--nou-salt') && existsSync(sortida)) {
  salt = JSON.parse(readFileSync(sortida, 'utf8')).salt;
}

const paquet = await xifra(contingut, resposta, salt);
// Comprovació: es pot tornar a desxifrar?
const torna = await desxifra(paquet, await derivaClau(resposta, deBase64(paquet.salt), paquet.iteracions));
if (JSON.stringify(torna) !== JSON.stringify(contingut)) throw new Error('La comprovació del xifrat ha fallat');

writeFileSync(sortida, JSON.stringify(paquet) + '\n');
console.log(`✓ ${Object.keys(contingut.dies || {}).length} dies xifrats → adviento/contingut.enc.json (${(JSON.stringify(paquet).length / 1024).toFixed(0)} KB)`);
