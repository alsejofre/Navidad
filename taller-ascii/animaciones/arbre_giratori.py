#!/usr/bin/env python3
"""Uso: python3 arbre_giratori.py [--fps 20] [--missatge "Bon Nadal!"] [--sense-intro] [--mida 120x45]
                                  [--256] [--gif sortida.gif --segons 16]

Árbol de Navidad 3D en ASCII sobre fondo negro: crece desde el suelo, se le pone la
estrella, el espumillón, las bolas y las luces, caen los regalos y gira sobre sí mismo
mientras nieva. Ctrl+C para salir.

Requiere numpy (`pip install numpy`); para --gif también Pillow.

Cómo funciona: la escena es una nube de puntos 3D (conos para los pisos del árbol,
cilindro para el tronco, esferas para las bolas, cajas para los regalos...). En cada
fotograma se gira la escena, se proyecta con una cámara en perspectiva, se queda el punto
más cercano de cada celda (z-buffer) y se ilumina (difusa + especular + contraluz). La
luminosidad elige el carácter de la rampa ASCII y el color va en 24 bits.

--256       fuerza 256 colores (para terminales sin truecolor, p. ej. Terminal.app antiguo).
--gif F     en vez de animar en la terminal, graba un GIF de --segons segundos.
"""
import argparse
import math
import os
import shutil
import sys
import time

import numpy as np

TAU = 2 * math.pi
RAMPA = np.array(list(".,-~:;=!*#%@"))
VEL_GIR = 0.65                     # rad/s

# Pisos del árbol: (y de la base, y de la punta, radio de la base)
PISOS = [(0.60, 2.35, 1.70), (1.30, 2.95, 1.32), (1.98, 3.50, 0.97), (2.62, 4.00, 0.60)]
Y_ESTEL = 4.55
R_TERRA = 2.55

# Línea de tiempo (segundos)
T_CREIX = (0.0, 3.2)
T_ESTEL = (3.0, 4.2)
T_GARLANDA = (4.0, 6.2)
T_BOLES = (4.6, 7.2)
T_LLUMS = (6.2, 7.4)
T_REGALS = (7.2, 10.0)
T_TEXT = 10.2
T_SENSE_INTRO = 12.5

# Cámara
DIST = 8.4
CAM_Y = 3.0
OBJECTIU_Y = 2.0

# Luz (espacio de cámara: x dreta, y amunt, z endavant)
def _norm(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)

LLUM = _norm([-0.65, 0.60, -0.45])
VISTA = np.array([0.0, 0.0, -1.0])
MIG = _norm(LLUM + VISTA)
FARCIMENT = _norm([0.8, 0.1, -0.4])


