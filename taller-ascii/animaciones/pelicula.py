#!/usr/bin/env python3
"""Uso: python3 pelicula.py [sortida.html] [--mida 240x68] [--fps 12] [--qualitat 1.0]
                           [--png CARPETA] [--terminal] [--escena N]

«Nadal a Barcelona»: curtmetratge ASCII 3D (~86 s) fet amb el motor de l'arbre.
  1. El cotxe vermell (amb l'avet al sostre) baixa per un carrer de l'Eixample il·luminat,
     amb la Sagrada Família al fons.
  2. Una noia rossa i un noi que li treu un cap passegen de la mà sota els llums.
  3. Patinen junts sobre gel, amb l'arbre gegant al fons.
  4. Arriben davant l'arbre gegant (l'arbre del taller, ×3,4: uns 15 m), la càmera puja
     fins a l'estrella i fa la volta a l'arbre.
  5. Sense tall, la càmera s'allunya i s'enlaira: es veu la ciutat de nit amb la plaça,
     l'arbre i la pista de gel, i al cel apareix «BON NADAL» en lletres grans fetes d'ASCII.
Neva durant tota la pel·lícula.

Per defecte desa un HTML a pantalla completa per al navegador de l'ordinador (16:9).
Tarda uns minuts a renderitzar (és molt detall).
  --png CARPETA   en comptes de l'HTML, desa uns quants fotogrames de mostra.
  --terminal      la renderitza i després la reprodueix a la terminal (cal truecolor i
                  una finestra gran: tantes columnes com --mida).
  --escena N      només l'escena N (1–5), per provar.
"""
import argparse
import base64
import gzip
import json
import math
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import arbre_giratori as AG  # noqa: E402
from arbre_giratori import TAU, Grup, _norm, estel, uneix  # noqa: E402
from escenes3d import (  # noqa: E402
    Escena3D, Rx, Ry, Rz, avet, bloc, cilindre, con, disc, ellipsoide, esfera, hash1, mou,
    particules, superellipsoide, tor, tub,
)

# Línia de temps (segons)
ESCENES = [(0.0, 14.0), (14.0, 27.0), (27.0, 40.0), (40.0, 68.0), (68.0, 86.0)]
DURADA = ESCENES[-1][1]
TALLS = (14.0, 27.0, 40.0)   # canvis d'escena amb fosa a negre (de l'arbre al pla final no hi ha tall)
FOS = 0.7                 # durada de la fosa
TEXT_CEL = 'BON NADAL'
ESCALA_ARBRE = 3.4


