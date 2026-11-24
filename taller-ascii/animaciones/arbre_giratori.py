#!/usr/bin/env python3
"""Uso: python3 arbre_giratori.py [--fps 20] [--missatge "Bon Nadal!"] [--sense-intro] [--mida 140x50]
                                  [--qualitat 1.0] [--256] [--gif sortida.gif --segons 18]

Árbol de Navidad 3D en ASCII sobre fondo negro. Crece desde el suelo rama a rama, le ponen
la estrella, el espumillón, las bolas y las luces, caen los regalos y gira sobre sí mismo
mientras nieva. Ctrl+C para salir.

Requiere numpy (`pip install numpy`); para --gif también Pillow.

Cómo está hecho
  · Geometría: nube de puntos 3D. El árbol son ~250 ramas en verticilos (cada una cae y
    levanta la punta, con agujas en grupos), más tronco, bolas, espumillón, luces, estrella,
    regalos, suelo nevado y copos.
  · Cámara en perspectiva y z-buffer a resolución de SUBPÍXEL: cada carácter son 2×4
    subpíxeles. Para cada celda se busca el carácter ASCII cuya forma (cobertura 2×4,
    precalculada con DejaVu Sans Mono) se parece más a lo que se ha pintado dentro. Así los
    contornos salen con / \\ _ ' , y no a escalones.
  · Luz: difusa + relleno + especular + contraluz + oclusión ambiental. Cada bombilla tiñe
    las agujas cercanas con su color (y se apaga cuando parpadea).
  · Resplandor (bloom): las luces y la estrella iluminan el fondo con un halo de color muy
    suave (color de fondo de la celda).

--qualitat 0.6   menos puntos si va lento en un ordenador antiguo (1.0 por defecto).
--256            256 colores para terminales sin truecolor (p. ej. Terminal.app antiguo).
--gif F          graba un GIF de --segons segundos en vez de animar en la terminal.
"""
import argparse
import math
import os
import shutil
import sys
import time

import numpy as np

TAU = 2 * math.pi
SX, SY = 2, 4                          # subpíxels per caràcter
VEL_GIR = 0.6                          # rad/s

# Pisos de l'arbre: (y base, y punta, radi base)
PISOS = [(0.55, 2.30, 1.72), (1.25, 2.95, 1.34), (1.95, 3.52, 0.98), (2.62, 4.05, 0.60)]
Y_PUNTA = 4.25
Y_ESTEL = 4.62
R_TERRA = 2.6

# Línia de temps (segons)
T_CREIX = (0.0, 4.0)
T_ESTEL = (3.8, 5.0)
T_GARLANDA = (4.8, 7.0)
T_BOLES = (5.4, 8.0)
T_LLUMS = (7.0, 8.4)
T_REGALS = (8.2, 11.0)
T_TEXT = 11.2
T_SENSE_INTRO = 13.5

# Càmera
DIST = 8.6
CAM_Y = 3.1
OBJECTIU_Y = 2.15


