#!/usr/bin/env python3
"""Uso: python3 escenes3d.py [nom ...] [--png]   (sense noms: totes)

Escenes 3D en ASCII per al calendari, amb el mateix motor que l'arbre (arbre_giratori.py):
núvol de punts 3D → càmera amb perspectiva → z-buffer a subpíxel (2×4 per caràcter) →
llum difusa, especular, contrallum i oclusió → caràcter triat per forma → color 24 bits
i halo (bloom) al voltant de les llums.

Cada escena és un bucle perfecte (tot el que es mou ho fa amb períodes enters dins de
«durada») i s'exporta com a fotogrames a adviento/anim/<fitxer>.json, que el calendari
reprodueix en un canvas (adviento/js/animacions.js).

  --png    a més, desa 3 fotogrames de mostra de cada escena (per revisar-les).

Escenes: cor, cotxe, cotxe-pluja, patins, cafe, avio, marieta, foc, focs.
"""
import json
import math
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from arbre_giratori import (  # noqa: E402
    FARCIMENT, GLIF_CARS, GLIF_MAT, GLIF_N2, LLUM, MIG, RAMPA, SX, SY, TAU, VISTA,
    Grup, _difumina, _norm, estel, uneix,
)

SORTIDA = os.path.join(AQUI, '..', '..', 'adviento', 'anim')


# ---------------------------------------------------------------- Geometria bàsica

def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def mou(g, R=None, t=(0, 0, 0), escala=1.0):
    """Còpia del grup girada (R), escalada i desplaçada."""
    R = np.eye(3) if R is None else R
    return g.copia(pos=(g.pos * escala) @ R.T + np.asarray(t, float), nor=g.nor @ R.T)


def _col(color, pos, nor):
    if callable(color):
        return np.asarray(color(pos, nor), float)
    return np.broadcast_to(np.asarray(color, float), (len(pos), 3)).copy()


def ellipsoide(rng, radis, dens, color, espec=0.6, emis=0.0, ao=1.0, filtre=None):
    rx, ry, rz = radis
    area = 4 * math.pi * ((rx * ry + rx * rz + ry * rz) / 3)
    n = max(24, int(area * dens * 1.3))
    d = _norm(rng.normal(size=(n, 3)))
    pos = d * np.array(radis)
    nor = _norm(d / np.array(radis))
    if filtre is not None:
        m = filtre(pos, nor)
        pos, nor = pos[m], nor[m]
    return Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)


def superellipsoide(rng, radis, e, dens, color, espec=0.6, emis=0.0, ao=1.0, filtre=None):
    """Caixa arrodonida: e≈0.2 molt quadrada, e=1 el·lipsoide."""
    a, b, c = radis
    area = 8 * (a * b + a * c + b * c) / 2
    n = max(40, int(area * dens * 1.6))
    d = _norm(rng.normal(size=(n, 3)))
    sg = lambda v, p: np.sign(v) * np.abs(v) ** p
    pos = np.column_stack([sg(d[:, 0], e) * a, sg(d[:, 1], e) * b, sg(d[:, 2], e) * c])
    q = 2 / e
    nor = _norm(np.column_stack([sg(pos[:, 0] / a, q - 1) / a, sg(pos[:, 1] / b, q - 1) / b, sg(pos[:, 2] / c, q - 1) / c]))
    if filtre is not None:
        m = filtre(pos, nor)
        pos, nor = pos[m], nor[m]
    return Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)


def esfera(rng, radi, dens, color, espec=0.6, **kw):
    return ellipsoide(rng, (radi, radi, radi), dens, color, espec, **kw)


def cilindre(rng, radi, alt, dens, color, espec=0.4, emis=0.0, ao=1.0, tapes=True, dins=False):
    """Cilindre d'eix Y, centrat a l'origen."""
    n = max(16, int(TAU * radi * alt * dens))
    th = rng.random(n) * TAU
    y = (rng.random(n) - 0.5) * alt
    nor = np.column_stack([np.cos(th), np.zeros(n), np.sin(th)])
    pos = nor * radi + np.column_stack([np.zeros(n), y, np.zeros(n)])
    if dins:
        nor = -nor
    grups = [Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)]
    if tapes:
        for s in (1, -1):
            grups.append(mou(disc(rng, radi, dens, color, espec, emis, ao), Rx(0 if s > 0 else math.pi), (0, s * alt / 2, 0)))
    return uneix(grups)


def disc(rng, radi, dens, color, espec=0.4, emis=0.0, ao=1.0, radi_int=0.0):
    """Disc horitzontal (normal +Y) a y=0."""
    n = max(12, int(math.pi * (radi ** 2 - radi_int ** 2) * dens))
    r = np.sqrt(radi_int ** 2 + rng.random(n) * (radi ** 2 - radi_int ** 2))
    th = rng.random(n) * TAU
    pos = np.column_stack([r * np.cos(th), np.zeros(n), r * np.sin(th)])
    nor = np.tile([0, 1.0, 0], (n, 1))
    return Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)


def con(rng, radi, alt, dens, color, espec=0.3, emis=0.0, ao=1.0):
    """Con d'eix Y: base a y=0, punta a y=alt."""
    n = max(20, int(math.pi * radi * math.hypot(radi, alt) * dens))
    s = np.sqrt(rng.random(n))
    th = rng.random(n) * TAU
    r = s * radi
    pos = np.column_stack([r * np.cos(th), alt * (1 - s), r * np.sin(th)])
    nor = _norm(np.column_stack([np.cos(th), np.full(n, radi / alt), np.sin(th)]))
    return Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)


def bloc(rng, mida, dens, color, espec=0.4, emis=0.0, ao=1.0, sense=()):
    """Caixa centrada a l'origen. «sense»: cares a ometre ('+x', '-y', ...)."""
    w, h, d = (m / 2 for m in mida)
    cares = {'+x': ((w, 0, 0), (1, 0, 0), (0, 0, d), (0, h, 0)), '-x': ((-w, 0, 0), (-1, 0, 0), (0, 0, d), (0, h, 0)),
             '+y': ((0, h, 0), (0, 1, 0), (w, 0, 0), (0, 0, d)), '-y': ((0, -h, 0), (0, -1, 0), (w, 0, 0), (0, 0, d)),
             '+z': ((0, 0, d), (0, 0, 1), (w, 0, 0), (0, h, 0)), '-z': ((0, 0, -d), (0, 0, -1), (w, 0, 0), (0, h, 0))}
    grups = []
    for nom, (c, nrm, u, v) in cares.items():
        if nom in sense:
            continue
        u, v = np.array(u, float), np.array(v, float)
        n = max(8, int(4 * np.linalg.norm(u) * np.linalg.norm(v) * dens * 1.2))
        a, b = rng.random(n) * 2 - 1, rng.random(n) * 2 - 1
        pos = np.asarray(c, float) + a[:, None] * u + b[:, None] * v
        nor = np.tile(nrm, (n, 1)).astype(float)
        grups.append(Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao))
    return uneix(grups)


def tor(rng, R, r, dens, color, espec=0.6, emis=0.0, ao=1.0, arc=(0, TAU)):
    """Torus al pla XZ (eix Y)."""
    n = max(16, int(TAU * R * TAU * r * dens * (arc[1] - arc[0]) / TAU))
    u = arc[0] + rng.random(n) * (arc[1] - arc[0])
    v = rng.random(n) * TAU
    centre = np.column_stack([R * np.cos(u), np.zeros(n), R * np.sin(u)])
    nor = np.column_stack([np.cos(u) * np.cos(v), np.sin(v), np.sin(u) * np.cos(v)])
    pos = centre + nor * r
    return Grup(pos, nor, _col(color, pos, nor), espec, emis, ao=ao)


