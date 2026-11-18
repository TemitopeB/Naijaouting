import math, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from art import *

S = {}
def scene(slug):
    def d(f): S[slug] = f; return f
    return d


@scene("music")
def music():
    A = Art(11)
    # night stage: deep purple to indigo
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#1A0F2E", 1), (.6, "#2B1446", 1), (1, "#0D0A1A", 1)]))
    # LED wall behind the stage
    A.rect(120, 150, 760, 400, A.lin([(0, "#3A1C5C", 1), (1, "#1A0E30", 1)]), 6)
    for i in range(24):
        for j in range(12):
            A.rect(132 + i * 31, 162 + j * 32, 27, 28, P["marigold"] if (i - 12) ** 2 + (j - 5) ** 2 * 3 < 60 else "#5B2A7A", 2, .18 if (i + j) % 3 else .3)
    A.glow(500, 330, 330, "#FF8A3D", .45)
    # beams from the truss
    for x, ang, c in [(180, 62, "#FF5FA2"), (330, 75, "#FFC857"), (500, 90, "#FFFFFF"), (670, 105, "#FFC857"), (820, 118, "#FF5FA2")]:
        A.beam(x, 120, ang, 900, 6, 150, c, .22)
    A.rect(80, 100, 840, 22, "#0B0814")  # truss
    for x in range(100, 920, 40):
        A.line(x, 102, x + 20, 120, "#2A2238", 3)
    for x in (180, 330, 500, 670, 820):
        A.circ(x, 126, 12, "#FFF2D0"); A.glow(x, 126, 46, "#FFE2A0", .8)
    # stage floor
    A.poly([(40, 640), (960, 640), (1000, 720), (0, 720)], A.lin([(0, "#2A1B3A", 1), (1, "#120C1C", 1)]))
    A.rect(0, 636, 1000, 6, "#FFB35C", op=.6)
    # drummer with talking drum (left), singer (centre), guitarist (right)
    person(A, 290, 645, 3.4, "hold", skin=P["skin3"], top=P["kola"], bottom="#1E1830", head="fila", headc=P["marigold"], pattern=("aso", P["marigold"], P["ink"], 10))
    # talking drum (hourglass with cords) under arm
    A.path("M268 450 L330 462 L322 500 L330 538 L268 526 L276 488Z", A.shade("#8A5A33", .3))
    for k in range(7):
        A.line(272 + k * 8, 452 + k * 1.6, 268 + k * 9, 528 + k * 1.4, "#E8D5B0", 1.6, .8)
    A.stroke("M335 430 Q352 445 344 470", "#3A2516", 5)  # curved beater
    person(A, 712, 645, 3.4, "hold", skin=P["skin1"], top="#1F3D2E", bottom="#141022", head="cap", flip=True)
    A.path("M650 470 L748 520 L742 534 L640 486Z", A.shade("#7A3A22", .3))  # guitar neck/body
    A.ell(735, 528, 30, 24, A.shade("#B5652F", .3))
    # lead singer, agbada with gold neck embroidery
    person(A, 500, 668, 4.6, "mic", skin=P["skin2"], top=P["white"], bottom="#EDE4D3", head="cap", agbada=("#F3ECDD", P["gold"]))
    A.circ(523, 300, 9, "#2E2E2E"); A.line(523, 308, 530, 330, "#2E2E2E", 5)
    A.glow(500, 420, 260, "#FFE6B0", .25)
    # haze
    A.haze(380, 700, "#C9A6FF", .18)
    # crowd from behind with phones
    back_crowd(A, 770, 2, ["#160F22", "#0A0710"], seed=5, scale=1.5, rim="#FFB86B", phones=.5, hands=.45, dens=.95)
    aso_trim(A)
    return A.svg("#140C22", warm="#FF9A3D")