def suau(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def mescla(a, b, p):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * p


# ---------------------------------------------------------------- Persones

PELL = (0.94, 0.76, 0.64)


def persona(d, alcada, estil, fase=0.0, mode='camina', ma_dins=None, mirada=0.0):
    """Persona mirant +x amb els peus a y=0.
    estil: {'llavor', 'abric', 'pantalons', 'sabates', 'bufanda', 'cabell', 'llarg', 'gorro'}.
    mode: 'camina', 'patina' o 'quiet'. ma_dins: (x, y, z) local on va la mà de la banda +z
    (per anar de la mà); mirada: inclinació del cap cap amunt (radians)."""
    rng = np.random.default_rng(estil['llavor'])
    s = alcada / 1.75
    g = []
    bob = 0.02 * s * abs(math.sin(fase)) if mode == 'camina' else 0.0
    inclina = 0.22 if mode == 'patina' else 0.0
    y_maluc = 0.93 * s + bob - (0.06 * s if mode == 'patina' else 0)
    y_esp = y_maluc + 0.5 * s
    cuixa, cama = 0.45 * s, 0.45 * s

    # Cames
    for costat, off in ((1, 0.0), (-1, math.pi)):
        maluc = np.array([0, y_maluc, costat * 0.095 * s])
        if mode == 'camina':
            a = 0.42 * math.sin(fase + off)
            flex = 0.55 * max(0.0, math.sin(fase + off + math.pi / 2))
            genoll = maluc + cuixa * np.array([math.sin(a), -math.cos(a), 0])
            turmell = genoll + cama * np.array([math.sin(a - flex), -math.cos(a - flex), 0])
        elif mode == 'patina':
            empenta = max(0.0, math.sin(fase + off))
            genoll = maluc + np.array([0.12 * s, -cuixa * 0.95, costat * 0.05 * s])
            turmell = np.array([-0.15 * s * empenta, 0.09 * s, costat * (0.11 + 0.22 * empenta) * s])
        else:
            genoll = maluc + np.array([0.01, -cuixa, 0.01 * costat])
            turmell = np.array([0.0, 0.09 * s, costat * 0.11 * s])
        g.append(tub(rng, maluc, genoll, 0.075 * s, d, estil['pantalons'], 0.3))
        g.append(tub(rng, genoll, turmell, 0.06 * s, d, estil['pantalons'], 0.3))
        g.append(mou(superellipsoide(rng, (0.13 * s, 0.055 * s, 0.055 * s), 0.5, d, estil['sabates'], 0.6),
                     t=turmell + [0.05 * s, -0.04 * s, 0]))
        if mode == 'patina':
            g.append(tub(rng, turmell + [-0.1 * s, -0.11 * s, 0], turmell + [0.2 * s, -0.11 * s, 0], 0.012 * s, d * 2, (0.85, 0.87, 0.9), 2.0))

    # Tronc i abric
    centre_tronc = np.array([0.0, (y_maluc + y_esp) / 2 + 0.02 * s, 0])
    tronc = uneix([
        mou(superellipsoide(rng, (0.12 * s, 0.29 * s, 0.19 * s), 0.6, d, estil['abric'], 0.5), t=centre_tronc),
        mou(superellipsoide(rng, (0.135 * s, 0.17 * s, 0.205 * s), 0.7, d, estil['abric'], 0.5), t=(0, y_maluc - 0.03 * s, 0)),
    ])
    botons = (tronc.nor[:, 0] > 0.8) & (np.abs(tronc.pos[:, 2]) < 0.012 * s) & (tronc.pos[:, 1] > y_maluc)
    tronc.col[botons] = (0.15, 0.12, 0.1)
    g.append(mou(tronc, Rz(-inclina), (0, 0, 0)))
    pit = Rz(-inclina) @ np.array([0, y_esp, 0])

    # Coll, bufanda i cap
    coll = pit + [0, 0.05 * s, 0]
    g.append(mou(tor(rng, 0.075 * s, 0.04 * s, d * 1.5, estil['bufanda'], 0.3), t=coll + [0, 0.01 * s, 0]))
    g.append(tub(rng, coll + [0.07 * s, 0, 0.04 * s], coll + [0.09 * s, -0.25 * s, 0.05 * s], 0.035 * s, d, estil['bufanda'], 0.3))
    cap_c = coll + [0.01 * s, 0.17 * s, 0]
    Rcap = Rz(mirada)
    cap = [mou(ellipsoide(rng, (0.095 * s, 0.115 * s, 0.09 * s), d * 1.6, PELL, 0.5), t=(0, 0, 0))]
    for zz in (-0.033, 0.033):
        cap.append(mou(esfera(rng, 0.011 * s, d * 6, (0.12, 0.09, 0.08), 1.0), t=(0.088 * s, 0.015 * s, zz * s)))
    cap.append(mou(ellipsoide(rng, (0.025 * s, 0.02 * s, 0.018 * s), d * 4, (0.9, 0.68, 0.58), 0.4), t=(0.098 * s, -0.02 * s, 0)))
    cabell = estil['cabell']
    # casquet de cabell (deixa la cara lliure)
    brill_cabell = 0.18 if estil.get('llarg') else 0.0
    cap.append(mou(ellipsoide(rng, (0.105 * s, 0.123 * s, 0.1 * s), d * 1.6, cabell, 0.9, emis=brill_cabell,
                              filtre=lambda p, n: (p[:, 0] < 0.02 * s) | (p[:, 1] > 0.065 * s)), t=(-0.01 * s, 0.012 * s, 0)))
    if estil.get('llarg'):
        cap.append(mou(superellipsoide(rng, (0.065 * s, 0.22 * s, 0.115 * s), 0.7, d * 1.4, cabell, 0.9, emis=brill_cabell), t=(-0.075 * s, -0.17 * s, 0)))
        for zz in (-0.085, 0.085):
            cap.append(mou(superellipsoide(rng, (0.035 * s, 0.16 * s, 0.03 * s), 0.7, d * 1.6, cabell, 0.9, emis=brill_cabell), t=(0.0, -0.13 * s, zz * s)))
    if estil.get('gorro'):
        cap.append(mou(ellipsoide(rng, (0.108 * s, 0.075 * s, 0.103 * s), d * 1.6, estil['gorro'], 0.4,
                                  filtre=lambda p, n: p[:, 1] > -0.01 * s), t=(-0.005 * s, 0.07 * s, 0)))
        cap.append(mou(tor(rng, 0.098 * s, 0.022 * s, d * 2, estil['gorro'], 0.3), t=(-0.005 * s, 0.07 * s, 0)))
        cap.append(mou(esfera(rng, 0.035 * s, d * 2, (0.95, 0.95, 0.93), 0.2), t=(-0.01 * s, 0.155 * s, 0)))
    g.append(mou(uneix(cap), Rcap, cap_c))

    # Braços
    for costat, off in ((1, math.pi), (-1, 0.0)):
        esp = pit + np.array([0, -0.03 * s, costat * 0.2 * s])
        if costat > 0 and ma_dins is not None:
            ma = np.asarray(ma_dins, float)
            colze = (esp + ma) / 2 + np.array([-0.03 * s, -0.04 * s, costat * 0.05 * s])
        elif mode == 'patina':
            ma = esp + np.array([0.1 * s, -0.25 * s, costat * 0.45 * s])
            colze = (esp + ma) / 2 + np.array([0, 0.04 * s, 0])
        else:
            b = -0.38 * math.sin(fase + off) if mode == 'camina' else 0.05
            colze = esp + 0.29 * s * np.array([math.sin(b), -math.cos(b), 0.02 * costat])
            ma = colze + 0.27 * s * np.array([math.sin(b + 0.35), -math.cos(b + 0.35), 0])
        g.append(tub(rng, esp, colze, 0.055 * s, d, estil['abric'], 0.4))
        g.append(tub(rng, colze, ma, 0.047 * s, d, estil['abric'], 0.4))
        g.append(mou(esfera(rng, 0.042 * s, d * 2, estil.get('guants', PELL), 0.4), t=ma))
    return uneix(g)


NOIA = {'llavor': 21, 'abric': (0.72, 0.1, 0.14), 'pantalons': (0.12, 0.14, 0.24), 'sabates': (0.32, 0.2, 0.12),
        'bufanda': (0.96, 0.95, 0.92), 'cabell': (1.0, 0.86, 0.5), 'llarg': True, 'guants': (0.96, 0.95, 0.92)}
NOI = {'llavor': 34, 'abric': (0.12, 0.17, 0.3), 'pantalons': (0.16, 0.16, 0.18), 'sabates': (0.2, 0.13, 0.08),
       'bufanda': (0.62, 0.12, 0.14), 'cabell': (0.3, 0.19, 0.11), 'gorro': (0.15, 0.35, 0.22), 'guants': (0.2, 0.2, 0.22)}
H_NOIA = 1.65
H_NOI = H_NOIA + 0.23          # li treu un cap


def parella(d, pos, rumb, fase, mode='camina', separacio=0.62, mirada=0.0):
    """La noia (a l'esquerra, banda -z local) i el noi, agafats de la mà, mirant en la direcció «rumb»."""
    R = Ry(rumb)
    ma = np.array([0.12, 0.86, 0.0])                          # on s'ajunten les mans, entre tots dos
    noia = persona(d, H_NOIA, NOIA, fase, mode, ma_dins=ma - [0, 0, -separacio / 2], mirada=mirada)
    # El noi agafa la mà amb el braç de la banda -z: el construïm amb el braç +z i el reflectim (z → -z)
    noi_mirall = persona(d, H_NOI, NOI, fase, mode, ma_dins=(ma - [0, 0, separacio / 2]) * [1, 1, -1], mirada=mirada)
    noi_mirall.pos[:, 2] *= -1
    noi_mirall.nor[:, 2] *= -1
    g = uneix([mou(noia, R, pos + R @ np.array([0, 0, -separacio / 2])),
               mou(noi_mirall, R, pos + R @ np.array([0, 0, separacio / 2]))])
    g.extra = g.col * np.array([0.35, 0.3, 0.22])          # llum càlida de fanals i aparadors
    return g


# ---------------------------------------------------------------- Llums de Nadal de Barcelona

def garlanda_carrer(x, amplada, alcada, n=56, caiguda=1.0):
    z = np.linspace(-amplada / 2, amplada / 2, n)
    y = alcada - caiguda * (1 - (2 * z / amplada) ** 2)
    return np.column_stack([np.full(n, x), y, z])


def motiu(x, y, tipus, radi=0.95):
    """Motiu lluminós penjat al mig del carrer: estrella (0) o floc de neu (1)."""
    if tipus == 0:
        a = np.pi / 2 + np.arange(10) * TAU / 10
        r = np.where(np.arange(10) % 2 == 0, radi, radi * 0.42)
        v = np.column_stack([np.cos(a) * r, np.sin(a) * r])
        punts = []
        for i in range(10):
            p, q = v[i], v[(i + 1) % 10]
            for u in np.linspace(0, 1, 9, endpoint=False):
                punts.append(p + (q - p) * u)
        p2 = np.array(punts)
    else:
        punts = []
        for k in range(6):
            a = k * TAU / 6
            dvec = np.array([math.cos(a), math.sin(a)])
            for u in np.linspace(0.08, 1, 10):
                punts.append(dvec * radi * u)
            for br in (0.55, 0.8):
                for sgn in (1, -1):
                    b = a + sgn * 0.7
                    for u in np.linspace(0.05, 0.3, 4):
                        punts.append(dvec * radi * br + np.array([math.cos(b), math.sin(b)]) * radi * u)
        p2 = np.array(punts)
    return np.column_stack([np.full(len(p2), x), y + p2[:, 1], p2[:, 0]])


# ---------------------------------------------------------------- La pel·lícula

class Pelicula(Escena3D):
    nom = 'pelicula'
    durada = DURADA
    fps = 12
    mida = (240, 68)
    camera = ((0, 0, -10.0), (0, 0, 0))       # referència per a la densitat de punts (a 10 m)
    fov = 58
    amb = 0.1
    difusa = 0.6
    bloom = 0.45
    qualitat = 1.0
    boira = (9.0, 16.0)

    def __init__(self, mida=None, qualitat=1.0, escenes=(1, 2, 3, 4, 5)):
        if mida:
            self.mida = mida
        self.qualitat = qualitat
        self.escenes = escenes
        super().__init__(llavor=2026)

    def dens_a(self, dist):
        """Punts per m² perquè una superfície a «dist» metres quedi plena."""
        return self.dens * (10.0 / dist) ** 2

    def posa_camera(self, C, T, fov=None):
        C, T = np.asarray(C, float), np.asarray(T, float)
        fwd = _norm(T - C)
        dreta = _norm(np.cross([0, 1.0, 0], fwd))
        self.Rcam = np.stack([dreta, np.cross(fwd, dreta), fwd])
        self.C = C
        if fov:
            self.f = (self.W / 2) / math.tan(math.radians(fov) / 2)

    # --- construcció
    def construeix(self):
        t0 = time.time()
        if 1 in self.escenes or 2 in self.escenes:
            self._carrer()
            self._cotxe()
        if {3, 4, 5} & set(self.escenes):
            self._placa()
        if 5 in self.escenes:
            self._ciutat()
            self.cartell = cartell_ascii(TEXT_CEL, int(self.W * 0.62), max(7, int(self.H * 0.17)))
        print(f'  escenari construït en {time.time() - t0:.0f} s', file=sys.stderr)

    def _carrer(self):
        """Carrer de l'Eixample: façanes amb balcons i finestres, aparadors, fanals, llums de Nadal
        creuant el carrer i la Sagrada Família al fons."""
        rng = np.random.default_rng(1)
        X0, X1, XDET = -30.0, 380.0, 200.0
        pedra = np.array([0.62, 0.55, 0.45])
        grups = []
        for costat in (-1, 1):
            zf = costat * 6.8
            nrm = np.array([0, 0, -costat], float)
            n = int((X1 - X0) * 20 * self.dens_a(14) * 0.01)
            x = X0 + rng.random(n) * (X1 - X0)
            y = rng.random(n) * 20
            col = pedra * (0.8 + 0.3 * rng.random((n, 1)))
            grups.append(Grup(np.column_stack([x, y, np.full(n, zf)]), np.tile(nrm, (n, 1)), col, 0.1, ao=0.35))
            for yc, r in ((4.35, 0.14), (20.1, 0.3)):
                grups.append(tub(rng, (X0, yc, zf - costat * 0.15), (X1, yc, zf - costat * 0.15), r, self.dens_a(14) * 0.3, pedra, 0.2))
            for xc in np.arange(X0 + 1.8, X1 - 1.0, 3.6):
                prop = xc < XDET
                dd = self.dens_a(12) * (0.35 if prop else 0.05)
                # aparador a la planta baixa
                if rng.random() < 0.7:
                    tint = [(1.0, 0.78, 0.45), (1.0, 0.85, 0.6), (1.0, 0.7, 0.5)][rng.integers(3)]
                    m = int(2.2 * 2.6 * dd * 0.25)
                    px = xc + (rng.random(m) - 0.5) * 2.2
                    py = 0.5 + rng.random(m) * 2.6
                    grups.append(Grup(np.column_stack([px, py, np.full(m, zf - costat * 0.03)]), np.tile(nrm, (m, 1)),
                                      tint, 0.0, emis=0.3 + 0.15 * rng.random(), ao=0.5))
                for pis in range(5):
                    yb = 4.75 + pis * 3.05
                    encesa = rng.random() < 0.42
                    m = int(1.2 * 2.1 * dd * (1.0 if encesa else 0.5))
                    px = xc + (rng.random(m) - 0.5) * 1.2
                    py = yb + 0.2 + rng.random(m) * 2.1
                    if encesa:
                        tint = (1.0, 0.76 + 0.1 * rng.random(), 0.42)
                        grups.append(Grup(np.column_stack([px, py, np.full(m, zf - costat * 0.03)]), np.tile(nrm, (m, 1)),
                                          tint, 0.0, emis=0.3 + 0.2 * rng.random()))
                    else:
                        grups.append(Grup(np.column_stack([px, py, np.full(m, zf - costat * 0.03)]), np.tile(nrm, (m, 1)),
                                          (0.07, 0.08, 0.11), 0.6, ao=0.6))
                    if prop:   # balcó amb barana
                        dz = zf - costat * 0.3
                        grups.append(mou(superellipsoide(rng, (0.92, 0.055, 0.28), 0.35, self.dens_a(12) * 0.5, pedra * 0.9, 0.3), t=(xc, yb + 0.05, dz)))
                        ferro = (0.12, 0.12, 0.13)
                        for yy in (yb + 0.95, yb + 0.5):
                            grups.append(tub(rng, (xc - 0.88, yy, zf - costat * 0.55), (xc + 0.88, yy, zf - costat * 0.55), 0.02, self.dens_a(10) * 0.8, ferro, 0.9))
                        for xx in np.linspace(xc - 0.85, xc + 0.85, 5):
                            grups.append(tub(rng, (xx, yb + 0.08, zf - costat * 0.55), (xx, yb + 0.97, zf - costat * 0.55), 0.015, self.dens_a(10) * 0.8, ferro, 0.9))
        # Calçada i voreres (pols de punts) amb línies i vorades
        n = int((X1 - X0) * 9 * self.dens_a(10) * 0.04)
        x = X0 + rng.random(n) * (X1 - X0)
        z = (rng.random(n) - 0.5) * 7.2
        col = np.tile([0.2, 0.2, 0.23], (n, 1)) * (0.8 + 0.4 * rng.random((n, 1)))
        col[(np.abs(z) < 0.08) & (np.mod(x, 6) < 3)] = (0.9, 0.9, 0.85)
        grups.append(Grup(np.column_stack([x, np.zeros(n), z]), np.tile([0, 1.0, 0], (n, 1)), col, 1.2, ao=0.5))
        for costat in (-1, 1):
            m = int((X1 - X0) * 3.2 * self.dens_a(8) * 0.04)
            x = X0 + rng.random(m) * (X1 - X0)
            z = costat * (3.6 + rng.random(m) * 3.2)
            grups.append(Grup(np.column_stack([x, np.full(m, 0.15), z]), np.tile([0, 1.0, 0], (m, 1)),
                              np.tile([0.75, 0.78, 0.85], (m, 1)) * (0.7 + 0.3 * rng.random((m, 1))), 0.5, ao=0.55))
            grups.append(tub(rng, (X0, 0.1, costat * 3.6), (X1, 0.1, costat * 3.6), 0.09, self.dens_a(10) * 0.5, (0.6, 0.6, 0.62), 0.3))
        # Fanals (cada 16 m a banda i banda)
        self.fanals = []
        for x in np.arange(X0 + 6, X1, 16.0):
            for costat in (-1, 1):
                z = costat * 4.0
                grups.append(tub(rng, (x, 0.15, z), (x, 4.4, z), 0.07, self.dens_a(10), (0.14, 0.15, 0.14), 0.8))
                grups.append(tub(rng, (x, 4.4, z), (x, 4.55, z - costat * 0.6), 0.05, self.dens_a(10), (0.14, 0.15, 0.14), 0.8))
                cap = mou(ellipsoide(rng, (0.22, 0.3, 0.22), self.dens_a(10) * 2, (1.0, 0.86, 0.58), 0.0, emis=1.4), t=(x, 4.35, z - costat * 0.6))
                grups.append(cap)
                self.fanals.append((x, 4.35, z - costat * 0.6))
        # Sagrada Família al fons del carrer (silueta il·luminada)
        sf = []
        dsf = self.dens_a(200) * 2.5
        for xo, zo, h in ((0, -10, 50), (0, -3.5, 54), (0, 3.5, 54), (0, 10, 50), (-14, -6, 61), (-14, 6, 61), (-22, 0, 86), (-17, -14, 65), (-17, 14, 65)):
            def col_sf(p, n, h=h):
                c = np.tile([0.68, 0.6, 0.48], (len(p), 1)) * (0.85 + 0.15 * np.sin(p[:, 1] * 2.1) ** 2)[:, None]
                fin = (np.mod(p[:, 1], 6.0) < 1.2) & (hash1(np.floor(p[:, 1] / 6.0) * 3.3 + h) > 0.4)
                c[fin] = (1.0, 0.82, 0.5)
                return c
            torre = mou(con(rng, 3.8, h, dsf, col_sf, 0.3), t=(430 + xo, 0, zo))
            fin = np.all(torre.col == (1.0, 0.82, 0.5), axis=1)
            torre.emis[fin] = 0.6
            sf.append(torre)
            sf.append(mou(esfera(rng, 1.7, dsf, (1.0, 0.9, 0.6), 0.0, emis=0.9), t=(430 + xo, h + 0.8, zo)))
        sf.append(mou(estel(rng, dsf * 4), Ry(math.pi / 2), (430 - 22, 92, 0), 7.0))
        sagrada = uneix(sf)
        sagrada.emis[-len(sf[-1].pos):] = 1.3
        sagrada.ao = sagrada.ao * 0.6
        grups.append(sagrada)
        carrer = uneix(grups)
        # Llum dels fanals sobre el que tenen a prop
        fan = np.array(self.fanals)
        extra = np.zeros((len(carrer.pos), 3))
        for k in range(0, len(fan), 2):
            d2 = ((carrer.pos[:, None, :] - fan[None, k:k + 2, :]) ** 2).sum(-1)
            extra += (1 / (1 + d2 / 5.0)).sum(1)[:, None] * np.array([1.0, 0.8, 0.5]) * 0.18
        carrer.extra = np.minimum(extra, 0.6)
        self.carrer = carrer
        # Llums de Nadal que creuen el carrer
        llums, motius, tipus = [], [], []
        for k, x in enumerate(np.arange(X0 + 2, X1, 9.0)):
            llums.append(garlanda_carrer(x, 13.2, 9.2))
            if x < 300:
                motius.append(motiu(x, 7.4, k % 2))
                tipus.append(k % 2)
        self.llums_carrer = np.concatenate(llums)
        self.llums_carrer_f = np.random.default_rng(3).random(len(self.llums_carrer))
        self.motius = np.concatenate(motius)
        self.motius_col = np.concatenate([np.tile([1.0, 0.86, 0.5] if t == 0 else [0.75, 0.88, 1.0], (len(m), 1)) for m, t in zip(motius, tipus)])

    def _cotxe(self):
        rng = np.random.default_rng(5)
        d = self.dens_a(7)
        # El mateix cotxe de l'escena «cotxe» (escenes3d.py): carrosseria arrodonida, avet al sostre
        vermell = (0.74, 0.06, 0.08)
        vidre = (0.10, 0.16, 0.26)

        def cabina(p, n):
            cc = np.tile(vermell, (len(p), 1))
            vidres = (n[:, 1] < 0.75) & (p[:, 1] > -0.05)
            pilars = (np.abs(np.abs(p[:, 0]) - 0.72) < 0.06) | (np.abs(p[:, 0] - 0.05) < 0.05)
            cc[vidres & ~pilars] = vidre
            return cc
        cos = uneix([
            mou(superellipsoide(rng, (1.42, 0.3, 0.64), 0.35, d, vermell, 1.6), t=(0, 0.62, 0)),
            mou(superellipsoide(rng, (0.8, 0.27, 0.56), 0.5, d, cabina, 2.0, filtre=lambda p, n: p[:, 1] > -0.12), t=(-0.25, 0.98, 0)),
            mou(superellipsoide(rng, (1.45, 0.07, 0.66), 0.3, d, (0.22, 0.22, 0.24), 0.8), t=(0, 0.36, 0)),
        ])
        fars = uneix([mou(ellipsoide(rng, (0.04, 0.09, 0.14), d * 3, (1, 0.95, 0.75), 0, 1.5), t=(1.41, 0.66, s * 0.42)) for s in (1, -1)])
        pilots = uneix([mou(ellipsoide(rng, (0.04, 0.08, 0.13), d * 3, (1, 0.15, 0.1), 0, 1.2), t=(-1.41, 0.66, s * 0.45)) for s in (1, -1)])
        arbre = mou(avet(rng, 1.4, d, neu=True), Rz(math.pi / 2), (0.55, 1.42, 0))
        corda = uneix([mou(tor(rng, 0.36, 0.015, d * 2, (0.85, 0.8, 0.6)), Rz(math.pi / 2) @ Rx(math.pi / 2), (x, 1.42, 0)) for x in (-0.55, 0.05)])
        self.carrosseria = uneix([cos, fars, pilots, arbre, corda])

        def tapacubs(p, n):
            th = np.arctan2(p[:, 2], p[:, 0])
            r = np.hypot(p[:, 0], p[:, 2])
            cc = np.tile([0.75, 0.77, 0.8], (len(p), 1))
            cc[(np.cos(5 * th) < 0.55) & (r > 0.07)] = (0.25, 0.26, 0.28)
            return cc
        roda = uneix([cilindre(rng, 0.33, 0.26, d, (0.07, 0.07, 0.08), 0.3, tapes=False),
                      mou(disc(rng, 0.22, d * 1.5, tapacubs, 1.2), None, (0, 0.135, 0)),
                      mou(disc(rng, 0.22, d * 1.5, tapacubs, 1.2), Rx(math.pi), (0, -0.135, 0))])
        self.roda = mou(roda, Rx(math.pi / 2))
        self.rodes_pos = [(x, 0.33, z) for x in (0.95, -0.95) for z in (0.62, -0.62)]
        k = 1400
        r2 = np.random.default_rng(9)
        s = r2.random(k)
        self.feix = np.column_stack([1.45 + s * 9, 0.62 + (r2.random(k) - 0.5) * s * 1.2 - s * 0.45,
                                     np.where(r2.random(k) > 0.5, 0.42, -0.42) + (r2.random(k) - 0.5) * s * 2.0])
        self.feix_s = s

    def _placa(self):
        """Plaça amb l'arbre gegant, la pista de gel al davant i edificis al voltant."""
        print('  construint l\'arbre gegant...', file=sys.stderr)
        mida_ref = (int(self.W * 1.25), int(self.H * 1.8))
        self.arbre = AG.Escena(*mida_ref, '', qualitat=1.0)          # l'arbre del taller, en gran
        rng = np.random.default_rng(7)
        S = ESCALA_ARBRE
        grups = []
        # Terra de la plaça (pols de neu)
        n = int(math.pi * 45 ** 2 * self.dens_a(14) * 0.008)
        r = 45 * np.sqrt(rng.random(n))
        a = rng.random(n) * TAU
        self.terra_placa = Grup(np.column_stack([r * np.cos(a), np.zeros(n), r * np.sin(a)]), np.tile([0, 1.0, 0], (n, 1)),
                                np.tile([0.8, 0.84, 0.92], (n, 1)) * (0.7 + 0.3 * rng.random((n, 1))), 0.5, ao=0.5)
        # Pista de gel davant de l'arbre
        self.pista_c = np.array([0.0, 0.0, -17.0])

        def gel(p, n):
            rr = np.hypot(p[:, 0], p[:, 2])
            c = np.tile([0.72, 0.84, 0.95], (len(p), 1)) * (0.9 + 0.1 * rng.random((len(p), 1)))
            c[np.abs(np.mod(rr, 0.9) - 0.45) < 0.03] = (0.92, 0.96, 1.0)
            return c
        grups.append(mou(disc(rng, 7.0, self.dens_a(9) * 0.03, gel, 1.8, ao=0.4), t=self.pista_c + [0, 0.02, 0]))
        tanca = cilindre(rng, 7.05, 0.5, self.dens_a(9) * 0.6,
                         lambda p, n: np.where((p[:, 1] > 0.12)[:, None], [0.75, 0.1, 0.12], [0.95, 0.95, 0.95]), 0.6, tapes=False, dins=True)
        grups.append(mou(tanca, t=self.pista_c + [0, 0.25, 0]))
        k = 120
        aa = np.arange(k) / k * TAU
        self.llums_pista = self.pista_c + np.column_stack([7.05 * np.cos(aa), np.full(k, 0.55), 7.05 * np.sin(aa)])
        # Edificis il·luminats al voltant de la plaça
        for k in range(14):
            ang = math.pi * (0.15 + 0.7 * k / 13)
            dist = 42
            w, h = rng.uniform(10, 16), rng.uniform(16, 24)
            cx, cz = dist * math.cos(ang), dist * math.sin(ang) - 5
            g = mou(bloc(rng, (w, h, 6), self.dens_a(40) * 0.25, (0.5, 0.45, 0.38), 0.2, sense=('+z', '-y')), Ry(-(ang - math.pi / 2)), (cx, h / 2, cz))
            fin = (np.mod(g.pos[:, 1], 3.0) < 1.4) & (hash1(np.floor(g.pos[:, 0] / 1.8) * 7 + np.floor(g.pos[:, 1] / 3) * 13 + k) > 0.5)
            g.col[fin] = (1.0, 0.78, 0.45)
            g.emis[fin] = 0.5
            g.ao = g.ao * 0.4
            grups.append(g)
        # Fanals de la plaça
        fanals = []
        for k in range(10):
            ang = TAU * k / 10 + 0.3
            x, z = 24 * math.cos(ang), 24 * math.sin(ang) - 6
            grups.append(tub(rng, (x, 0, z), (x, 4.2, z), 0.08, self.dens_a(15), (0.14, 0.15, 0.14), 0.8))
            grups.append(mou(ellipsoide(rng, (0.25, 0.32, 0.25), self.dens_a(15) * 2, (1.0, 0.86, 0.58), 0.0, emis=1.4), t=(x, 4.4, z)))
            fanals.append((x, 4.4, z))
        placa = uneix(grups)
        fan = np.array(fanals)
        d2 = ((placa.pos[:, None, :] - fan[None, :, :]) ** 2).sum(-1)
        placa.extra = np.minimum((1 / (1 + d2 / 6.0)).sum(1)[:, None] * np.array([1.0, 0.8, 0.5]) * 0.18, 0.5)
        self.placa = placa

    # --- l'arbre gegant a l'instant t
    def _arbre_gegant(self, t):
        E, S = self.arbre, ESCALA_ARBRE
        tt = AG.T_SENSE_INTRO + t
        intens = E._intensitats(tt)
        copa = E.copa.copia()
        w = E.resp_pes * intens[E.resp_llum]
        cl = E.llums_col[E.resp_llum]
        copa.extra = np.column_stack([np.bincount(E.resp_punt, weights=w * cl[:, k], minlength=len(copa.pos)) for k in range(3)]) * 0.55
        espurna = (np.sin(tt * 6 + E.garlanda_fase * 7) > 0.93) * 0.9
        parts = [E.tronc, copa, E.garlanda.copia(emis=0.12 + espurna)]
        for centre, local, _ in E.boles:
            parts.append(local.copia(pos=centre + local.pos))
        gir = 0.5 * math.sin(tt * 1.2)
        parts.append(E.estel.copia(pos=AG.rot_y(E.estel.pos, gir) + [0, AG.Y_ESTEL, 0], nor=AG.rot_y(E.estel.nor, gir),
                                   emis=E.estel.emis * (1 + 0.25 * math.sin(tt * 4)) + 0.2))
        arbre = uneix(parts)
        arbre = arbre.copia(pos=arbre.pos * S)
        regals = [local.copia(pos=local.pos * 1.6 + base * S) for base, local, _ in E.regals]
        arbre = uneix([arbre] + regals)
        # Llumetes com a punts brillants (dos punts per bombeta, perquè es vegin)
        ll = E.llums_pos * S
        col = E.llums_col * (0.35 + 0.65 * intens)[:, None] + 0.25 * intens[:, None]
        emis = 0.35 + 1.6 * intens
        bombetes = particules(np.concatenate([ll, ll + [0, 0.05 * S, 0]]), np.concatenate([col, col]), np.concatenate([emis, emis * 0.6]))
        return uneix([arbre, bombetes])

    # --- neu
    def _neu(self, t, centre):
        """Neu al voltant de la càmera: flocs llunyans (punts) i propers (creuetes que es veuen grans)."""
        rng = np.random.default_rng(77)
        n = 2600
        base = rng.random((n, 3))
        caixa = np.array([44.0, 22.0, 44.0])
        p = (base - 0.5) * caixa
        y0 = max(0.0, float(self.C[1]) - caixa[1] / 2)
        p[:, 1] = y0 + np.mod(base[:, 1] * caixa[1] - t * (0.8 + 0.6 * base[:, 0]), caixa[1])
        p[:, 0] += 0.4 * np.sin(t * 0.7 + base[:, 2] * 9)
        p[:, 2] += 0.4 * np.cos(t * 0.5 + base[:, 0] * 9)
        p[:, [0, 2]] = np.mod(p[:, [0, 2]] - centre[[0, 2]] + caixa[[0, 2]] / 2, caixa[[0, 2]]) + centre[[0, 2]] - caixa[[0, 2]] / 2
        fina = particules(p, (0.86, 0.9, 0.98), 0.45 + 0.3 * base[:, 2])
        m = 260
        b2 = rng.random((m, 3))
        caixa2 = np.array([10.0, 6.0, 10.0])
        q = (b2 - 0.5) * caixa2
        q[:, 1] = np.mod(b2[:, 1] * caixa2[1] - t * 0.9, caixa2[1]) - 1.0
        q[:, [0, 2]] = np.mod(q[:, [0, 2]] + caixa2[[0, 2]] / 2, caixa2[[0, 2]]) - caixa2[[0, 2]] / 2
        q += self.C + (self.Rcam[2] * 4.5)
        creu = np.concatenate([q + dlt for dlt in ([0, 0, 0], [0.025, 0, 0], [-0.025, 0, 0], [0, 0.025, 0], [0, -0.025, 0])])
        grossa = particules(creu, (0.92, 0.95, 1.0), 0.6)
        return uneix([fina, grossa])

    # --- escenes
    def grups(self, t):
        if t < ESCENES[1][0]:
            return self._escena1(t - ESCENES[0][0])
        if t < ESCENES[2][0]:
            return self._escena2(t - ESCENES[1][0])
        if t < ESCENES[3][0]:
            return self._escena3(t - ESCENES[2][0])
        if t < ESCENES[4][0]:
            return self._escena4(t - ESCENES[3][0])
        return self._escena5(t - ESCENES[4][0])

    def _llums_carrer(self, t):
        f = self.llums_carrer_f
        brill = 1.0 + 0.7 * (np.sin(TAU * (t * 0.8 + f)) > -0.3)
        col = np.where((np.arange(len(f)) % 3 == 0)[:, None], [1.0, 0.72, 0.35], [1.0, 0.92, 0.7])
        mot = 1.2 + 0.5 * np.clip(np.sin(TAU * (t * 0.5 + self.motius[:, 0] * 0.03 + self.motius[:, 1] * 0.2)), 0, 1)
        dalt = [0, 0.06, 0]
        return uneix([particules(np.concatenate([self.llums_carrer, self.llums_carrer + dalt]), np.concatenate([col, col]), np.concatenate([brill, brill])),
                      particules(np.concatenate([self.motius, self.motius + dalt]), np.concatenate([self.motius_col] * 2), np.concatenate([mot, mot]))])

    def _escena1(self, t):
        """El cotxe baixa pel carrer. Càmera darrere i a l'esquerra, mirant cap a la Sagrada Família."""
        self.amb, self.difusa, self.exposicio, self.boira = 0.12, 0.7, 1.0, (9.0, 16.0)
        v = 8.0
        x = 8 + v * t
        z = 1.7
        bot = 0.02 * math.sin(t * 13) + 0.015 * math.sin(t * 21)
        cotxe = [mou(self.carrosseria, None, (x, bot, z))]
        angle = -v * t / 0.33
        for p in self.rodes_pos:
            cotxe.append(mou(self.roda, Rz(angle), np.array(p) + [x, 0, z]))
        cotxe.append(particules(self.feix + [x, bot, z], (1, 0.92, 0.65), 0.22 * (1 - self.feix_s) ** 1.5))
        # Càmera: comença baixa i a prop, després s'enlaira una mica per veure el carrer
        p = suau(t / 14)
        C = np.array([x - mescla(6.2, 7.6, p), mescla(2.2, 2.9, p), mescla(-0.1, 0.5, p)])
        T = np.array([x + mescla(4.0, 8.0, p), mescla(0.55, 1.5, p), 1.5])
        self.posa_camera(C, T, 56)
        return uneix([self.carrer, *cotxe, self._llums_carrer(t), self._neu(t, C)])

    def _escena2(self, t):
        """La parella passeja per la vorera sota els llums. Càmera davant i al costat, acompanyant-los."""
        self.amb, self.difusa, self.exposicio, self.boira = 0.16, 0.9, 1.15, (9.0, 16.0)
        vel = 1.15
        x = 150 + vel * t
        pos = np.array([x, 0.15, 4.9])
        fase = TAU * 0.95 * t
        gent = parella(self.dens_a(3.5), pos, 0.0, fase, 'camina')
        p = suau(t / 13)
        C = np.array([x + mescla(4.4, 3.6, p), mescla(0.95, 1.1, p), mescla(2.2, 2.7, p)])
        T = np.array([x + 0.2, 1.55, 5.2])
        self.posa_camera(C, T, 60)
        return uneix([self.carrer, gent, self._llums_carrer(t + 14), self._neu(t + 14, C)])

    def _escena3(self, t):
        """Patinen junts a la pista de gel, amb l'arbre gegant al fons."""
        self.amb, self.difusa, self.exposicio, self.boira = 0.16, 1.0, 1.1, (28.0, 45.0)
        c = self.pista_c
        th = -math.pi / 2 + 0.45 * t
        R0 = 3.2
        pos = c + np.array([R0 * math.cos(th), 0.02, R0 * math.sin(th)])
        rumb = -(th + math.pi / 2)
        fase = TAU * 0.8 * t
        gent = parella(self.dens_a(4.5), pos, rumb, fase, 'patina', separacio=0.7)
        k = np.arange(1, 60)
        thr = th - k * 0.03
        rastre = c + np.column_stack([R0 * np.cos(thr), np.full(len(k), 0.03), R0 * np.sin(thr)])
        rastre = np.concatenate([rastre + [0, 0, 0.35], rastre - [0, 0, 0.35]])
        parp = 0.5 + 0.9 * (np.sin(TAU * (t * 0.6 + np.arange(len(self.llums_pista)) * 0.21)) > 0)
        pal = np.array([(1, .85, .45), (1, .3, .25), (.4, 1, .5), (.45, .6, 1), (1, .9, .2)])[np.arange(len(self.llums_pista)) % 5]
        # Càmera que patina davant seu (els veu de cara, l'un al costat de l'altre)
        radial = np.array([math.cos(th), 0, math.sin(th)])
        tangent = np.array([-math.sin(th), 0, math.cos(th)])
        C = pos + tangent * 3.9 + radial * 1.1 + [0, 1.35, 0]
        T = pos + [0, 0.95, 0]
        self.posa_camera(C, T, 60)
        return uneix([self.placa, self.terra_placa, self._arbre_gegant(27 + t), gent,
                      particules(rastre, (0.95, 0.98, 1.0), 0.35 * np.tile(1 - k / 60, 2)),
                      particules(self.llums_pista, pal, parp), self._neu(t + 27, C)])

    def _escena4(self, t):
        """Arriben davant l'arbre gegant; la càmera puja fins a l'estrella i s'obre."""
        self.amb, self.difusa, self.exposicio, self.boira = 0.16, 1.0, 1.1, (30.0, 50.0)
        cami = suau(t / 6)
        pos = mescla([0.0, 0.0, -14.5], [0.0, 0.0, -8.5], cami)
        caminant = t < 6
        fase = TAU * 0.95 * t if caminant else 0.0
        mirada = 0.0 if caminant else 0.45 * suau((t - 6) / 2)
        gent = parella(self.dens_a(6), pos, -math.pi / 2, fase, 'camina' if caminant else 'quiet', mirada=mirada)  # cap a +z (l'arbre)
        # Pla 1 (0–8 s): darrere la parella, mirant l'arbre. Pla 2 (8–17): grua cap a l'estrella.
        # Pla 3 (17–28): volta lenta a l'arbre, sencer, amb la parella petita als peus.
        if t < 8:
            p = suau(t / 8)
            C = mescla([1.8, 1.7, -19.5], [2.2, 1.9, -15.5], p)
            T = mescla(pos + [0, 1.4, 0], [0, 5.5, 0], 0.25 + 0.35 * p)
            fov = 58
        elif t < 17:
            p = suau((t - 8) / 9)
            C = mescla([2.2, 1.9, -15.5], [5.5, 13.0, -17.0], p)
            T = mescla([0, 6.2, 0], [0, 14.0, 0], p)
            fov = 58
        else:
            p = suau((t - 17) / 11)
            ang = mescla(-1.35, -0.55, p)
            C = np.array([27 * math.cos(ang), mescla(8.0, 6.5, p), 27 * math.sin(ang)])
            T = np.array([0, 7.0, 0])
            fov = 52
        self.posa_camera(C, T, fov)
        return uneix([self.placa, self.terra_placa, self._arbre_gegant(40 + t), gent, self._neu(t + 40, C)])

    def _escena5(self, t):
        """Pla final: la càmera s'allunya i s'enlaira; es veu la ciutat, la plaça, l'arbre i la pista,
        i al cel apareix «BON NADAL» en ASCII."""
        self.amb, self.difusa, self.exposicio = 0.16, 1.0, 1.1
        p = suau(t / 13)
        ang = mescla(-0.55, -0.75, p)
        radi = mescla(27, 68, p)
        C = np.array([radi * math.cos(ang), mescla(6.5, 20.0, p), radi * math.sin(ang)])
        T = mescla([0, 7.0, 0], [0, 14.0, -6.0], p)
        self.boira = (mescla(30, 60, p), mescla(50, 110, p))
        self.posa_camera(C, T, mescla(52, 64, p))
        gent = parella(self.dens_a(6), np.array([0.0, 0.0, -8.5]), -math.pi / 2, 0.0, 'quiet', mirada=0.45)
        parp = 0.5 + 0.9 * (np.sin(TAU * (t * 0.6 + np.arange(len(self.llums_pista)) * 0.21)) > 0)
        pal = np.array([(1, .85, .45), (1, .3, .25), (.4, 1, .5), (.45, .6, 1), (1, .9, .2)])[np.arange(len(self.llums_pista)) % 5]
        llums_ciutat = particules(self.fanals_ciutat, (1.0, 0.82, 0.5), 1.1 + 0.2 * np.sin(t * 3 + self.fanals_ciutat[:, 0]))
        self._t5 = t
        terra = self.terra_placa if p < 0.35 else self.terra_placa.copia(np.arange(len(self.terra_placa.pos)) % 4 == 0)
        return uneix([self.placa, terra, self.ciutat, self._arbre_gegant(68 + t), gent, llums_ciutat,
                      particules(self.llums_pista, pal, parp), self._neu(t + 68, C)])

    def superposa(self, t, car, fg, Z):
        """«BON NADAL» al cel, a l'escena final: s'escriu d'esquerra a dreta i brilla."""
        if not (ESCENES[4][0] + 8.5 <= t < DURADA):
            return
        u = t - (ESCENES[4][0] + 8.5)
        lletres, intensitat = self.cartell
        h, w = lletres.shape
        y0 = max(1, int(self.H * 0.06))
        x0 = (self.W - w) // 2
        avanc = min(1.0, u / 2.6) * (w + 6)
        rng = np.random.default_rng(int(t * 9))
        tinta = lletres != ' '
        vora = np.zeros((h + 2, w + 4), bool)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2, 3, 4):
                vora[dy:dy + h, dx:dx + w] |= tinta
        ya, xa = y0 - 1, x0 - 2
        for y in range(h + 2):
            for x in range(w + 4):
                yy, xx = ya + y, xa + x
                if vora[y, x] and x - 2 <= avanc and 0 <= yy < self.H and 0 <= xx < self.W:
                    car[yy, xx] = ' '
                    fg[yy, xx] *= 0.0
        for y in range(h):
            for x in range(w):
                ch = lletres[y, x]
                if ch == ' ' or x > avanc:
                    continue
                aparicio = min(1.0, (avanc - x) / 6)
                ona = 0.78 + 0.22 * math.sin(t * 2.6 - x * 0.09 + y * 0.3)
                k = (0.7 + 0.3 * intensitat[y, x]) * ona * aparicio
                col = np.array([1.0, 0.86, 0.45]) * k + 0.08
                if rng.random() < 0.012:
                    col = np.array([1.0, 1.0, 0.95])
                car[y0 + y, x0 + x] = ch
                fg[y0 + y, x0 + x] = np.clip(col, 0, 1)
        # espurnes al voltant del cartell
        for _ in range(int(14 * min(1.0, u / 2.6))):
            yy = y0 + rng.integers(-2, h + 2)
            xx = x0 + rng.integers(-4, w + 4)
            if 0 <= yy < self.H and 0 <= xx < self.W and car[yy, xx] == ' ':
                car[yy, xx] = rng.choice(['.', '+', '*', "'"])
                fg[yy, xx] = (1.0, 0.92, 0.6)

    def _ciutat(self):
        """Illes de l'Eixample al voltant de la plaça (per al pla final, des de dalt)."""
        rng = np.random.default_rng(11)
        grups, fanals = [], []
        PAS = 56.0
        d = self.dens_a(90) * 0.9
        for i in range(-4, 5):
            for j in range(-4, 4):
                cx, cz = i * PAS, j * PAS - 6
                if math.hypot(cx, cz + 6) < 95:
                    continue
                h = rng.uniform(17, 24)
                g = mou(bloc(rng, (36, h, 36), d, (0.46, 0.41, 0.35), 0.2, sense=('-y', '+y')), Ry(0), (cx, h / 2, cz))
                fin = (np.abs(g.nor[:, 1]) < 0.5) & (np.mod(g.pos[:, 1], 3.0) < 1.3) & \
                      (hash1(np.floor((g.pos[:, 0] + g.pos[:, 2]) / 2.2) * 7 + np.floor(g.pos[:, 1] / 3) * 13 + i * 31 + j) > 0.55)
                g.col[fin] = (1.0, 0.78, 0.45)
                g.emis[fin] = 0.55
                g.ao = g.ao * 0.4
                grups.append(g.copia(fin | (rng.random(len(g.pos)) < 0.15)))
        for k in np.arange(-4.5, 4.6, 1.0):
            for u in np.arange(-240, 240, 9.0):
                fanals.append((k * PAS, 4.5, u - 6))
                fanals.append((u, 4.5, k * PAS - 6))
        f = np.array(fanals)
        lluny = np.hypot(f[:, 0], f[:, 2] + 6) > 88
        self.fanals_ciutat = f[lluny]
        self.ciutat = uneix(grups)

    # --- render amb foses
    def fotograma(self, t):
        car, fg, bg = super().fotograma(t)
        f = min(1.0, t / FOS, (DURADA - t) / (FOS * 1.5))
        for tall in TALLS:
            if abs(t - tall) < FOS:
                f = min(f, abs(t - tall) / FOS)
        if f < 1.0:
            fg = (fg * f).astype(np.uint8)
            bg = (bg * f).astype(np.uint8)
            car = np.where(fg.max(-1) < 12, ' ', car)
        return car, fg, bg