def tub(rng, p0, p1, radi, dens, color, espec=0.3, emis=0.0, ao=1.0):
    """Cilindre prim entre dos punts."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    eix = p1 - p0
    llarg = float(np.linalg.norm(eix))
    g = cilindre(rng, radi, llarg, dens, color, espec, emis, ao, tapes=False)
    d = eix / max(llarg, 1e-9)
    y = np.array([0, 1.0, 0])
    v = np.cross(y, d)
    s, c = np.linalg.norm(v), float(np.dot(y, d))
    if s < 1e-8:
        R = np.eye(3) if c > 0 else Rx(math.pi)
    else:
        k = v / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + math.sin(math.acos(c)) * K + (1 - c) * K @ K
    return mou(g, R, (p0 + p1) / 2)


def particules(pos, color, emis):
    """Punts sense volum que brillen (neu, espurnes, vapor, focs)."""
    n = len(pos)
    return Grup(pos, np.tile(VISTA, (n, 1)), np.broadcast_to(np.asarray(color, float), (n, 3)).copy() if np.ndim(color) == 1 else color,
                0.0, emis, cull=False, part=True)


def avet(rng, alt, dens, neu=True, llums=0):
    """Avet petit: tres pisos de con, tronc, neu a les puntes i, opcionalment, llumetes."""
    grups = [mou(cilindre(rng, alt * 0.05, alt * 0.2, dens, (0.35, 0.22, 0.12)), t=(0, alt * 0.1, 0))]
    for k, (b, h, r) in enumerate([(0.15, 0.5, 0.36), (0.38, 0.42, 0.28), (0.6, 0.4, 0.19)]):
        def color(p, n, k=k):
            c = np.tile([0.08, 0.38, 0.16], (len(p), 1)) * (0.8 + 0.4 * rng.random((len(p), 1)))
            if neu:
                m = (n[:, 1] > 0.35) & (rng.random(len(p)) < 0.35)
                c[m] = [0.88, 0.92, 1.0]
            return c
        grups.append(mou(con(rng, r * alt, h * alt, dens, color, espec=0.25), t=(0, b * alt, 0)))
    g = uneix(grups)
    if llums:
        idx = rng.choice(len(g.pos), size=min(llums, len(g.pos)), replace=False)
        idx = idx[g.pos[idx, 1] > alt * 0.2]
        pal = np.array([(1, .85, .45), (1, .3, .25), (.4, 1, .5), (.45, .6, 1), (1, .9, .2)])
        g.col[idx] = pal[rng.integers(len(pal), size=len(idx))]
        g.emis[idx] = 1.2
    return g


def hash1(n):
    s = np.sin(np.asarray(n, float) * 127.1 + 311.7) * 43758.5453
    return s - np.floor(s)


# ---------------------------------------------------------------- Motor de render

class Escena3D:
    nom = ''
    fitxer = None
    durada = 10.0
    fps = 10
    mida = (64, 30)
    camera = ((0, 2, -6), (0, 0.5, 0))
    fov = 50
    amb = 0.14
    difusa = 1.05
    exposicio = 1.0
    bloom = 0.35
    qualitat = 1.3

    def __init__(self, llavor=11):
        self.W, self.H = self.mida
        C, T = (np.array(v, float) for v in self.camera)
        fwd = _norm(T - C)
        dreta = _norm(np.cross([0, 1.0, 0], fwd))
        amunt = np.cross(fwd, dreta)
        self.Rcam = np.stack([dreta, amunt, fwd])
        self.C = C
        self.dist = float(np.linalg.norm(T - C))
        self.f = (self.W / 2) / math.tan(math.radians(self.fov) / 2)
        self.cx = self.W / 2
        self.r0 = self.H / 2
        self.dens = self.qualitat * (self.f / self.dist * SX) * (0.5 * self.f / self.dist * SY)
        self.rng = np.random.default_rng(llavor)
        self.construeix()

    def construeix(self):
        pass

    def grups(self, t):
        raise NotImplementedError

    def superposa(self, t, car, fg, Z):
        pass

    # --- càmera
    def a_camera(self, p):
        return (np.asarray(p, float) - self.C) @ self.Rcam.T

    def projecta(self, p):
        q = self.a_camera(np.atleast_2d(p))
        return self.cx + self.f * q[:, 0] / q[:, 2], self.r0 - 0.5 * self.f * q[:, 1] / q[:, 2], q[:, 2]

    # --- render
    def fotograma(self, t):
        W, F = self.W, self.H
        G = self.grups(t)
        q = self.a_camera(G.pos)
        n = G.nor @ self.Rcam.T
        n[~G.cull] = VISTA
        z = q[:, 2]
        vista = -q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-9)
        de_cara = np.einsum('ij,ij->i', n, vista) > -0.08
        ok = (z > 0.2) & (de_cara | ~G.cull)
        sc = np.floor((self.cx + self.f * q[:, 0] / np.maximum(z, 1e-6) + 0.0) * SX).astype(np.int64)
        sr = np.floor((self.r0 - 0.5 * self.f * q[:, 1] / np.maximum(z, 1e-6) + 0.0) * SY).astype(np.int64)
        Ws, Hs = W * SX, F * SY
        ok &= (sc >= 0) & (sc < Ws) & (sr >= 0) & (sr < Hs)
        idx = np.nonzero(ok)[0]
        cel = sr[idx] * Ws + sc[idx]
        lluny_primer = np.argsort(-z[idx], kind='stable')
        buf = np.full(Hs * Ws, -1)
        buf[cel[lluny_primer]] = idx[lluny_primer]
        cel_t = np.nonzero(buf >= 0)[0]
        tria = buf[cel_t]

        nn = n[tria]
        dif = np.clip(nn @ LLUM, 0, None)
        farc = np.clip(nn @ FARCIMENT, 0, None) * 0.22
        esp = np.clip(nn @ MIG, 0, None) ** 30 * G.espec[tria]
        contra = (1 - np.abs(np.einsum('ij,ij->i', nn, vista[tria]))) ** 3 * 0.30
        emis = G.emis[tria]
        part = G.part[tria]
        ao = G.ao[tria]
        llum = np.where(part, 0.0, (self.amb + self.difusa * dif + farc + contra) * ao) * self.exposicio
        base = G.col[tria]
        extra = G.extra[tria]
        rgb = base * (llum + emis)[:, None] * 1.1 + esp[:, None] * np.array([1.0, 0.97, 0.90]) * self.exposicio + extra
        rgb += np.where(part, 0, contra * ao * self.exposicio)[:, None] * np.array([0.10, 0.18, 0.38])
        lum = np.clip(llum + emis + esp * 0.7 * self.exposicio + extra.max(1) * 0.6, 0, 1.6)

        L = np.zeros(Hs * Ws)
        C = np.zeros((Hs * Ws, 3))
        E = np.zeros((Hs * Ws, 3))
        Zs = np.full(Hs * Ws, np.inf)
        L[cel_t] = lum
        C[cel_t] = rgb
        Zs[cel_t] = z[tria]
        E[cel_t] = rgb * np.clip(emis - 0.5, 0, None)[:, None]
        L, C, E = L.reshape(Hs, Ws), C.reshape(Hs, Ws, 3), E.reshape(Hs, Ws, 3)
        Z = Zs.reshape(F, SY, W, SX).min(axis=(1, 3))
        _omple_forats(L, C)

        L4 = L.reshape(F, SY, W, SX).transpose(0, 2, 1, 3).reshape(F, W, 8)
        C4 = C.reshape(F, SY, W, SX, 3).transpose(0, 2, 1, 3, 4).reshape(F, W, 8, 3)
        tinta = np.clip(L4, 0, 1.25) * 0.66
        car = np.full((F, W), ' ')
        ple = (L4 > 0).sum(-1)
        vora = (tinta.sum(-1) > 0.03) & (ple < 7)
        v = tinta[vora]
        dist = (v ** 2).sum(1)[:, None] - 2 * v @ GLIF_MAT.T + GLIF_N2[None, :]
        car[vora] = GLIF_CARS[dist.argmin(1)]
        plena = ple >= 7
        car[plena] = RAMPA[np.clip((L4[plena].mean(-1) / 1.25 * len(RAMPA)).astype(int), 0, len(RAMPA) - 1)]
        pes = L4 + 1e-6
        fg = (C4 * pes[..., None]).sum(2) / pes.sum(2)[..., None]
        maxim = fg.max(-1, keepdims=True)
        fg = fg / np.maximum(maxim, 1e-3) * np.clip(0.22 + 0.95 * maxim, 0, 1)

        E4 = E.reshape(F, SY, W, SX, 3).sum((1, 3)) / (SX * SY)
        bg = np.clip(_difumina(E4, 6, 3) * self.bloom, 0, 0.18)
        bg[bg < 0.02] = 0
        self.superposa(t, car, fg, Z)
        return car, (np.clip(fg, 0, 1) * 255).astype(np.uint8), (bg * 255).astype(np.uint8)


def _omple_forats(L, C):
    ple = L > 0
    veins = np.zeros(L.shape, int)
    suma_l = np.zeros(L.shape)
    suma_c = np.zeros(C.shape)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sp = np.roll(ple, (dy, dx), (0, 1))
        veins += sp
        suma_l += np.roll(L, (dy, dx), (0, 1)) * sp
        suma_c += np.roll(C, (dy, dx), (0, 1)) * sp[..., None]
    omple = ~ple & (veins >= 3)
    L[omple] = suma_l[omple] / veins[omple]
    C[omple] = suma_c[omple] / veins[omple][:, None]


def neu_que_cau(llavor, n, caixa, t, durada, color=(0.85, 0.88, 0.96), emis=0.5):
    """Flocs que cauen en bucle perfecte dins d'una caixa ((x0,x1),(y0,y1),(z0,z1))."""
    rng = np.random.default_rng(llavor)                 # mateixos flocs a cada fotograma
    (x0, x1), (y0, y1), (z0, z1) = caixa
    base = rng.random((n, 3))
    voltes = rng.integers(1, 3, size=n)            # cada floc fa 1 o 2 caigudes per bucle
    y = y1 - np.mod(base[:, 1] + voltes * t / durada, 1) * (y1 - y0)
    x = x0 + base[:, 0] * (x1 - x0) + 0.15 * np.sin(TAU * (t / durada) * 3 + base[:, 2] * 9)
    z = z0 + base[:, 2] * (z1 - z0)
    return particules(np.column_stack([x, y, z]), color, emis * (0.6 + 0.4 * base[:, 0]))