@scene("food-drink")
def food():
    A = Art(21)
    # warm evening courtyard
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#F4B76A", 1), (.45, "#E58A45", 1), (1, "#7A3A1E", 1)]))
    A.glow(760, 210, 260, "#FFE3A1", .8)
    # compound wall and zinc roof
    A.rect(0, 330, 1000, 260, A.lin([(0, "#D9A06B", 1), (1, "#B9784A", 1)]))
    A.poly([(0, 300), (1000, 250), (1000, 300), (0, 352)], A.lin([(0, "#8E8F93", 1), (1, "#5D5E62", 1)], 0, 0, 1, 0))
    for k in range(0, 1000, 26):
        A.line(k, 352 - k * .052, k, 300 - k * .05, "#4A4B4F", 2, .5)
    A.rect(620, 380, 140, 210, A.lin([(0, "#5A3A26", 1), (1, "#3A2416", 1)]))  # doorway
    A.rect(120, 400, 120, 90, "#3E2B1E"); A.rect(126, 406, 108, 78, A.lin([(0, "#F6CF83", 1), (1, "#C98A4A", 1)]))
    string_lights(A, -20, 1020, 330, 24, "#FFD98A", 18)
    # table with ankara cloth
    A.poly([(60, 640), (940, 640), (1000, 1000), (0, 1000)], A.shade("#2E3D8F", .2, "v"))
    A.poly([(60, 640), (940, 640), (1000, 1000), (0, 1000)], A.pattern("ankara", P["marigold"], P["kola"], 46, "scale(1 .5)"), .55)
    A.haze(640, 1000, "#000", .25, up=True)
    # big black pot of jollof on firewood (three-stone fire) at left
    A.shadow(330, 760, 220, 40, .5)
    for i, (x0, y0) in enumerate([(200, 800), (300, 815), (420, 805)]):
        A.ell(x0, y0, 46, 26, A.shade("#6B6159", .3))
    for k in range(5):
        A.limb(220 + k * 45, 820, 280 + k * 30, 780, 16, 12, A.shade("#5A3A1E", .3))
    A.glow(320, 790, 120, "#FF8A1E", .9)
    for k in range(9):
        fx = 250 + k * 18
        A.path(f"M{fx} 795 Q{fx-12} {760-k%3*14} {fx+4} {730-k%4*16} Q{fx+16} {765} {fx+10} 795Z", "#FFB12E" if k % 2 else "#FF6A1A", .85)
    A.path("M175 610 Q170 760 330 770 Q490 760 485 610Z", A.shade("#262422", .35))
    A.ell(330, 610, 156, 34, "#121110")
    A.ell(330, 606, 148, 28, A.rad([(0, "#F07A2C", 1), (.7, "#C8441A", 1), (1, "#8C2A10", 1)]))
    r = random.Random(4)
    for k in range(140):
        a = r.uniform(0, 6.28); d = r.uniform(0, 1) ** .5
        A.ell(330 + math.cos(a) * 140 * d, 606 + math.sin(a) * 24 * d, 4, 2.2, r.choice(["#FFB36B", "#E65A1E", "#F69A45"]), .9)
    for k in range(5):  # steam
        sx0 = 260 + k * 35
        A.stroke(f"M{sx0} 590 Q{sx0-30} 540 {sx0} 500 Q{sx0+30} 460 {sx0} 410", "#FFF4E0", 10, .18)
    A.limb(470, 580, 560, 470, 12, 9, A.shade("#6B4A2A", .3))  # wooden spoon
    A.ell(560, 468, 18, 12, A.shade("#6B4A2A", .3))
    # plates: plantain (dodo), peppers, chicken
    for (px, py, rr) in [(650, 720, 96), (840, 790, 80), (560, 880, 86)]:
        A.shadow(px, py + 14, rr * 1.05, rr * .35, .4)
        A.ell(px, py, rr, rr * .38, A.shade("#F6F0E4", .2))
        A.ell(px, py - 3, rr * .78, rr * .28, "#EDE3D0")
    for k in range(10):
        a = k * .63
        A.ell(650 + math.cos(a) * 46, 715 + math.sin(a) * 16, 22, 9, A.shade("#E8962B", .3), extra=f'transform="rotate({k*20} {650+math.cos(a)*46} {715+math.sin(a)*16})"')
    for k in range(7):
        A.path(f"M{810+k*12} {785-k%2*10} q8 -18 16 0 q-8 14 -16 0Z", "#D7261E" if k % 3 else "#F2A20B")
    A.ell(560, 874, 44, 20, A.shade("#9C4F1E", .3)); A.ell(600, 870, 30, 16, A.shade("#B3652A", .3))
    # zobo (hibiscus drink) in glasses, catching the light
    for gx in (790, 870):
        A.shadow(gx, 668, 34, 8, .45)
        A.path(f"M{gx-26} 560 L{gx+26} 560 L{gx+20} 664 L{gx-20} 664Z", A.lin([(0, "#E7EEF2", .55), (1, "#BCC8CF", .45)], 0, 0, 1, 0))
        A.path(f"M{gx-24} 590 L{gx+24} 590 L{gx+20} 662 L{gx-20} 662Z", A.lin([(0, "#9E1B3A", 1), (1, "#5A0E22", 1)], 0, 0, 1, 0))
        A.rect(gx - 16, 566, 6, 90, "#FFFFFF", 3, .35)
        A.ell(gx, 590, 24, 5, "#C2304F")
    aso_trim(A)
    return A.svg("#7A3A1E", warm="#FFB25C")


