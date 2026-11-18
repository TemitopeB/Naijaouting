"""Painterly cover kit (v3): light, shadow, depth and Nigerian figures, drawn as SVG.
Canvas is 1000x1000. Light comes from the upper left unless a scene says otherwise."""
import math, random

# ---------- colour ----------
def _rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _hex(c): return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c)
def mix(a, b, t):
    A, B = _rgb(a), _rgb(b); return _hex([A[i] + (B[i] - A[i]) * t for i in range(3)])
def lt(c, t): return mix(c, "#FFF6E8", t)     # warm light
def dk(c, t): return mix(c, "#0B0A14", t)     # cool shadow

P = dict(
    indigo="#1F2A5A", night="#0E1430", deep="#151B3D", kola="#B3261E", laterite="#C2562E", ochre="#D99A2B",
    marigold="#E9A21B", gold="#F2C14E", palm="#1E6B47", leaf="#5E9438", cream="#F2E8D5", sand="#E2D3B5",
    ink="#1A1714", coral="#E27D6A", sky="#9FC3CF", plum="#5B2A4E", clay="#8A4B2A", teal="#2F6F73",
    skin1="#5A3A27", skin2="#6B4430", skin3="#4A2F21", skin4="#7A4E35", hair="#17110E", white="#F7F1E6",
    green="#178A4C", flag="#0F7A45", red="#C8332B", blue="#2E5AAC", purple="#6C3B8E", pink="#D9577A",
)
SKINS = [P["skin1"], P["skin2"], P["skin3"], P["skin4"]]