# ---------------------------------------------------------------- Escenes

class Cor(Escena3D):
    """💓 Cor de vidre vermell que batega i gira, envoltat d'espurnes."""
    nom = 'cor'
    durada = 12.0
    mida = (56, 34)
    camera = ((0, 0.2, -4.4), (0, 0.0, 0))
    fov = 46

    def construeix(self):
        rng = self.rng
        n = int(4 * math.pi * 1.2 ** 2 * self.dens * 2.2)
        d = _norm(rng.normal(size=(n, 3)))

        def F(p):
            x, y, z = p[:, 0], p[:, 1], p[:, 2]
            return (x * x + 2.25 * z * z + y * y - 1) ** 3 - x * x * y ** 3 - 0.1125 * z * z * y ** 3

        lo, hi = np.zeros(n), np.full(n, 2.0)
        for _ in range(32):
            mig = (lo + hi) / 2
            dins = F(d * mig[:, None]) < 0
            lo, hi = np.where(dins, mig, lo), np.where(dins, hi, mig)
        p = d * lo[:, None]
        e = 1e-4
        g = np.column_stack([F(p + [e, 0, 0]) - F(p - [e, 0, 0]), F(p + [0, e, 0]) - F(p - [0, e, 0]),
                             F(p + [0, 0, e]) - F(p - [0, 0, e])])
        nor = _norm(g)
        col = np.tile([0.80, 0.06, 0.13], (n, 1)) * (0.92 + 0.08 * rng.random((n, 1)))
        self.cor = Grup(p * 1.05, nor, col, 2.2, 0.06)
        k = 90
        self.esp_base = rng.random((k, 4))

    def grups(self, t):
        f = (t % 1.2) / 1.2
        batec = math.exp(-((f - 0.08) ** 2) / 0.002) + 0.6 * math.exp(-((f - 0.26) ** 2) / 0.002)
        s = 1 + 0.09 * batec
        R = Ry(TAU * t / self.durada) @ Rx(0.12)
        cor = mou(self.cor, R, (0, 0, 0), s)
        cor.emis = cor.emis + 0.12 * batec
        b = self.esp_base
        a = b[:, 0] * TAU + TAU * t / self.durada * np.where(b[:, 1] > 0.5, 1, -1)
        r = 1.5 + 0.8 * b[:, 2]
        y = (b[:, 3] - 0.5) * 2.6 + 0.15 * np.sin(TAU * t / self.durada * 2 + b[:, 0] * 7)
        pos = np.column_stack([r * np.cos(a), y, r * np.sin(a) * 0.6])
        brill = np.clip(np.sin(TAU * (t / self.durada * 6 + b[:, 1])), 0, 1) ** 6
        col = np.where(b[:, 2:3] > 0.5, [1.0, 0.75, 0.82], [1.0, 0.85, 0.5])
        return uneix([cor, particules(pos, col, 0.25 + 1.2 * brill)])


class Cotxe(Escena3D):
    """🚗 Cotxe vermell amb un avet al sostre, per una carretera entre avets nevats.
    Amb pluja=True: de nit, pluja, muntanyes nevades i els fars encesos (Andorra)."""
    nom = 'cotxe'
    durada = 8.0
    mida = (80, 36)
    camera = ((3.3, 1.75, -4.6), (0.05, 0.75, 0.2))
    fov = 50
    pluja = False
    qualitat = 1.8

    def construeix(self):
        rng, d = self.rng, self.dens
        if self.pluja:
            self.amb, self.difusa, self.exposicio, self.bloom = 0.12, 0.8, 1.05, 0.5
        r_roda = 0.33
        self.v = TAU * 24 * r_roda / self.durada           # rodes: 24 voltes senceres per bucle
        self.P = self.v * self.durada                      # període de l'escenari
        self.r_roda = r_roda
        vermell = (0.74, 0.06, 0.08)
        vidre = (0.10, 0.16, 0.26)

        def cabina(p, n):
            c = np.tile(vermell, (len(p), 1))
            vidres = (n[:, 1] < 0.75) & (p[:, 1] > -0.05)
            pilars = (np.abs(np.abs(p[:, 0]) - 0.72) < 0.06) | (np.abs(p[:, 0] - 0.05) < 0.05)
            c[vidres & ~pilars] = vidre
            return c

        cos = uneix([
            mou(superellipsoide(rng, (1.42, 0.3, 0.64), 0.35, d, vermell, 1.6), t=(0, 0.62, 0)),
            mou(superellipsoide(rng, (0.8, 0.27, 0.56), 0.5, d, cabina, 2.0, filtre=lambda p, n: p[:, 1] > -0.12), t=(-0.25, 0.98, 0)),
            mou(superellipsoide(rng, (1.45, 0.07, 0.66), 0.3, d, (0.22, 0.22, 0.24), 0.8), t=(0, 0.36, 0)),
        ])
        fars = uneix([mou(ellipsoide(rng, (0.04, 0.09, 0.14), d * 3, (1, 0.95, 0.75), 0, 1.4), t=(1.41, 0.66, s * 0.42)) for s in (1, -1)])
        pilots = uneix([mou(ellipsoide(rng, (0.04, 0.08, 0.13), d * 3, (1, 0.15, 0.1), 0, 1.0), t=(-1.41, 0.66, s * 0.45)) for s in (1, -1)])
        # Avet estirat al sostre (lligat!)
        arbre = mou(avet(rng, 1.4, d, neu=False), Rz(math.pi / 2), (0.55, 1.42, 0))
        corda = uneix([mou(tor(rng, 0.36, 0.015, d * 2, (0.85, 0.8, 0.6)), Rz(math.pi / 2) @ Rx(math.pi / 2), (x, 1.42, 0)) for x in (-0.55, 0.05)])
        self.carrosseria = uneix([cos, fars, pilots, arbre, corda])

        def tapacubs(p, n):
            th = np.arctan2(p[:, 2], p[:, 0])
            r = np.hypot(p[:, 0], p[:, 2])
            c = np.tile([0.75, 0.77, 0.8], (len(p), 1))
            c[(np.cos(5 * th) < 0.55) & (r > 0.07)] = (0.25, 0.26, 0.28)
            return c

        roda = uneix([cilindre(rng, r_roda, 0.26, d, (0.07, 0.07, 0.08), 0.3, tapes=False),
                      mou(disc(rng, 0.22, d * 1.5, tapacubs, 1.2), None, (0, 0.135, 0)),
                      mou(disc(rng, 0.22, d * 1.5, tapacubs, 1.2), Rx(math.pi), (0, -0.135, 0))])
        self.roda = mou(roda, Rx(math.pi / 2))             # eix Y → eix Z
        self.rodes_pos = [(x, r_roda, z) for x in (0.95, -0.95) for z in (0.62, -0.62)]

        # Escenari (es desplaça en -x amb període P)
        P = self.P
        n = int(P * 3.3 * d * 0.14)
        x = (rng.random(n) - 0.5) * P
        z = (rng.random(n) - 0.5) * 3.3
        asfalt = (0.16, 0.16, 0.18) if not self.pluja else (0.09, 0.09, 0.11)
        col = np.tile(asfalt, (n, 1)) * (0.85 + 0.3 * rng.random((n, 1)))
        ratlla = (np.abs(z) < 0.09) & (np.mod(x, P / 24) < P / 48)
        col[ratlla] = (0.85, 0.85, 0.8)
        col[np.abs(np.abs(z) - 1.5) < 0.06] = (0.8, 0.8, 0.75)
        self.carretera = Grup(np.column_stack([x, np.zeros(n), z]), np.tile([0, 1.0, 0], (n, 1)), col,
                              1.6 if self.pluja else 0.15, ao=0.38)
        grups = []
        for costat, (z0, z1) in ((-1, (-2.6, -1.65)), (1, (1.65, 3.2))):
            area = P * (z1 - z0)
            m = int(area * d * 0.12)
            gx = (rng.random(m) - 0.5) * P
            gz = z0 + rng.random(m) * (z1 - z0)
            gcol = np.tile([0.62, 0.66, 0.76], (m, 1)) * (0.7 + 0.3 * rng.random((m, 1)))
            if self.pluja:
                gcol *= 0.55
            grups.append(Grup(np.column_stack([gx, np.zeros(m), gz]), _norm(np.tile([0, 1.0, 0], (m, 1)) + rng.normal(0, 0.1, (m, 3))), gcol, 0.4, ao=0.85))
        self.terra = uneix(grups)
        self.terra.ao *= 0.4
        arbres = []
        for k in range(int(P / 3.2)):
            for z, alt in ((4.2, 2.2), (7.5, 2.8)):
                if rng.random() < 0.8:
                    arbres.append(mou(avet(rng, alt * (0.8 + 0.4 * rng.random()), d * 0.9),
                                      t=(-P / 2 + k * 3.2 + rng.random() * 1.5, 0, z + rng.normal(0, 0.5))))
        self.arbres = uneix(arbres)
        self.arbres.ao *= 0.6
        if self.pluja:
            munts = []
            for k in range(5):
                alt = 9 + rng.random() * 5

                def mcol(p, n, alt=alt):
                    c = np.tile([0.13, 0.15, 0.2], (len(p), 1))
                    c[p[:, 1] > alt * 0.66] = (0.55, 0.58, 0.66)
                    return c
                munts.append(mou(con(rng, 8 + rng.random() * 4, alt, d * 0.12, mcol, 0.0), t=(-22 + k * 11, -1.5, 42 + rng.random() * 6)))
            self.muntanyes = uneix(munts)
            self.muntanyes.ao *= 0.35
            m = 380
            self.gotes = rng.random((m, 3))
            # Feixos de llum dels fars (punts molt tènues davant del cotxe)
            k = 900
            s = rng.random(k)
            self.feix = np.column_stack([1.45 + s * 6, 0.62 + (rng.random(k) - 0.5) * s * 1.0 - s * 0.25,
                                         np.where(rng.random(k) > 0.5, 0.42, -0.42) + (rng.random(k) - 0.5) * s * 1.6])
            self.feix_s = s
        else:
            self.neu_rng = 5

    def grups(self, t):
        P, desp = self.P, self.v * t
        esc = lambda g: g.copia(pos=np.column_stack([np.mod(g.pos[:, 0] - desp + P / 2, P) - P / 2, g.pos[:, 1], g.pos[:, 2]]))
        bot = 0.03 * math.sin(TAU * 16 * t / self.durada) + 0.02 * math.sin(TAU * 27 * t / self.durada)
        grups = [esc(self.carretera), esc(self.terra), esc(self.arbres),
                 mou(self.carrosseria, Rz(0.01 * math.sin(TAU * 16 * t / self.durada)), (0, bot, 0))]
        angle = -self.v * t / self.r_roda
        for p in self.rodes_pos:
            grups.append(mou(self.roda, Rz(angle), p))
        if self.pluja:
            grups.append(self.muntanyes)
            g = self.gotes
            y = 6 - np.mod(g[:, 1] * 6 + 2 * 6 * t / self.durada * 4, 6)
            x = np.mod(g[:, 0] * 18 - 0.35 * (6 - y), 18) - 8
            z = g[:, 2] * 9 - 3
            gotes = [np.column_stack([x + k * 0.04, y + k * 0.18, z]) for k in range(3)]
            grups.append(particules(np.concatenate(gotes), (0.55, 0.68, 0.9), 0.26))
            grups.append(particules(self.feix + [0, bot, 0], (1, 0.92, 0.65), 0.22 * (1 - self.feix_s) ** 1.5))
        else:
            grups.append(neu_que_cau(self.neu_rng, 140, ((-7, 8), (0, 5), (-3, 8)), t, self.durada, emis=0.4))
        return uneix(grups)


