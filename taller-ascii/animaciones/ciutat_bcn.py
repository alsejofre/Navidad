#!/usr/bin/env python3
"""Barcelona de nit des de l'aire, per al pla final de «Nadal a Barcelona».

No s'executa sol: el fa servir pelicula.py (escena 5). Conté:
  · Illes de l'Eixample a escala real (113 m, xamfrans de 20 m, carrers de 20 m) amb edificis
    d'alçades diferents, finestres i botigues enceses, pati d'illa, casetes als terrats i, en
    alguns, llumetes de Nadal.
  · Fanals a tots els carrers, dos carrers guarnits amb garlandes de colors i trànsit.
  · La Sagrada Família (torres il·luminades, l'estel de la torre de Maria i la creu de la de
    Jesús), la Torre Glòries amb els llums de colors i la serra de Collserola amb el Tibidabo
    i la torre de comunicacions.
  · La lluna i les estrelles.
  · Detalls de la plaça per al pla aeri: paviment, parades del mercat de Nadal i patinadors.

Les parets i els terrats són «oclusors»: punts negres que no fan llum però tapen el que tenen
darrere. Així la ciutat no es veu transparent i les finestres de cada façana es llegeixen netes.
A aquesta resolució la ciutat només es llegeix com a llums sobre negre (amb parets o terrats
pintats surt una textura de «:::» i «===» que ofega l'arbre).
"""
import math

import numpy as np

from arbre_giratori import TAU, Grup, uneix
from escenes3d import particules

PAS, ILLA, XAMFRA, FONS = 133.3, 113.3, 14.14, 24.0
OZ = -5.0                        # la plaça és la cel·la (0, 0), centrada a (0, OZ)
UP = np.array([0.0, 1.0, 0.0])
CALIDS = np.array([(1.0, 0.80, 0.50), (1.0, 0.72, 0.42), (1.0, 0.86, 0.62), (0.98, 0.66, 0.38)])
NADAL = np.array([(1.0, 0.25, 0.2), (0.3, 1.0, 0.45), (1.0, 0.82, 0.3), (0.5, 0.6, 1.0)])
SODI = np.array([1.0, 0.70, 0.36])
BLANC_CALID = np.array([1.0, 0.90, 0.72])


def negre(pos, nor):
    """Oclusor: no fa llum però tapa el que té darrere."""
    pos = np.asarray(pos, float)
    return Grup(pos, np.broadcast_to(np.asarray(nor, float), pos.shape), (0.0, 0.0, 0.0), 0.0, 0.0, ao=0.0)


def mostres(rng, O, U, V, su, sv):
    """Punts en una graella amb soroll dins el paral·lelogram O + a·U + b·V (cobreix sense forats)."""
    U, V = np.asarray(U, float), np.asarray(V, float)
    nu = max(1, int(math.ceil(np.linalg.norm(U) / su)))
    nv = max(1, int(math.ceil(np.linalg.norm(V) / sv)))
    i, j = np.meshgrid(np.arange(nu), np.arange(nv), indexing='ij')
    a = (i.ravel() + rng.random(i.size)) / nu
    b = (j.ravel() + rng.random(i.size)) / nv
    return np.asarray(O, float) + a[:, None] * U + b[:, None] * V


def linia(p0, p1, pas):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    n = max(2, int(np.linalg.norm(p1 - p0) / pas) + 1)
    return p0 + np.linspace(0, 1, n)[:, None] * (p1 - p0)


class Acumula:
    """Recull punts per categories i en fa un sol Grup al final (molt més ràpid que mil grups)."""

    def __init__(self):
        self.pos, self.nor, self.col, self.emis, self.ao = [], [], [], [], []

    def afegeix(self, pos, nor, col, emis, ao=1.0):
        n = len(pos)
        if not n:
            return
        self.pos.append(np.asarray(pos, float).reshape(n, 3))
        self.nor.append(np.broadcast_to(np.asarray(nor, float), (n, 3)))
        self.col.append(np.broadcast_to(np.asarray(col, float), (n, 3)))
        self.emis.append(np.broadcast_to(np.asarray(emis, float), (n,)))
        self.ao.append(np.broadcast_to(np.asarray(ao, float), (n,)))

    def grup(self, part=False, espec=0.0, ao=None):
        if not self.pos:
            return None
        pos = np.concatenate(self.pos)
        if part:
            return particules(pos, np.concatenate(self.col), np.concatenate(self.emis))
        return Grup(pos, np.concatenate(self.nor), np.concatenate(self.col), espec, np.concatenate(self.emis),
                    ao=np.concatenate(self.ao) if ao is None else ao)