def limita(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def fase(t, interval):
    a, b = interval
    return limita((t - a) / (b - a))


def suau(p):
    return 1 - (1 - limita(p)) ** 3


def elastic(p):
    """Crece con un pequeño rebote al final (0→1)."""
    p = limita(p)
    if p in (0.0, 1.0):
        return p
    return 1 + 2 ** (-9 * p) * math.sin((p * 9 - 0.75) * TAU / 3) * 0.6


def rebot(p):
    p = limita(p)
    if p < 0.7:
        return (p / 0.7) ** 2
    q = (p - 0.7) / 0.3
    return 1 - 0.15 * math.sin(q * math.pi)


def radi_copa(y):
    """Radio exterior del árbol a la altura y (el piso más ancho que pasa por ahí)."""
    r = np.zeros_like(y, dtype=float)
    for yb, yt, rb in PISOS:
        dins = (y >= yb) & (y <= yt)
        r = np.where(dins, np.maximum(r, rb * (yt - y) / (yt - yb)), r)
    return r


# ---------------------------------------------------------------- Geometria

class Grup:
    """Conjunto de puntos con normal, color, brillo especular y emisión."""

    def __init__(self, pos, nor, col, espec=0.0, emis=0.0, cull=True, ao=1.0):
        n = len(pos)
        self.pos = np.asarray(pos, dtype=float)
        self.nor = np.asarray(nor, dtype=float)
        self.col = np.asarray(col, dtype=float)
        self.espec = np.broadcast_to(np.asarray(espec, dtype=float), (n,)).copy()
        self.emis = np.broadcast_to(np.asarray(emis, dtype=float), (n,)).copy()
        self.cull = np.broadcast_to(np.asarray(cull, dtype=bool), (n,)).copy()
        self.ao = np.broadcast_to(np.asarray(ao, dtype=float), (n,)).copy()   # oclusió ambiental

    def copia(self, pos=None, nor=None, m=None, **canvis):
        """Còpia amb posicions/normals noves (i opcionalment només els punts de la màscara m)."""
        sel = (lambda a: a) if m is None else (lambda a: a[m])
        g = Grup(sel(self.pos) if pos is None else pos, sel(self.nor) if nor is None else nor, sel(self.col),
                 sel(self.espec), sel(self.emis), sel(self.cull), sel(self.ao))
        for k, v in canvis.items():
            setattr(g, k, v)
        return g


def uneix(grups):
    grups = [g for g in grups if g is not None and len(g.pos)]
    if not grups:
        return None
    return Grup(np.concatenate([g.pos for g in grups]), np.concatenate([g.nor for g in grups]),
                np.concatenate([g.col for g in grups]), np.concatenate([g.espec for g in grups]),
                np.concatenate([g.emis for g in grups]), np.concatenate([g.cull for g in grups]),
                np.concatenate([g.ao for g in grups]))


def esfera(rng, centre, radi, dens, color, espec=1.0, emis=0.0):
    n = max(12, int(4 * math.pi * radi ** 2 * dens * 1.5))
    d = _norm(rng.normal(size=(n, 3)))
    return Grup(np.asarray(centre) + d * radi, d, np.tile(color, (n, 1)), espec, emis)


def con(rng, yb, yt, rb, dens):
    alt = yt - yb
    n = int(math.pi * rb * math.hypot(rb, alt) * dens)
    s = np.sqrt(rng.random(n))                    # distància relativa des de la punta
    th = rng.random(n) * TAU
    r = s * rb * (1 + 0.08 * np.sin(th * 13 + s * 7) * s ** 2)   # branques que fan ones a la vora
    y = yt - s * alt - 0.10 * s ** 4 * (0.5 + 0.5 * np.sin(th * 13))   # puntes que pengen
    nor = _norm(np.stack([np.cos(th), np.full(n, rb / alt), np.sin(th)], 1))
    pos = np.stack([r * np.cos(th), y, r * np.sin(th)], 1) + nor * ((rng.random(n) - 0.5) * 0.09)[:, None]
    nor = _norm(nor + rng.normal(0, 0.20, (n, 3)))                 # textura d'agulles
    barreja = rng.random(n)[:, None]
    fosc, clar = np.array([0.04, 0.38, 0.14]), np.array([0.30, 0.90, 0.36])
    col = fosc * (1 - barreja) + clar * barreja
    ao = 0.12 + 0.88 * s ** 2.0                                   # fosc a dalt de cada pis (sota el pis superior)
    neu = (rng.random(n) < 0.16 * s ** 3) & (nor[:, 1] > 0.25)
    col[neu] = [0.88, 0.92, 1.0]
    return Grup(pos, nor, col, np.where(neu, 0.6, 0.12), ao=ao)


def cilindre(rng, radi, y0, y1, dens, color):
    n = int(TAU * radi * (y1 - y0) * dens)
    th = rng.random(n) * TAU
    y = y0 + rng.random(n) * (y1 - y0)
    nor = np.stack([np.cos(th), np.zeros(n), np.sin(th)], 1)
    estries = 0.75 + 0.25 * np.sin(th * 9 + rng.random(n))
    return Grup(nor * radi + np.stack([np.zeros(n), y, np.zeros(n)], 1), nor,
                np.asarray(color) * estries[:, None], 0.05)


def terra(rng, radi, dens):
    n = int(math.pi * radi ** 2 * dens * 0.7)
    r = radi * np.sqrt(rng.random(n))
    th = rng.random(n) * TAU
    pos = np.stack([r * np.cos(th), np.zeros(n), r * np.sin(th)], 1)
    nor = _norm(np.tile([0, 1.0, 0], (n, 1)) + rng.normal(0, 0.15, (n, 3)))
    ombra = 0.30 + 0.70 * limita_arr(r / 1.9)
    vora = 1 - limita_arr((r - radi * 0.75) / (radi * 0.25)) * 0.8   # s'esvaeix cap a la vora
    col = np.array([0.42, 0.46, 0.58]) * (ombra * vora * (0.7 + 0.3 * rng.random(n)))[:, None]
    brilla = rng.random(n) < 0.03
    return Grup(pos, nor, col, np.where(brilla, 1.5, 0.0), ao=0.45 * ombra * vora)


def limita_arr(a):
    return np.clip(a, 0, 1)


def caixa(rng, w, h, d, dens, paper, cinta):
    cares = [  # centre, normal, eix u, eix v
        ((0, h, 0), (0, 1, 0), (w / 2, 0, 0), (0, 0, d / 2), True),
        ((0, h / 2, d / 2), (0, 0, 1), (w / 2, 0, 0), (0, h / 2, 0), False),
        ((0, h / 2, -d / 2), (0, 0, -1), (w / 2, 0, 0), (0, h / 2, 0), False),
        ((w / 2, h / 2, 0), (1, 0, 0), (0, 0, d / 2), (0, h / 2, 0), False),
        ((-w / 2, h / 2, 0), (-1, 0, 0), (0, 0, d / 2), (0, h / 2, 0), False),
    ]
    grups = []
    for c, nrm, u, v, dalt in cares:
        u, v = np.array(u, float), np.array(v, float)
        n = max(10, int(4 * np.linalg.norm(u) * np.linalg.norm(v) * dens * 1.3))
        a, b = rng.random(n) * 2 - 1, rng.random(n) * 2 - 1
        pos = np.asarray(c, float) + a[:, None] * u + b[:, None] * v
        es_cinta = (np.abs(a) < 0.13) | ((np.abs(b) < 0.13) if dalt else False)
        col = np.where(es_cinta[:, None], np.asarray(cinta), np.asarray(paper) * (0.88 + 0.12 * rng.random(n))[:, None])
        grups.append(Grup(pos, np.tile(nrm, (n, 1)), col, np.where(es_cinta, 0.9, 0.2)))
    for dx in (-0.075, 0.075):          # llaç
        grups.append(esfera(rng, (dx, h + 0.05, 0), 0.065, dens, cinta, 0.9))
    return uneix(grups)


def estel(rng, dens, r_ext=0.50, r_int=0.21, gruix=0.12):
    """Estrella de 5 puntes amb gruix, centrada a l'origen, en el pla XY."""
    angles = np.pi / 2 + np.arange(10) * TAU / 10
    radis = np.where(np.arange(10) % 2 == 0, r_ext, r_int)
    vert = np.stack([np.cos(angles) * radis, np.sin(angles) * radis], 1)
    grups = []
    # Cares davant i darrere: punts dins dels 10 triangles (centre, v_i, v_i+1)
    for signe in (1, -1):
        for i in range(10):
            a, b = vert[i], vert[(i + 1) % 10]
            n = max(8, int(abs(a[0] * b[1] - a[1] * b[0]) / 2 * dens * 2))
            u, v = rng.random(n), rng.random(n)
            fora = u + v > 1
            u[fora], v[fora] = 1 - u[fora], 1 - v[fora]
            p2 = u[:, None] * a + v[:, None] * b
            relleu = 1 - np.linalg.norm(p2, axis=1) / r_ext      # el centre sobresurt: facetes
            pos = np.column_stack([p2, signe * gruix / 2 * (0.4 + 0.6 * relleu)])
            nrm = _norm(np.column_stack([p2 * 1.2, np.full(n, signe * 1.0)]))
            grups.append(Grup(pos, nrm, np.tile([1.0, 0.82, 0.28], (n, 1)) * (0.75 + 0.25 * relleu)[:, None], 1.4, 0.35 + 0.5 * relleu))
    # Laterals
    for i in range(10):
        a, b = vert[i], vert[(i + 1) % 10]
        llarg = np.linalg.norm(b - a)
        n = max(6, int(llarg * gruix * dens * 3))
        u, z = rng.random(n), (rng.random(n) - 0.5) * gruix * 0.4
        p2 = a + u[:, None] * (b - a)
        dirc = (b - a) / llarg
        nrm = np.tile([dirc[1], -dirc[0], 0.0], (n, 1))
        grups.append(Grup(np.column_stack([p2, z]), nrm, np.tile([1.0, 0.95, 0.6], (n, 1)), 1.2, 1.1))
    return uneix(grups)


# ---------------------------------------------------------------- Escena

COLORS_BOLES = [(0.85, 0.08, 0.12), (0.95, 0.75, 0.2), (0.15, 0.35, 0.95), (0.85, 0.85, 0.9),
                (0.85, 0.2, 0.6), (0.6, 0.1, 0.75)]
COLORS_LLUMS = [(1.0, 0.85, 0.55), (1.0, 0.3, 0.25), (0.35, 1.0, 0.45), (0.4, 0.6, 1.0), (1.0, 0.9, 0.2)]
REGALS = [  # angle, distància, w, h, d, gir, paper, cinta
    (0.25, 1.95, 0.58, 0.44, 0.50, 0.3, (0.70, 0.06, 0.10), (1.0, 0.85, 0.3)),
    (1.35, 1.70, 0.42, 0.34, 0.42, 0.9, (0.08, 0.30, 0.75), (0.95, 0.95, 1.0)),
    (2.45, 2.00, 0.64, 0.52, 0.48, 0.1, (0.05, 0.45, 0.40), (1.0, 0.8, 0.25)),
    (3.55, 1.75, 0.40, 0.58, 0.40, 0.6, (0.75, 0.55, 0.10), (0.75, 0.05, 0.1)),
    (4.65, 1.95, 0.52, 0.36, 0.56, 1.2, (0.55, 0.12, 0.60), (0.4, 0.95, 1.0)),
    (5.60, 1.65, 0.36, 0.30, 0.36, 0.4, (0.85, 0.85, 0.88), (0.85, 0.1, 0.15)),
]


class Escena:
    def __init__(self, amplada, alcada, missatge, llavor=2026):
        self.W, self.H = amplada, alcada
        self.missatge = missatge
        self.files_escena = alcada - 2          # l'última fila és per al missatge
        rng = np.random.default_rng(llavor)
        self._camera()
        dens = 7.0 * self.px_unitat * self.px_unitat * 0.5   # punts per unitat² (≈3 per cel·la)

        self.terra = terra(rng, R_TERRA, dens)
        self.tronc = cilindre(rng, 0.22, 0.0, 0.75, dens, (0.38, 0.22, 0.11))
        self.copa = uneix([con(rng, *p, dens) for p in PISOS])

        # Garlanda en espiral: tub prim al voltant del con, amb paràmetre g (0 dalt → 1 baix)
        n = int(28 * 0.32 * dens)
        g = rng.random(n)
        y = 3.80 - g * (3.80 - 0.80)
        th = g * TAU * 4.5
        r = radi_copa(y) + 0.11
        psi = rng.random(n) * TAU
        radial = np.stack([np.cos(th), np.zeros(n), np.sin(th)], 1)
        amunt = np.tile([0, 1.0, 0], (n, 1))
        nor = _norm(radial * np.cos(psi)[:, None] + amunt * np.sin(psi)[:, None])
        pos = np.stack([r * np.cos(th), y, r * np.sin(th)], 1) + nor * 0.05
        self.garlanda = Grup(pos, nor, np.tile([1.0, 0.74, 0.22], (n, 1)), 1.3, 0.25)
        self.garlanda_g = g

        # Boles
        self.boles = []
        for _ in range(38):
            yb, yt, rb = PISOS[rng.choice(len(PISOS), p=np.array([p[2] for p in PISOS]) / sum(p[2] for p in PISOS))]
            yy = yt - rng.uniform(0.45, 0.97) * (yt - yb)
            a = rng.random() * TAU
            rr = float(radi_copa(np.array([yy]))[0]) + 0.05
            radi = rng.uniform(0.075, 0.11)
            centre = np.array([rr * math.cos(a), yy - radi * 0.6, rr * math.sin(a)])
            color = COLORS_BOLES[rng.integers(len(COLORS_BOLES))]
            local = esfera(rng, (0, 0, 0), radi, dens, color, espec=1.6)
            self.boles.append((centre, local, rng.random()))

        # Llums
        n = 70
        yy = rng.uniform(0.7, 3.85, n)
        a = rng.random(n) * TAU
        rr = radi_copa(yy) + 0.04
        self.llums_pos = np.stack([rr * np.cos(a), yy, rr * np.sin(a)], 1)
        self.llums_col = np.array([COLORS_LLUMS[i] for i in rng.integers(len(COLORS_LLUMS), size=n)])
        self.llums_fase = rng.random(n) * TAU
        self.llums_vel = rng.uniform(1.5, 4.0, n)
        self.llums_ordre = rng.random(n)

        self.estel = estel(rng, dens * 2.5)

        self.regals = []
        for i, (ang, dist, w, h, d, gir, paper, cinta) in enumerate(REGALS):
            local = caixa(rng, w, h, d, dens, paper, cinta)
            local.pos = rot_y(local.pos, gir)
            local.nor = rot_y(local.nor, gir)
            self.regals.append((np.array([dist * math.cos(ang), 0, dist * math.sin(ang)]), local, i * 0.32))

        # Neu que cau
        n = 260
        self.neu0 = np.column_stack([rng.uniform(-3.2, 3.2, n), rng.uniform(0, 6.0, n), rng.uniform(-3.2, 3.2, n)])
        self.neu_vel = rng.uniform(0.25, 0.6, n)
        self.neu_fase = rng.random(n) * TAU
        self.espurnes = np.random.default_rng(llavor + 7)

    # -- càmera: calcula focal i centre perquè tota l'escena hi càpiga
    def _camera(self):
        self.alfa = math.atan2(CAM_Y - OBJECTIU_Y, DIST)
        mostres = []
        for a in np.linspace(0, TAU, 48, endpoint=False):
            mostres.append((R_TERRA * math.cos(a), 0, R_TERRA * math.sin(a)))
            mostres.append((1.6 * math.cos(a), 0.55, 1.6 * math.sin(a)))
        mostres.append((0, Y_ESTEL + 0.6, 0))
        p = self._a_camera(np.array(mostres, float))
        u, v = p[:, 0] / p[:, 2], 0.5 * p[:, 1] / p[:, 2]
        self.f = min((self.W - 2) / (u.max() - u.min()), (self.files_escena - 1) / (v.max() - v.min()))
        self.cx = self.W / 2 - self.f * (u.max() + u.min()) / 2
        self.r0 = 0.5 + self.f * v.max()
        self.px_unitat = self.f / DIST

    def _a_camera(self, p):
        q = p - np.array([0, CAM_Y, -DIST])
        ca, sa = math.cos(self.alfa), math.sin(self.alfa)
        return np.column_stack([q[:, 0], q[:, 1] * ca + q[:, 2] * sa, -q[:, 1] * sa + q[:, 2] * ca])

    def _rot_normal_camera(self, n):
        ca, sa = math.cos(self.alfa), math.sin(self.alfa)
        return np.column_stack([n[:, 0], n[:, 1] * ca + n[:, 2] * sa, -n[:, 1] * sa + n[:, 2] * ca])

    # -- muntatge de l'escena a l'instant t
    def _grups(self, t):
        grups = [self.terra]
        g = elastic(fase(t, T_CREIX))
        if g > 0.001:
            esc = np.array([g ** 0.75, g, g ** 0.75])
            for base in (self.tronc, self.copa):
                grups.append(base.copia(pos=base.pos * esc))

        pg = fase(t, T_GARLANDA)
        if pg > 0:
            m = self.garlanda_g <= pg
            G = self.garlanda
            grups.append(G.copia(m=m))

        pb = fase(t, T_BOLES)
        for centre, local, ordre in self.boles:
            k = elastic((pb - ordre * 0.85) / 0.15) if pb > ordre * 0.85 else 0
            if k > 0.01:
                grups.append(local.copia(pos=centre + local.pos * k))

        pl = fase(t, T_LLUMS)
        if pl > 0:
            m = self.llums_ordre <= pl
            on = np.sin(t * self.llums_vel + self.llums_fase) > -0.2
            n = int(m.sum())
            if n:
                col = self.llums_col[m] * np.where(on[m], 1.0, 0.25)[:, None]
                grups.append(Grup(self.llums_pos[m], np.tile(VISTA_MON, (n, 1)), col,
                                  0.0, np.where(on[m], 1.5, 0.45), False))

        pe = fase(t, T_ESTEL)
        if pe > 0:
            k = elastic(pe)
            gir = -VEL_GIR * t + 0.55 * math.sin(t * 1.3) + (1 - suau(pe)) * 9
            pos = rot_y(self.estel.pos * k, gir) + [0, Y_ESTEL + (1 - suau(pe)) * 1.2, 0]
            grups.append(self.estel.copia(pos=pos, nor=rot_y(self.estel.nor, gir),
                                          emis=self.estel.emis * (1 + 0.4 * math.sin(t * 5))))

        for base, local, retard in self.regals:
            p = fase(t, (T_REGALS[0] + retard, T_REGALS[0] + retard + 0.9))
            if p > 0:
                alt = (1 - rebot(p)) * 3.5
                grups.append(local.copia(pos=local.pos + base + [0, alt, 0]))

        # Neu (funció pura del temps, perquè el GIF i la terminal coincideixin)
        y = (self.neu0[:, 1] - self.neu_vel * t) % 6.0
        x = self.neu0[:, 0] + 0.15 * np.sin(t * 0.9 + self.neu_fase)
        neu = np.column_stack([x, y, self.neu0[:, 2]])
        n = len(neu)
        grups.append(Grup(neu, np.tile(VISTA_MON, (n, 1)), np.tile([0.85, 0.88, 0.95], (n, 1)), 0.0, 0.22, False))
        return uneix(grups)

    def fotograma(self, t):
        """Retorna (caràcters H×W, colors H×W×3 en 0-255)."""
        car = np.full((self.H, self.W), ' ')
        col = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        G = self._grups(t)

        fi = VEL_GIR * t
        pos = rot_y(G.pos, fi)
        nor = rot_y(G.nor, fi)
        # Les partícules «sense cull» (llums, neu) no giren la normal: sempre miren la càmera.
        q = self._a_camera(pos)
        n = self._rot_normal_camera(nor)
        n[~G.cull] = VISTA

        z = q[:, 2]
        vista = -q / np.linalg.norm(q, axis=1, keepdims=True)
        de_cara = np.einsum('ij,ij->i', n, vista) > -0.05
        ok = (z > 0.2) & (de_cara | ~G.cull)

        c = np.round(self.cx + self.f * q[:, 0] / z).astype(int)
        r = np.round(self.r0 - 0.5 * self.f * q[:, 1] / z).astype(int)
        ok &= (c >= 0) & (c < self.W) & (r >= 0) & (r < self.files_escena)
        idx = np.nonzero(ok)[0]
        cel = r[idx] * self.W + c[idx]
        ordre = np.lexsort((z[idx], cel))                 # per cel·la, el més proper primer
        cel_ord = cel[ordre]
        primer = np.ones(len(cel_ord), bool)
        primer[1:] = cel_ord[1:] != cel_ord[:-1]
        tria = idx[ordre[primer]]

        nn = n[tria]
        dif = np.clip(nn @ LLUM, 0, None)
        esp = np.clip(nn @ MIG, 0, None) ** 28 * G.espec[tria]
        contra = (1 - np.abs(np.einsum('ij,ij->i', nn, vista[tria]))) ** 3 * 0.35
        emis = G.emis[tria]
        particula = ~G.cull[tria]
        amb = 0.16
        farc = np.clip(nn @ FARCIMENT, 0, None) * 0.25
        ao = G.ao[tria]
        llum = np.where(particula, 0.0, (amb + 1.1 * dif + farc + contra) * ao)
        base = G.col[tria]
        rgb = base * (llum + emis)[:, None] * 1.1 + esp[:, None] * np.array([1.0, 0.97, 0.9])
        rgb += np.where(particula, 0, contra)[:, None] * np.array([0.10, 0.18, 0.35])
        lum = np.clip(llum + emis + esp * 0.8, 0, 1.5)
        # Les partícules properes es veuen més grosses
        lum = np.where(particula, lum * np.clip(9.5 / z[tria], 0.6, 1.4), lum)
        ic = np.clip((lum / 1.5 * (len(RAMPA) - 1)).astype(int), 0, len(RAMPA) - 1)

        fr, fc = np.divmod(cel_ord[primer], self.W)
        chars = RAMPA[ic]
        part_chars = np.array(list('.:+*o@'))
        chars = np.where(particula, part_chars[np.clip((lum / 1.5 * 5.99).astype(int), 0, 5)], chars)
        car[fr, fc] = chars
        col[fr, fc] = np.clip(rgb * 255, 0, 255).astype(np.uint8)

        self._espurnes_estel(t, car, col)
        self._missatge(t, car, col)
        return car, col

    def _espurnes_estel(self, t, car, col):
        pe = fase(t, T_ESTEL)
        if pe < 1:
            return
        p = self._a_camera(rot_y(np.array([[0, Y_ESTEL, 0.0]]), VEL_GIR * t))[0]
        c0 = self.cx + self.f * p[0] / p[2]
        r0 = self.r0 - 0.5 * self.f * p[1] / p[2]
        rng = np.random.default_rng(int(t * 8))
        for _ in range(7):
            a = rng.random() * TAU
            d = rng.uniform(0.45, 1.0) * self.f * 0.55 / DIST
            c, r = int(round(c0 + math.cos(a) * d * 2)), int(round(r0 + math.sin(a) * d))
            if 0 <= c < self.W and 0 <= r < self.files_escena and car[r, c] == ' ':
                car[r, c] = rng.choice(['+', '.', '*', "'"])
                col[r, c] = (255, 230, 140) if rng.random() < 0.7 else (255, 255, 255)

    def _missatge(self, t, car, col):
        if t < T_TEXT:
            return
        m = self.missatge
        n = min(len(m), int((t - T_TEXT) * 12))
        x0 = self.W // 2 - len(m) // 2
        for i, ch in enumerate(m[:n]):
            x = x0 + i
            if 0 <= x < self.W:
                ona = 0.5 + 0.5 * math.sin(t * 3 - i * 0.45)
                car[self.H - 1, x] = ch
                col[self.H - 1, x] = (255, int(170 + 70 * ona), int(60 + 120 * (1 - ona)))


VISTA_MON = np.array([0.0, 0.0, -1.0])


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    p = np.asarray(p, float)
    return np.column_stack([p[:, 0] * c + p[:, 2] * s, p[:, 1], -p[:, 0] * s + p[:, 2] * c])


# ---------------------------------------------------------------- Sortida

def a_ansi(car, col, truecolor=True):
    H, W = car.shape
    fons = '\x1b[48;2;0;0;0m' if truecolor else '\x1b[48;5;16m'
    linies = []
    car_l = car.tolist()
    q = (col // 6 * 6).tolist() if truecolor else (16 + 36 * (col[..., 0] // 43) + 6 * (col[..., 1] // 43) + col[..., 2] // 43).tolist()
    for y in range(H):
        tros = [fons]
        ultim = None
        fila_c, fila_q = car_l[y], q[y]
        for x in range(W):
            ch = fila_c[x]
            if ch != ' ':
                c = fila_q[x]
                c = tuple(c) if truecolor else c
                if c != ultim:
                    tros.append(f'\x1b[38;2;{c[0]};{c[1]};{c[2]}m' if truecolor else f'\x1b[38;5;{c}m')
                    ultim = c
            tros.append(ch)
        linies.append(''.join(tros))
    return '\x1b[H' + '\n'.join(linies)


def grava_gif(escena, sortida, segons, fps, sense_intro):
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
    t0 = T_SENSE_INTRO if sense_intro else 0.0
    for i in range(int(segons * fps)):
        car, col = escena.fotograma(t0 + i / fps)
        im = Image.new('RGB', (escena.W * cw, escena.H * ch), (0, 0, 0))
        d = ImageDraw.Draw(im)
        for y, x in zip(*np.nonzero(car != ' ')):
            d.text((x * cw, y * ch), car[y, x], font=font, fill=tuple(int(v) for v in col[y, x]))
        imatges.append(im)
        print(f'\rFotograma {i + 1}/{int(segons * fps)}', end='', file=sys.stderr)
    print(file=sys.stderr)
    imatges[0].save(sortida, save_all=True, append_images=imatges[1:], duration=int(1000 / fps), loop=0)


def main():
    ap = argparse.ArgumentParser(description='Árbol de Navidad 3D en ASCII.')
    ap.add_argument('--fps', type=float, default=20)
    ap.add_argument('--missatge', default='Bon Nadal, Bitxo!')
    ap.add_argument('--sense-intro', action='store_true', help='empieza directamente girando')
    ap.add_argument('--mida', help='AMPLADAxALÇADA, p. ej. 120x45 (por defecto, la terminal)')
    ap.add_argument('--256', dest='c256', action='store_true', help='usar 256 colores en vez de truecolor')
    ap.add_argument('--gif', help='graba un GIF en vez de animar')
    ap.add_argument('--segons', type=float, default=16, help='duración del GIF')
    args = ap.parse_args()

    def mida():
        if args.mida:
            w, h = args.mida.lower().split('x')
            return int(w), int(h)
        s = shutil.get_terminal_size((100, 40))
        return s.columns, s.lines

    if args.gif:
        grava_gif(Escena(*mida(), args.missatge), args.gif, args.segons, min(args.fps, 15), args.sense_intro)
        return

    truecolor = not args.c256 and (os.environ.get('COLORTERM', '') in ('truecolor', '24bit')
                                   or os.environ.get('TERM_PROGRAM') in ('iTerm.app', 'vscode', 'WezTerm', 'ghostty')
                                   or 'WT_SESSION' in os.environ)
    sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[48;2;0;0;0m\x1b[2J' if truecolor else '\x1b[?1049h\x1b[?25l\x1b[48;5;16m\x1b[2J')
    try:
        actual, escena = None, None
        inici = time.monotonic()
        desfase = T_SENSE_INTRO if args.sense_intro else 0.0
        while True:
            t_frame = time.monotonic()
            m = mida()
            if m != actual:
                actual = m
                escena = Escena(*m, args.missatge)
                sys.stdout.write('\x1b[2J')
            car, col = escena.fotograma(desfase + time.monotonic() - inici)
            sys.stdout.write(a_ansi(car, col, truecolor))
            sys.stdout.flush()
            time.sleep(max(0, 1 / args.fps - (time.monotonic() - t_frame)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