class CotxePluja(Cotxe):
    nom = 'cotxe-pluja'
    pluja = True


class Patins(Escena3D):
    """⛸️ Patinadora fent voltes en una pista de gel amb llumetes i un avet al fons."""
    nom = 'patins'
    durada = 10.0
    mida = (80, 36)
    camera = ((0, 2.7, -6.3), (0, 1.0, 1.3))
    fov = 52
    qualitat = 1.6

    def construeix(self):
        rng, d = self.rng, self.dens

        def gel(p, n):
            r = np.hypot(p[:, 0], p[:, 2] - 0.0)
            c = np.tile([0.72, 0.84, 0.95], (len(p), 1)) * (0.9 + 0.1 * rng.random((len(p), 1)))
            c[np.abs(np.mod(r, 0.7) - 0.35) < 0.02] = (0.92, 0.96, 1.0)
            return c
        self.pista = mou(disc(rng, 4.2, d * 0.13, gel, 1.8, ao=0.6), t=(0, 0, 1.0))
        tanca = cilindre(rng, 4.25, 0.4, d, lambda p, n: np.where((p[:, 1] > 0.1)[:, None], [0.75, 0.1, 0.12], [0.95, 0.95, 0.95]),
                         0.6, tapes=False, dins=True)
        self.tanca = mou(tanca, t=(0, 0.2, 1.0))
        self.tanca.ao = self.tanca.ao * 0.6
        k = 70
        a = np.arange(k) / k * TAU
        self.llums_pos = np.column_stack([4.25 * np.cos(a), np.full(k, 0.44), 4.25 * np.sin(a) + 1.0])
        self.llums_col = np.array([(1, .85, .45), (1, .3, .25), (.4, 1, .5), (.45, .6, 1), (1, .9, .2)])[np.arange(k) % 5]
        self.arbre = mou(avet(rng, 3.6, d, llums=140), t=(0, 0, 7.0))
        self.estel = mou(estel(rng, d * 2.5), None, (0, 3.75, 7.0), 0.55)
        self.neu_rng = 8

        # Patinadora (mirant +x): parts fixes
        pell = (0.95, 0.78, 0.65)
        abric = (0.72, 0.09, 0.12)
        self.cap = uneix([
            mou(esfera(rng, 0.13, d * 2, pell, 0.4), t=(0, 1.66, 0)),
            mou(ellipsoide(rng, (0.1, 0.12, 0.13), d * 2, (0.35, 0.2, 0.1), 0.5), t=(-0.05, 1.68, 0)),
            mou(con(rng, 0.13, 0.26, d * 2, abric, 0.3), t=(0, 1.73, 0)),
            mou(tor(rng, 0.13, 0.03, d * 3, (0.95, 0.95, 0.95)), t=(0, 1.74, 0)),
            mou(esfera(rng, 0.05, d * 3, (0.97, 0.97, 0.97)), t=(0, 2.0, 0)),
        ])
        self.cos = uneix([
            mou(ellipsoide(rng, (0.17, 0.32, 0.21), d * 1.5, abric, 0.6), t=(0, 1.2, 0)),
            mou(tor(rng, 0.12, 0.045, d * 3, (0.95, 0.95, 0.95)), t=(0, 1.5, 0)),
            mou(ellipsoide(rng, (0.2, 0.13, 0.23), d * 1.5, abric, 0.5), t=(0, 0.92, 0)),
        ])

    def _patinadora(self, t):
        rng, d = np.random.default_rng(3), self.dens * 1.5
        fase = TAU * 10 * t / self.durada                  # 10 impulsos per volta
        g1, g2 = math.sin(fase), -math.sin(fase)
        parts = [self.cap, self.cos]
        for s, g in ((1, g1), (-1, g2)):                   # cames i patins
            maluc = np.array([0, 0.9, s * 0.1])
            peu = np.array([-0.35 * max(0, g), 0.1 + 0.15 * max(0, g), s * 0.16])
            parts.append(tub(rng, maluc, peu, 0.06, d, (0.12, 0.16, 0.35), 0.3))
            parts.append(mou(bloc(rng, (0.26, 0.16, 0.1), d, (0.95, 0.95, 0.95), 0.5), t=peu + [0.04, -0.02, 0]))
            parts.append(mou(bloc(rng, (0.34, 0.03, 0.03), d, (0.8, 0.82, 0.86), 2.0), t=peu + [0.04, -0.1, 0]))
            espatlla = np.array([0, 1.38, s * 0.19])
            ma = np.array([0.05, 1.18 + 0.05 * g, s * 0.62])
            parts.append(tub(rng, espatlla, ma, 0.045, d, (0.72, 0.09, 0.12), 0.4))
            parts.append(mou(esfera(rng, 0.05, d, (0.95, 0.95, 0.95)), t=ma))
        # Bufanda al vent
        punts = [np.array([-0.12, 1.47, 0.02])]
        for k in range(1, 5):
            punts.append(punts[-1] + [-0.12, -0.03, 0.05 * math.sin(fase * 0.5 + k)])
        for a, b in zip(punts, punts[1:]):
            parts.append(tub(rng, a, b, 0.04, d, (0.95, 0.95, 0.95), 0.3))
        return uneix(parts)

    def grups(self, t):
        th = TAU * t / self.durada
        R0 = 2.4
        pos = np.array([R0 * math.cos(th), 0, R0 * math.sin(th) + 1.0])
        yaw = -(th + math.pi / 2)
        figura = mou(self._patinadora(t), Ry(yaw) @ Rx(0.16), pos, 1.25)
        # Rastre al gel
        k = np.arange(1, 45)
        thr = th - k * 0.035
        rastre = np.column_stack([R0 * np.cos(thr), np.full(len(k), 0.004), R0 * np.sin(thr) + 1.0])
        parpelleig = 0.35 + 0.9 * (np.sin(TAU * (t / self.durada * 5) + np.arange(len(self.llums_pos)) * 0.8) > 0)
        return uneix([
            self.pista, self.tanca, self.arbre, self.estel, figura,
            particules(rastre, (0.95, 0.98, 1.0), 0.35 * (1 - k / 45)),
            particules(self.llums_pos, self.llums_col, parpelleig),
            neu_que_cau(self.neu_rng, 260, ((-7, 7), (0, 6), (-2, 9)), t, self.durada),
        ])


