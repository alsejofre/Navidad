#!/usr/bin/env python3
"""Uso: python3 arbre_giratori.py [--sense-color] [--fps 15] [--missatge "Bon Nadal!"] [--sense-intro] [--fotograma N]

Árbol de Navidad ASCII que crece desde el suelo, se le pone la estrella y los adornos,
caen los regalos y luego gira sobre sí mismo para siempre. Ctrl+C para salir.

Cómo funciona el giro: el árbol es un cono en 3D. Cada carácter de la copa es un punto de
la superficie del cono; se calcula su ángulo y se le resta la rotación actual. Así la
textura de las ramas, el espumillón en espiral y las bolas se desplazan de lado a lado y
las bolas de detrás desaparecen.

--fotograma N  imprime solo el fotograma N, sin color, y sale (útil para copiar un dibujo
               a taller-ascii/dibujos/ o para probar).
"""
import argparse
import math
import random
import shutil
import sys
import time

ASPECTE = 2.0          # un carácter es el doble de alto que de ancho
VEL_GIR = 0.11         # radianes por fotograma
TAU = 2 * math.pi

# Fases (en fotogramas)
F_TRONC = 10
F_CREIX = 45
F_ESTEL = 15
F_DECO = 40
F_REGALS = 35


def limita(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def suau(p):
    """Easing de salida cúbico."""
    p = limita(p)
    return 1 - (1 - p) ** 3


def rebot(p):
    """Caída con un pequeño rebote al final."""
    p = limita(p)
    if p < 0.75:
        return (p / 0.75) ** 2
    q = (p - 0.75) / 0.25
    return 1 - 0.12 * math.sin(q * math.pi)


# ---------------------------------------------------------------- Llenç

class Llenc:
    """Cuadrícula de caracteres con color de texto y de fondo (ANSI de 256 colores)."""

    def __init__(self, amplada, alcada):
        self.w, self.h = amplada, alcada
        self.car = [[' '] * amplada for _ in range(alcada)]
        self.col = [[(None, None)] * amplada for _ in range(alcada)]

    def posa(self, x, y, c, fg=None, bg=None):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.car[y][x] = c
            self.col[y][x] = (fg, bg)

    def text(self, x, y, s, fg=None, bg=None, transparent=True):
        for i, c in enumerate(s):
            if c == ' ' and transparent:
                continue
            self.posa(x + i, y, c, fg, bg)

    def pinta(self, color=True):
        linies = []
        for y in range(self.h):
            tros = []
            ultim = (None, None)
            for x in range(self.w):
                c = self.col[y][x] if color else (None, None)
                if c != ultim:
                    fg, bg = c
                    codi = '\x1b[0m'
                    if fg is not None:
                        codi += f'\x1b[38;5;{fg}m'
                    if bg is not None:
                        codi += f'\x1b[48;5;{bg}m'
                    tros.append(codi)
                    ultim = c
                tros.append(self.car[y][x])
            if color:
                tros.append('\x1b[0m')
            linies.append(''.join(tros).rstrip() if not color else ''.join(tros))
        return '\n'.join(linies)


# ---------------------------------------------------------------- Escena

VERDS = [22, 28, 34, 40, 41]                   # del fons (fosc) al davant (clar)
COLORS_BOLES = [196, 33, 220, 201, 231, 208]   # vermell, blau, or, rosa, blanc, taronja
COLORS_LLUMS = [226, 51, 213, 118, 214]
CAIXES = [  # (color del paper com a fons, color de la cinta)
    (124, 226),
    (25, 231),
    (30, 220),
    (127, 51),
    (94, 196),
]


class Escena:
    def __init__(self, amplada, alcada, missatge, llavor=24):
        self.W, self.H = amplada, alcada
        self.missatge = missatge
        self.cx = amplada // 2
        self.y_terra = alcada - 3
        self.alt_tronc = 3
        self.y_base = self.y_terra - self.alt_tronc - 1      # última fila de la copa
        self.N = max(6, min(26, self.y_base - 4))            # files de la copa
        self.R = min(self.N * 0.5, (amplada / 2 - 3) / ASPECTE)

        rng = random.Random(llavor)
        self.adorns = []
        for _ in range(int(self.N * 2.6)):
            llum = rng.random() < 0.55
            self.adorns.append({
                'h': rng.uniform(0.15, 0.97),
                'a': rng.uniform(0, TAU),
                'llum': llum,
                'color': rng.choice(COLORS_LLUMS if llum else COLORS_BOLES),
                'fase': rng.randrange(12),
                'ordre': rng.random(),
            })

        # Regals a banda i banda del tronc, sense trepitjar-se: (amplada, alçada del cos)
        self.regals = []
        costats = [(-1, [(7, 3), (9, 2)]), (1, [(8, 2), (10, 3)])]
        n = 0
        for signe, caixes in costats:
            vora = self.cx - 4 if signe < 0 else self.cx + 4
            for w, h in caixes:
                x = vora - w if signe < 0 else vora
                vora = x - 1 if signe < 0 else x + w + 1
                if x < 0 or x + w > amplada:
                    continue
                paper, cinta = CAIXES[n % len(CAIXES)]
                self.regals.append({'x': x, 'w': w, 'h': h, 'paper': paper, 'cinta': cinta, 'retard': n * 7})
                n += 1

        rng_neu = random.Random(llavor + 1)
        self.neu_terra = [rng_neu.random() < 0.25 for _ in range(amplada)]

    # Radi del con a l'alçada relativa h (0 = punta, 1 = base), amb «pisos» de branques.
    def radi(self, h):
        pisos = 3
        t = h * pisos - math.floor(h * pisos - 1e-9)   # 0..1 dins de cada pis (la base val 1)
        return self.R * (0.12 + 0.88 * h) * (0.78 + 0.22 * t)

    def fotograma(self, t, sense_intro=False):
        if sense_intro:
            t += F_TRONC + F_CREIX + F_ESTEL + F_DECO + F_REGALS + 20
        ll = Llenc(self.W, self.H)
        fi = t * VEL_GIR

        p_tronc = suau(t / F_TRONC)
        p_creix = suau((t - F_TRONC + 2) / F_CREIX)
        t0 = F_TRONC + F_CREIX
        p_estel = limita((t - t0) / F_ESTEL)
        t1 = t0 + F_ESTEL
        p_deco = limita((t - t1) / F_DECO)
        t2 = t1 + F_DECO
        t3 = t2 + F_REGALS

        self._terra(ll)
        self._tronc(ll, p_tronc, fi)
        if p_creix > 0:
            files = self._copa(ll, p_creix, fi, p_deco, t)
            if p_estel > 0:
                self._estel(ll, p_estel, fi, t, self.y_base - files)
        self._regals(ll, t - t2)
        if t > t3:
            self._missatge(ll, t - t3)
        return ll

    def _terra(self, ll):
        for x in range(self.W):
            c = '*' if self.neu_terra[x] else '~'
            ll.posa(x, self.y_terra, c, 255 if self.neu_terra[x] else 252)

    def _tronc(self, ll, p, fi):
        files = int(round(self.alt_tronc * p))
        amp = 2
        for j in range(files):
            y = self.y_terra - 1 - j
            for x in range(-amp, amp + 1):
                u = x / (amp + 0.5)
                a = math.asin(limita(u, -1, 1)) - fi
                c = '|' if abs(x) == amp else ('#' if math.sin(a * 3) > 0 else '=')
                ll.posa(self.cx + x, y, c, 94 if abs(x) == amp else 130)

    def _copa(self, ll, p, fi, p_deco, t):
        files = max(1, int(round(self.N * p)))
        y_dalt = self.y_base - files + 1
        mides = []
        for j in range(files):
            h = (j + 1) / files
            r = self.radi(h) * (0.35 + 0.65 * p)
            hw = r * ASPECTE
            mides.append(hw)
            y = y_dalt + j
            n = int(hw)
            for x in range(-n, n + 1):
                u = x / (hw + 0.5)
                theta = math.asin(limita(u, -1, 1))
                a = theta - fi
                fondaria = math.cos(theta)           # 1 = davant, 0 = vora
                if x == -n:
                    c = '/'
                elif x == n:
                    c = '\\'
                else:
                    v = math.sin(a * 6 + h * 14)
                    c = '*' if v > 0.75 else ('^' if v > -0.4 else '"')
                tint = VERDS[int(limita(fondaria * 0.75 + (0.25 if c == '*' else 0), 0, 0.999) * len(VERDS))]
                ll.posa(self.cx + x, y, c, tint)

                # Garlanda en espiral: es dibuixa de dalt a baix a mesura que avança p_deco.
                if p_deco > 0 and h <= p_deco * 1.05 and abs(x) < n:
                    g = (a + h * TAU * 2.2) % TAU
                    if g < 0.45:
                        ll.posa(self.cx + x, y, '~' if fondaria > 0.4 else '-', 220 if fondaria > 0.5 else 178)

        # Adorns: només els de la cara de davant.
        if p_deco > 0:
            for o in self.adorns:
                if o['ordre'] > p_deco:
                    continue
                local = o['a'] + fi
                davant = math.cos(local)
                if davant < 0.15:
                    continue
                j = min(files - 1, max(0, int(round(o['h'] * files)) - 1))
                x = math.sin(local) * mides[j] * 0.88
                if o['llum']:
                    encesa = (t + o['fase']) % 12 < 8
                    c, col = ('*', o['color']) if encesa else ('.', 240)
                else:
                    c, col = ('O' if davant > 0.75 else 'o'), o['color']
                ll.posa(self.cx + x, y_dalt + j, c, col)
        return files

    def _estel(self, ll, p, fi, t, y_punta):
        y = y_punta - 1
        brilla = 226 if (t // 3) % 2 else 228
        if p < 0.35:
            ll.posa(self.cx, y, '.', brilla)
            return
        if p < 0.7:
            ll.posa(self.cx, y, '+', brilla)
            return
        cara = abs(math.cos(fi))   # l'estrella també gira: de cara és ampla, de cantó és prima
        if cara > 0.6:
            dibuix = [' \\|/ ', '--*--', ' /|\\ ']
        elif cara > 0.25:
            dibuix = ['  |  ', ' -*- ', '  |  ']
        else:
            dibuix = ['  |  ', '  *  ', '  |  ']
        for k, fila in enumerate(dibuix):
            ll.text(self.cx - 2, y - 1 + k, fila, brilla)
        ll.posa(self.cx, y, '*', 231 if (t // 2) % 3 == 0 else brilla)

    def _regals(self, ll, t):
        if t < 0:
            return
        for r in self.regals:
            p = (t - r['retard']) / 14
            if p <= 0:
                continue
            alt_total = r['h'] + 1          # cos + llaç
            y_final = self.y_terra - alt_total
            y = int(round(-alt_total + (y_final + alt_total) * rebot(p)))
            self._caixa(ll, r, y)

    def _caixa(self, ll, r, y):
        x, w, h = r['x'], r['w'], r['h']
        mig = x + w // 2
        ll.text(mig - 1, y, '\\/', r['cinta'])                    # llaç
        for k in range(h):
            fila = y + 1 + k
            for i in range(w):
                xx = x + i
                if xx == mig:
                    ll.posa(xx, fila, '|', r['cinta'], r['paper'])
                elif k == h // 2:
                    ll.posa(xx, fila, '=', r['cinta'], r['paper'])
                elif i in (0, w - 1):
                    ll.posa(xx, fila, '|', 16, r['paper'])
                else:
                    ll.posa(xx, fila, ' ', None, r['paper'])

    def _missatge(self, ll, t):
        m = self.missatge
        n = min(len(m), t // 2)
        x0 = self.cx - len(m) // 2
        colors = [196, 220, 46, 231]
        for i, c in enumerate(m[:n]):
            ll.posa(x0 + i, self.H - 1, c, colors[(i + t // 4) % len(colors)])


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description='Árbol de Navidad ASCII giratorio.')
    ap.add_argument('--sense-color', action='store_true', help='sin colores ANSI')
    ap.add_argument('--fps', type=float, default=15)
    ap.add_argument('--missatge', default='Bon Nadal, Bitxo!')
    ap.add_argument('--sense-intro', action='store_true', help='empieza directamente girando')
    ap.add_argument('--fotograma', type=int, help='imprime solo este fotograma y sale')
    ap.add_argument('--mida', help='AMPLADAxALÇADA, p. ej. 80x30 (por defecto, la terminal)')
    args = ap.parse_args()

    def mida():
        if args.mida:
            w, h = args.mida.lower().split('x')
            return int(w), int(h)
        s = shutil.get_terminal_size((80, 30))
        return s.columns, s.lines - 1

    if args.fotograma is not None:
        w, h = mida()
        print(Escena(w, h, args.missatge).fotograma(args.fotograma, args.sense_intro).pinta(color=False))
        return

    color = not args.sense_color and sys.stdout.isatty()
    sys.stdout.write('\x1b[?1049h\x1b[?25l')   # pantalla alternativa, cursor amagat
    try:
        actual = None
        escena = None
        t = 0
        pausa = 1 / args.fps
        while True:
            inici = time.monotonic()
            m = mida()
            if m != actual:                          # la terminal ha canviat de mida
                actual = m
                escena = Escena(*m, args.missatge)
                sys.stdout.write('\x1b[2J')
            sys.stdout.write('\x1b[H' + escena.fotograma(t, args.sense_intro).pinta(color))
            sys.stdout.flush()
            t += 1
            time.sleep(max(0, pausa - (time.monotonic() - inici)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
