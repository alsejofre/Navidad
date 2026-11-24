// Xifrat compartit entre el navegador i herramientas/xifrar.mjs (Node ≥ 20).
// AES-GCM 256 amb clau derivada per PBKDF2-SHA256 a partir de la resposta normalitzada.

export const ITERACIONS = 310000;

const codifica = new TextEncoder();
const descodifica = new TextDecoder();

/** Minúscules, sense accents i sense espais de més: «  Bítxo » → «bitxo». */
export function normalitza(text) {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export function aBase64(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = '';
  for (let i = 0; i < b.length; i += 0x8000) {
    s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  }
  return btoa(s);
}

export function deBase64(text) {
  const s = atob(text);
  const b = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i);
  return b;
}

export async function derivaClau(resposta, salt, iteracions = ITERACIONS) {
  const base = await crypto.subtle.importKey(
    'raw', codifica.encode(normalitza(resposta)), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations: iteracions },
    base,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt']);
}

export async function exportaClau(clau) {
  return aBase64(await crypto.subtle.exportKey('raw', clau));
}

export function importaClau(base64) {
  return crypto.subtle.importKey('raw', deBase64(base64), 'AES-GCM', true, ['encrypt', 'decrypt']);
}

/** Retorna el paquet que es publica: { v, salt, iteracions, iv, dades }. */
export async function xifra(objecte, resposta, saltBase64) {
  const salt = saltBase64 ? deBase64(saltBase64) : crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const clau = await derivaClau(resposta, salt);
  const dades = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv }, clau, codifica.encode(JSON.stringify(objecte)));
  return { v: 1, salt: aBase64(salt), iteracions: ITERACIONS, iv: aBase64(iv), dades: aBase64(dades) };
}

/** Llança una excepció si la clau no és correcta. */
export async function desxifra(paquet, clau) {
  const dades = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: deBase64(paquet.iv) }, clau, deBase64(paquet.dades));
  return JSON.parse(descodifica.decode(dades));
}