def _norm(v):
    v = np.asarray(v, dtype=float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


LLUM = _norm([-0.62, 0.62, -0.48])         # espai de càmera: x dreta, y amunt, z endavant
FARCIMENT = _norm([0.85, 0.05, -0.35])
VISTA = np.array([0.0, 0.0, -1.0])
MIG = _norm(LLUM + VISTA)

# Cobertura 2×4 de cada caràcter ASCII (files de dalt a baix, esquerra-dreta), 0..1.
GLIFS = {
    '!': (0.05, 0.06, 0.26, 0.32, 0.16, 0.19, 0.04, 0.05),
    '"': (0.10, 0.10, 0.33, 0.33, 0.00, 0.00, 0.00, 0.00),
    '#': (0.04, 0.10, 0.68, 0.81, 0.79, 0.71, 0.08, 0.05),
    '$': (0.01, 0.06, 0.63, 0.48, 0.35, 0.91, 0.14, 0.23),
    '%': (0.08, 0.00, 0.81, 0.32, 0.29, 0.79, 0.00, 0.14),
    '&': (0.17, 0.18, 0.68, 0.06, 0.67, 0.97, 0.17, 0.20),
    "'": (0.05, 0.05, 0.15, 0.18, 0.00, 0.00, 0.00, 0.00),
    '(': (0.00, 0.14, 0.32, 0.22, 0.43, 0.12, 0.02, 0.25),
    ')': (0.14, 0.00, 0.17, 0.37, 0.08, 0.47, 0.24, 0.04),
    '*': (0.04, 0.05, 0.53, 0.58, 0.04, 0.05, 0.00, 0.00),
    '+': (0.00, 0.00, 0.14, 0.17, 0.54, 0.59, 0.00, 0.00),
    ',': (0.00, 0.00, 0.00, 0.00, 0.11, 0.15, 0.24, 0.08),
    '-': (0.00, 0.00, 0.00, 0.00, 0.18, 0.19, 0.00, 0.00),
    '.': (0.00, 0.00, 0.00, 0.00, 0.12, 0.13, 0.05, 0.06),
    '/': (0.00, 0.11, 0.03, 0.52, 0.49, 0.06, 0.25, 0.00),
    '0': (0.17, 0.18, 0.66, 0.67, 0.68, 0.69, 0.12, 0.13),
    '1': (0.16, 0.10, 0.17, 0.51, 0.16, 0.60, 0.15, 0.21),
    '2': (0.26, 0.17, 0.08, 0.64, 0.51, 0.33, 0.20, 0.20),
    '3': (0.27, 0.17, 0.21, 0.68, 0.13, 0.68, 0.23, 0.13),
    '4': (0.00, 0.16, 0.37, 0.68, 0.54, 0.82, 0.00, 0.09),
    '5': (0.23, 0.21, 0.66, 0.34, 0.12, 0.66, 0.23, 0.11),
    '6': (0.13, 0.25, 0.78, 0.39, 0.65, 0.63, 0.12, 0.15),
    '7': (0.27, 0.27, 0.07, 0.62, 0.32, 0.27, 0.09, 0.00),
    '8': (0.19, 0.20, 0.64, 0.65, 0.68, 0.69, 0.15, 0.16),
    '9': (0.20, 0.18, 0.61, 0.65, 0.41, 0.79, 0.19, 0.10),
    ':': (0.00, 0.00, 0.17, 0.19, 0.12, 0.13, 0.05, 0.06),
    ';': (0.00, 0.00, 0.17, 0.19, 0.11, 0.15, 0.24, 0.08),
    '<': (0.00, 0.00, 0.24, 0.42, 0.46, 0.42, 0.00, 0.00),
    '=': (0.00, 0.00, 0.38, 0.39, 0.38, 0.39, 0.00, 0.00),
    '>': (0.00, 0.00, 0.41, 0.25, 0.41, 0.48, 0.00, 0.00),
    '?': (0.21, 0.20, 0.10, 0.63, 0.24, 0.18, 0.05, 0.04),
    '@': (0.01, 0.03, 0.61, 0.84, 0.80, 0.69, 0.33, 0.24),
    'A': (0.08, 0.09, 0.53, 0.54, 0.75, 0.76, 0.09, 0.09),
    'B': (0.26, 0.16, 0.76, 0.72, 0.69, 0.73, 0.19, 0.12),
    'C': (0.11, 0.29, 0.63, 0.07, 0.64, 0.13, 0.08, 0.22),
    'D': (0.27, 0.09, 0.63, 0.66, 0.67, 0.66, 0.20, 0.05),
    'E': (0.24, 0.27, 0.77, 0.39, 0.64, 0.14, 0.18, 0.21),
    'F': (0.22, 0.29, 0.74, 0.39, 0.59, 0.00, 0.09, 0.00),
    'G': (0.13, 0.27, 0.64, 0.13, 0.64, 0.75, 0.10, 0.20),
    'H': (0.12, 0.12, 0.78, 0.79, 0.59, 0.59, 0.09, 0.09),
    'I': (0.24, 0.24, 0.32, 0.36, 0.36, 0.41, 0.18, 0.18),
    'J': (0.14, 0.20, 0.03, 0.61, 0.17, 0.61, 0.23, 0.09),
    'K': (0.12, 0.14, 0.88, 0.46, 0.67, 0.64, 0.09, 0.10),
    'L': (0.12, 0.00, 0.59, 0.00, 0.64, 0.15, 0.17, 0.23),
    'M': (0.17, 0.17, 0.95, 0.96, 0.63, 0.64, 0.08, 0.08),
    'N': (0.16, 0.11, 0.98, 0.62, 0.59, 1.00, 0.08, 0.12),
    'O': (0.18, 0.19, 0.62, 0.62, 0.64, 0.64, 0.13, 0.14),
    'P': (0.24, 0.18, 0.64, 0.75, 0.71, 0.18, 0.09, 0.00),
    'Q': (0.18, 0.19, 0.62, 0.62, 0.64, 0.64, 0.13, 0.36),
    'R': (0.27, 0.13, 0.70, 0.72, 0.70, 0.63, 0.09, 0.09),
    'S': (0.18, 0.25, 0.74, 0.21, 0.18, 0.74, 0.20, 0.15),
    'T': (0.32, 0.33, 0.33, 0.39, 0.27, 0.32, 0.04, 0.05),
    'U': (0.12, 0.12, 0.59, 0.58, 0.62, 0.63, 0.14, 0.15),
    'V': (0.12, 0.12, 0.57, 0.57, 0.51, 0.52, 0.06, 0.06),
    'W': (0.11, 0.11, 0.74, 0.75, 0.85, 0.85, 0.09, 0.09),
    'X': (0.12, 0.12, 0.52, 0.55, 0.59, 0.59, 0.09, 0.09),
    'Y': (0.12, 0.12, 0.57, 0.58, 0.28, 0.32, 0.04, 0.05),
    'Z': (0.25, 0.31, 0.09, 0.67, 0.62, 0.23, 0.20, 0.24),
    '[': (0.13, 0.21, 0.42, 0.11, 0.42, 0.11, 0.23, 0.24),
    '\\': (0.11, 0.00, 0.54, 0.01, 0.11, 0.44, 0.00, 0.25),
    ']': (0.19, 0.14, 0.06, 0.47, 0.06, 0.47, 0.21, 0.26),
    '^': (0.08, 0.09, 0.37, 0.38, 0.00, 0.00, 0.00, 0.00),
    '_': (0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.44, 0.44),
    '`': (0.20, 0.01, 0.03, 0.06, 0.00, 0.00, 0.00, 0.00),
    'a': (0.00, 0.00, 0.30, 0.43, 0.68, 0.86, 0.18, 0.15),
    'b': (0.16, 0.00, 0.72, 0.46, 0.66, 0.61, 0.15, 0.16),
    'c': (0.00, 0.00, 0.37, 0.34, 0.61, 0.13, 0.08, 0.21),
    'd': (0.00, 0.16, 0.45, 0.74, 0.61, 0.66, 0.15, 0.16),
    'e': (0.00, 0.00, 0.42, 0.44, 0.81, 0.56, 0.11, 0.21),
    'f': (0.03, 0.33, 0.54, 0.49, 0.33, 0.20, 0.05, 0.03),
    'g': (0.00, 0.00, 0.45, 0.52, 0.63, 0.68, 0.38, 0.54),
    'h': (0.16, 0.00, 0.70, 0.46, 0.53, 0.54, 0.08, 0.08),
    'i': (0.06, 0.10, 0.33, 0.22, 0.29, 0.45, 0.19, 0.21),
    'j': (0.01, 0.15, 0.24, 0.33, 0.02, 0.51, 0.34, 0.30),
    'k': (0.16, 0.00, 0.57, 0.37, 0.71, 0.56, 0.08, 0.10),
    'l': (0.35, 0.03, 0.44, 0.09, 0.40, 0.24, 0.01, 0.17),
    'm': (0.00, 0.00, 0.62, 0.59, 0.69, 0.77, 0.10, 0.11),
    'n': (0.00, 0.00, 0.48, 0.46, 0.53, 0.54, 0.08, 0.08),
    'o': (0.00, 0.00, 0.44, 0.45, 0.62, 0.62, 0.13, 0.14),
    'p': (0.00, 0.00, 0.51, 0.46, 0.66, 0.61, 0.50, 0.16),
    'q': (0.00, 0.00, 0.44, 0.53, 0.61, 0.67, 0.14, 0.52),
    'r': (0.00, 0.00, 0.37, 0.41, 0.54, 0.00, 0.08, 0.00),
    's': (0.00, 0.00, 0.41, 0.28, 0.40, 0.61, 0.19, 0.14),
    't': (0.05, 0.00, 0.73, 0.32, 0.49, 0.17, 0.02, 0.18),
    'u': (0.00, 0.00, 0.32, 0.32, 0.58, 0.64, 0.15, 0.16),
    'v': (0.00, 0.00, 0.33, 0.33, 0.52, 0.53, 0.06, 0.06),
    'w': (0.00, 0.00, 0.33, 0.33, 0.82, 0.83, 0.09, 0.09),
    'x': (0.00, 0.00, 0.35, 0.35, 0.52, 0.54, 0.09, 0.09),
    'y': (0.00, 0.00, 0.33, 0.33, 0.49, 0.53, 0.46, 0.12),
    'z': (0.00, 0.00, 0.28, 0.51, 0.46, 0.30, 0.18, 0.19),
    '{': (0.02, 0.29, 0.24, 0.32, 0.50, 0.22, 0.09, 0.41),
    '|': (0.07, 0.08, 0.23, 0.27, 0.23, 0.27, 0.20, 0.24),
    '}': (0.28, 0.02, 0.27, 0.28, 0.18, 0.53, 0.39, 0.11),
    '~': (0.00, 0.00, 0.03, 0.00, 0.35, 0.39, 0.00, 0.00),
}
SIMBOLS = " .,'`-_:;~^\"=+*/\\|()<>!#%@&$o"
GLIF_CARS = np.array([c for c in SIMBOLS])
GLIF_MAT = np.array([GLIFS[c] if c != ' ' else (0,) * 8 for c in SIMBOLS], float)
GLIF_N2 = (GLIF_MAT ** 2).sum(1)
# Rampa per a cel·les plenes (textura uniforme), ordenada per densitat de tinta
RAMPA = np.array(list(".:-=+*#%@"))


def limita(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def fase(t, interval):
    a, b = interval
    return limita((t - a) / (b - a))


def suau(p):
    return 1 - (1 - limita(p)) ** 3


def elastic(p):
    p = limita(p)
    if p in (0.0, 1.0):
        return p
    return 1 + 2 ** (-9 * p) * math.sin((p * 9 - 0.75) * TAU / 3) * 0.55


def rebot(p):
    p = limita(p)
    if p < 0.7:
        return (p / 0.7) ** 2
    q = (p - 0.7) / 0.3
    return 1 - 0.15 * math.sin(q * math.pi)


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    p = np.asarray(p, float)
    return np.column_stack([p[:, 0] * c + p[:, 2] * s, p[:, 1], -p[:, 0] * s + p[:, 2] * c])


def radi_copa(y):
    """Radi aproximat de l'arbre (fins a les puntes de les branques) a l'alçada y."""
    y = np.asarray(y, float)
    r = np.zeros_like(y)
    for yb, yt, rb in PISOS:
        dins = (y >= yb - 0.15) & (y <= yt)
        r = np.where(dins, np.maximum(r, rb * np.clip((yt - y) / (yt - yb), 0, 1.05)), r)
    return r


# ---------------------------------------------------------------- Geometria

class Grup:
    """Punts amb normal, color, brillantor especular, emissió, oclusió ambiental..."""

    CAMPS = ('pos', 'nor', 'col', 'espec', 'emis', 'cull', 'ao', 'part', 'extra')

    def __init__(self, pos, nor, col, espec=0.0, emis=0.0, cull=True, ao=1.0, part=False):
        n = len(pos)
        self.pos = np.asarray(pos, float).reshape(n, 3)
        self.nor = np.asarray(nor, float).reshape(n, 3)
        self.col = np.broadcast_to(np.asarray(col, float), (n, 3)).copy()
        self.espec = np.broadcast_to(np.asarray(espec, float), (n,)).copy()
        self.emis = np.broadcast_to(np.asarray(emis, float), (n,)).copy()
        self.cull = np.broadcast_to(np.asarray(cull, bool), (n,)).copy()
        self.ao = np.broadcast_to(np.asarray(ao, float), (n,)).copy()
        self.part = np.broadcast_to(np.asarray(part, bool), (n,)).copy()   # partícula (neu)
        self.extra = np.zeros((n, 3))

    def copia(self, m=None, **canvis):
        g = Grup.__new__(Grup)
        for k in Grup.CAMPS:
            v = getattr(self, k)
            setattr(g, k, v if m is None else v[m])
        for k, v in canvis.items():
            setattr(g, k, np.broadcast_to(v, getattr(g, k).shape).copy() if k not in ('pos', 'nor', 'extra') else v)
        return g


def uneix(grups):
    grups = [g for g in grups if g is not None and len(g.pos)]
    g = Grup.__new__(Grup)
    for k in Grup.CAMPS:
        setattr(g, k, np.concatenate([getattr(x, k) for x in grups]))
    return g


def esfera(rng, centre, radi, dens, color, espec=1.0, emis=0.0, ao=1.0):
    n = max(16, int(4 * math.pi * radi ** 2 * dens * 1.4))
    d = _norm(rng.normal(size=(n, 3)))
    return Grup(np.asarray(centre, float) + d * radi, d, color, espec, emis, ao=ao)


def branca(rng, th, y0, llarg, dens, fr, ultim_pis):
    """Una branca d'avet: surt del tronc, cau i aixeca la punta; agulles en grups."""
    n = max(30, int(llarg * 0.62 * dens))
    t = rng.random(n) ** 0.55                                # més agulles cap a la punta
    rad = np.array([math.cos(th), 0, math.sin(th)])
    costat = np.array([-math.sin(th), 0, math.cos(th)])
    amunt = np.array([0.0, 1.0, 0.0])
    r = t * llarg
    y = y0 + 0.05 * llarg * t - 0.30 * llarg * t ** 2 + 0.16 * llarg * t ** 4
    eix = r[:, None] * rad + y[:, None] * amunt
    ample = (0.035 + 0.19 * t * (1.2 - 0.55 * t)) * min(1.0, 0.55 + llarg * 0.4)
    a = np.clip(rng.normal(0, 0.55, n), -1.2, 1.2)
    c = np.clip(rng.normal(0.1, 0.40, n), -1.0, 1.0)
    desp = (a[:, None] * costat + c[:, None] * amunt * 0.55) * ample[:, None]
    desp += rad * (rng.normal(0, 0.04, n) * (0.5 + t))[:, None]
    pos = eix + desp
    nor = _norm(rad * 0.75 + amunt * 0.55 + _norm(desp + 1e-6) * 0.85 + rng.normal(0, 0.28, (n, 3)))
    # Color: agulles fosques a dins, brots tendres més clars a la punta
    barreja = rng.random(n)
    fosc, clar, brot = np.array([0.03, 0.30, 0.11]), np.array([0.10, 0.62, 0.24]), np.array([0.40, 0.88, 0.38])
    col = fosc * (1 - barreja)[:, None] + clar * barreja[:, None]
    punta = (t > 0.86) & (rng.random(n) < 0.6)
    col[punta] = brot * (0.8 + 0.2 * rng.random(punta.sum()))[:, None]
    ao = (0.30 + 0.70 * t) * (0.55 + 0.45 * np.clip(c + 0.5, 0, 1))
    if not ultim_pis:
        ao *= 0.35 + 0.65 * fr                              # el pis de dalt fa ombra als verticils alts
    neu = (nor[:, 1] > 0.45) & (t > 0.45) & (rng.random(n) < 0.16 * t)
    col[neu] = [0.86, 0.90, 1.0]
    espec = np.where(neu, 0.7, 0.10)
    punta_pos = rad * llarg + amunt * (y0 + 0.05 * llarg - 0.30 * llarg + 0.16 * llarg)
    return Grup(pos, nor, col, espec, ao=ao), punta_pos, rad


def arbre(rng, dens):
    grups, puntes = [], []
    for k, (yb, yt, rb) in enumerate(PISOS):
        ultim = k == len(PISOS) - 1
        verticils = 4 if not ultim else 5
        for w in range(verticils):
            fr = (w + 0.75) / verticils
            yw = yt - fr * (yt - yb)
            llarg = rb * (yt - yw) / (yt - yb) * 1.08 + 0.10
            nb = int(6 + 8 * llarg)
            gir = rng.random() * TAU
            for b in range(nb):
                th = gir + b * TAU / nb + rng.normal(0, 0.13)
                g, p, d = branca(rng, th, yw + 0.12, llarg * rng.uniform(0.86, 1.06), dens, fr, ultim)
                grups.append(g)
                puntes.append((p, d, llarg))
        # nucli fosc (perquè pels forats es vegi verd fosc i no el fons)
        n = int(math.pi * rb * 0.55 * (yt - yb) * dens * 0.35)
        s = np.sqrt(rng.random(n))
        th = rng.random(n) * TAU
        rr = s * rb * 0.55
        pos = np.column_stack([rr * np.cos(th), yt - s * (yt - yb), rr * np.sin(th)])
        nor = _norm(np.column_stack([np.cos(th), np.full(n, 0.5), np.sin(th)]))
        grups.append(Grup(pos, nor, [0.02, 0.16, 0.06], 0.0, ao=0.25))
    # punta (guia) de l'arbre
    n = int(0.4 * dens)
    tt = rng.random(n)
    pos = np.column_stack([rng.normal(0, 0.03, n), PISOS[-1][1] + tt * (Y_PUNTA - PISOS[-1][1]), rng.normal(0, 0.03, n)])
    grups.append(Grup(pos, _norm(rng.normal(size=(n, 3)) + [0, 0.5, 0]), [0.10, 0.55, 0.22], 0.1))
    return uneix(grups), puntes


def tronc(rng, dens):
    radi, y1 = 0.20, 0.9
    n = int(TAU * radi * y1 * dens)
    th = rng.random(n) * TAU
    y = rng.random(n) * y1
    nor = np.column_stack([np.cos(th), np.zeros(n), np.sin(th)])
    escorça = 0.7 + 0.3 * np.sin(th * 11 + 3 * np.sin(y * 9))
    return Grup(nor * radi + np.column_stack([np.zeros(n), y, np.zeros(n)]), nor,
                np.array([0.36, 0.21, 0.10]) * escorça[:, None], 0.05, ao=0.6)


def terra(rng, dens):
    n = int(math.pi * R_TERRA ** 2 * dens * 0.30)
    r = R_TERRA * np.sqrt(rng.random(n))
    th = rng.random(n) * TAU
    pos = np.column_stack([r * np.cos(th), rng.normal(0, 0.01, n), r * np.sin(th)])
    nor = _norm(np.tile([0, 1.0, 0], (n, 1)) + rng.normal(0, 0.18, (n, 3)))
    ombra = 0.25 + 0.75 * np.clip((r - 0.3) / 1.8, 0, 1)
    vora = 1 - np.clip((r - R_TERRA * 0.7) / (R_TERRA * 0.3), 0, 1)
    col = np.array([0.55, 0.60, 0.75]) * (0.75 + 0.25 * rng.random(n))[:, None]
    brilla = rng.random(n) < 0.025
    return Grup(pos, nor, col, np.where(brilla, 2.0, 0.0), ao=0.42 * ombra * vora ** 1.5)


def caixa(rng, w, h, d, dens, paper, cinta):
    cares = [
        ((0, h, 0), (0, 1, 0), (w / 2, 0, 0), (0, 0, d / 2), True),
        ((0, h / 2, d / 2), (0, 0, 1), (w / 2, 0, 0), (0, h / 2, 0), False),
        ((0, h / 2, -d / 2), (0, 0, -1), (w / 2, 0, 0), (0, h / 2, 0), False),
        ((w / 2, h / 2, 0), (1, 0, 0), (0, 0, d / 2), (0, h / 2, 0), False),
        ((-w / 2, h / 2, 0), (-1, 0, 0), (0, 0, d / 2), (0, h / 2, 0), False),
    ]
    grups = []
    for c, nrm, u, v, dalt in cares:
        u, v = np.array(u, float), np.array(v, float)
        n = max(12, int(4 * np.linalg.norm(u) * np.linalg.norm(v) * dens * 1.3))
        a, b = rng.random(n) * 2 - 1, rng.random(n) * 2 - 1
        pos = np.asarray(c, float) + a[:, None] * u + b[:, None] * v
        es_cinta = (np.abs(a) < 0.12) | ((np.abs(b) < 0.12) if dalt else np.zeros(n, bool))
        col = np.where(es_cinta[:, None], np.asarray(cinta), np.asarray(paper) * (0.9 + 0.1 * rng.random(n))[:, None])
        ao = 0.9 if dalt else 0.75 + 0.25 * (b + 1) / 2         # més fosc a baix
        grups.append(Grup(pos, np.tile(nrm, (n, 1)), col, np.where(es_cinta, 1.0, 0.25), ao=ao))
    for dx in (-0.07, 0.07):
        grups.append(esfera(rng, (dx, h + 0.055, 0), 0.065, dens, cinta, 1.0))
    return uneix(grups)


def estel(rng, dens, r_ext=0.50, r_int=0.21, gruix=0.13):
    angles = np.pi / 2 + np.arange(10) * TAU / 10
    radis = np.where(np.arange(10) % 2 == 0, r_ext, r_int)
    vert = np.stack([np.cos(angles) * radis, np.sin(angles) * radis], 1)
    grups = []
    for signe in (1, -1):
        for i in range(10):
            a, b = vert[i], vert[(i + 1) % 10]
            n = max(10, int(abs(a[0] * b[1] - a[1] * b[0]) / 2 * dens * 2))
            u, v = rng.random(n), rng.random(n)
            fora = u + v > 1
            u[fora], v[fora] = 1 - u[fora], 1 - v[fora]
            p2 = u[:, None] * a + v[:, None] * b
            relleu = 1 - np.linalg.norm(p2, axis=1) / r_ext
            pos = np.column_stack([p2, signe * gruix / 2 * (0.3 + 0.7 * relleu)])
            # faceta plana per triangle (com una estrella de vidre tallada)
            mig = (a + b) / 2
            mig = mig / np.linalg.norm(mig)
            nrm = np.tile(_norm([mig[0] * 1.3, mig[1] * 1.3, signe * 1.0]), (n, 1))
            col = np.array([1.0, 0.80, 0.26]) * (0.85 + 0.15 * relleu)[:, None]
            grups.append(Grup(pos, nrm, col, 1.8, 0.12 + 0.25 * relleu))
    for i in range(10):
        a, b = vert[i], vert[(i + 1) % 10]
        llarg = np.linalg.norm(b - a)
        n = max(8, int(llarg * gruix * dens * 3))
        u = rng.random(n)
        z = (rng.random(n) - 0.5) * gruix * 0.35
        p2 = a + u[:, None] * (b - a)
        dirc = (b - a) / llarg
        nrm = np.tile([dirc[1], -dirc[0], 0.0], (n, 1))
        grups.append(Grup(np.column_stack([p2, z]), nrm, [1.0, 0.95, 0.65], 1.2, 1.0))
    return uneix(grups)


# ---------------------------------------------------------------- Escena

COLORS_BOLES = [(0.82, 0.05, 0.10), (0.95, 0.72, 0.18), (0.12, 0.30, 0.92), (0.82, 0.84, 0.90),
                (0.85, 0.18, 0.55), (0.55, 0.08, 0.72), (0.05, 0.62, 0.62)]
COLORS_LLUMS = [(1.0, 0.82, 0.50), (1.0, 0.82, 0.50), (1.0, 0.25, 0.20), (0.30, 1.0, 0.40),
                (0.35, 0.55, 1.0), (1.0, 0.85, 0.15)]
REGALS = [  # angle, distància, w, h, d, gir, paper, cinta
    (0.20, 2.00, 0.60, 0.46, 0.52, 0.30, (0.68, 0.05, 0.09), (1.00, 0.84, 0.30)),
    (1.30, 1.75, 0.44, 0.36, 0.44, 0.90, (0.07, 0.28, 0.72), (0.95, 0.95, 1.00)),
    (2.40, 2.05, 0.66, 0.54, 0.50, 0.10, (0.04, 0.42, 0.38), (1.00, 0.78, 0.25)),
    (3.50, 1.80, 0.42, 0.60, 0.42, 0.60, (0.78, 0.56, 0.10), (0.75, 0.05, 0.10)),
    (4.60, 2.00, 0.54, 0.38, 0.58, 1.20, (0.52, 0.10, 0.58), (0.40, 0.95, 1.00)),
    (5.55, 1.70, 0.38, 0.32, 0.38, 0.40, (0.86, 0.86, 0.90), (0.85, 0.10, 0.15)),
]


class Escena:
    def __init__(self, amplada, alcada, missatge, qualitat=1.0, llavor=2026):
        self.W, self.H = amplada, alcada
        self.missatge = missatge
        self.files = alcada - 2                          # l'última fila és per al missatge
        rng = np.random.default_rng(llavor)
        self._camera()
        # punts per unitat² perquè hi hagi ~2,5 punts per subpíxel
        dens = 1.25 * qualitat * (self.f / DIST * SX) * (0.5 * self.f / DIST * SY)

        self.terra = terra(rng, dens)
        self.tronc = tronc(rng, dens)
        self.copa, puntes = arbre(rng, dens)

        # Espumilló: tub prim en espiral; paràmetre g (0 dalt → 1 baix) per anar-lo posant
        n = int(30 * 0.30 * dens)
        g = rng.random(n)
        y = 3.85 - g * (3.85 - 0.75)
        th = g * TAU * 4.3
        r = radi_copa(y) * 0.93 + 0.06
        psi = rng.random(n) * TAU
        radial = np.column_stack([np.cos(th), np.zeros(n), np.sin(th)])
        nor = _norm(radial * np.cos(psi)[:, None] + np.array([0, 1.0, 0]) * np.sin(psi)[:, None])
        pos = np.column_stack([r * np.cos(th), y - 0.05 * np.sin(th * 3) ** 2, r * np.sin(th)]) + nor * 0.045
        self.garlanda = Grup(pos, nor, [1.0, 0.74, 0.22], 1.6, 0.15)
        self.garlanda_g = g
        self.garlanda_fase = rng.random(n) * TAU

        # Boles: penjades sota les puntes de les branques
        self.boles = []
        escollides = rng.choice(len(puntes), size=min(42, len(puntes)), replace=False)
        for i in escollides:
            p, d, llarg = puntes[i]
            radi = rng.uniform(0.075, 0.115)
            centre = p - d * 0.10 * llarg + np.array([0, -radi - 0.06, 0])
            color = COLORS_BOLES[rng.integers(len(COLORS_BOLES))]
            local = esfera(rng, (0, 0, 0), radi, dens, color, espec=2.0)
            self.boles.append((centre, local, rng.random()))

        # Llums: petites esferes emissives prop de les puntes
        n_ll = 90
        idx = rng.choice(len(puntes), size=n_ll, replace=len(puntes) < n_ll)
        ll_pos = []
        for i in idx:
            p, d, llarg = puntes[i]
            ll_pos.append(p - d * rng.uniform(0.05, 0.35) * llarg + np.array([0, 0.07, 0]) + rng.normal(0, 0.04, 3))
        self.llums_pos = np.array(ll_pos)
        self.llums_col = np.array([COLORS_LLUMS[i] for i in rng.integers(len(COLORS_LLUMS), size=n_ll)])
        self.llums_fase = rng.random(n_ll) * TAU
        self.llums_vel = rng.uniform(1.2, 3.6, n_ll)
        self.llums_ordre = rng.random(n_ll)
        punts, quin = [], []
        for i in range(n_ll):
            e = esfera(rng, self.llums_pos[i], 0.038, dens * 2, (1, 1, 1))
            punts.append(e.pos)
            quin.append(np.full(len(e.pos), i))
        self.llums_punts = np.concatenate(punts)
        self.llums_quin = np.concatenate(quin)
        self.llums_nor = _norm(self.llums_punts - self.llums_pos[self.llums_quin])

        # Com il·lumina cada bombeta les agulles properes (matriu punts × llums)
        punts_i, llums_i, pesos = [], [], []
        for i, lp in enumerate(self.llums_pos):
            d2 = ((self.copa.pos - lp) ** 2).sum(1)
            a_prop = np.nonzero(d2 < 0.40 ** 2)[0]
            punts_i.append(a_prop)
            llums_i.append(np.full(len(a_prop), i))
            pesos.append(np.exp(-d2[a_prop] / (2 * 0.14 ** 2)))
        self.resp_punt = np.concatenate(punts_i)
        self.resp_llum = np.concatenate(llums_i)
        self.resp_pes = np.concatenate(pesos)

        self.estel = estel(rng, dens * 2.2)

        self.regals = []
        for i, (ang, dist, w, h, d, gir, paper, cinta) in enumerate(REGALS):
            local = caixa(rng, w, h, d, dens, paper, cinta)
            local.pos, local.nor = rot_y(local.pos, gir), rot_y(local.nor, gir)
            self.regals.append((np.array([dist * math.cos(ang), 0, dist * math.sin(ang)]), local, i * 0.33))

        n = 320
        self.neu0 = np.column_stack([rng.uniform(-3.6, 3.6, n), rng.uniform(0, 6.5, n), rng.uniform(-3.6, 3.6, n)])
        self.neu_vel = rng.uniform(0.22, 0.55, n)
        self.neu_fase = rng.random(n) * TAU

    # -- càmera: focal i centre perquè tota l'escena hi càpiga
    def _camera(self):
        self.alfa = math.atan2(CAM_Y - OBJECTIU_Y, DIST)
        mostres = []
        for a in np.linspace(0, TAU, 48, endpoint=False):
            mostres.append((R_TERRA * math.cos(a), 0, R_TERRA * math.sin(a)))
            mostres.append((1.85 * math.cos(a), 0.5, 1.85 * math.sin(a)))
        mostres.append((0, Y_ESTEL + 0.62, 0))
        p = self._a_camera(np.array(mostres, float))
        u, v = p[:, 0] / p[:, 2], 0.5 * p[:, 1] / p[:, 2]
        self.f = min((self.W - 2) / (u.max() - u.min()), (self.files - 1) / (v.max() - v.min()))
        self.cx = self.W / 2 - self.f * (u.max() + u.min()) / 2
        self.r0 = 0.5 + self.f * v.max()

    def _a_camera(self, p):
        q = p - np.array([0, CAM_Y, -DIST])
        ca, sa = math.cos(self.alfa), math.sin(self.alfa)
        return np.column_stack([q[:, 0], q[:, 1] * ca + q[:, 2] * sa, -q[:, 1] * sa + q[:, 2] * ca])

    def _dir_a_camera(self, n):
        ca, sa = math.cos(self.alfa), math.sin(self.alfa)
        return np.column_stack([n[:, 0], n[:, 1] * ca + n[:, 2] * sa, -n[:, 1] * sa + n[:, 2] * ca])

    # -- l'escena a l'instant t
    def _grups(self, t):
        grups = [self.terra]
        pl = fase(t, T_LLUMS)
        llums_on = np.sin(t * self.llums_vel + self.llums_fase) > -0.25
        llums_vis = self.llums_ordre <= pl
        intensitat = np.where(llums_vis, np.where(llums_on, 1.0, 0.12), 0.0)

        g = fase(t, T_CREIX)
        if g > 0:
            # Creix des de terra: primer el tronc, després els pisos de baix a dalt
            alt_visible = elastic(g) * (Y_PUNTA + 0.1)
            esc = 0.25 + 0.75 * suau(g * 1.3)
            for base in (self.tronc, self.copa):
                if g >= 1:                                  # ja ha crescut: sense còpies
                    m = slice(None)
                    sub = base.copia()
                else:
                    m = base.pos[:, 1] <= alt_visible
                    if not m.any():
                        continue
                    sub = base.copia(m)
                    # les branques s'obren a mesura que la «saba» puja
                    obertura = np.clip((alt_visible - sub.pos[:, 1]) / 0.9, 0.15, 1.0) * esc
                    sub.pos = sub.pos * np.column_stack([obertura, np.ones(len(obertura)), obertura])
                sub.extra = np.zeros((len(sub.pos), 3))
                if base is self.copa and pl > 0:
                    w = self.resp_pes * intensitat[self.resp_llum]
                    cl = self.llums_col[self.resp_llum]
                    brill = np.column_stack([np.bincount(self.resp_punt, weights=w * cl[:, k], minlength=len(base.pos))
                                             for k in range(3)])
                    sub.extra = brill[m] * 0.55
                grups.append(sub)

        pg = fase(t, T_GARLANDA)
        if pg > 0:
            m = self.garlanda_g <= pg
            espurna = (np.sin(t * 6 + self.garlanda_fase[m] * 7) > 0.93) * 0.9
            grups.append(self.garlanda.copia(m, emis=0.12 + espurna))

        pb = fase(t, T_BOLES)
        for centre, local, ordre in self.boles:
            k = elastic((pb - ordre * 0.85) / 0.15) if pb > ordre * 0.85 else 0
            if k > 0.01:
                balanceig = np.array([0.02 * math.sin(t * 2 + ordre * 9), 0, 0])
                grups.append(local.copia(pos=centre + balanceig + local.pos * k))

        self._llums_ara = (llums_vis, intensitat)

        pe = fase(t, T_ESTEL)
        if pe > 0:
            k = elastic(pe)
            gir = -VEL_GIR * t + 0.5 * math.sin(t * 1.2) + (1 - suau(pe)) * 8
            pos = rot_y(self.estel.pos * k, gir) + [0, Y_ESTEL + (1 - suau(pe)) * 1.4, 0]
            grups.append(self.estel.copia(pos=pos, nor=rot_y(self.estel.nor, gir),
                                          emis=self.estel.emis * (1 + 0.25 * math.sin(t * 4))))

        for base, local, retard in self.regals:
            p = fase(t, (T_REGALS[0] + retard, T_REGALS[0] + retard + 0.9))
            if p > 0:
                grups.append(local.copia(pos=local.pos + base + [0, (1 - rebot(p)) * 3.8, 0]))

        return uneix(grups)

    def _neu(self, t):
        y = (self.neu0[:, 1] - self.neu_vel * t) % 6.5
        x = self.neu0[:, 0] + 0.18 * np.sin(t * 0.8 + self.neu_fase)
        z = self.neu0[:, 2] + 0.18 * np.cos(t * 0.6 + self.neu_fase)
        return np.column_stack([x, y, z])

    def _projecta(self, p, t):
        q = self._a_camera(rot_y(p, VEL_GIR * t))
        c = np.round(self.cx + self.f * q[:, 0] / q[:, 2]).astype(int)
        r = np.round(self.r0 - 0.5 * self.f * q[:, 1] / q[:, 2]).astype(int)
        return c, r, q[:, 2]

    def _superposa(self, t, car, fg, Z, E):
        """Llums i neu: caràcters nets per cel·la, amb prova de profunditat."""
        F, W = self.files, self.W
        dins = lambda c, r: (c >= 0) & (c < W) & (r >= 0) & (r < F)
        # neu
        c, r, z = self._projecta(self._neu(t), t)
        for ci, ri, zi in zip(c, r, z):
            if 0 <= ci < W and 0 <= ri < F and zi < Z[ri, ci] - 0.05:
                prop = zi < DIST - 1.0
                if car[ri, ci] == ' ' or prop:
                    car[ri, ci] = '*' if zi < DIST - 3.0 else ("'" if zi < DIST - 1.8 else '.')
                    br = float(np.clip(1.1 - (zi - DIST + 3) * 0.18, 0.3, 0.95))
                    fg[ri, ci] = (0.85 * br, 0.88 * br, 0.97 * br)
        # llums
        if not hasattr(self, '_llums_ara'):
            return
        vis, inten = self._llums_ara
        c, r, z = self._projecta(self.llums_pos, t)
        ordre = np.argsort(-z)
        for i in ordre:
            if not vis[i] or not (0 <= c[i] < W and 0 <= r[i] < F):
                continue
            if z[i] > Z[r[i], c[i]] + 0.08:        # amagada darrere les branques
                continue
            on = inten[i] > 0.5
            car[r[i], c[i]] = ('@' if z[i] < DIST - 0.6 else 'o') if on else '.'
            col = self.llums_col[i]
            fg[r[i], c[i]] = np.minimum(1, col * (1.0 if on else 0.35) + (0.25 if on else 0))
            if on:
                E[r[i], c[i]] += col * 1.0

    # -- render
    def fotograma(self, t):
        """Retorna (caràcters H×W, color de text H×W×3, color de fons H×W×3), en 0-255."""
        W, F = self.W, self.files
        G = self._grups(t)
        fi = VEL_GIR * t
        q = self._a_camera(rot_y(G.pos, fi))
        n = self._dir_a_camera(rot_y(G.nor, fi))
        n[~G.cull] = VISTA
        z = q[:, 2]
        vista = -q / np.linalg.norm(q, axis=1, keepdims=True)
        de_cara = np.einsum('ij,ij->i', n, vista) > -0.08
        ok = (z > 0.2) & (de_cara | ~G.cull)
        sc = np.floor((self.cx + self.f * q[:, 0] / z + 0.5) * SX).astype(int)
        sr = np.floor((self.r0 - 0.5 * self.f * q[:, 1] / z + 0.5) * SY).astype(int)
        Ws, Hs = W * SX, F * SY
        ok &= (sc >= 0) & (sc < Ws) & (sr >= 0) & (sr < Hs)
        idx = np.nonzero(ok)[0]
        cel = sr[idx] * Ws + sc[idx]
        # z-buffer: s'escriu del més llunyà al més proper; a cada subpíxel hi queda el més proper
        lluny_primer = np.argsort(-z[idx], kind='stable')
        buf = np.full(Hs * Ws, -1)
        buf[cel[lluny_primer]] = idx[lluny_primer]
        cel_t = np.nonzero(buf >= 0)[0]
        tria = buf[cel_t]

        # Il·luminació
        nn = n[tria]
        dif = np.clip(nn @ LLUM, 0, None)
        farc = np.clip(nn @ FARCIMENT, 0, None) * 0.22
        esp = np.clip(nn @ MIG, 0, None) ** 30 * G.espec[tria]
        contra = (1 - np.abs(np.einsum('ij,ij->i', nn, vista[tria]))) ** 3 * 0.30
        emis = G.emis[tria]
        part = G.part[tria]
        ao = G.ao[tria]
        llum = np.where(part, 0.0, (0.14 + 1.05 * dif + farc + contra) * ao)
        base = G.col[tria]
        extra = G.extra[tria]
        rgb = base * (llum + emis)[:, None] * 1.1 + esp[:, None] * np.array([1.0, 0.97, 0.90]) + extra
        rgb += np.where(part, 0, contra * ao)[:, None] * np.array([0.10, 0.18, 0.38])
        lum = np.clip(llum + emis + esp * 0.7 + extra.max(1) * 0.5, 0, 1.6)

        # Buffers de subpíxel
        L = np.zeros(Hs * Ws)
        C = np.zeros((Hs * Ws, 3))
        E = np.zeros((Hs * Ws, 3))
        Zs = np.full(Hs * Ws, np.inf)
        L[cel_t] = lum
        C[cel_t] = rgb
        Zs[cel_t] = z[tria]
        E[cel_t] = rgb * np.clip(emis - 0.6, 0, None)[:, None]        # només fonts de llum (estrella)
        L, C, E = L.reshape(Hs, Ws), C.reshape(Hs, Ws, 3), E.reshape(Hs, Ws, 3)
        Z = Zs.reshape(F, SY, W, SX).min(axis=(1, 3))
        self._omple_forats(L, C)

        # Per cel·la: vector 2×4 de «tinta» i color mitjà
        L4 = L.reshape(F, SY, W, SX).transpose(0, 2, 1, 3).reshape(F, W, 8)
        C4 = C.reshape(F, SY, W, SX, 3).transpose(0, 2, 1, 3, 4).reshape(F, W, 8, 3)
        tinta = np.clip(L4, 0, 1.25) * 0.66
        car = np.full((self.H, W), ' ')
        fg = np.zeros((self.H, W, 3))
        ple = (L4 > 0).sum(-1)
        vora = (tinta.sum(-1) > 0.03) & (ple < 7)            # cel·les de contorn: tria per forma
        v = tinta[vora]
        dist = (v ** 2).sum(1)[:, None] - 2 * v @ GLIF_MAT.T + GLIF_N2[None, :]
        cf = car[:F]
        cf[vora] = GLIF_CARS[dist.argmin(1)]
        plena = ple >= 7                                      # cel·les plenes: rampa de densitat
        mitjana = L4[plena].mean(-1)
        cf[plena] = RAMPA[np.clip((mitjana / 1.25 * len(RAMPA)).astype(int), 0, len(RAMPA) - 1)]
        pes = L4 + 1e-6
        mitja = (C4 * pes[..., None]).sum(2) / pes.sum(2)[..., None]
        maxim = mitja.max(-1, keepdims=True)
        mitja = mitja / np.maximum(maxim, 1e-3) * np.clip(0.22 + 0.95 * maxim, 0, 1)   # comprimeix el rang
        fg[:F] = mitja

        E4 = E.reshape(F, SY, W, SX, 3).sum((1, 3)) / (SX * SY)
        self._superposa(t, car, fg, Z, E4)

        # Resplendor (bloom) al fons: halo suau només al voltant de les llums i l'estrella
        bg = np.zeros((self.H, W, 3))
        bg[:F] = np.clip(_difumina(E4, 6, 3) * 0.35, 0, 0.16)
        bg[bg < 0.02] = 0

        self._espurnes_estel(t, car, fg)
        self._missatge(t, car, fg)
        return car, (np.clip(fg, 0, 1) * 255).astype(np.uint8), (bg * 255).astype(np.uint8)

    @staticmethod
    def _omple_forats(L, C):
        """Omple subpíxels buits envoltats de superfície (forats entre punts)."""
        ple = L > 0
        veins = np.zeros(L.shape, int)
        suma_l = np.zeros(L.shape)
        suma_c = np.zeros(C.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sl = np.roll(L, (dy, dx), (0, 1))
            sp = np.roll(ple, (dy, dx), (0, 1))
            veins += sp
            suma_l += sl * sp
            suma_c += np.roll(C, (dy, dx), (0, 1)) * sp[..., None]
        omple = ~ple & (veins >= 3)
        L[omple] = suma_l[omple] / veins[omple]
        C[omple] = suma_c[omple] / veins[omple][:, None]

    def _espurnes_estel(self, t, car, fg):
        if fase(t, T_ESTEL) < 1:
            return
        p = self._a_camera(rot_y(np.array([[0, Y_ESTEL, 0.0]]), VEL_GIR * t))[0]
        c0 = self.cx + self.f * p[0] / p[2]
        r0 = self.r0 - 0.5 * self.f * p[1] / p[2]
        rng = np.random.default_rng(int(t * 7))
        for _ in range(9):
            a = rng.random() * TAU
            d = rng.uniform(0.75, 1.5) * self.f * 0.5 / DIST
            c, r = int(round(c0 + math.cos(a) * d * 2)), int(round(r0 + math.sin(a) * d))
            if 0 <= c < self.W and 0 <= r < self.files and car[r, c] == ' ':
                car[r, c] = rng.choice(['+', '.', '*', "'", '`'])
                fg[r, c] = (1.0, 0.9, 0.55) if rng.random() < 0.7 else (1.0, 1.0, 1.0)

    def _missatge(self, t, car, fg):
        if t < T_TEXT:
            return
        m = self.missatge
        n = min(len(m), int((t - T_TEXT) * 12))
        x0 = self.W // 2 - len(m) // 2
        for i, ch in enumerate(m[:n]):
            if 0 <= x0 + i < self.W:
                ona = 0.5 + 0.5 * math.sin(t * 3 - i * 0.45)
                car[self.H - 1, x0 + i] = ch
                fg[self.H - 1, x0 + i] = (1.0, 0.66 + 0.28 * ona, 0.25 + 0.45 * (1 - ona))


def _difumina(a, rx, ry):
    """Difuminat gaussià separable (amb rodament a les vores, prou bo per a un halo)."""
    def nucli(r):
        x = np.arange(-r, r + 1)
        k = np.exp(-x ** 2 / (2 * (r / 2) ** 2))
        return x, k / k.sum()
    out = np.zeros_like(a)
    xs, ks = nucli(rx)
    for x, k in zip(xs, ks):
        out += np.roll(a, x, 1) * k
    a, out = out, np.zeros_like(out)
    ys, ks = nucli(ry)
    for y, k in zip(ys, ks):
        out += np.roll(a, y, 0) * k
    return out


# ---------------------------------------------------------------- Sortida

def a_ansi(car, fg, bg, truecolor=True):
    H, W = car.shape
    if truecolor:
        fq = (fg // 6 * 6).tolist()
        bq = (bg // 4 * 4).tolist()
        cfg = lambda c: f'\x1b[38;2;{c[0]};{c[1]};{c[2]}m'
        cbg = lambda c: f'\x1b[48;2;{c[0]};{c[1]};{c[2]}m'
    else:
        cub = lambda a: (16 + 36 * (a[..., 0] // 43) + 6 * (a[..., 1] // 43) + a[..., 2] // 43).tolist()
        fq, bq = cub(fg.astype(int)), cub(bg.astype(int))
        cfg = lambda c: f'\x1b[38;5;{c}m'
        cbg = lambda c: f'\x1b[48;5;{c}m'
    linies = []
    cars = car.tolist()
    for y in range(H):
        tros, ufg, ubg = [], None, None
        fc, ff, fb = cars[y], fq[y], bq[y]
        for x in range(W):
            b = tuple(fb[x]) if truecolor else fb[x]
            if b != ubg:
                tros.append(cbg(b))
                ubg = b
            ch = fc[x]
            if ch != ' ':
                f = tuple(ff[x]) if truecolor else ff[x]
                if f != ufg:
                    tros.append(cfg(f))
                    ufg = f
            tros.append(ch)
        linies.append(''.join(tros))
    return '\x1b[H' + '\n'.join(linies)


def grava_gif(escena, sortida, segons, fps, inici):
    from PIL import Image, ImageDraw, ImageFont
    cw, ch = 8, 15
    font = None
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 'DejaVuSansMono-Bold.ttf',
              '/System/Library/Fonts/Menlo.ttc', 'C:/Windows/Fonts/consolab.ttf'):
        try:
            font = ImageFont.truetype(f, 13)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    imatges = []
    total = int(segons * fps)
    for i in range(total):
        car, fg, bg = escena.fotograma(inici + i / fps)
        fons = Image.fromarray(np.repeat(np.repeat(bg, ch, 0), cw, 1), 'RGB')
        d = ImageDraw.Draw(fons)
        for y, x in zip(*np.nonzero(car != ' ')):
            d.text((x * cw, y * ch), car[y, x], font=font, fill=tuple(int(v) for v in fg[y, x]))
        imatges.append(fons)
        print(f'\rFotograma {i + 1}/{total}', end='', file=sys.stderr)
    print(file=sys.stderr)
    imatges[0].save(sortida, save_all=True, append_images=imatges[1:], duration=int(1000 / fps), loop=0)


def main():
    ap = argparse.ArgumentParser(description='Árbol de Navidad 3D en ASCII.')
    ap.add_argument('--fps', type=float, default=20)
    ap.add_argument('--missatge', default='Bon Nadal, Bitxo!')
    ap.add_argument('--sense-intro', action='store_true', help='empieza directamente girando')
    ap.add_argument('--mida', help='AMPLADAxALÇADA, p. ej. 140x50 (por defecto, la terminal)')
    ap.add_argument('--qualitat', type=float, default=1.0, help='densidad de puntos (0.5-1.5)')
    ap.add_argument('--256', dest='c256', action='store_true', help='256 colores en vez de truecolor')
    ap.add_argument('--gif', help='graba un GIF en vez de animar')
    ap.add_argument('--segons', type=float, default=18, help='duración del GIF')
    args = ap.parse_args()

    def mida():
        if args.mida:
            w, h = args.mida.lower().split('x')
            return int(w), int(h)
        s = shutil.get_terminal_size((100, 40))
        return s.columns, s.lines

    inici_t = T_SENSE_INTRO if args.sense_intro else 0.0
    if args.gif:
        grava_gif(Escena(*mida(), args.missatge, args.qualitat), args.gif, args.segons, min(args.fps, 15), inici_t)
        return

    truecolor = not args.c256 and (os.environ.get('COLORTERM', '') in ('truecolor', '24bit')
                                   or os.environ.get('TERM_PROGRAM') in ('iTerm.app', 'vscode', 'WezTerm', 'ghostty')
                                   or 'WT_SESSION' in os.environ)
    fons = '\x1b[48;2;0;0;0m' if truecolor else '\x1b[48;5;16m'
    sys.stdout.write('\x1b[?1049h\x1b[?25l' + fons + '\x1b[2J')
    try:
        actual, escena = None, None
        rellotge = time.monotonic()
        while True:
            t_frame = time.monotonic()
            m = mida()
            if m != actual:
                actual = m
                escena = Escena(*m, args.missatge, args.qualitat)
                sys.stdout.write(fons + '\x1b[2J')
            sys.stdout.write(a_ansi(*escena.fotograma(inici_t + time.monotonic() - rellotge), truecolor))
            sys.stdout.flush()
            time.sleep(max(0, 1 / args.fps - (time.monotonic() - t_frame)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