# ---------------------------------------------------------------- Cartell «BON NADAL» en ASCII

def cartell_ascii(text, amplada, alcada):
    """Rasteritza el text amb una lletra gruixuda i el converteix a caràcters ASCII triats per
    forma (com la resta de l'animació). Retorna (caràcters, intensitat) de mida alcada×amplada."""
    from PIL import Image, ImageDraw, ImageFont
    from arbre_giratori import GLIF_CARS, GLIF_MAT, GLIF_N2, RAMPA, SX, SY
    K = 6
    Wp, Hp = amplada * SX * K, alcada * SY * K
    font = None
    for ruta in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                 '/System/Library/Fonts/Supplemental/Arial Bold.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            font = ImageFont.truetype(ruta, 100)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    caixa = ImageDraw.Draw(Image.new('L', (10, 10))).textbbox((0, 0), text, font=font)
    tw, th = caixa[2] - caixa[0], caixa[3] - caixa[1]
    escala = min(Wp / tw, Hp / th) * 0.96
    font = ImageFont.truetype(font.path, int(100 * escala)) if hasattr(font, 'path') else font
    caixa = ImageDraw.Draw(Image.new('L', (10, 10))).textbbox((0, 0), text, font=font)
    im = Image.new('L', (Wp, Hp), 0)
    ImageDraw.Draw(im).text(((Wp - (caixa[2] - caixa[0])) / 2 - caixa[0], (Hp - (caixa[3] - caixa[1])) / 2 - caixa[1]),
                            text, font=font, fill=255)
    a = np.asarray(im, float) / 255
    sub = a.reshape(alcada * SY, K, amplada * SX, K).mean((1, 3))
    L4 = sub.reshape(alcada, SY, amplada, SX).transpose(0, 2, 1, 3).reshape(alcada, amplada, 8)
    tinta = L4 * 0.8
    car = np.full((alcada, amplada), ' ')
    ple = (L4 > 0.5).sum(-1)
    vora = (tinta.sum(-1) > 0.15) & (ple < 8)
    v = tinta[vora]
    dist = (v ** 2).sum(1)[:, None] - 2 * v @ GLIF_MAT.T + GLIF_N2[None, :]
    car[vora] = GLIF_CARS[dist.argmin(1)]
    car[ple >= 8] = RAMPA[-2]
    return car, np.clip(L4.mean(-1) * 1.4, 0.35, 1.0)