@scene("markets-pop-ups")
def market():
    A = Art(31)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#BFE0EA", 1), (.5, "#F3E1BC", 1), (1, "#C98F5A", 1)]))
    A.glow(160, 120, 240, "#FFF4D0", .9)
    # buildings with balconies (Lagos Island)
    for i, (x, w, h, c) in enumerate([(-20, 220, 360, "#D98C5F"), (190, 200, 420, "#E6C089"), (380, 240, 380, "#8FB6A8"), (610, 210, 450, "#E0A36E"), (810, 220, 400, "#C9C1B2")]):
        A.rect(x, 520 - h, w, h, A.shade(c, .18, "v"))
        for fy in range(int(520 - h + 30), 470, 70):
            for fx in range(int(x + 20), int(x + w - 40), 50):
                A.rect(fx, fy, 30, 40, A.lin([(0, "#2F3A40", 1), (1, "#55636A", 1)]))
            A.rect(x + 8, fy + 44, w - 16, 6, dk(c, .3))
        sg = [P["kola"], P["blue"], P["marigold"], P["green"], P["purple"]][i]
        A.rect(x + 14, 520 - h * .42, w - 28, 34, A.shade(sg, .2, "v"), 3)  # shop signboard (no lettering)
        A.rect(x + 24, 520 - h * .42 + 12, (w - 48) * .6, 6, "#FFFFFF", 2, .55)
        A.rect(x + 14, 470, w - 28, 50, A.lin([(0, "#2A2A2A", 1), (1, "#4A3A2A", 1)]))  # shop opening
    A.stroke("M-10 210 Q300 260 620 200 T1020 230", "#222", 2.5, .6)
    A.haze(260, 560, "#FBE7C2", .45)
    # danfo passing behind
    danfo(A, 640, 600, 1.3)
    # ground
    A.rect(0, 560, 1000, 440, A.lin([(0, "#B98454", 1), (1, "#7A4E2E", 1)]))
    # umbrellas row (big striped, perspective)
    umbrella(A, 470, 500, 130, P["blue"], P["marigold"]); umbrella(A, 170, 540, 170, P["kola"], P["cream"]); umbrella(A, 820, 540, 175, P["green"], P["cream"])
    # trader women
    person(A, 330, 790, 2.9, "hold", skin=P["skin2"], top=P["kola"], dress=True, head="gele", headc=P["marigold"], pattern=("ankara", P["marigold"], P["indigo"], 18))
    person(A, 690, 800, 3.0, "point", skin=P["skin3"], top=P["teal"], dress=True, head="wrap", headc=P["kola"], pattern=("leaf", P["cream"], P["teal"], 20), flip=True)
    # head-tray of oranges on woman walking at back
    person(A, 520, 700, 2.1, "walk", skin=P["skin1"], top=P["purple"], dress=True, head="wrap", headc=P["indigo"], pattern=("dots", P["gold"], P["purple"], 12))
    A.ell(520, 505, 52, 12, A.shade("#9C6B3A", .3))
    for k in range(9):
        A.circ(484 + k * 9, 496 - (k % 3) * 6, 9, A.shade("#F08A1E", .3))
    # baskets of produce in the foreground
    r = random.Random(3)
    for (bx, by, br, prod) in [(130, 900, 120, "#D7261E"), (390, 930, 110, "#E8A21E"), (640, 920, 120, "#3E8E3A"), (880, 900, 120, "#C8381F")]:
        A.shadow(bx, by + br * .35, br * 1.1, br * .2, .45)
        A.path(f"M{bx-br} {by-br*.25} Q{bx} {by+br*.55} {bx+br} {by-br*.25}Z", A.shade("#B98A4E", .3))
        for k in range(0, 2 * br, 14):
            A.line(bx - br + k, by - br * .25, bx - br + k * .9 + 8, by + br * .2, "#8A6233", 2, .5)
        for k in range(26):
            px = bx + r.uniform(-br * .85, br * .85); py = by - br * .25 - r.uniform(0, br * .3) * (1 - abs(px - bx) / br)
            A.circ(px, py, r.uniform(14, 20), A.rad([(0, lt(prod, .35), 1), (.6, prod, 1), (1, dk(prod, .3), 1)], .35, .3, .7))
    aso_trim(A)
    return A.svg("#C98F5A", warm="#FFC46B")