class Cafe(Escena3D):
    """☕ Tassa nadalenca amb un cor de latte, galeta de gingebre i canyella, i vapor."""
    nom = 'cafe'
    durada = 12.0
    mida = (64, 36)
    camera = ((0.3, 2.3, -5.0), (0, 0.85, 0))
    fov = 46
    qualitat = 1.6

    def construeix(self):
        rng, d = self.rng, self.dens

        def tassa(p, n):
            th = np.arctan2(p[:, 2], p[:, 0])
            c = np.tile([0.74, 0.08, 0.11], (len(p), 1))
            y = p[:, 1]
            c[np.abs(y + 0.32) < 0.07] = (0.96, 0.95, 0.93)
            c[np.abs(y - 0.47) < 0.04] = (0.96, 0.95, 0.93)
            flocs = (np.abs(np.sin(7 * th)) > 0.985) & (np.abs(y - 0.08) < 0.18)
            c[flocs] = (0.97, 0.97, 0.97)
            return c

        def latte(p, n):
            u, w = p[:, 0] / 0.36, -p[:, 2] / 0.36 + 0.25
            cor = (u * u + w * w - 1) ** 3 - u * u * w ** 3 < 0
            c = np.tile([0.36, 0.2, 0.1], (len(p), 1))
            c[cor] = (0.94, 0.86, 0.72)
            anell = np.hypot(p[:, 0], p[:, 2]) > 0.62
            c[anell] = (0.75, 0.55, 0.36)
            return c

        self.tassa = uneix([
            mou(cilindre(rng, 0.8, 1.3, d, tassa, 1.2, tapes=False), t=(0, 0.71, 0)),
            mou(cilindre(rng, 0.74, 0.18, d, (0.95, 0.93, 0.9), 0.8, tapes=False, dins=True), t=(0, 1.27, 0)),
            mou(tor(rng, 0.77, 0.035, d * 2, (0.96, 0.95, 0.93), 1.2), t=(0, 1.36, 0)),
            mou(disc(rng, 0.74, d * 1.3, latte, 0.9), t=(0, 1.2, 0)),
            mou(tor(rng, 0.33, 0.09, d * 2, (0.74, 0.08, 0.11), 1.2, arc=(-math.pi / 2, math.pi / 2)), Rx(math.pi / 2), (0.8, 0.72, 0)),
        ])
        plat = lambda p, n: np.where((np.hypot(p[:, 0], p[:, 2]) > 1.33)[:, None], [0.85, 0.68, 0.3], [0.95, 0.94, 0.92])
        self.plat = uneix([disc(rng, 1.45, d, plat, 1.0), mou(tor(rng, 1.45, 0.045, d * 2, (0.85, 0.68, 0.3), 1.2), t=(0, 0.02, 0))])
        galeta = estel(rng, d * 2.4)
        galeta.col[:] = (0.62, 0.38, 0.18)
        galeta.emis[:] = 0
        galeta.espec[:] = 0.4
        vora = galeta.nor[:, 2] == 0
        galeta.col[vora] = (0.97, 0.96, 0.92)                    # glaç blanc a la vora
        self.galeta = mou(galeta, Ry(0.4) @ Rx(-math.pi / 2), (-1.05, 0.08, -0.55), 1.1)
        self.canyella = uneix([mou(cilindre(rng, 0.06, 0.95, d * 2, (0.55, 0.3, 0.15), 0.3), Ry(0.6) @ Rz(math.pi / 2), (0.95, 0.07 + k * 0.1, -0.85 + k * 0.08)) for k in range(2)])
        n = int(math.pi * 2.6 ** 2 * d * 0.2)
        r = 2.6 * np.sqrt(rng.random(n))
        a = rng.random(n) * TAU
        x, z = r * np.cos(a), r * np.sin(a)
        fusta = np.tile([0.2, 0.12, 0.07], (n, 1)) * (1 - 0.6 * (r / 2.6) ** 2)[:, None]
        fusta = fusta * (0.75 + 0.25 * (0.5 + 0.5 * np.sin(z * 9 + np.sin(x * 1.3) * 2)))[:, None]
        self.taula = Grup(np.column_stack([x, np.full(n, -0.01), z]), np.tile([0, 1.0, 0], (n, 1)), fusta, 0.5, ao=0.35)
        self.vapor = rng.random((700, 4))

    def grups(self, t):
        R = Ry(TAU * t / self.durada)
        v = self.vapor
        a = np.mod(v[:, 0] + 3 * t / self.durada, 1)
        col = np.floor(v[:, 1] * 3)
        x0 = (col - 1) * 0.25
        alt = a * 2.2
        x = x0 + np.sin(a * 6 + col * 2 + TAU * t / self.durada * 2) * 0.22 * (0.3 + a) + (v[:, 2] - 0.5) * 0.12
        z = (v[:, 3] - 0.5) * 0.3 + np.cos(a * 5 + col) * 0.12 * a
        brill = 0.5 * (1 - a) * np.clip(a * 6, 0, 1)
        return uneix([self.taula, self.plat, self.galeta, self.canyella, mou(self.tassa, R),
                      particules(np.column_stack([x, 1.3 + alt, z]), (0.88, 0.88, 0.9), brill)])