class Ciutat:
    def __init__(self, cams, subs, C_fi, fwd_fi, fov_fi, llavor=31):
        """cams: posicions de la càmera al llarg del pla (K×3); subs: mida angular d'un subpíxel a
        cada posició (rad). C_fi, fwd_fi: càmera final (decideix què es construeix i on va cada cosa)."""
        self.rng = np.random.default_rng(llavor)
        self.cams = np.asarray(cams, float)
        self.subs = np.asarray(subs, float)
        self.C_fi = np.asarray(C_fi, float)
        self.fov_fi = fov_fi
        fh = np.array([fwd_fi[0], 0.0, fwd_fi[2]])
        self.fh = fh / np.linalg.norm(fh)                       # endavant (horitzontal)
        self.dh = np.array([self.fh[2], 0.0, -self.fh[0]])     # a la dreta de la imatge
        # Monuments, triats perquè no quedin sota el cartell: la Sagrada Família a la dreta, la
        # Torre Glòries a sota del cartell i el Tibidabo a l'esquerra, sota la lluna.
        self.dist_fi = float(np.hypot(self.C_fi[0], self.C_fi[2]))      # de la càmera final a l'arbre
        self.cel_sagrada = self.cella(self.pantalla(0.86, 950))
        self.cel_glories = self.cella(self.pantalla(0.62, 1800))
        self.oclusors, self.finestres, self.vores, self.fanals = Acumula(), Acumula(), Acumula(), Acumula()
        self._illes()
        self._fanals()
        self._sagrada()
        self._glories()
        self._collserola()
        self._cel()
        self._placa()
        self._transit()
        self.estatic = uneix([self.oclusors.grup(ao=0.0), self.finestres.grup(), self.vores.grup(part=True),
                              self.fanals.grup(part=True), self.sf, self.serra])
        self.n_punts = len(self.estatic.pos)

    # ------------------------------------------------------------ utilitats
    def pantalla(self, x, dist):
        """Punt de terra que la càmera final veu a la fracció x de l'amplada, a «dist» metres."""
        lat = (2 * x - 1) * math.tan(math.radians(self.fov_fi / 2)) * dist
        return (dist - self.dist_fi) * self.fh + lat * self.dh

    @staticmethod
    def cella(p):
        return int(round(p[0] / PAS)), int(round((p[2] - OZ) / PAS))

    def visible(self, p, marge=160.0):
        """Dins la falca que veu la càmera final (o prop de la plaça, per al començament del pla)."""
        v = np.atleast_2d(p) - self.C_fi
        f = v @ self.fh
        l = v @ self.dh
        prop = np.hypot(np.atleast_2d(p)[:, 0], np.atleast_2d(p)[:, 2] - OZ) < 430
        return ((f > -40) & (f < 2600) & (np.abs(l) < f * 1.15 + marge)) | prop

    def espaiat(self, p, n=None):
        """Separació entre punts perquè una superfície a p quedi plena des de totes les càmeres que la veuen."""
        p = np.atleast_2d(p)
        v = self.cams[None, :, :] - p[:, None, :]
        s = np.linalg.norm(v, axis=2) * self.subs[None, :]
        if n is not None:
            s = np.where(v @ np.asarray(n, float) > 0, s, np.inf)
        return 0.8 * s.min(1)

    # ------------------------------------------------------------ illes de l'Eixample
    def _illes(self):
        rng = self.rng
        b, k = ILLA / 2, XAMFRA
        V = np.array([(b - k, b), (-(b - k), b), (-b, b - k), (-b, -(b - k)), (-(b - k), -b), (b - k, -b), (b, -(b - k)), (b, b - k)])
        self.n_illes = 0
        for i in range(-21, 22):
            for j in range(-21, 22):
                if (i, j) in ((0, 0), self.cel_sagrada, self.cel_glories):
                    continue
                cx, cz = i * PAS, OZ + j * PAS
                if not self.visible(np.array([cx, 0, cz]))[0]:
                    continue
                self.n_illes += 1
                hb = rng.uniform(19, 25)
                hmax = 25.0 if (i, j) == (1, -1) else 31.0   # la càmera hi passa per sobre
                for e in range(8):
                    A = np.array([cx + V[e, 0], 0.0, cz + V[e, 1]])
                    B = np.array([cx + V[(e + 1) % 8, 0], 0.0, cz + V[(e + 1) % 8, 1]])
                    L = float(np.linalg.norm(B - A))
                    d = (B - A) / L
                    n = np.array([d[2], 0.0, -d[0]])
                    talls = [0.0]
                    while L - talls[-1] > 26:
                        talls.append(talls[-1] + rng.uniform(13, 22))
                    talls.append(L)
                    for u0, u1 in zip(talls[:-1], talls[1:]):
                        h = float(np.clip(hb + rng.normal(0, 2.2) + (6 if rng.random() < 0.06 else 0), 15, hmax))
                        self._tram(A, d, n, u0, u1, h)

    def _tram(self, A, d, n, u0, u1, h):
        """Un edifici: façana (oclusor + finestres), terrat (oclusor + vores nevades) i, potser, llumetes."""
        rng = self.rng
        mig = A + d * (u0 + u1) / 2
        s_f = float(self.espaiat(mig + UP * h / 2, n)[0])
        dist_fi = float(np.linalg.norm(self.C_fi - mig))
        caiguda = min(1.0, (900 / dist_fi) ** 0.8)
        if np.isfinite(s_f):
            s_f = max(s_f, 0.3)
            O = A + d * u0
            self.oclusors.afegeix(mostres(rng, O, d * (u1 - u0), UP * h, s_f, s_f), n, 0, 0)
            # Botigues (planta baixa)
            us = np.arange(u0 + 3.0, u1 - 2.0, 6.0)
            enceses = us[rng.random(len(us)) < 0.72 * caiguda]
            self._finestres(A, d, n, enceses, np.full(len(enceses), 0.6), 3.4, 3.0, s_f,
                            np.tile([1.0, 0.85, 0.62], (len(enceses), 1)), 1.0)
            # Pisos
            p_llum = rng.uniform(0.3, 0.65) * caiguda
            to = CALIDS[rng.integers(len(CALIDS))]
            ys = np.arange(4.6, h - 2.9, 3.2)
            us = np.arange(u0 + 1.7, u1 - 1.0, 3.4)
            if len(ys) and len(us):
                U, Y = np.meshgrid(us, ys + 0.4)
                U, Y = U.ravel(), Y.ravel()
                m = rng.random(len(U)) < p_llum
                U, Y = U[m], Y[m]
                col = to * (0.85 + 0.3 * rng.random((len(U), 1)))
                r = rng.random(len(U))
                col[r < 0.07] = (0.80, 0.86, 1.0)
                nad = r > 0.97
                col[nad] = NADAL[rng.integers(len(NADAL), size=int(nad.sum()))]
                self._finestres(A, d, n, U, Y, 1.4, 2.0, s_f, col, 1.0)
        # Façana del pati d'illa (tapa el que hi ha darrere quan es mira des de dalt)
        Ai = A - n * FONS
        s_i = float(self.espaiat(mig - n * FONS + UP * h / 2, -n)[0])
        if np.isfinite(s_i):
            s_i = max(s_i, 0.3)
            self.oclusors.afegeix(mostres(rng, Ai + d * u0, d * (u1 - u0), UP * h, s_i, s_i), -n, 0, 0)
            ys = np.arange(4.6, h - 2.9, 3.2)
            us = np.arange(u0 + 1.7, u1 - 1.0, 3.4)
            if len(ys) and len(us):
                U, Y = np.meshgrid(us, ys + 0.4)
                m = rng.random(U.size) < 0.3 * caiguda
                col = CALIDS[rng.integers(4, size=int(m.sum()))] * 0.9
                self._finestres(Ai, d, -n, U.ravel()[m], Y.ravel()[m], 1.4, 2.0, s_i, col, 0.7)
        # Terrat
        cim = A + UP * h
        s_r = float(self.espaiat(mig + UP * h, UP)[0])
        if not np.isfinite(s_r):
            return
        s_r = max(s_r, 0.25)
        sin_dep = max(0.2, (self.C_fi[1] - h) / dist_fi)
        pt = mostres(rng, cim + d * u0, d * (u1 - u0), -n * FONS, s_r, s_r / sin_dep)
        self.oclusors.afegeix(pt, UP, 0, 0)
        if rng.random() < 0.07:                                     # terrat amb llumetes de Nadal
            ll = linia(cim + d * u0 + UP * 0.3, cim + d * u1 + UP * 0.3, 1.6)
            self.vores.afegeix(ll, UP, NADAL[np.arange(len(ll)) % 4], 1.1)
        if rng.random() < 0.5 and u1 - u0 > 8:                      # caseta del terrat
            c = cim + d * rng.uniform(u0 + 3, u1 - 3) - n * rng.uniform(5, FONS - 5) + UP * 2.2
            e1, e2 = d * 1.6, -n * 1.6
            self.oclusors.afegeix(mostres(rng, c - e1 - e2, 2 * e1, 2 * e2, s_r, s_r / sin_dep), UP, 0, 0)


    def _finestres(self, A, d, n, us, ys, w, hh, s, col, emis):
        """Finestres enceses: un rectangle de punts per finestra (com a mínim un punt)."""
        if not len(us):
            return
        nu, nv = max(1, int(round(w / s))), max(1, int(round(hh / s)))
        a = ((np.arange(nu) + 0.5) / nu - 0.5) * w
        b = (np.arange(nv) + 0.5) / nv * hh
        A_, B_ = np.meshgrid(a, b)
        off = A_.ravel()[None, :, None] * d + B_.ravel()[None, :, None] * UP
        base = A[None, None, :] + (us[:, None, None]) * d + ys[:, None, None] * UP + n * 0.12
        pos = (base + off).reshape(-1, 3)
        c = np.repeat(np.asarray(col, float), nu * nv, axis=0)
        self.finestres.afegeix(pos, n, c, emis)

    # ------------------------------------------------------------ fanals i carrers guarnits
    def _fanals(self):
        rng = self.rng
        self.guarnits = [('z', -PAS / 2), ('x', OZ + PAS / 2)]      # dos carrers amb garlandes
        garl, garl_col = [], []
        for eix in ('x', 'z'):
            for kk in range(-21, 21):
                c = (kk + 0.5) * PAS + (OZ if eix == 'x' else 0.0)
                guarnit = (eix, round(c, 3)) in [(e, round(v, 3)) for e, v in self.guarnits]
                pas = 6.0 if guarnit else 8.0
                s = np.arange(-2800, 2800, pas)
                # treu els que cauen a les cruïlles
                ref = s - (PAS / 2 if eix == 'x' else OZ + PAS / 2)
                lliure = np.abs(np.mod(ref + 10, PAS) - 10) > 10.5
                s = s[lliure]
                for costat in (-8.5, 8.5):
                    if eix == 'x':
                        p = np.column_stack([s, np.full(len(s), 6.0), np.full(len(s), c + costat)])
                    else:
                        p = np.column_stack([np.full(len(s), c + costat), np.full(len(s), 6.0), s])
                    p = p[self.visible(p)]
                    p = p[~((np.abs(p[:, 0]) < ILLA / 2 + 1) & (np.abs(p[:, 2] - OZ) < ILLA / 2 + 1))]
                    col = (BLANC_CALID if guarnit else SODI) * (0.9 + 0.1 * rng.random((len(p), 1)))
                    em = 1.2 if guarnit else 1.0
                    self.fanals.afegeix(p, UP, col, em)
                    self.fanals.afegeix(p + UP * 0.25, UP, col, em)
                    # clapa de llum a terra (només a prop: lluny es faria una ratlla)
                    a_prop = np.linalg.norm(p - self.C_fi, axis=1) < 900
                    q = p[a_prop]
                    for rr, em_ in ((1.6, 0.32), (3.4, 0.18)):
                        for ang in np.arange(0, TAU, 1.2) + rr:
                            g = q + np.array([rr * math.cos(ang), -5.95, rr * math.sin(ang)])
                            self.fanals.afegeix(g, UP, SODI * 0.9, em_)
                if guarnit:
                    for u in np.arange(-2800, 2800, 20.0):
                        x = np.linspace(-9, 9, 11)
                        y = 8.6 - 1.3 * (1 - (x / 9) ** 2)
                        if eix == 'x':
                            p = np.column_stack([np.full(11, u), y, c + x])
                        else:
                            p = np.column_stack([c + x, y, np.full(11, u)])
                        if not self.visible(p[5:6])[0] or abs(np.mod(u - (PAS / 2 if eix == 'x' else OZ + PAS / 2) + 10, PAS) - 10) < 11:
                            continue
                        garl.append(p)
                        garl_col.append(np.array([(1.0, 0.82, 0.3), (1.0, 0.25, 0.2), (1.0, 0.82, 0.3), (0.3, 1.0, 0.45),
                                                  (1.0, 0.82, 0.3), (0.95, 0.95, 1.0), (1.0, 0.82, 0.3), (0.3, 1.0, 0.45),
                                                  (1.0, 0.82, 0.3), (1.0, 0.25, 0.2), (1.0, 0.82, 0.3)]))
        self.garl = np.concatenate(garl)
        self.garl_col = np.concatenate(garl_col)
        self.garl_fase = rng.random(len(self.garl)) * TAU

    # ------------------------------------------------------------ trànsit
    def _transit(self):
        rng = self.rng
        carrers = [('z', -PAS / 2), ('x', OZ + PAS / 2), ('x', OZ - PAS / 2), ('z', PAS / 2),
                   ('z', -1.5 * PAS), ('x', OZ + 1.5 * PAS), ('z', 2.5 * PAS), ('x', OZ + 3.5 * PAS)]
        self.cotxes = []
        for eix, c in carrers:
            s = np.arange(-2800, 2800, 5.0)
            p = np.column_stack([s, np.zeros(len(s)), np.full(len(s), c)]) if eix == 'x' else \
                np.column_stack([np.full(len(s), c), np.zeros(len(s)), s])
            vis = self.visible(p)
            if not vis.any():
                continue
            s0, s1 = s[vis].min(), s[vis].max()
            n = int((s1 - s0) / 28)
            eixv = np.array([1.0, 0, 0]) if eix == 'x' else np.array([0, 0, 1.0])
            lat = np.array([0, 0, 1.0]) if eix == 'x' else np.array([1.0, 0, 0])
            for _ in range(n):
                sentit = rng.choice([-1, 1])
                self.cotxes.append((eixv, lat, c, s0, s1, rng.uniform(s0, s1), sentit * rng.uniform(8, 13), sentit))

    def _cotxes(self, t):
        pos, col, em = [], [], []
        for eixv, lat, c, s0, s1, si, v, sentit in self.cotxes:
            s = s0 + np.mod(si + v * t - s0, s1 - s0)
            base = eixv * s + lat * (c + 3.0 * sentit) + UP * 0.8
            lluny = float(np.dot(eixv * sentit, self.fh)) > 0
            cc, e = ((1.0, 0.15, 0.1), 1.0) if lluny else ((1.0, 0.95, 0.82), 1.3)
            for k in (-0.8, 0.8):
                pos.append(base + eixv * k * 0 + np.cross(UP, eixv) * k)
                col.append(cc)
                em.append(e)
        return particules(np.array(pos), np.array(col), np.array(em))

    # ------------------------------------------------------------ Sagrada Família
    def _fus(self, centre, r0, h, esp, color, emis, punta=0.12):
        """Torre en forma de fus (paraboloide), amb el pinacle de mosaic de colors."""
        rng = self.rng
        ys = np.arange(0, h, esp * 0.8)
        pos, nor, col, em = [], [], [], []
        for y in ys:
            u = y / h
            r = r0 * (1 - u) ** 0.55 + 0.4
            nth = max(5, int(TAU * r / (esp * 0.8)))
            th = (np.arange(nth) + rng.random(nth)) / nth * TAU
            dr = -0.55 * r0 * (1 - u + 1e-3) ** -0.45 / h
            nn = np.column_stack([np.cos(th), np.full(nth, -dr), np.sin(th)])
            nn /= np.linalg.norm(nn, axis=1, keepdims=True)
            pos.append(centre + np.column_stack([r * np.cos(th), np.full(nth, y), r * np.sin(th)]))
            nor.append(nn)
            if u > 1 - punta:
                c = np.array([(1.0, 0.3, 0.2), (1.0, 0.85, 0.3), (0.95, 0.95, 0.9), (0.4, 0.9, 0.5)])[rng.integers(4, size=nth)]
                col.append(c)
                em.append(np.full(nth, emis * 1.5))
            else:
                ratlla = (np.sin(th * 6 + y * 0.35) > 0.75)           # obertures en espiral de les torres
                c = np.tile(color, (nth, 1)) * (0.88 + 0.12 * rng.random((nth, 1)))
                c[ratlla] *= 0.45
                col.append(c)
                em.append(np.full(nth, emis))
        return Grup(np.concatenate(pos), np.concatenate(nor), np.concatenate(col), 0.2, np.concatenate(em), ao=0.8)

    def _sagrada(self):
        rng = self.rng
        i, j = self.cel_sagrada
        O = np.array([i * PAS, 0.0, OZ + j * PAS])
        esp = max(0.8, float(self.espaiat(O + UP * 60)[0]))
        pedra = np.array([1.0, 0.84, 0.6])
        g = []
        # Nau i creuer: oclusors amb la pedra il·luminada i vitralls de colors
        for (lx, ly, lz), cc in (((80, 44, 44), (0, 0, 0)), ((30, 40, 92), (0, 0, 0))):
            for nrm, Oc, U, Vv in (((0, 0, 1), (-lx / 2, 0, lz / 2), (lx, 0, 0), (0, ly, 0)),
                                   ((0, 0, -1), (-lx / 2, 0, -lz / 2), (lx, 0, 0), (0, ly, 0)),
                                   ((1, 0, 0), (lx / 2, 0, -lz / 2), (0, 0, lz), (0, ly, 0)),
                                   ((-1, 0, 0), (-lx / 2, 0, -lz / 2), (0, 0, lz), (0, ly, 0)),
                                   ((0, 1, 0), (-lx / 2, ly, -lz / 2), (lx, 0, 0), (0, 0, lz))):
                p = mostres(rng, O + Oc, U, Vv, esp, esp)
                c = np.tile(pedra * 0.75, (len(p), 1)) * (0.8 + 0.2 * rng.random((len(p), 1)))
                e = np.full(len(p), 0.3)
                if nrm[1] == 0:
                    rel = p - O
                    eix_h = rel[:, 0] if nrm[2] != 0 else rel[:, 2]
                    vitrall = (np.abs(np.mod(eix_h, 7.0) - 3.5) < 1.2) & (rel[:, 1] > 9) & (rel[:, 1] < ly - 6)
                    tons = np.array([(0.3, 0.5, 1.0), (0.3, 0.9, 0.6)]) if (nrm[2] + nrm[0]) > 0 else np.array([(1.0, 0.45, 0.2), (1.0, 0.8, 0.3)])
                    c[vitrall] = tons[rng.integers(2, size=int(vitrall.sum()))]
                    e[vitrall] = 1.3
                g.append(Grup(p, np.tile(nrm, (len(p), 1)), c, 0.1, e, ao=0.8))
        g.append(mou_t(self._fus_absis(esp, pedra), O))
        # Torres
        for x, z, h, r0 in ([(x, 47, h, 4.2) for x, h in ((-13, 98), (-4.5, 107), (4.5, 107), (13, 98))] +
                            [(x, -47, h, 4.2) for x, h in ((-13, 107), (-4.5, 112), (4.5, 112), (13, 107))] +
                            [(sx * 14, sz * 14, 135, 7.0) for sx in (-1, 1) for sz in (-1, 1)] +
                            [(30, 0, 138, 8.0), (0, 0, 160, 10.0)]):
            g.append(self._fus(O + [x, 0, z], r0, h, esp, pedra, 1.5))
        # Estel de la torre de Maria i creu de la de Jesús
        a = np.arange(24) / 24 * TAU
        rr = np.where(np.arange(24) % 2 == 0, 6.5, 2.6)
        contorn = np.column_stack([rr * np.cos(a), rr * np.sin(a)])
        punts = []
        for q in range(24):
            for f in np.linspace(0, 1, 6):
                punts.append(contorn[q] * (1 - f) + contorn[(q + 1) % 24] * f)
        punts = np.array(punts)
        punts = np.concatenate([punts * f for f in (1.0, 0.7, 0.4)] + [np.zeros((1, 2))])
        estel = O + [30, 145, 0] + np.column_stack([punts[:, 0] * 0.7071, punts[:, 1], punts[:, 0] * 0.7071])
        creu = np.concatenate([linia(O + [0, 159, 0], O + [0, 174, 0], 0.8),
                               linia(O + [-5.5 * 0.7071, 168, -5.5 * 0.7071], O + [5.5 * 0.7071, 168, 5.5 * 0.7071], 0.8)])
        g.append(particules(np.concatenate([estel, creu]), (0.92, 0.95, 1.0), 2.6))
        self.sf = uneix(g)

    def _fus_absis(self, esp, pedra):
        """Absis semicircular darrere la nau."""
        rng = self.rng
        pos, nor = [], []
        for y in np.arange(0, 38, esp):
            nth = int(math.pi * 22 / esp) + 1
            th = (np.arange(nth) + rng.random(nth)) / nth * math.pi - math.pi / 2
            pos.append(np.column_stack([40 + 22 * np.cos(th), np.full(nth, y), 22 * np.sin(th)]))
            nor.append(np.column_stack([np.cos(th), np.zeros(nth), np.sin(th)]))
        pos, nor = np.concatenate(pos), np.concatenate(nor)
        c = np.tile(pedra * 0.75, (len(pos), 1))
        e = np.full(len(pos), 0.55)
        vitrall = (np.mod(pos[:, 1], 9) > 4) & (np.mod(np.arctan2(pos[:, 2], pos[:, 0] - 40) * 6, 1) < 0.35)
        c[vitrall] = (0.5, 0.6, 1.0)
        e[vitrall] = 1.2
        return Grup(pos, nor, c, 0.1, e, ao=0.8)

    # ------------------------------------------------------------ Torre Glòries
    def _glories(self):
        i, j = self.cel_glories
        O = np.array([i * PAS, 0.0, OZ + j * PAS])
        esp = max(1.0, float(self.espaiat(O + UP * 70)[0]))
        R, h = 19.0, 144.0
        pos, nor, ys, ths = [], [], [], []
        for y in np.arange(0.5, h, esp * 0.9):
            r = R * max(0.04, 1 - (y / h) ** 2.4) ** 0.5
            nth = max(6, int(TAU * r / (esp * 0.9)))
            th = np.arange(nth) / nth * TAU
            pos.append(O + np.column_stack([r * np.cos(th), np.full(nth, y), 0.92 * r * np.sin(th)]))
            dr = -R * 0.5 * 2.4 * (y / h) ** 1.4 / h / max(0.05, r / R)
            nn = np.column_stack([np.cos(th), np.full(nth, -dr), np.sin(th)])
            nor.append(nn / np.linalg.norm(nn, axis=1, keepdims=True))
            ys.append(np.full(nth, y))
            ths.append(th)
        self.gl_pos, self.gl_nor = np.concatenate(pos), np.concatenate(nor)
        self.gl_y, self.gl_th = np.concatenate(ys), np.concatenate(ths)
        # cúpula de dalt, una mica més clara
        self.gl_cim = particules(np.array([O + [0, h + 1.5, 0]]), (1.0, 1.0, 1.0), 1.5)

    def _glories_llums(self, t):
        pal = np.array([(1.0, 0.22, 0.2), (1.0, 0.8, 0.3), (0.25, 1.0, 0.45), (0.9, 0.92, 1.0), (0.75, 0.35, 1.0)])
        franja = np.floor(self.gl_th * 6 / TAU + t * 0.35 + self.gl_y / 48).astype(int) % len(pal)
        ona = 0.55 + 0.45 * np.sin(self.gl_y / 11 - t * 2.4)
        g = Grup(self.gl_pos, self.gl_nor, pal[franja] * (0.6 + 0.4 * ona[:, None]), 0.0, 0.7 + 1.1 * ona, ao=0.3)
        return uneix([g, self.gl_cim])

    # ------------------------------------------------------------ Collserola i Tibidabo
    def _collserola(self):
        rng = self.rng
        fh, dh = self.fh, self.dh
        s = np.arange(-3600, 3600, 7.0)
        tg = math.tan(math.radians(self.fov_fi / 2)) * (2450 + 450 + self.dist_fi)
        S_TIBI, S_TORRE = -0.64 * tg, -0.80 * tg            # a l'esquerra, fora del cartell

        def crest(s):
            h = 150 + 35 * np.sin(s / 520) + 22 * np.sin(s / 230 + 2.0)
            h += 95 * np.exp(-((s - S_TIBI) / 260) ** 2)       # Tibidabo
            h += 55 * np.exp(-((s - S_TORRE) / 200) ** 2)      # turó de la torre de Collserola
            return h

        def lloc(s, frac):
            """Punt del vessant: frac 0 = peu de la muntanya, 1 = carena."""
            fwd = 2450 + frac * (380 + 120 * np.sin(s / 800 + 1.0))
            return fwd[:, None] * fh + s[:, None] * dh + (frac * crest(s))[:, None] * UP

        esp = 8.0
        files = int(1 / 0.025)
        g = []
        cara = np.concatenate([lloc(s + rng.uniform(-3, 3, len(s)), np.full(len(s), (q + rng.random()) / files)) for q in range(files)])
        g.append(negre(cara, -fh))
        carena = lloc(s, np.ones(len(s)))
        g.append(particules(carena, (0.42, 0.5, 0.72), 0.85))
        # llums de cases als vessants i la carretera de les Aigües
        n = 900
        ss = rng.uniform(-3400, 3400, n)
        fr = rng.random(n) ** 1.8 * 0.85
        cases = lloc(ss, fr)
        g.append(particules(cases, CALIDS[rng.integers(4, size=n)], 1.6 + rng.random(n)))
        sc = np.arange(-3300, 3300, 16.0)
        g.append(particules(lloc(sc, 0.5 + 0.06 * np.sin(sc / 300)), SODI, 1.5))
        # Temple del Tibidabo
        cim = lloc(np.array([S_TIBI]), np.ones(1))[0]
        temple = []
        for y in np.arange(0, 34, 3.0):
            for x in np.arange(-16, 17, 3.0):
                temple.append(cim + x * dh + y * UP)
        for y in np.arange(34, 62, 2.5):
            w = 6 * (1 - (y - 34) / 34)
            for x in np.arange(-w, w + 0.1, 2.5):
                temple.append(cim + x * dh + y * UP)
        temple += list(linia(cim + UP * 62, cim + UP * 72, 2.0))
        g.append(particules(np.array(temple), (1.0, 0.9, 0.72), 2.6))
        # Torre de Collserola (agulla amb llums vermells a dalt)
        peu = lloc(np.array([S_TORRE]), np.ones(1))[0]
        self.torre_peu = peu
        g.append(particules(linia(peu, peu + UP * 150, 4.0), (0.85, 0.85, 0.9), 0.9))
        self.serra = uneix(g)

    # ------------------------------------------------------------ cel
    def _cel(self):
        rng = self.rng
        C = self.C_fi

        def dir_(az, el):
            az, el = np.radians(az), np.radians(el)
            return (np.cos(el) * np.cos(az))[:, None] * self.fh + (np.cos(el) * np.sin(az))[:, None] * self.dh + np.sin(el)[:, None] * UP

        n = 700
        mig = self.fov_fi / 2
        az = rng.uniform(-mig - 4, mig + 4, n)
        el = 2.5 + 24 * rng.random(n) ** 1.2
        lluna_az = -math.degrees(math.atan(0.86 * math.tan(math.radians(mig))))
        lluna_el = 8.5
        lluny_lluna = np.hypot(az - lluna_az, el - lluna_el) > 4.5
        az, el = az[lluny_lluna], el[lluny_lluna]
        self.est_pos = C + dir_(az, el) * 6000
        self.est_em = 0.3 + 0.9 * rng.random(len(az)) ** 3
        self.est_col = np.array([1.0, 1.0, 1.0]) - rng.random((len(az), 1)) * np.array([0.15, 0.1, 0.0]) * rng.choice([-1, 1], (len(az), 1))
        self.est_fase = rng.random(len(az)) * TAU
        self.est_vel = 1.5 + 3 * rng.random(len(az))
        # Lluna: disc de cara a la càmera, amb mars més foscos
        centre = C + dir_(np.array([lluna_az]), np.array([lluna_el]))[0] * 6000
        cap = (C - centre) / np.linalg.norm(C - centre)
        e1 = np.cross(UP, cap)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(cap, e1)
        R = 175.0
        p = mostres(rng, centre - R * e1 - R * e2, 2 * R * e1, 2 * R * e2, 13.0, 13.0)
        rel = p - centre
        a, b = rel @ e1 / R, rel @ e2 / R
        dins = a ** 2 + b ** 2 < 1
        p, a, b = p[dins], a[dins], b[dins]
        llum = 0.86 + 0.14 * np.sqrt(np.clip(1 - a ** 2 - b ** 2, 0, 1))
        for ca, cb, rr in ((-0.3, 0.25, 0.32), (0.25, 0.35, 0.22), (0.1, -0.2, 0.28), (-0.35, -0.4, 0.15)):
            llum = llum * np.where((a - ca) ** 2 + (b - cb) ** 2 < rr ** 2, 0.74, 1.0)
        self.lluna = particules(p, np.array([1.0, 0.96, 0.84]) * llum[:, None], 1.25 * llum)

    def _estrelles(self, t):
        em = self.est_em * (0.72 + 0.28 * np.sin(t * self.est_vel + self.est_fase))
        return particules(self.est_pos, self.est_col, em)

    # ------------------------------------------------------------ plaça (pla aeri)
    def _placa(self):
        rng = self.rng
        pista = np.array([0.0, 0.0, -17.0])
        pav = []
        for r in (14.0, 36.0):
            a = np.arange(0, TAU, 0.5 / r)
            pav.append(np.column_stack([r * np.cos(a), np.full(len(a), 0.03), r * np.sin(a)]))
        h = ILLA / 2 - 2.5
        cant = [(-h, OZ - h), (h, OZ - h), (h, OZ + h), (-h, OZ + h)]
        for q in range(4):
            pav.append(linia([cant[q][0], 0.03, cant[q][1]], [cant[(q + 1) % 4][0], 0.03, cant[(q + 1) % 4][1]], 0.6))
        pav = np.concatenate(pav)
        lluny_pista = np.hypot(pav[:, 0] - pista[0], pav[:, 2] - pista[2]) > 8.5
        rr = np.hypot(pav[:, 0], pav[:, 2] - OZ)
        sota_edificis = (rr > 33) & (rr < 51) & (pav[:, 2] > OZ + 6)
        pav = pav[lluny_pista & ~sota_edificis]
        self.paviment = particules(pav, (0.72, 0.77, 0.88), 0.2)
        g = []
        # Parades del mercat de Nadal, en arc al costat de la càmera
        oc, llum, llum_c, sostre, sostre_c, bomb, bomb_c = [], [], [], [], [], [], []
        for a in np.linspace(1.06 * math.pi, 1.70 * math.pi, 12):       # deixa lliure el pas de la càmera
            radial = np.array([math.cos(a), 0, math.sin(a)])
            tang = np.array([-math.sin(a), 0, math.cos(a)])
            c = radial * 31
            s = 0.3
            davant = c + radial * 1.2
            oc.append(negre(mostres(rng, davant - tang * 1.6, tang * 3.2, UP * 2.3, s, s), radial))
            oc.append(negre(mostres(rng, c - radial * 1.2 - tang * 1.6, tang * 3.2, UP * 2.3, s, s), -radial))
            for sgn in (-1, 1):
                oc.append(negre(mostres(rng, c + tang * 1.6 * sgn - radial * 1.2, radial * 2.4, UP * 2.3, s, s), tang * sgn))
            llum.append(mostres(rng, davant + radial * 0.05 - tang * 1.4 + UP * 0.9, tang * 2.8, UP * 1.1, 0.25, 0.25))
            for sgn in (-1, 1):
                p = mostres(rng, c + UP * 2.3 + radial * 1.4 * sgn - tang * 1.7, tang * 3.4, -radial * 1.4 * sgn + UP * 0.8, 0.22, 0.22)
                ratlla = np.floor((p - c) @ tang / 0.45).astype(int) % 2 == 0
                sostre.append(p)
                sostre_c.append(np.where(ratlla[:, None], [0.9, 0.12, 0.12], [0.95, 0.95, 0.95]))
            bb = linia(davant + UP * 2.35 - tang * 1.6, davant + UP * 2.35 + tang * 1.6, 0.45)
            bomb.append(bb)
            bomb_c.append(np.array([(1.0, 0.82, 0.3), (1.0, 0.25, 0.2), (0.3, 1.0, 0.45)])[np.arange(len(bb)) % 3])
        g += oc
        llum = np.concatenate(llum)
        g.append(Grup(llum, np.tile([0, 0, 0.0], (len(llum), 1)), (1.0, 0.82, 0.55), 0.0, 1.0, cull=False))
        sostre = np.concatenate(sostre)
        g.append(Grup(sostre, np.tile(UP, (len(sostre), 1)), np.concatenate(sostre_c), 0.3, 0.3))
        g.append(particules(np.concatenate(bomb), np.concatenate(bomb_c), 1.2))
        self.placa_aeri = uneix(g)
        # Patinadors (punts de colors que giren per la pista)
        n = 14
        self.pat_r = rng.uniform(2.5, 6.2, n)
        self.pat_f = rng.random(n) * TAU
        self.pat_w = rng.uniform(0.25, 0.5, n) * rng.choice([1, 1, 1, -1], n)
        self.pat_c = np.array([(0.9, 0.2, 0.2), (0.3, 0.5, 1.0), (0.3, 0.9, 0.4), (0.95, 0.95, 0.95), (1.0, 0.8, 0.3)])[np.arange(n) % 5]
        self.pista = pista

    def _patinadors(self, t):
        a = self.pat_f + self.pat_w * t
        base = self.pista + np.column_stack([self.pat_r * np.cos(a), np.full(len(a), 1.0), self.pat_r * np.sin(a)])
        return particules(np.concatenate([base, base + UP * 0.6]), np.concatenate([self.pat_c, self.pat_c * 0.8 + 0.2]), 0.55)

    # ------------------------------------------------------------ per fotograma
    def grups(self, t, fosa=1.0, fosa_placa=1.0):
        """Tot el que es veu a l'instant t. «fosa» (0→1) encén els llums de la ciutat en entrar al pla;
        «fosa_placa», els detalls de la plaça que no hi eren a l'escena 4 (paviment, mercat, patinadors)."""
        brill = 0.9 + 0.55 * (np.sin(t * 2.2 + self.garl_fase) > 0.2)
        garl = particules(self.garl, self.garl_col, brill)
        torre = particules(self.torre_peu + UP * np.array([[150.0], [151.5], [148.5]]), (1.0, 0.12, 0.08),
                           3.2 if math.fmod(t, 1.6) < 0.8 else 0.6)
        ciutat = uneix([self.estatic, garl, torre, self._cotxes(t), self._glories_llums(t), self._estrelles(t), self.lluna])
        placa = uneix([self.paviment, self.placa_aeri, self._patinadors(t)])
        if fosa < 1:
            ciutat.emis = ciutat.emis * fosa
        if fosa_placa < 1:
            placa.emis = placa.emis * fosa_placa
        return uneix([ciutat, placa])


def mou_t(g, t):
    return g.copia(pos=g.pos + np.asarray(t, float))