class Art:
    def __init__(self, seed=1):
        self.defs, self.body, self._g, self.n = [], [], {}, 0
        self.rnd = random.Random(seed)

    def id(self, p="g"):
        self.n += 1; return f"{p}{self.n}"

    # ----- gradients -----
    def lin(self, stops, x1=0, y1=0, x2=0, y2=1, units="objectBoundingBox"):
        key = ("l", tuple(stops), x1, y1, x2, y2, units)
        if key in self._g: return self._g[key]
        i = self.id("l")
        s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        self.defs.append(f'<linearGradient id="{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" gradientUnits="{units}">{s}</linearGradient>')
        self._g[key] = f"url(#{i})"; return self._g[key]

    def rad(self, stops, cx=.5, cy=.5, r=.5, fx=None, fy=None):
        key = ("r", tuple(stops), cx, cy, r, fx, fy)
        if key in self._g: return self._g[key]
        i = self.id("r")
        s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        f = f' fx="{fx}" fy="{fy}"' if fx is not None else ""
        self.defs.append(f'<radialGradient id="{i}" cx="{cx}" cy="{cy}" r="{r}"{f}>{s}</radialGradient>')
        self._g[key] = f"url(#{i})"; return self._g[key]

    def shade(self, c, k=.22, side="h", flip=False):
        """Volume fill: lit edge -> base -> shadow edge."""
        a, b = (lt(c, k * .8), dk(c, k * 1.3))
        if flip: a, b = b, a
        if side == "h": return self.lin([(0, a, 1), (.45, c, 1), (1, b, 1)], 0, 0, 1, 0)
        return self.lin([(0, a, 1), (.5, c, 1), (1, b, 1)], 0, 0, 0, 1)

    def vfade(self, c, a0=1, a1=0):
        return self.lin([(0, c, a0), (1, c, a1)])

    # ----- primitives -----
    def add(self, s): self.body.append(s); return s
    def rect(self, x, y, w, h, fill, rx=0, op=1, extra=""):
        return self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" opacity="{op}" {extra}/>')
    def path(self, d, fill, op=1, extra=""):
        return self.add(f'<path d="{d}" fill="{fill}" opacity="{op}" {extra}/>')
    def poly(self, pts, fill, op=1, extra=""):
        return self.path("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z", fill, op, extra)
    def circ(self, x, y, r, fill, op=1, extra=""):
        return self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" opacity="{op}" {extra}/>')
    def ell(self, x, y, rx, ry, fill, op=1, extra=""):
        return self.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" opacity="{op}" {extra}/>')
    def line(self, x1, y1, x2, y2, col, w=2, op=1, cap="round"):
        return self.add(f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{col}" stroke-width="{w}" stroke-linecap="{cap}" opacity="{op}" fill="none"/>')
    def stroke(self, d, col, w=2, op=1, extra=""):
        return self.add(f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="{op}" {extra}/>')
    def group(self, inner, extra=""):
        return self.add(f'<g {extra}>{inner}</g>')

    def capture(self):
        """Start capturing primitives into a string (for clipping / grouping)."""
        self._mark = len(self.body)
    def release(self):
        s = "".join(self.body[self._mark:]); del self.body[self._mark:]; return s

    # ----- light -----
    def glow(self, x, y, r, col, op=1):
        return self.circ(x, y, r, self.rad([(0, col, op), (.35, col, op * .45), (1, col, 0)]))
    def beam(self, x, y, ang, length, w0, w1, col, op=.35):
        a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
        pts = [(x + nx * w0, y + ny * w0), (x + ux * length + nx * w1, y + uy * length + ny * w1),
               (x + ux * length - nx * w1, y + uy * length - ny * w1), (x - nx * w0, y - ny * w0)]
        g = self.lin([(0, col, op), (1, col, 0)], x, y, x + ux * length, y + uy * length, "userSpaceOnUse")
        return self.poly(pts, g)
    def haze(self, y0, y1, col, op=.5, up=True):
        return self.rect(0, y0, 1000, y1 - y0, self.lin([(0, col, 0 if up else op), (1, col, op if up else 0)]))
    def shadow(self, x, y, rx, ry, op=.35, col="#000"):
        return self.ell(x, y, rx, ry, self.rad([(0, col, op), (1, col, 0)]))

    # ----- tapered limb -----
    def limb(self, x1, y1, x2, y2, w1, w2, fill):
        """Tapered limb with round ends: a quad plus two end circles (always convex, no gaps at joints)."""
        a = math.atan2(y2 - y1, x2 - x1); nx, ny = -math.sin(a), math.cos(a)
        d = (f"M{x1+nx*w1/2:.1f} {y1+ny*w1/2:.1f} L{x2+nx*w2/2:.1f} {y2+ny*w2/2:.1f} L{x2-nx*w2/2:.1f} {y2-ny*w2/2:.1f} "
             f"L{x1-nx*w1/2:.1f} {y1-ny*w1/2:.1f}Z")
        return self.add(f'<g fill="{fill}"><path d="{d}"/><circle cx="{x1:.1f}" cy="{y1:.1f}" r="{w1/2:.1f}"/><circle cx="{x2:.1f}" cy="{y2:.1f}" r="{w2/2:.1f}"/></g>')

    # ----- patterns -----
    def pattern(self, kind, c1, c2, s=24, tf=None):
        key = ("p", kind, c1, c2, s, tf)
        if key in self._g: return self._g[key]
        i = self.id("p")
        if kind == "ankara":
            inner = (f'<circle cx="{s/2}" cy="{s/2}" r="{s*.32}" fill="none" stroke="{c1}" stroke-width="{s*.09}"/>'
                     f'<circle cx="{s/2}" cy="{s/2}" r="{s*.12}" fill="{c2}"/><circle cx="0" cy="0" r="{s*.14}" fill="{c1}"/>'
                     f'<circle cx="{s}" cy="0" r="{s*.14}" fill="{c1}"/><circle cx="0" cy="{s}" r="{s*.14}" fill="{c1}"/><circle cx="{s}" cy="{s}" r="{s*.14}" fill="{c1}"/>')
        elif kind == "leaf":
            inner = (f'<path d="M{s/2} {s*.1} Q{s*.85} {s/2} {s/2} {s*.9} Q{s*.15} {s/2} {s/2} {s*.1}Z" fill="{c1}"/>'
                     f'<path d="M{s/2} {s*.25} L{s/2} {s*.75}" stroke="{c2}" stroke-width="{s*.06}"/>')
        elif kind == "aso":
            inner = (f'<rect width="{s*.18}" height="{s}" fill="{c1}"/><rect x="{s*.5}" width="{s*.07}" height="{s}" fill="{c2}"/>'
                     f'<rect x="{s*.7}" width="{s*.07}" height="{s}" fill="{c1}" opacity=".6"/>')
        elif kind == "adire":
            inner = (f'<path d="M{s*.2} {s/2} A{s*.3} {s*.3} 0 1 1 {s/2} {s*.8} A{s*.18} {s*.18} 0 1 1 {s*.62} {s*.5}" fill="none" stroke="{c1}" stroke-width="{s*.07}"/>'
                     f'<circle cx="{s*.1}" cy="{s*.1}" r="{s*.05}" fill="{c1}"/>')
        elif kind == "dots":
            inner = f'<circle cx="{s/2}" cy="{s/2}" r="{s*.18}" fill="{c1}"/>'
        elif kind == "zig":
            inner = f'<path d="M0 {s*.7} L{s/4} {s*.3} L{s/2} {s*.7} L{s*.75} {s*.3} L{s} {s*.7}" fill="none" stroke="{c1}" stroke-width="{s*.12}"/>'
        else:
            inner = ""
        t = f' patternTransform="{tf}"' if tf else ""
        self.defs.append(f'<pattern id="{i}" width="{s}" height="{s}" patternUnits="userSpaceOnUse"{t}>{inner}</pattern>')
        self._g[key] = f"url(#{i})"; return self._g[key]

    # ----- output -----
    def svg(self, bg, grain=.16, paint=4, vignette=.38, warm=None):
        pid, gid, vid = self.id("f"), self.id("f"), self.id("v")
        defs = "".join(self.defs) + (
            f'<filter id="{pid}" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="2" seed="7" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="{paint}" xChannelSelector="R" yChannelSelector="G"/></filter>'
            f'<filter id="{gid}"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/><feColorMatrix type="saturate" values="0"/>'
            f'<feComponentTransfer><feFuncA type="table" tableValues="0 {grain}"/></feComponentTransfer></filter>'
            f'<radialGradient id="{vid}" cx=".5" cy=".46" r=".72"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{vignette}"/></radialGradient>')
        w = f'<rect width="1000" height="1000" fill="{warm}" opacity=".10" style="mix-blend-mode:soft-light"/>' if warm else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000"><defs>{defs}</defs>'
                f'<rect width="1000" height="1000" fill="{bg}"/><g filter="url(#{pid})">{"".join(self.body)}</g>{w}'
                f'<rect width="1000" height="1000" fill="url(#{vid})"/><rect width="1000" height="1000" filter="url(#{gid})" style="mix-blend-mode:multiply"/></svg>')


# ---------- figures ----------
POSES = {
    "stand": dict(eL=(-15, -56), hL=(-15, -40), eR=(15, -56), hR=(15, -40), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "cheer": dict(eL=(-21, -84), hL=(-25, -101), eR=(21, -84), hR=(25, -101), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "wave": dict(eL=(-15, -56), hL=(-14, -40), eR=(22, -82), hR=(26, -100), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "mic": dict(eL=(-15, -56), hL=(-14, -40), eR=(16, -58), hR=(5, -78), kL=(-6, -21), fL=(-9, 0), kR=(6, -21), fR=(9, 0)),
    "dance": dict(eL=(-24, -78), hL=(-20, -97), eR=(22, -60), hR=(33, -70), kL=(-13, -20), fL=(-20, -1), kR=(7, -22), fR=(14, 0)),
    "dance2": dict(eL=(-22, -62), hL=(-33, -72), eR=(24, -80), hR=(21, -98), kL=(-7, -22), fL=(-14, 0), kR=(13, -20), fR=(20, -1)),
    "walk": dict(eL=(-12, -56), hL=(-6, -42), eR=(14, -56), hR=(20, -44), kL=(-9, -21), fL=(-16, 0), kR=(7, -22), fR=(12, 0)),
    "run": dict(eL=(-20, -62), hL=(-12, -50), eR=(14, -52), hR=(24, -62), kL=(-16, -26), fL=(-28, -10), kR=(12, -20), fR=(10, 0)),
    "kick": dict(eL=(-24, -66), hL=(-34, -58), eR=(20, -64), hR=(30, -72), kL=(-4, -21), fL=(-6, 0), kR=(18, -30), fR=(36, -24)),
    "sit": dict(eL=(-15, -56), hL=(-6, -46), eR=(15, -56), hR=(6, -46), kL=(-14, -40), fL=(-14, -14), kR=(14, -40), fR=(14, -14)),
    "hold": dict(eL=(-16, -54), hL=(-4, -50), eR=(16, -54), hR=(4, -50), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "point": dict(eL=(-15, -56), hL=(-15, -40), eR=(26, -66), hR=(44, -74), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "shake": dict(eL=(-15, -56), hL=(-15, -40), eR=(17, -57), hR=(29, -51), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "read": dict(eL=(-16, -52), hL=(-6, -60), eR=(16, -52), hR=(6, -60), kL=(-14, -40), fL=(-14, -14), kR=(14, -40), fR=(14, -14)),
    "carry": dict(eL=(-14, -55), hL=(2, -52), eR=(14, -55), hR=(22, -50), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "praise": dict(eL=(-19, -86), hL=(-26, -104), eR=(19, -86), hR=(26, -104), kL=(-6, -21), fL=(-8, 0), kR=(6, -21), fR=(8, 0)),
    "hoe": dict(eL=(-6, -58), hL=(10, -50), eR=(14, -54), hR=(22, -46), kL=(-10, -21), fL=(-14, 0), kR=(8, -22), fR=(12, 0)),
}


def person(A, x, y, s, pose="stand", skin=None, top=None, bottom=None, dress=False, head=None, headc=None,
           pattern=None, flip=False, agbada=None, shoes=None, back=False, sleeve=None):
    """x,y = point between the feet; s = pixels per body unit (body is ~100 units tall). Light from the left."""
    skin = skin or P["skin2"]; top = top or P["indigo"]; bottom = bottom or P["ink"]; shoes = shoes or P["ink"]
    J = dict(POSES[pose]); sx = -1 if flip else 1
    T = lambda p: (x + sx * p[0] * s, y + p[1] * s)
    w = lambda u: u * s
    sit = pose == "sit"
    shL, shR = T((-12.5, -69)), T((12.5, -69))
    hpL, hpR = (T((-10, -40)), T((10, -40))) if sit else (T((-9.5, -43)), T((9.5, -43)))
    SK, TP, BT = A.shade(skin, .38), A.shade(top, .38), A.shade(bottom, .34)
    A.shadow(x + w(6), y + w(1), w(26), w(4.5), .38)
    # legs
    for side in "LR":
        hp = hpL if side == "L" else hpR
        k, f = T(J["k" + side]), T(J["f" + side])
        base = skin if dress else bottom
        lc = base if side == "L" else dk(base, .14)   # far leg a touch darker, flat fill (no blobs at the knee)
        A.limb(*hp, *k, w(11.5), w(9), lc)
        A.limb(*k, *f, w(9), w(6.4), lc)
        fx = f[0] + sx * w(3.2) + (sx * w(1.2) if side == "R" else -sx * w(.4))
        A.limb(f[0] - sx * w(1), f[1] - w(1.4), fx + sx * w(1.5), f[1] - w(.2), w(5.6), w(4.8), shoes)
    def torso_d(hw=10):
        a = T((-12.5, -69)); b = T((12.5, -69))
        return (f"M{a[0]:.1f} {a[1]:.1f} Q{T((-15,-67))[0]:.1f} {T((-15,-67))[1]:.1f} {T((-13.5,-61))[0]:.1f} {T((-13.5,-61))[1]:.1f} "
                f"L{T((-hw+.5,-50))[0]:.1f} {T((-hw+.5,-50))[1]:.1f} L{T((-hw,-42))[0]:.1f} {T((-hw,-42))[1]:.1f} L{T((hw,-42))[0]:.1f} {T((hw,-42))[1]:.1f} "
                f"L{T((hw-.5,-50))[0]:.1f} {T((hw-.5,-50))[1]:.1f} L{T((13.5,-61))[0]:.1f} {T((13.5,-61))[1]:.1f} Q{T((15,-67))[0]:.1f} {T((15,-67))[1]:.1f} {b[0]:.1f} {b[1]:.1f} "
                f"Q{T((0,-73))[0]:.1f} {T((0,-73))[1]:.1f} {a[0]:.1f} {a[1]:.1f}Z")
    if dress:
        hem = -14 if not sit else -30
        hl, hr = T((-21, hem)), T((21, hem))
        d = (f"M{shL[0]:.1f} {shL[1]:.1f} Q{T((0,-73))[0]:.1f} {T((0,-73))[1]:.1f} {shR[0]:.1f} {shR[1]:.1f} "
             f"Q{T((15,-67))[0]:.1f} {T((15,-67))[1]:.1f} {T((12.5,-60))[0]:.1f} {T((12.5,-60))[1]:.1f} L{T((10,-49))[0]:.1f} {T((10,-49))[1]:.1f} "
             f"Q{T((16,-34))[0]:.1f} {T((16,-34))[1]:.1f} {hr[0]:.1f} {hr[1]:.1f} Q{x:.1f} {T((0,hem+3))[1]:.1f} {hl[0]:.1f} {hl[1]:.1f} "
             f"Q{T((-16,-34))[0]:.1f} {T((-16,-34))[1]:.1f} {T((-10,-49))[0]:.1f} {T((-10,-49))[1]:.1f} L{T((-12.5,-60))[0]:.1f} {T((-12.5,-60))[1]:.1f} "
             f"Q{T((-15,-67))[0]:.1f} {T((-15,-67))[1]:.1f} {shL[0]:.1f} {shL[1]:.1f}Z")
        A.path(d, TP)
        if pattern: A.path(d, A.pattern(*pattern), .6)
        A.path(d, A.lin([(0, "#FFF8E8", .18), (.4, "#000", 0), (1, "#000", .32)], 0, 0, 1, 0))
        for k, u in enumerate((-9, -2, 6, 13)):  # folds
            a, b = T((u * .5, -47)), T((u * 1.25, hem + 2))
            A.stroke(f"M{a[0]:.1f} {a[1]:.1f} Q{(a[0]+b[0])/2 + w(2):.1f} {(a[1]+b[1])/2:.1f} {b[0]:.1f} {b[1]:.1f}", dk(top, .45), w(1.1), .35)
        wa, wb = T((-10, -49)), T((10, -49))
        A.stroke(f"M{wa[0]:.1f} {wa[1]:.1f} Q{x:.1f} {wa[1]+w(2):.1f} {wb[0]:.1f} {wb[1]:.1f}", dk(top, .5), w(1.6), .45)
    else:
        d = torso_d()
        A.path(d, TP)
        if pattern: A.path(d, A.pattern(*pattern), .6)
        A.path(d, A.lin([(0, "#FFF8E8", .16), (.45, "#000", 0), (1, "#000", .3)], 0, 0, 1, 0))
        A.path(f"M{T((-10,-43))[0]:.1f} {T((-10,-43))[1]:.1f} L{T((10,-43))[0]:.1f} {T((10,-43))[1]:.1f} L{T((10.2,-36))[0]:.1f} {T((10.2,-36))[1]:.1f} L{T((-10.2,-36))[0]:.1f} {T((-10.2,-36))[1]:.1f}Z", BT)
        A.stroke(f"M{T((-9.6,-44))[0]:.1f} {T((-9.6,-44))[1]:.1f} L{T((9.6,-44))[0]:.1f} {T((9.6,-44))[1]:.1f}", dk(top, .5), w(1.4), .5)
    if agbada:
        ac = agbada[0]
        d = (f"M{shL[0]:.1f} {shL[1]-w(1):.1f} Q{T((0,-74))[0]:.1f} {T((0,-74))[1]:.1f} {shR[0]:.1f} {shR[1]-w(1):.1f} L{T((31,-47))[0]:.1f} {T((31,-47))[1]:.1f} "
             f"Q{T((27,-20))[0]:.1f} {T((27,-20))[1]:.1f} {T((16,-15))[0]:.1f} {T((16,-15))[1]:.1f} Q{x:.1f} {T((0,-13))[1]:.1f} {T((-16,-15))[0]:.1f} {T((-16,-15))[1]:.1f} "
             f"Q{T((-27,-20))[0]:.1f} {T((-27,-20))[1]:.1f} {T((-31,-47))[0]:.1f} {T((-31,-47))[1]:.1f}Z")
        A.path(d, A.shade(ac, .42))
        for u in (-20, -8, 8, 20):
            a, b = T((u * .4, -66)), T((u, -17))
            A.stroke(f"M{a[0]:.1f} {a[1]:.1f} Q{(a[0]+b[0])/2:.1f} {(a[1]+b[1])/2 + w(3):.1f} {b[0]:.1f} {b[1]:.1f}", dk(ac, .35), w(1.2), .4)
        if len(agbada) > 1:
            nk = T((0, -71))
            A.path(f"M{nk[0]-w(7):.1f} {nk[1]:.1f} Q{nk[0]:.1f} {nk[1]+w(26):.1f} {nk[0]+w(7):.1f} {nk[1]:.1f} Q{nk[0]:.1f} {nk[1]+w(14):.1f} {nk[0]-w(7):.1f} {nk[1]:.1f}Z", agbada[1], .95)
    # arms
    armc = A.shade(agbada[0], .42) if agbada else A.shade(sleeve, .38) if sleeve else TP
    for side in "LR":
        sh = T((-12, -67.5)) if side == "L" else T((12, -67.5))
        e, h = T(J["e" + side]), T(J["h" + side])
        ac0 = agbada[0] if agbada else sleeve or top
        far = side == "R"
        A.limb(*sh, *e, w(8.6), w(7), dk(ac0, .16) if far else ac0)
        if dress and not sleeve: A.circ(sh[0], sh[1] + w(1), w(5.2), TP)
        skc = dk(skin, .14) if far else skin
        A.limb(*e, *h, w(6.8), w(5.2), skc)
        A.circ(h[0], h[1], w(3.6), skc)
    # neck, head
    nk, hd = T((0, -73)), T((0, -85.5))
    A.limb(nk[0], nk[1] + w(2), hd[0], hd[1] + w(5), w(6.2), w(6), SK)
    A.path(f"M{nk[0]-w(3):.1f} {nk[1]-w(1):.1f} Q{nk[0]:.1f} {nk[1]+w(2.5):.1f} {nk[0]+w(3):.1f} {nk[1]-w(1):.1f}Z", dk(skin, .35), .5)
    HR = w(9)
    A.circ(hd[0], hd[1], HR, A.rad([(0, lt(skin, .32), 1), (.55, skin, 1), (1, dk(skin, .42), 1)], .36, .33, .72))
    A.ell(hd[0] + sx * w(8.4), hd[1] + w(1.2), w(1.6), w(2.6), dk(skin, .15))  # ear
    A.path(f"M{hd[0]-HR*.6:.1f} {hd[1]+HR*.45:.1f} Q{hd[0]:.1f} {hd[1]+HR*1.05:.1f} {hd[0]+HR*.6:.1f} {hd[1]+HR*.45:.1f} Q{hd[0]:.1f} {hd[1]+HR*.85:.1f} {hd[0]-HR*.6:.1f} {hd[1]+HR*.45:.1f}Z", dk(skin, .4), .35)  # jaw shade
    hc = headc or P["kola"]
    hx, hy = hd
    if head == "gele":
        A.path(f"M{hx-w(12):.1f} {hy-w(1):.1f} C{hx-w(19):.1f} {hy-w(16):.1f} {hx-w(5):.1f} {hy-w(29):.1f} {hx+sx*w(8):.1f} {hy-w(23):.1f} "
               f"C{hx+sx*w(22):.1f} {hy-w(28):.1f} {hx+sx*w(20):.1f} {hy-w(8):.1f} {hx+sx*w(11):.1f} {hy-w(1):.1f} Q{hx:.1f} {hy-w(6):.1f} {hx-w(12):.1f} {hy-w(1):.1f}Z", A.shade(hc, .42))
        for k in range(3):
            A.stroke(f"M{hx-w(9-k):.1f} {hy-w(6+k*5):.1f} Q{hx:.1f} {hy-w(15+k*5):.1f} {hx+sx*w(12+k):.1f} {hy-w(8+k*5):.1f}", lt(hc, .45) if k % 2 == 0 else dk(hc, .35), w(1.2), .65)
    elif head == "fila":
        A.path(f"M{hx-w(9.4):.1f} {hy-w(2.5):.1f} Q{hx-w(9.6):.1f} {hy-w(12):.1f} {hx:.1f} {hy-w(13):.1f} Q{hx+sx*w(15):.1f} {hy-w(13):.1f} {hx+sx*w(16):.1f} {hy-w(7):.1f} L{hx+sx*w(9.4):.1f} {hy-w(2.5):.1f}Z", A.shade(hc, .42))
        A.stroke(f"M{hx-w(9.2):.1f} {hy-w(3):.1f} L{hx+sx*w(9.2):.1f} {hy-w(3):.1f}", dk(hc, .4), w(1.3), .6)
    elif head == "afro":
        A.circ(hx, hy - w(3.5), w(12), A.rad([(0, "#3A2C22", 1), (1, P["hair"], 1)], .38, .33, .72))
        A.circ(hx, hy + w(1.4), w(8.3), A.rad([(0, lt(skin, .32), 1), (.55, skin, 1), (1, dk(skin, .42), 1)], .36, .33, .72))
    elif head == "braids":
        A.path(f"M{hx-w(9.6):.1f} {hy:.1f} Q{hx:.1f} {hy-w(17):.1f} {hx+w(9.6):.1f} {hy:.1f} L{hx+w(10.5):.1f} {hy+w(17):.1f} L{hx+w(6.4):.1f} {hy+w(17):.1f} "
               f"L{hx+w(5.4):.1f} {hy-w(2.5):.1f} L{hx-w(5.4):.1f} {hy-w(2.5):.1f} L{hx-w(6.4):.1f} {hy+w(17):.1f} L{hx-w(10.5):.1f} {hy+w(17):.1f}Z", P["hair"])
    elif head == "cap":
        A.path(f"M{hx-w(9):.1f} {hy-w(1):.1f} Q{hx-w(8.6):.1f} {hy-w(10.2):.1f} {hx:.1f} {hy-w(10.3):.1f} Q{hx+w(8.6):.1f} {hy-w(10.2):.1f} {hx+w(9):.1f} {hy-w(1):.1f} Q{hx:.1f} {hy-w(5.5):.1f} {hx-w(9):.1f} {hy-w(1):.1f}Z", P["hair"])
    elif head == "grad":
        A.path(f"M{hx-w(9):.1f} {hy-w(2):.1f} Q{hx:.1f} {hy-w(12):.1f} {hx+w(9):.1f} {hy-w(2):.1f}Z", P["ink"])
        A.poly([(hx - w(15), hy - w(9.5)), (hx, hy - w(15)), (hx + w(15), hy - w(9.5)), (hx, hy - w(5))], P["ink"])
        A.stroke(f"M{hx:.1f} {hy-w(10):.1f} Q{hx+w(12):.1f} {hy-w(8):.1f} {hx+w(12):.1f} {hy+w(2):.1f}", P["gold"], w(1.1))
    elif head == "wrap":
        A.path(f"M{hx-w(9.6):.1f} {hy-w(1):.1f} Q{hx-w(11):.1f} {hy-w(15):.1f} {hx:.1f} {hy-w(15):.1f} Q{hx+w(11):.1f} {hy-w(15):.1f} {hx+w(9.6):.1f} {hy-w(1):.1f}Z", A.shade(hc, .42))
    return hd


def back_crowd(A, y0, rows, cols, seed=3, scale=1.0, rim=None, phones=0, hands=.2, xs=(-40, 1040), dens=1.0):
    """Heads and shoulders seen from behind, lit from the stage (rim light)."""
    r = random.Random(seed)
    for row in range(rows):
        y = y0 + row * 58 * scale
        s = (1 + row * .22) * scale
        x = xs[0] - r.uniform(0, 50)
        c = cols[min(row, len(cols) - 1)]
        while x < xs[1]:
            hr = 19 * s
            if r.random() < hands:
                side = r.choice((-1, 1)); hx, hy = x + side * 36 * s, y - 70 * s
                A.limb(x + side * 22 * s, y + 18 * s, hx, hy, 13 * s, 9 * s, c)
                if phones and r.random() < phones:
                    A.rect(hx - 7 * s, hy - 16 * s, 14 * s, 22 * s, "#CFE6FF", 2 * s)
                    A.glow(hx, hy - 6 * s, 28 * s, "#BFE0FF", .35)
                else:
                    A.circ(hx, hy - 4 * s, 7 * s, c)
            A.path(f"M{x-38*s:.1f} {y+80*s:.1f} Q{x-36*s:.1f} {y+10*s:.1f} {x:.1f} {y+10*s:.1f} Q{x+36*s:.1f} {y+10*s:.1f} {x+38*s:.1f} {y+80*s:.1f}Z", c)
            A.circ(x, y - 12 * s, hr, c)
            if rim:
                A.stroke(f"M{x-hr*.85:.1f} {y-12*s-hr*.45:.1f} A{hr:.1f} {hr:.1f} 0 0 1 {x+hr*.85:.1f} {y-12*s-hr*.45:.1f}", rim, 2.6 * s, .75)
                A.stroke(f"M{x-30*s:.1f} {y+16*s:.1f} Q{x:.1f} {y+8*s:.1f} {x+30*s:.1f} {y+16*s:.1f}", rim, 2 * s, .45)
            x += r.uniform(60, 82) * s / dens


# ---------- scenery ----------
def skyline(A, base, seed, x0=-20, x1=1020, hmin=80, hmax=360, wmin=40, wmax=110, col="#2A3052", lit="#FFD27A",
            lit_p=.35, haze_col=None, top_light=None):
    r = random.Random(seed); x = x0
    while x < x1:
        bw = r.uniform(wmin, wmax); bh = r.uniform(hmin, hmax)
        if r.random() < .15: bh *= 1.35
        g = A.lin([(0, top_light or lt(col, .12), 1), (1, col, 1)])
        A.rect(x, base - bh, bw - 4, bh + 2, g)
        if r.random() < .3:  # antenna / crown
            A.rect(x + bw / 2 - 3, base - bh - 26, 3, 26, col)
        # windows
        if lit_p:
            for wy in range(int(base - bh + 12), int(base - 6), 14):
                for wx in range(int(x + 6), int(x + bw - 10), 11):
                    if r.random() < lit_p:
                        A.rect(wx, wy, 5, 7, lit, 0, r.uniform(.45, .95))
        x += bw
    if haze_col:
        A.haze(base - hmax * .6, base, haze_col, .55)


def palm(A, x, y, h, lean=0, col="#16301F", trunk="#2C2016", fronds=7, seed=1):
    r = random.Random(seed)
    tx, ty = x + lean, y - h
    A.stroke(f"M{x:.1f} {y:.1f} Q{x+lean*.2:.1f} {y-h*.6:.1f} {tx:.1f} {ty:.1f}", trunk, h * .045)
    for i in range(fronds):
        a = math.radians(-170 + i * (160 / (fronds - 1)) + r.uniform(-8, 8))
        L = h * r.uniform(.42, .55)
        ex, ey = tx + math.cos(a) * L, ty + math.sin(a) * L * .55 + L * .25
        cx, cy = tx + math.cos(a) * L * .5, ty + math.sin(a) * L * .5 - L * .12
        A.path(f"M{tx:.1f} {ty:.1f} Q{cx:.1f} {cy-L*.08:.1f} {ex:.1f} {ey:.1f} Q{cx:.1f} {cy+L*.1:.1f} {tx:.1f} {ty:.1f}Z", col)


def tree(A, x, y, r, col, trunk="#3A2A1C", seed=1, light=None):
    rr = random.Random(seed)
    A.rect(x - r * .07, y - r * .9, r * .14, r * .9, trunk)
    for i in range(9):
        a = rr.uniform(0, math.pi * 2); d = rr.uniform(0, r * .55)
        A.circ(x + math.cos(a) * d, y - r * 1.15 + math.sin(a) * d * .7, r * rr.uniform(.38, .58), A.shade(col, .25, "v") if not light else col)


def string_lights(A, x0, x1, y, sag, col="#FFD27A", n=16, wire="#1A1714"):
    A.stroke(f"M{x0} {y} Q{(x0+x1)/2} {y+sag*2} {x1} {y}", wire, 2.2, .8)
    for k in range(n):
        t = (k + .5) / n; px = x0 + (x1 - x0) * t
        py = (1 - t) ** 2 * y + 2 * (1 - t) * t * (y + sag * 2) + t * t * y
        A.glow(px, py + 9, 26, col, .55); A.circ(px, py + 9, 5.5, lt(col, .5))


def danfo(A, x, y, s=1.0, flip=False):
    """Lagos yellow minibus with black stripes, side view. x,y = rear wheel ground point."""
    sx = -1 if flip else 1
    X = lambda u: x + sx * u * s
    Y = lambda v: y - v * s
    body = f"M{X(-30)} {Y(18)} L{X(-30)} {Y(92)} Q{X(-28)} {Y(100)} {X(-18)} {Y(100)} L{X(150)} {Y(100)} Q{X(178)} {Y(98)} {X(196)} {Y(62)} L{X(206)} {Y(56)} L{X(206)} {Y(18)}Z"
    A.shadow(X(88), y + 4 * s, 130 * s, 10 * s, .4)
    A.path(body, A.shade("#F2B705", .22, "v"))
    A.rect(min(X(-30), X(206)), Y(44), 236 * s, 7 * s, "#151311")
    A.rect(min(X(-30), X(206)), Y(30), 236 * s, 4 * s, "#151311")
    for i, (a, b) in enumerate([(-22, 18), (22, 62), (66, 106), (110, 148)]):
        xa, xb = sorted((X(a), X(b)))
        A.rect(xa, Y(92), xb - xa, 30 * s, A.lin([(0, "#9DC4D8", 1), (1, "#3D5E73", 1)]), 3 * s)
    A.path(f"M{X(154)} {Y(92)} L{X(176)} {Y(92)} L{X(192)} {Y(64)} L{X(154)} {Y(64)}Z", A.lin([(0, "#9DC4D8", 1), (1, "#3D5E73", 1)]))
    for wx in (0, 160):
        A.circ(X(wx), y, 17 * s, "#141414"); A.circ(X(wx), y, 8 * s, "#8A8A8A")
    A.rect(min(X(200), X(208)), Y(40), 8 * s, 10 * s, "#FFE9A8")


def floor_lines(A, vx, vy, y0, col, n=14, op=.25, w=2):
    for i in range(n + 1):
        x = -600 + i * (2200 / n)
        A.line(vx, vy, x, 1000, col, w, op)
    k = 0; y = y0
    while y < 1000:
        A.line(0, y, 1000, y, col, w * .8, op * .8); k += 1; y = y0 + (1000 - y0) * (k / 9) ** 1.6


def aso_trim(A, y=970, h=30):
    """Woven Aso-oke strip along the bottom: the series signature."""
    cols = [P["kola"], P["marigold"], P["indigo"], P["cream"], P["palm"], P["marigold"]]
    x = 0; i = 0
    while x < 1000:
        w = [34, 10, 22, 6, 28, 10][i % 6]
        A.rect(x, y, w + 1, h, cols[i % len(cols)]); x += w; i += 1
    A.rect(0, y, 1000, 3, "#000", op=.25)
    for k in range(0, 1000, 8):
        A.rect(k, y + 4, 3, h - 8, "#FFF", op=.07)


def umbrella(A, cx, cy, r, c1, c2, pole=True):
    """Market umbrella seen from the side: domed canopy with alternating panels."""
    if pole:
        A.shadow(cx + r * .15, cy + r * 1.75, r * 1.05, r * .2, .35)
        A.line(cx, cy - r * .5, cx, cy + r * 1.7, "#2B2B2B", max(3, r * .045))
    apex = (cx, cy - r * .58)
    n = 8
    for k in range(n):
        xa = cx - r + 2 * r * k / n; xb = cx - r + 2 * r * (k + 1) / n
        ca = (cx + (xa - cx) * .88, cy - r * .5); cb = (cx + (xb - cx) * .88, cy - r * .5)
        d = (f"M{apex[0]:.1f} {apex[1]:.1f} Q{ca[0]:.1f} {ca[1]:.1f} {xa:.1f} {cy:.1f} Q{(xa+xb)/2:.1f} {cy + r*.1:.1f} {xb:.1f} {cy:.1f} "
             f"Q{cb[0]:.1f} {cb[1]:.1f} {apex[0]:.1f} {apex[1]:.1f}Z")
        A.path(d, c1 if k % 2 else c2)
    # light from upper left across the dome, shadow underneath
    A.path(f"M{cx-r:.1f} {cy:.1f} Q{cx-r*.9:.1f} {cy-r*.62:.1f} {cx:.1f} {cy-r*.58:.1f} Q{cx+r*.9:.1f} {cy-r*.62:.1f} {cx+r:.1f} {cy:.1f}Z",
           A.lin([(0, "#FFF6E0", .28), (.5, "#000", 0), (1, "#000", .3)], 0, 0, 1, 0))
    A.path(f"M{cx-r:.1f} {cy:.1f} Q{cx:.1f} {cy+r*.12:.1f} {cx+r:.1f} {cy:.1f} Q{cx:.1f} {cy+r*.2:.1f} {cx-r:.1f} {cy:.1f}Z", "#000", .25)