class Avio(Escena3D):
    """✈️ Avió de nit entre núvols il·luminats per la lluna, camí de Budapest."""
    nom = 'avio'
    durada = 10.0
    mida = (80, 36)
    camera = ((-4.3, 1.5, -5.6), (0.5, -0.05, 0))
    fov = 54
    qualitat = 1.5
    amb = 0.10
    difusa = 0.85

    def construeix(self):
        rng, d = self.rng, self.dens
        blanc = (0.9, 0.91, 0.94)
        fus = ellipsoide(rng, (2.3, 0.35, 0.35), d * 1.2, blanc, 1.4)
        fin = (np.abs(fus.pos[:, 1] - 0.09) < 0.05) & (np.mod(fus.pos[:, 0], 0.24) < 0.12) & (np.abs(fus.pos[:, 0]) < 1.6)
        fus.col[fin] = (1.0, 0.85, 0.5)
        fus.emis[fin] = 0.9
        cabina = (fus.pos[:, 0] > 1.85) & (fus.pos[:, 1] > 0.05)
        fus.col[cabina] = (0.1, 0.14, 0.22)
        self.avio = uneix([
            fus,
            mou(bloc(rng, (1.05, 0.06, 4.8), d, blanc, 1.0), Ry(0.0), (0.1, -0.1, 0)),
            mou(bloc(rng, (0.75, 0.85, 0.06), d, (0.75, 0.1, 0.12), 1.0), Rz(-0.35), (-1.95, 0.5, 0)),
            mou(bloc(rng, (0.5, 0.05, 1.6), d, blanc, 1.0), t=(-1.95, 0.08, 0)),
            mou(cilindre(rng, 0.17, 0.65, d, (0.6, 0.62, 0.66), 1.2), Rz(math.pi / 2), (0.35, -0.32, 1.25)),
            mou(cilindre(rng, 0.17, 0.65, d, (0.6, 0.62, 0.66), 1.2), Rz(math.pi / 2), (0.35, -0.32, -1.25)),
        ])
        self.v = 4.0
        self.P = self.v * self.durada
        nuvols = []
        for k in range(10):
            centre = np.array([(k / 10 - 0.5) * self.P + rng.normal(0, 1), rng.choice([-2.6, -2.2, 2.4]) + rng.normal(0, 0.3), rng.uniform(2, 14)])
            for j in range(6):
                r = rng.uniform(0.5, 1.2)
                nuvols.append(mou(esfera(rng, r, d * 0.5, (0.45, 0.5, 0.62), 0.0, ao=0.55), t=centre + rng.normal(0, [1.1, 0.25, 0.5])))
        self.nuvols = uneix(nuvols)
        self.lluna = mou(esfera(rng, 1.5, d * 0.6, (1.0, 0.96, 0.82), 0.0, emis=1.1), t=(9, 6.5, 26))
        n = 260
        dirs = rng.random((n, 3))
        self.estels = np.column_stack([(dirs[:, 0] - 0.5) * 60, dirs[:, 1] * 22 - 2, 40 + dirs[:, 2] * 5])
        self.estels_f = rng.random(n)

    def grups(self, t):
        u = t / self.durada
        R = Rx(0.12 * math.sin(TAU * u)) @ Rz(0.04 * math.sin(TAU * u * 2))
        bob = (0, 0.12 * math.sin(TAU * u * 2), 0)
        avio = mou(self.avio, R, bob)
        nav = np.array([[0.1, -0.1, -2.4], [0.1, -0.1, 2.4], [-2.2, 0.95, 0]]) @ R.T + bob
        estrob = 1.6 if (t * 1.0) % 1 < 0.12 else 0.0
        llums = uneix([particules(nav[:1], (1, 0.2, 0.15), 1.3), particules(nav[1:2], (0.3, 1, 0.4), 1.3),
                       particules(nav[2:], (1, 1, 1), estrob)])
        P = self.P
        nuv = self.nuvols.copia(pos=np.column_stack([np.mod(self.nuvols.pos[:, 0] - self.v * t + P / 2, P) - P / 2,
                                                     self.nuvols.pos[:, 1], self.nuvols.pos[:, 2]]))
        brill = 0.25 + 0.55 * np.clip(np.sin(TAU * (u * 3 + self.estels_f)), 0, 1) ** 4
        return uneix([self.lluna, nuv, avio, llums, particules(self.estels, (0.9, 0.92, 1.0), brill)])


class Marieta(Escena3D):
    """🐞 La marieta (el bitxo) passejant per una fulla amb gotes de rosada."""
    nom = 'marieta'
    durada = 10.0
    mida = (72, 36)
    camera = ((0.5, 1.9, -3.3), (0, 0.25, 0.15))
    fov = 52
    qualitat = 1.6

    @staticmethod
    def alt_fulla(x, z):
        return -0.06 * x * x + 0.16 * np.abs(z) - 0.05 * z * z

    def construeix(self):
        rng, d = self.rng, self.dens
        n = int(math.pi * 3.2 * 1.6 * d * 0.28)
        x = (rng.random(n) - 0.5) * 6.4
        z = (rng.random(n) - 0.5) * 3.2
        m = (x / 3.2) ** 2 + (z / (1.6 * (1 - 0.25 * (x / 3.2)))) ** 2 < 1
        x, z = x[m], z[m]
        y = self.alt_fulla(x, z)
        e = 1e-3
        dx = (self.alt_fulla(x + e, z) - self.alt_fulla(x - e, z)) / (2 * e)
        dz = (self.alt_fulla(x, z + e) - self.alt_fulla(x, z - e)) / (2 * e)
        nor = _norm(np.column_stack([-dx, np.ones(len(x)), -dz]))
        col = np.tile([0.17, 0.46, 0.15], (len(x), 1)) * (0.85 + 0.15 * rng.random((len(x), 1)))
        col[np.abs(z) < 0.035] = (0.5, 0.74, 0.34)
        venes = np.abs(np.mod(x * 0.9 + np.abs(z) * 1.2, 0.8) - 0.4) < 0.022
        col[venes] = (0.36, 0.62, 0.27)
        self.fulla = Grup(np.column_stack([x, y, z]), nor, col, 0.7, ao=0.38)
        gotes = []
        for (gx, gz, r) in ((-1.9, 0.7, 0.11), (1.2, -0.9, 0.09), (2.2, 0.3, 0.07), (-0.6, -1.05, 0.08), (0.4, 1.0, 0.1)):
            gotes.append(mou(ellipsoide(rng, (r, r * 0.7, r), d * 4, (0.75, 0.86, 0.95), 3.0, 0.08,
                                        filtre=lambda p, n: p[:, 1] > -0.01), t=(gx, float(self.alt_fulla(np.array(gx), np.array(gz))), gz)))
        self.gotes = uneix(gotes)
        flors = []
        for (fx, fz, h) in ((-2.6, 2.4, 1.1), (-0.8, 3.2, 1.5), (1.6, 2.8, 1.25), (3.0, 1.8, 0.9)):
            parts = [tub(rng, (0, 0, 0), (0, h, 0), 0.03, d, (0.2, 0.5, 0.2)), mou(esfera(rng, 0.13, d * 2, (0.98, 0.8, 0.2), 0.5), t=(0, h, 0))]
            for k in range(12):
                a = k / 12 * TAU
                parts.append(mou(ellipsoide(rng, (0.22, 0.03, 0.07), d * 2, (0.97, 0.97, 0.95), 0.5), Ry(-a), (0.24 * math.cos(a), h, 0.24 * math.sin(a))))
            flors.append(mou(uneix(parts), Rx(-0.5), (fx, -0.3, fz)))
        self.flors = uneix(flors)
        self.flors.ao *= 0.6

        # Marieta (mirant +x)
        taques = _norm(np.array([[0.35, 0.6, 0.45], [0.35, 0.6, -0.45], [-0.2, 0.75, 0.5], [-0.2, 0.75, -0.5],
                                 [-0.55, 0.5, 0.35], [-0.55, 0.5, -0.35], [0.55, 0.8, 0.0]]))

        def closca(p, n):
            u = _norm(p / np.array([0.55, 0.38, 0.46]))
            c = np.tile([0.85, 0.08, 0.06], (len(p), 1))
            c[(u @ taques.T).max(1) > math.cos(0.2)] = (0.04, 0.03, 0.03)
            c[(np.abs(p[:, 2]) < 0.022) & (p[:, 0] < 0.38)] = (0.04, 0.03, 0.03)
            return c
        self.closca = mou(ellipsoide(rng, (0.55, 0.38, 0.46), d * 3, closca, 2.4, filtre=lambda p, n: p[:, 1] > -0.02), t=(0, 0.12, 0))
        self.cap = uneix([
            mou(ellipsoide(rng, (0.16, 0.15, 0.2), d * 3, (0.05, 0.05, 0.06), 1.2), t=(0.55, 0.14, 0)),
            mou(esfera(rng, 0.045, d * 6, (0.97, 0.97, 0.97), 1.5), t=(0.66, 0.21, 0.09)),
            mou(esfera(rng, 0.045, d * 6, (0.97, 0.97, 0.97), 1.5), t=(0.66, 0.21, -0.09)),
        ] + [tub(rng, (0.62, 0.22, s * 0.06), (0.86, 0.44, s * 0.2), 0.012, d * 6, (0.05, 0.05, 0.06)) for s in (1, -1)]
          + [mou(esfera(rng, 0.03, d * 6, (0.05, 0.05, 0.06)), t=(0.86, 0.44, s * 0.2)) for s in (1, -1)])

    def grups(self, t):
        rng, d = np.random.default_rng(4), self.dens * 5
        th = TAU * t / self.durada
        px, pz = 0.9 * math.cos(th), 0.38 * math.sin(th)
        py = float(self.alt_fulla(np.array(px), np.array(pz)))
        yaw = -math.atan2(0.38 * math.cos(th), -0.9 * math.sin(th))
        potes = []
        for i, xb in enumerate((0.25, 0.0, -0.25)):
            for s in (1, -1):
                fase = TAU * 20 * t / self.durada + (math.pi if (i + (s > 0)) % 2 else 0)
                peu = (xb + 0.09 * math.sin(fase), -0.1 + 0.04 * max(0, math.cos(fase)), s * 0.5)
                potes.append(tub(rng, (xb, 0.1, s * 0.3), peu, 0.018, d, (0.05, 0.05, 0.06)))
        bitxo = mou(uneix([self.closca, self.cap] + potes), Ry(yaw), (px, py + 0.27, pz), 1.35)
        return uneix([self.fulla, self.gotes, self.flors, bitxo])