@scene("sports")
def sports():
    A = Art(41)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#070B1C", 1), (.5, "#13204A", 1), (1, "#0A1230", 1)]))
    # floodlights
    for x in (110, 890):
        A.line(x, 360, x, 80, "#1E2742", 8)
        A.rect(x - 70, 50, 140, 50, "#1B2340", 4)
        for i in range(4):
            for j in range(2):
                A.circ(x - 52 + i * 35, 64 + j * 22, 8, "#FFFFFF"); A.glow(x - 52 + i * 35, 64 + j * 22, 30, "#E9F2FF", .6)
        A.beam(x, 80, 115 if x > 500 else 65, 1000, 20, 380, "#DDE8FF", .16)
    # stands: tiers of crowd as dots in green & white
    r = random.Random(6)
    for row in range(14):
        y = 250 + row * 17
        A.rect(0, y, 1000, 17, "#0F1A3A" if row % 2 else "#13214A")
        for k in range(70):
            x = k * 14.5 + (row % 2) * 7 + r.uniform(-2, 2)
            A.circ(x, y + 8, 5.5, r.choice(["#1F9D57", "#F2F2F2", "#1F9D57", "#2B3A6B", "#E9A21B", "#1F9D57"]), .85)
    A.haze(240, 500, "#C9D8FF", .25)
    A.rect(0, 485, 1000, 18, "#0C3A24")
    for x in range(0, 1000, 120):
        A.rect(x + 6, 488, 100, 12, "#E9F2FF", 2, .18)  # LED board (blank)
    # pitch with stripes in perspective
    A.rect(0, 500, 1000, 500, "#1E7A3E")
    for k in range(9):
        y0 = 500 + 500 * (k / 9) ** 1.5; y1 = 500 + 500 * ((k + 1) / 9) ** 1.5
        if k % 2: A.rect(0, y0, 1000, y1 - y0, "#238846")
    A.stroke("M-50 620 Q500 560 1050 620", "#E8F5EC", 4, .7)
    A.glow(500, 760, 520, "#C8FFD8", .18)
    # player striking the ball
    person(A, 470, 900, 4.2, "kick", skin=P["skin3"], top="#109447", bottom="#F2F2F2", head="cap", shoes="#F2C14E")
    A.rect(426, 618, 22, 10, "#F2F2F2", op=.0)
    # ball with motion
    for k in range(5):
        A.circ(640 + k * 26, 790 - k * 22, 22 - k * 3, "#FFFFFF", .12)
    A.circ(640, 790, 26, A.rad([(0, "#FFFFFF", 1), (.7, "#E2E2E2", 1), (1, "#9A9A9A", 1)], .35, .3, .7))
    A.path("M632 778 l10 -6 l10 6 l-4 12 l-12 0Z", "#1A1A1A")
    # other players in the distance
    person(A, 760, 650, 1.6, "run", skin=P["skin1"], top="#F2F2F2", bottom="#0F2A6B", head="cap", flip=True)
    person(A, 250, 640, 1.4, "run", skin=P["skin2"], top="#109447", bottom="#F2F2F2", head="cap")
    A.shadow(470, 905, 140, 18, .4)
    aso_trim(A)
    return A.svg("#0A1230", warm="#BFD4FF")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "svg"); os.makedirs(out, exist_ok=True)
    only = sys.argv[1:]
    for k, f in S.items():
        if only and k not in only: continue
        open(os.path.join(out, k + ".svg"), "w").write(f())
        print("ok", k)