# ---------------------------------------------------------------- Sortides

def codifica(car, fg, bg, W):
    regs = []
    for y, x in zip(*np.nonzero(bg.max(-1) >= 8)):
        c = bg[y, x] // 16
        regs.append((y * W + x, 0, (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
    for y, x in zip(*np.nonzero(car != ' ')):
        c = fg[y, x] // 16
        regs.append((y * W + x, ord(car[y, x]), (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
    a = np.zeros(len(regs), dtype=[('cel', '<u4'), ('ch', 'u1'), ('col', '<u2')])
    if regs:
        a['cel'], a['ch'], a['col'] = zip(*regs)
    return a


PLANTILLA = r"""<!doctype html>
<html lang="ca"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nadal a Barcelona</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; color: #8a8478;
               font: 13px ui-monospace, Menlo, Consolas, monospace; }
  [hidden] { display: none !important; }
  body { display: grid; place-items: center; }
  canvas { display: block; }
  #avis { position: fixed; inset: 0; display: grid; place-items: center; }
  #barra { position: fixed; right: 14px; bottom: 12px; display: flex; gap: 8px; opacity: .55; }
  button { font: inherit; color: #bbb; background: transparent; border: 1px solid #333; border-radius: 6px; padding: 5px 10px; cursor: pointer; }
</style></head>
<body>
<canvas id="c" aria-label="Nadal a Barcelona: curtmetratge en ASCII 3D"></canvas>
<div id="avis">carregant… (són uns quants MB)</div>
<div id="barra" hidden><button id="pausa" type="button">pausa</button><button id="inici" type="button">↺ des del principi</button><button id="ple" type="button">pantalla completa (F11)</button></div>
<script>
const W = __W__, H = __H__, FPS = __FPS__, N = __N__;
const OFFSETS = [__OFFSETS__];
const DADES = "__DADES__";
(async () => {
  const avis = document.getElementById('avis');
  let bytes;
  try {
    const s = atob(DADES);
    const bin = new Uint8Array(s.length);
    for (let k = 0; k < s.length; k++) bin[k] = s.charCodeAt(k);
    const flux = new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(flux).arrayBuffer());
  } catch (e) { avis.textContent = "Obre-ho amb Chrome, Edge, Firefox o Safari actualitzat."; return; }
  avis.hidden = true;
  document.getElementById('barra').hidden = false;
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  const colors = Array.from({ length: 4096 }, (_, i) => `rgb(${((i >> 8) & 15) * 17},${((i >> 4) & 15) * 17},${(i & 15) * 17})`);
  const dv = new DataView(bytes.buffer);
  let cw, ch, ultim = -1;
  function mida() {
    const asp = W / (H * 2);
    const w = Math.min(innerWidth, innerHeight * asp), h = w / asp;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    c.style.width = w + 'px'; c.style.height = h + 'px';
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    cw = c.width / W; ch = c.height / H;
    ctx.font = `bold ${ch * 0.86}px ui-monospace, Menlo, Consolas, monospace`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ultim = -1;
  }
  function pinta(i) {
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, c.width, c.height);
    for (let k = OFFSETS[i] * 7, fi = OFFSETS[i + 1] * 7; k < fi; k += 7) {
      const cel = dv.getUint32(k, true), car = bytes[k + 4], col = dv.getUint16(k + 5, true);
      const x = cel % W, y = (cel / W) | 0;
      ctx.fillStyle = colors[col];
      if (car === 0) ctx.fillRect(x * cw, y * ch, cw + 0.5, ch + 0.5);
      else ctx.fillText(String.fromCharCode(car), (x + 0.5) * cw, (y + 0.5) * ch);
    }
  }
  let t = 0, abans = null, pausa = false;
  function frame(ara) {
    if (abans !== null && !pausa) t += Math.min(0.1, (ara - abans) / 1000);
    abans = ara;
    const i = Math.floor(t * FPS) % N;
    if (i !== ultim) { pinta(i); ultim = i; }
    requestAnimationFrame(frame);
  }
  document.getElementById('pausa').onclick = (e) => { pausa = !pausa; e.target.textContent = pausa ? 'continua' : 'pausa'; };
  document.getElementById('inici').onclick = () => { t = 0; ultim = -1; };
  document.getElementById('ple').onclick = () => document.documentElement.requestFullscreen?.().catch(() => {});
  c.onclick = () => document.getElementById('pausa').click();
  addEventListener('resize', mida);
  mida();
  requestAnimationFrame(frame);
})();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description='Nadal a Barcelona: curtmetratge ASCII 3D.')
    ap.add_argument('sortida', nargs='?', default='nadal-a-barcelona.html')
    ap.add_argument('--mida', default='240x68')
    ap.add_argument('--fps', type=int, default=12)
    ap.add_argument('--qualitat', type=float, default=1.0)
    ap.add_argument('--png', help='desa fotogrames de mostra en aquesta carpeta')
    ap.add_argument('--terminal', action='store_true')
    ap.add_argument('--escena', type=int, help='només una escena (1–5)')
    ap.add_argument('--temps', help='amb --png: instants concrets en segons, separats per comes')
    args = ap.parse_args()
    W, H = (int(v) for v in args.mida.lower().split('x'))
    escenes = (args.escena,) if args.escena else (1, 2, 3, 4, 5)
    peli = Pelicula((W, H), args.qualitat, escenes)
    peli.fps = args.fps
    trams = [ESCENES[e - 1] for e in escenes]

    if args.png:
        from escenes3d import desa_png
        os.makedirs(args.png, exist_ok=True)
        if args.temps:
            for t in (float(v) for v in args.temps.split(',')):
                desa_png(peli, os.path.join(args.png, f'peli-t{t:05.1f}.png'), t)
                print(f'  t={t:.1f} desat', file=sys.stderr)
            return
        for e, (a, b) in zip(escenes, trams):
            for k, f in enumerate((0.15, 0.5, 0.9)):
                t = a + (b - a) * f
                desa_png(peli, os.path.join(args.png, f'peli-{e}-{k}.png'), t)
                print(f'  escena {e}: t={t:.1f} desat', file=sys.stderr)
        return

    temps = [t for a, b in trams for t in np.arange(a, b, 1 / peli.fps)]
    fotogrames = []
    inici = time.time()
    for i, t in enumerate(temps):
        fotogrames.append(peli.fotograma(float(t)))
        falta = (time.time() - inici) / (i + 1) * (len(temps) - i - 1)
        print(f'\r  fotograma {i + 1}/{len(temps)} · falten ~{falta / 60:.1f} min   ', end='', file=sys.stderr)
    print(file=sys.stderr)

    if args.terminal:
        from arbre_giratori import a_ansi
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[48;2;0;0;0m\x1b[2J')
        try:
            while True:
                for car, fg, bg in fotogrames:
                    t0 = time.monotonic()
                    sys.stdout.write(a_ansi(car, fg, bg, True))
                    sys.stdout.flush()
                    time.sleep(max(0, 1 / peli.fps - (time.monotonic() - t0)))
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
        return

    blocs, offsets = [], [0]
    for car, fg, bg in fotogrames:
        a = codifica(car, fg, bg, W)
        blocs.append(a.tobytes())
        offsets.append(offsets[-1] + len(a))
    dades = base64.b64encode(gzip.compress(b''.join(blocs), 6)).decode()
    html = (PLANTILLA.replace('__W__', str(W)).replace('__H__', str(H)).replace('__FPS__', str(peli.fps))
            .replace('__N__', str(len(fotogrames))).replace('__OFFSETS__', ','.join(map(str, offsets))).replace('__DADES__', dades))
    with open(args.sortida, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✓ {args.sortida} ({len(html) / 1e6:.1f} MB, {len(fotogrames)} fotogrames)', file=sys.stderr)


if __name__ == '__main__':
    main()