class Foc(Escena3D):
    """🔥 Primer pla d'una llar de foc: troncs sobre una graella, flames, brases que bateguen,
    espurnes que pugen i pedres il·luminades pel foc."""
    nom = 'foc'
    durada = 6.0
    mida = (72, 38)
    camera = ((0.9, 1.35, -3.3), (0, 0.85, 0.45))
    fov = 52
    amb = 0.05
    difusa = 0.35
    bloom = 0.5
    qualitat = 1.6

    def construeix(self):
        rng, d = self.rng, self.dens
        # Pedres de la llar (arrodonides) en semicercle i terra de pedra
        pedres = []
        for k in range(11):
            a = math.pi * (0.05 + 0.9 * k / 10)
            r = 1.55
            mida = (rng.uniform(0.22, 0.32), rng.uniform(0.13, 0.2), rng.uniform(0.18, 0.26))
            col = np.array([0.42, 0.38, 0.35]) * rng.uniform(0.8, 1.1)
            pedres.append(mou(superellipsoide(rng, mida, 0.6, d, col, 0.3), Ry(rng.uniform(0, 3)),
                              (r * math.cos(a), mida[1] * 0.8, 0.45 + r * math.sin(a) * 0.75)))
        n = int(math.pi * 1.7 ** 2 * d * 0.25)
        rr = 1.7 * np.sqrt(rng.random(n))
        aa = rng.random(n) * TAU
        terra = Grup(np.column_stack([rr * np.cos(aa), np.zeros(n), 0.45 + rr * np.sin(aa) * 0.75]),
                     np.tile([0, 1.0, 0], (n, 1)), np.tile([0.3, 0.27, 0.25], (n, 1)), 0.2, ao=0.45)
        cendra = Grup(np.column_stack([(rng.random(n // 2) - 0.5) * 1.4, np.full(n // 2, 0.01), 0.45 + (rng.random(n // 2) - 0.5) * 0.7]),
                      np.tile([0, 1.0, 0], (n // 2, 1)), np.tile([0.25, 0.23, 0.22], (n // 2, 1)), 0.1, ao=0.45)
        # Graella de ferro
        ferro = (0.16, 0.16, 0.18)
        graella = [tub(rng, (x, 0.18, 0.15), (x, 0.18, 0.8), 0.022, d * 3, ferro, 1.0) for x in np.linspace(-0.6, 0.6, 7)]
        graella += [tub(rng, (-0.68, 0.18, z), (0.68, 0.18, z), 0.025, d * 3, ferro, 1.0) for z in (0.15, 0.8)]
        graella += [tub(rng, (s * 0.68, 0.0, z), (s * 0.68, 0.18, z), 0.025, d * 3, ferro, 1.0) for s in (-1, 1) for z in (0.15, 0.8)]

        def escorca(p, n):
            c = np.tile([0.32, 0.19, 0.1], (len(p), 1)) * (0.75 + 0.35 * rng.random((len(p), 1)))
            talls = np.abs(p[:, 1]) > 0.8 * np.abs(p[:, 1]).max()
            c[talls] = (0.6, 0.45, 0.3)
            return c
        self.troncs = uneix([
            mou(cilindre(rng, 0.15, 1.5, d * 1.5, escorca, 0.25), Rz(math.pi / 2), (0, 0.36, 0.35)),
            mou(cilindre(rng, 0.14, 1.4, d * 1.5, escorca, 0.25), Rz(math.pi / 2), (0, 0.36, 0.65)),
            mou(cilindre(rng, 0.13, 1.3, d * 1.5, escorca, 0.25), Ry(0.5) @ Rz(math.pi / 2.4), (0.05, 0.6, 0.5)),
            mou(cilindre(rng, 0.12, 1.2, d * 1.5, escorca, 0.25), Ry(-0.6) @ Rz(-math.pi / 2.4), (-0.05, 0.62, 0.48)),
        ])
        self.estatic = uneix(pedres + [terra, cendra] + graella)
        self.brases = rng.choice(len(self.troncs.pos), size=len(self.troncs.pos) // 7, replace=False)
        self.brases_f = rng.random(len(self.brases))
        tot = uneix([self.estatic, self.troncs])
        dist = np.linalg.norm(tot.pos - [0, 0.75, 0.5], axis=1)
        self.pes_foc = 1 / (1 + (dist / 0.75) ** 2)
        self.n_estatic = len(self.estatic.pos)
        k = 2400
        self.flama = rng.random((k, 5))
        self.flama_per = np.array([6, 7, 8, 9])[rng.integers(4, size=k)]
        self.espurnes = rng.random((70, 4))

    def grups(self, t):
        u = t / self.durada
        tremol = 0.8 + 0.12 * math.sin(TAU * 7 * u) + 0.08 * math.sin(TAU * 13 * u + 1)
        tot = uneix([self.estatic, self.troncs])
        tot.extra = (self.pes_foc * tremol)[:, None] * np.array([1.0, 0.45, 0.12]) * 0.9
        br = self.n_estatic + self.brases
        tot.col[br] = (1.0, 0.42, 0.08)
        tot.emis[br] = 0.45 + 0.75 * np.clip(np.sin(TAU * (u * 5 + self.brases_f)), 0, 1)
        f = self.flama
        a = np.mod(f[:, 0] + u * self.flama_per, 1)
        llengua = np.floor(f[:, 1] * 9)
        cx = -0.6 + llengua * 0.15 + 0.05 * np.sin(TAU * (u * 2 + llengua * 0.3))
        hmax = (0.7 + 0.8 * hash1(llengua * 3.7 + np.floor(u * 3))) * (1.2 - np.abs(cx) * 0.7)
        alt = a * hmax
        ample = 0.12 * (1 - a) ** 0.7 + 0.015
        x = cx + (f[:, 4] - 0.5) * 2 * ample + 0.06 * a * np.sin(TAU * (a * 1.5 + u * 3 + llengua * 0.2))
        z = 0.35 + f[:, 3] * 0.35
        col = np.where(a[:, None] < 0.2, [1.0, 0.95, 0.7], np.where(a[:, None] < 0.45, [1.0, 0.7, 0.2],
                                                                     np.where(a[:, None] < 0.75, [0.97, 0.38, 0.08], [0.55, 0.13, 0.04])))
        flames = particules(np.column_stack([x, 0.5 + alt, z]), col, 1.3 * (1 - a) ** 0.9)
        e = self.espurnes
        ae = np.mod(e[:, 0] + u * 2, 1)
        esp = np.column_stack([(e[:, 1] - 0.5) * 0.9 + 0.15 * np.sin(TAU * (ae + e[:, 2])), 0.7 + ae * 2.2, 0.3 + e[:, 3] * 0.4])
        return uneix([tot, flames, particules(esp, (1.0, 0.75, 0.3), 1.1 * (1 - ae) * (ae > 0.05))])


class Focs(Escena3D):
    """🎆 Focs artificials sobre una ciutat nevada i, després, una estrella fugaz amb «BON NADAL»."""
    nom = 'focs'
    durada = 17.0
    mida = (80, 38)
    camera = ((0, 2.6, -11.5), (0, 5.0, 4))
    fov = 62
    amb = 0.08
    difusa = 0.5
    bloom = 0.45
    text = 'BON NADAL'

    def construeix(self):
        rng, d = self.rng, self.dens
        edificis = []
        x = -17.0
        while x < 17:
            w = rng.uniform(1.2, 2.6)
            h = rng.uniform(1.8, 6.5)
            z = rng.uniform(11, 15)

            def facana(p, n, h=h):
                c = np.tile([0.1, 0.12, 0.18], (len(p), 1))
                fin = (n[:, 2] < -0.5) & (np.mod(p[:, 0] + 5, 0.45) < 0.2) & (np.mod(p[:, 1] + h / 2, 0.6) < 0.3) & (p[:, 1] < h / 2 - 0.3)
                c[fin] = (0.08, 0.09, 0.12)
                return c
            g = mou(bloc(rng, (w, h, 2), d * 0.5, facana, 0.3, sense=('+z',)), t=(x + w / 2, h / 2, z))
            fin = (g.nor[:, 2] < -0.5) & (np.mod(g.pos[:, 0] + 5, 0.45) < 0.2) & (np.mod(g.pos[:, 1], 0.6) < 0.3) & (g.pos[:, 1] < h - 0.3) & (rng.random(len(g.pos)) < 0.9)
            encesa = hash1(np.floor(g.pos[:, 0] / 0.45) * 7 + np.floor(g.pos[:, 1] / 0.6) * 13) > 0.55
            g.col[fin & encesa] = (1.0, 0.8, 0.45)
            g.emis[fin & encesa] = 0.7
            edificis.append(g)
            x += w + rng.uniform(0.0, 0.5)
        n = int(30 * 14 * d * 0.08)
        terra = Grup(np.column_stack([(rng.random(n) - 0.5) * 30, np.zeros(n), rng.random(n) * 14 - 2]),
                     np.tile([0, 1.0, 0], (n, 1)), np.tile([0.7, 0.75, 0.85], (n, 1)), 0.5, ao=0.8)
        self.ciutat = uneix(edificis + [terra, mou(avet(rng, 3.2, d, llums=160), t=(0, 0, 6))])
        self.estel3d = estel(rng, d * 3.0)
        self.esclats = []
        pal = [(1, .82, .4), (1, .42, .55), (.5, .95, .65), (.55, .75, 1), (1, .65, .9), (1, .97, .85)]
        for k, t0 in enumerate([0.5, 1.2, 1.9, 2.5, 3.2, 3.9, 4.5, 5.2]):
            c = np.array([rng.uniform(-7, 7), rng.uniform(5.5, 9.5), rng.uniform(5, 9)])
            m = 340
            dirs = _norm(rng.normal(size=(m, 3)))
            vel = rng.uniform(0.85, 1.1, m)[:, None] * 2.8
            cols = np.array([pal[k % len(pal)], pal[(k + 2) % len(pal)]])[(rng.random(m) < 0.3).astype(int)]
            self.esclats.append((t0, c, dirs * vel, cols))

    def _cua(self, t):
        """Posició de l'estrella i punts de la cua a l'instant t (fase de l'estrella)."""
        u = t - 6.0
        arribada = min(1.0, u / 1.6)
        e = 1 - (1 - arribada) ** 3
        inici, fi = np.array([16.0, 12.0, 6.0]), np.array([-5.2, 3.4, 2.5])
        pos = inici + (fi - inici) * e
        dir_cua = _norm(inici - fi)
        return pos, dir_cua, min(1.0, 0.25 + u * 0.6)

    def grups(self, t):
        grups = [self.ciutat]
        for t0, c, vel, cols in self.esclats:
            a = t - t0
            if -0.9 < a < 0:                                     # coet que puja
                s = (a + 0.9) / 0.9
                p = np.array([[c[0], c[1] * s - k * 0.25, c[2]] for k in range(6)])
                grups.append(particules(p, (1, 0.85, 0.6), np.linspace(1.2, 0.2, 6)))
            elif 0 <= a < 2.2:
                desp = vel * (1 - math.exp(-2.4 * a)) / 2.4
                p = c + desp + [0, -0.55 * a * a, 0]
                brill = 1.6 * (1 - a / 2.2) ** 1.4
                if a > 1.2:
                    brill = brill * (hash1(np.arange(len(p)) + math.floor(t * 12) * 17) > 0.35)
                grups.append(particules(p, cols, brill))
                cua = c + desp * 0.82 + [0, -0.55 * a * a, 0]
                grups.append(particules(cua, cols * 0.8, brill * 0.35))
        if 6.0 <= t < 17.0:
            pos, dir_cua, llarg = self._cua(t)
            apaga = 1.0 if t < 16.0 else max(0.0, 17.0 - t)
            gir = Ry(0.4 * math.sin(t * 1.3)) @ Rz(0.3 * math.sin(t * 0.7))
            estel = mou(self.estel3d, gir, pos, 1.6)
            estel.col[:] = (1.0, 0.85, 0.35)
            estel.emis = estel.emis * apaga + 0.3 * apaga
            grups.append(estel)
            k = 1600
            s = np.linspace(0, 1, k)
            perp = _norm(np.cross(dir_cua, [0, 0, 1.0]))
            fil = np.repeat([-1, 0, 1], k)
            ss = np.tile(s, 3)
            punts = pos + np.outer(ss * 12 * llarg, dir_cua) + np.outer(fil * (0.15 + 0.9 * ss), perp)
            punts += np.column_stack([np.zeros(3 * k), 0.08 * np.sin(ss * 30 + t * 5), np.zeros(3 * k)])
            br = 1.3 * (1 - ss) ** 1.3 * apaga * (hash1(np.arange(3 * k) * 3.1) > ss * 0.7)
            grups.append(particules(punts, np.where(ss[:, None] < 0.35, [1.0, 0.9, 0.55], [0.95, 0.72, 0.32]), br))
        return uneix(grups)

    def superposa(self, t, car, fg, Z):
        if not (6.0 + 1.6 <= t < 16.5):
            return
        pos, dir_cua, llarg = self._cua(t)
        visibles = int((t - 7.6) / 0.16)
        k, n = 2.0, 0
        for paraula in self.text.split(' '):
            centre = pos + dir_cua * (k + len(paraula) * 0.35) * 0.85
            cx, cy, _ = self.projecta(centre)
            fila = int(round(cy[0])) - 1
            x0 = int(round(cx[0] - len(paraula) / 2))
            if n < visibles and 0 <= fila < self.H:
                for i in range(-1, len(paraula) + 1):
                    if 0 <= x0 + i < self.W:
                        car[fila, x0 + i] = ' '
            for i, lletra in enumerate(paraula):
                if n < visibles and 0 <= fila < self.H and 0 <= x0 + i < self.W:
                    car[fila, x0 + i] = lletra
                    fg[fila, x0 + i] = (1.0, 0.97, 0.86)
                n += 1
            k += len(paraula) * 0.7 + 1.6


ESCENES = {c.nom: c for c in (Cor, Cotxe, CotxePluja, Patins, Cafe, Avio, Marieta, Foc, Focs)}


# ---------------------------------------------------------------- Exportació

def exporta(escena, fitxer):
    W, H = escena.W, escena.H
    total = int(round(escena.durada * escena.fps))
    blocs, offsets = [], [0]
    for i in range(total):
        car, fg, bg = escena.fotograma(i / escena.fps)
        regs = []
        for y, x in zip(*np.nonzero(bg.max(-1) >= 8)):
            c = bg[y, x] // 16
            regs.append((y * W + x, 0, (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
        for y, x in zip(*np.nonzero(car != ' ')):
            c = fg[y, x] // 16
            regs.append((y * W + x, ord(car[y, x]), (int(c[0]) << 8) | (int(c[1]) << 4) | int(c[2])))
        a = np.zeros(len(regs), dtype=[('cel', '<u2'), ('ch', 'u1'), ('col', '<u2')])
        if regs:
            a['cel'], a['ch'], a['col'] = zip(*regs)
        blocs.append(a.tobytes())
        offsets.append(offsets[-1] + len(regs))
        print(f'\r  {escena.nom}: {i + 1}/{total}', end='', file=sys.stderr)
    import base64
    with open(fitxer, 'w', encoding='utf-8') as f:
        json.dump({'W': W, 'H': H, 'fps': escena.fps, 'bucle': 0, 'n': total, 'offsets': offsets,
                   'dades': base64.b64encode(b''.join(blocs)).decode()}, f, separators=(',', ':'))
    print(f'\r  {escena.nom}: ✓ {os.path.getsize(fitxer) / 1e6:.1f} MB ({total} fotogrames)', file=sys.stderr)


def desa_png(escena, ruta, t):
    from PIL import Image, ImageDraw, ImageFont
    car, fg, bg = escena.fotograma(t)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 13)
    im = Image.fromarray(np.repeat(np.repeat(bg, 15, 0), 8, 1), 'RGB')
    dr = ImageDraw.Draw(im)
    for y, x in zip(*np.nonzero(car != ' ')):
        dr.text((x * 8, y * 15), car[y, x], font=font, fill=tuple(int(v) for v in fg[y, x]))
    im.save(ruta)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    noms = args or list(ESCENES)
    os.makedirs(SORTIDA, exist_ok=True)
    for nom in noms:
        escena = ESCENES[nom]()
        if '--png' in sys.argv:
            carpeta = os.environ.get('PNG_DIR', '.')
            for k, f in enumerate((0.15, 0.5, 0.8)):
                desa_png(escena, os.path.join(carpeta, f'{nom}-{k}.png'), escena.durada * f)
            print(f'  {nom}: PNG desats', file=sys.stderr)
        if '--sense-json' not in sys.argv:
            exporta(escena, os.path.join(SORTIDA, f'{nom}.json'))


if __name__ == '__main__':
    main()
