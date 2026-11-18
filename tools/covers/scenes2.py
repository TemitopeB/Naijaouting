import math, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from art import *

S = {}
def scene(slug):
    def d(f): S[slug] = f; return f
    return d


def window_city(A, x, y, w, h, sky, seed, lit="#FFD27A", base_col="#1C2142", bridge=False, water=None):
    """A view through a window: sky, skyline, optional lagoon and bridge, clipped to the frame."""
    cid = A.id("c"); A.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
    A.capture()
    A.rect(x, y, w, h, sky)
    hor = y + h * .62
    skyline(A, hor, seed, x - 20, x + w + 20, h * .12, h * .5, 30, 80, base_col, lit, .3)
    if water:
        A.rect(x, hor, w, h - (hor - y), water)
        for k in range(12):
            A.rect(x + random.Random(seed + k).uniform(0, w), hor + 10 + k * 12, 60, 3, lit, 1, .25)
    if bridge:
        A.rect(x, hor + 18, w, 8, "#2A2D44")
        for k in range(0, int(w), 46):
            A.rect(x + k, hor + 26, 6, 26, "#2A2D44")
            A.circ(x + k + 3, hor + 16, 3, lit, .9)
    inner = A.release()
    A.add(f'<g clip-path="url(#{cid})">{inner}</g>')


@scene("arts-culture")
def arts():
    A = Art(51)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#EBDDC6", 1), (1, "#D9C3A2", 1)]))
    A.rect(0, 0, 1000, 70, "#2A2420")
    for x in (220, 500, 780):  # track lights
        A.rect(x - 14, 60, 28, 26, "#1A1614", 4); A.beam(x, 86, 90, 520, 10, 190, "#FFF1D2", .32)
    # big framed Adire cloth
    A.shadow(500, 520, 300, 30, .25)
    A.rect(250, 140, 500, 360, "#5A3A22", 4)
    A.rect(266, 156, 468, 328, P["indigo"])
    A.rect(266, 156, 468, 328, A.pattern("adire", "#D9E2F2", P["indigo"], 52), op=.85)
    for k in range(1, 3):
        A.line(266 + k * 156, 156, 266 + k * 156, 484, "#0E163A", 3, .7)
        A.line(266, 156 + k * 109, 734, 156 + k * 109, "#0E163A", 3, .7)
    A.glow(500, 300, 300, "#FFF1D2", .25)
    # side works: small framed abstract print, carved panel
    A.rect(70, 200, 120, 160, "#3A2A1C"); A.rect(80, 210, 100, 140, A.lin([(0, P["laterite"], 1), (1, P["ochre"], 1)]))
    A.circ(130, 270, 30, P["cream"], .8)
    A.rect(820, 180, 110, 220, A.shade("#7A4A28", .3));
    for k in range(6):
        A.path(f"M835 {200+k*34} l40 14 l40 -14", "none", 1, f'stroke="#4A2A14" stroke-width="5"')
    # floor
    A.rect(0, 620, 1000, 380, A.lin([(0, "#9C6B43", 1), (1, "#6A4428", 1)]))
    floor_lines(A, 500, 400, 640, "#4A2E18", 16, .35, 2)
    A.rect(0, 616, 1000, 8, "#3A2A1C", op=.6)
    # plinth with terracotta head (Nok-inspired, stylised)
    A.shadow(770, 860, 110, 18, .4)
    A.rect(700, 640, 140, 220, A.shade("#F2ECE2", .25))
    A.path("M770 470 Q820 470 822 540 Q824 600 792 630 L748 630 Q716 600 718 540 Q720 470 770 470Z", A.shade("#B8673A", .38))
    A.path("M742 548 Q752 538 762 548 Q752 556 742 548Z", "#5A2A14"); A.path("M778 548 Q788 538 798 548 Q788 556 778 548Z", "#5A2A14")
    A.stroke("M770 556 L770 586 M756 602 Q770 610 784 602", "#6A3218", 3, .8)
    for k in range(4): A.stroke(f"M{730+k*4} {500+k*8} Q770 {478+k*6} {810-k*4} {500+k*8}", "#7A3A1C", 2.5, .6)
    # visitors: woman in gele, man in fila (viewing)
    person(A, 400, 900, 4.3, "hold", skin=P["skin2"], top=P["marigold"], dress=True, head="gele", headc=P["kola"], pattern=("ankara", P["kola"], P["indigo"], 22))
    person(A, 580, 880, 4.0, "stand", skin=P["skin3"], top=P["palm"], bottom="#2A2A2A", head="fila", headc="#3A5A9A", pattern=("aso", "#CBB57A", P["palm"], 14), flip=True)
    aso_trim(A)
    return A.svg("#D9C3A2", warm="#FFD9A0")


@scene("business")
def business():
    A = Art(61)
    A.rect(0, 0, 1000, 1000, "#1C1A22")
    window_city(A, 0, 0, 1000, 700, A.lin([(0, "#F7B36A", 1), (.5, "#F08A4B", 1), (1, "#B9583A", 1)]), 7,
                lit="#FFD27A", base_col="#3A2E3E", bridge=True, water=A.lin([(0, "#C9734A", 1), (1, "#6A3A3A", 1)]))
    A.glow(640, 380, 260, "#FFE0A0", .7)
    for x in (0, 330, 660, 990):  # window mullions
        A.rect(x - 6, 0, 12, 700, "#15131A")
    A.rect(0, 690, 1000, 14, "#15131A")
    A.rect(0, 700, 1000, 300, A.lin([(0, "#3A2E2A", 1), (1, "#1A1414", 1)]))
    # two people shaking hands, backlit
    person(A, 400, 900, 4.6, "shake", skin=P["skin3"], top="#2E3550", bottom="#20222E", head="cap", agbada=("#EADFCB", P["gold"]))
    person(A, 400 + 58 * 4.6, 900, 4.6, "shake", skin=P["skin2"], top="#E8E4DA", bottom="#262A3A", head="braids", sleeve="#2A3350", flip=True)
    A.glow(533, 660, 60, "#FFE0A0", .5)
    # conference table edge with laptop and coffee
    A.poly([(0, 880), (1000, 840), (1000, 1000), (0, 1000)], A.lin([(0, "#5A3A26", 1), (1, "#2A1A12", 1)]))
    A.stroke("M0 880 L1000 840", "#C9935A", 3, .7)
    A.poly([(90, 900), (290, 892), (300, 930), (80, 940)], A.shade("#B8BCC4", .3))
    A.poly([(120, 800), (280, 794), (290, 892), (100, 900)], A.lin([(0, "#2A2E38", 1), (1, "#14161C", 1)]))
    A.ell(820, 905, 40, 14, "#F2EBE0"); A.rect(796, 860, 48, 44, A.shade("#F2EBE0", .25), 6); A.ell(820, 862, 24, 6, "#5A3A24")
    aso_trim(A)
    return A.svg("#1A1414", warm="#FFB061")


@scene("tech")
def tech():
    A = Art(71)
    A.rect(0, 0, 1000, 1000, "#0E1022")
    window_city(A, 80, 60, 840, 520, A.lin([(0, "#0E1640", 1), (1, "#25285A", 1)]), 17, lit="#FFCF6B", base_col="#161A3A")
    for k in range(40):
        r = random.Random(k); A.glow(r.uniform(100, 900), r.uniform(380, 560), r.uniform(8, 22), r.choice(["#FFCF6B", "#FF7A7A", "#9FD3FF"]), .5)
    A.rect(70, 50, 860, 540, "none", 6, 1, 'stroke="#2A2C44" stroke-width="20"')
    A.rect(495, 60, 10, 520, "#2A2C44")
    # desk
    A.poly([(0, 700), (1000, 700), (1000, 1000), (0, 1000)], A.lin([(0, "#6A4A30", 1), (1, "#2A1C12", 1)]))
    A.rect(0, 690, 1000, 14, "#8A6040")
    # developer seated behind desk (body visible above desk)
    person(A, 480, 800, 4.4, "hold", skin=P["skin2"], top="#2F6F73", bottom="#1A1A2A", head="braids")
    # laptop from behind (lid glows), screen light on her
    A.glow(480, 560, 220, "#9FD3FF", .35)
    A.poly([(360, 700), (600, 700), (585, 560), (375, 560)], A.lin([(0, "#3A3E4A", 1), (1, "#1E2028", 1)]))
    A.circ(480, 628, 14, "#5A5E6A", .6)
    A.rect(340, 696, 280, 10, "#9AA0AA", 4)
    # second monitor with code
    A.rect(640, 470, 270, 180, "#101420", 8)
    A.rect(652, 482, 246, 156, "#0A0E1A")
    r = random.Random(3)
    for k in range(10):
        x0 = 664 + r.choice([0, 0, 16, 32]); ww = r.uniform(50, 170)
        A.rect(x0, 492 + k * 14, ww, 6, r.choice(["#7FD6A0", "#FFCF6B", "#9FD3FF", "#E58A8A", "#C9C9D9"]), 3, .85)
    A.rect(765, 650, 20, 50, "#202430"); A.rect(735, 696, 80, 8, "#202430", 3)
    A.glow(775, 560, 180, "#9FD3FF", .2)
    # plant, mug, sticky notes
    A.path("M110 700 L170 700 L162 640 L118 640Z", A.shade("#C9734A", .3))
    for k in range(7):
        a = -150 + k * 20
        A.path(f"M140 640 Q{140+math.cos(math.radians(a))*60} {600+math.sin(math.radians(a))*40} {140+math.cos(math.radians(a))*90} {640+math.sin(math.radians(a))*90}", A.shade(P["leaf"], .3), 1, f'stroke="{P["palm"]}" stroke-width="2"')
    A.rect(240, 650, 44, 50, A.shade("#E9E3D8", .3), 6); A.stroke("M284 664 q16 4 0 22", "#E9E3D8", 6)
    for k, c in enumerate([P["gold"], P["coral"], "#9FE0C0"]):
        A.rect(660 + k * 48, 420 - k % 2 * 8, 40, 40, c, 2, .9)
    aso_trim(A)
    return A.svg("#0E1022", warm="#9FD3FF")


@scene("fashion")
def fashion():
    A = Art(81)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#2A1420", 1), (1, "#120A10", 1)]))
    # backdrop textile panels
    for i, (pk, c1, c2) in enumerate([("aso", P["marigold"], P["kola"]), ("ankara", P["gold"], P["teal"]), ("adire", "#D9E2F2", P["indigo"]), ("leaf", P["coral"], P["plum"]), ("zig", P["gold"], P["kola"])]):
        x = 60 + i * 180
        A.rect(x, 60, 160, 420, c2); A.rect(x, 60, 160, 420, A.pattern(pk, c1, c2, 34), op=.8)
        A.rect(x, 60, 160, 420, A.lin([(0, "#000", 0), (1, "#000", .55)]))
    A.glow(500, 300, 360, "#FFD9A8", .35)
    # runway in perspective
    A.poly([(430, 470), (570, 470), (860, 1000), (140, 1000)], A.lin([(0, "#E9E1D6", 1), (1, "#B9AFA2", 1)]))
    A.poly([(430, 470), (570, 470), (860, 1000), (140, 1000)], A.lin([(0, "#FFF", 0), (.5, "#FFF", .25), (1, "#FFF", 0)], 0, 0, 1, 0))
    # audience both sides with camera flashes
    for side in (-1, 1):
        for row in range(4):
            for k in range(7):
                x = 500 + side * (120 + row * 70 + k * 6) + side * k * 46 * (1 + row * .3)
                y = 520 + row * 120 + k * 28
                if 0 < x < 1000:
                    s = .9 + row * .35
                    A.circ(x, y, 17 * s, "#1A0E16"); A.path(f"M{x-30*s} {y+70*s} Q{x} {y+10*s} {x+30*s} {y+70*s}Z", "#1A0E16")
                    if (k + row) % 4 == 0:
                        A.glow(x + side * -10, y - 10, 60 * s, "#FFFFFF", .7); A.circ(x + side * -10, y - 10, 5 * s, "#FFFFFF")
    for x in (300, 700):
        A.beam(x, 0, 90 + (500 - x) / 12, 900, 10, 160, "#FFE9C9", .2)
    # models walking toward us
    person(A, 520, 640, 1.9, "walk", skin=P["skin1"], top=P["teal"], dress=True, head="gele", headc=P["gold"], pattern=("leaf", P["gold"], P["teal"], 12))
    person(A, 470, 940, 5.0, "walk", skin=P["skin3"], top=P["kola"], dress=True, head="gele", headc=P["marigold"], pattern=("ankara", P["marigold"], P["indigo"], 26), flip=True)
    aso_trim(A)
    return A.svg("#120A10", warm="#FFB0A0")


@scene("faith")
def faith():
    A = Art(91)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#0F2A30", 1), (1, "#081418", 1)]))
    # big arched opening of light at the front
    A.glow(500, 360, 520, "#FFE7B0", .55)
    A.path("M330 620 L330 300 Q330 130 500 130 Q670 130 670 300 L670 620Z", A.lin([(0, "#FFF6DC", 1), (1, "#FFD68A", 1)]))
    for k in range(9):
        A.beam(500, 220, 30 + k * 15, 900, 8, 70, "#FFF3D0", .12)
    # hall: pillars and hanging lights in perspective
    for i, x in enumerate((120, 230, 770, 880)):
        A.rect(x - 22, 180, 44, 520, A.shade("#1E4A50", .3))
    for row in range(4):
        for k in range(5):
            x = 180 + k * 160 + (row % 2) * 40; y = 90 + row * 34
            A.line(x, 0, x, y, "#0A1A1E", 2); A.glow(x, y + 8, 30 - row * 4, "#FFD27A", .8); A.circ(x, y + 8, 6 - row, "#FFE9B0")
    A.rect(0, 620, 1000, 380, A.lin([(0, "#2A3A30", 1), (1, "#0C1410", 1)]))
    # congregation from behind, many hands raised
    back_crowd(A, 600, 4, ["#1E3A3E", "#152C30", "#0E2024", "#081418"], seed=8, scale=1.0, rim="#FFD27A", phones=0, hands=.6, dens=1.05)
    # one standing worshipper in front, praising
    person(A, 760, 1000, 3.8, "praise", skin=P["skin2"], top=P["cream"], dress=True, head="wrap", headc=P["teal"], pattern=("dots", P["teal"], P["cream"], 14), flip=True)
    aso_trim(A)
    return A.svg("#081418", warm="#FFD27A")


@scene("civic")
def civic():
    A = Art(101)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#E9E4D8", 1), (1, "#CFC7B6", 1)]))
    for x in (90, 330, 570, 810):  # tall windows with daylight
        A.rect(x, 90, 110, 330, "#B7D3DB"); A.rect(x, 90, 110, 330, A.lin([(0, "#FFF", .5), (1, "#FFF", 0)]))
        A.line(x + 55, 90, x + 55, 420, "#9AA3A0", 4); A.line(x, 255, x + 110, 255, "#9AA3A0", 4)
        A.beam(x + 55, 300, 110, 600, 50, 120, "#FFF6DC", .18)
    A.rect(0, 440, 1000, 30, "#A8987A")
    # stage, podium, flag
    A.rect(0, 470, 1000, 120, A.lin([(0, "#7A5236", 1), (1, "#5A3A24", 1)]))
    A.line(800, 220, 800, 590, "#7A6A5A", 7); A.circ(800, 216, 9, P["gold"])
    A.path("M806 232 Q850 222 890 240 Q930 258 970 246 L970 380 Q930 392 890 374 Q850 356 806 366Z", P["flag"])
    A.path("M850 228 Q870 230 890 240 Q910 250 928 254 L928 388 Q910 384 890 374 Q870 364 850 362Z", "#F6F2EA")
    person(A, 420, 600, 3.4, "point", skin=P["skin3"], top=P["indigo"], bottom="#1A1A2A", head="fila", headc=P["kola"], agbada=("#2A3A7A", P["gold"]))
    A.poly([(330, 440), (510, 440), (500, 600), (340, 600)], A.shade("#6A4228", .35))
    A.rect(320, 432, 200, 16, "#3A2416", 3)
    A.line(420, 432, 434, 380, "#222", 4); A.circ(436, 374, 7, "#333")
    A.rect(0, 590, 1000, 410, A.lin([(0, "#BFB39C", 1), (1, "#8A7E68", 1)]))
    # audience in rows from behind
    back_crowd(A, 700, 3, ["#3A3A4A", "#2A2A38", "#1C1C28"], seed=12, scale=1.25, rim="#FFF2D6", hands=.18, dens=.95)
    aso_trim(A)
    return A.svg("#8A7E68", warm="#FFF0D0")


@scene("comedy")
def comedy():
    A = Art(111)
    A.rect(0, 0, 1000, 1000, "#2A1712")
    # brick wall
    for row in range(30):
        y = row * 26
        for k in range(-1, 14):
            x = k * 80 + (40 if row % 2 else 0)
            A.rect(x + 2, y + 2, 76, 22, random.Random(row * 31 + k).choice(["#6A2E20", "#7A3424", "#5E281C", "#713222"]), 2)
    A.rect(0, 0, 1000, 1000, A.rad([(0, "#000", 0), (.6, "#000", .5), (1, "#000", .85)], .5, .38, .75))
    A.glow(500, 360, 300, "#FFE3A8", .7)
    A.beam(500, -40, 90, 760, 30, 220, "#FFF2D0", .22)
    # stool and comedian
    A.shadow(500, 720, 160, 22, .5)
    A.rect(620, 560, 60, 10, "#2A2A2A"); A.line(630, 570, 616, 720, "#2A2A2A", 6); A.line(670, 570, 684, 720, "#2A2A2A", 6)
    A.rect(642, 520, 26, 40, A.lin([(0, "#7FB0E0", .7), (1, "#3A70A0", .7)]), 4)  # water bottle
    person(A, 480, 720, 4.6, "mic", skin=P["skin2"], top="#E9A21B", bottom="#1E1E2A", head="cap", pattern=("aso", P["kola"], "#E9A21B", 16))
    A.circ(503, 316, 10, "#2A2A2A"); A.stroke("M505 326 Q540 420 520 520 Q500 620 560 720", "#111", 3)
    A.rect(0, 720, 1000, 30, "#1A0E0A")
    # laughing audience silhouettes
    back_crowd(A, 820, 2, ["#140A08", "#0A0504"], seed=21, scale=1.4, rim="#FFC27A", hands=.25)
    aso_trim(A)
    return A.svg("#140A08", warm="#FFB86B")


@scene("nightlife-parties")
def nightlife():
    A = Art(121)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#1A0B33", 1), (.55, "#5B2A6E", 1), (1, "#2A1030", 1)]))
    A.glow(820, 160, 110, "#FFF2D0", .8); A.circ(820, 160, 40, "#FFF6E0")
    # skyline and cable-stayed bridge over the lagoon
    skyline(A, 560, 33, hmin=60, hmax=260, col="#24123A", lit="#FFC86B", lit_p=.3)
    A.rect(0, 560, 1000, 140, A.lin([(0, "#3A1A4A", 1), (1, "#160A20", 1)]))
    A.rect(0, 520, 1000, 10, "#1A0E26")
    A.poly([(560, 520), (590, 520), (582, 330), (568, 330)], "#2A1A3A")
    for k in range(9):
        A.line(575, 340 + k * 6, 300 + k * 30, 520, "#FFD9F0", 1.5, .55); A.line(575, 340 + k * 6, 850 - k * 30, 520, "#FFD9F0", 1.5, .55)
    for x in range(0, 1000, 22): A.circ(x, 516, 3, "#FFE0A0", .9)
    for k in range(10):
        A.rect(random.Random(k).uniform(0, 900), 580 + k * 11, 80, 3, "#FFC86B", 1, .3)
    # rooftop floor and rail
    A.rect(0, 690, 1000, 310, A.lin([(0, "#2A1A2E", 1), (1, "#120A14", 1)]))
    A.rect(0, 680, 1000, 10, "#4A3A52")
    for x in range(0, 1000, 60): A.rect(x, 640, 6, 48, "#4A3A52")
    A.rect(0, 636, 1000, 6, "#5A4A62")
    string_lights(A, -20, 1020, 40, 40, "#FFD98A", 16)
    palm(A, 70, 700, 360, 20, "#120818", "#1E1020", 8, 3)
    # DJ booth
    A.poly([(720, 740), (960, 740), (950, 880), (730, 880)], A.shade("#1E1428", .3))
    A.rect(720, 730, 240, 14, "#3A2A4A"); A.glow(840, 735, 90, "#C06BFF", .55)
    for k in range(6): A.rect(735 + k * 36, 760, 24, 100, "#6A3AA0" if k % 2 else "#3AA0C0", 3, .35)
    # three friends dancing
    person(A, 270, 940, 3.9, "dance", skin=P["skin2"], top=P["gold"], dress=True, head="braids", pattern=("dots", P["kola"], P["gold"], 14))
    person(A, 470, 950, 4.2, "dance2", skin=P["skin3"], top="#2F6F73", bottom="#1A1A2A", head="cap", pattern=("aso", P["gold"], "#2F6F73", 14))
    person(A, 650, 930, 3.7, "cheer", skin=P["skin1"], top=P["pink"], dress=True, head="afro", pattern=("leaf", P["cream"], P["pink"], 16))
    aso_trim(A)
    return A.svg("#120A14", warm="#C06BFF")


@scene("festivals-carnivals")
def festivals():
    A = Art(131)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#8FC3D6", 1), (.5, "#F3D9A8", 1), (1, "#D9A86A", 1)]))
    A.glow(800, 120, 200, "#FFF4D0", .9)
    # old Lagos street buildings with balconies
    for i, (x, w, h, c) in enumerate([(-10, 250, 330, "#E9C9A0"), (240, 260, 380, "#D98C5F"), (500, 250, 340, "#B9D3C2"), (750, 270, 390, "#E6B07A")]):
        A.rect(x, 520 - h, w, h, A.shade(c, .2, "v"))
        A.rect(x, 520 - h + 120, w, 16, dk(c, .35))
        for fx in range(int(x + 25), int(x + w - 30), 60):
            A.rect(fx, 520 - h + 40, 34, 60, "#5A3A2A"); A.rect(fx, 520 - h + 170, 34, 70, "#5A3A2A")
    for k, y in enumerate((150, 210)):
        bunting_cols = [P["kola"], P["marigold"], P["green"], P["cream"], P["blue"]]
        A.stroke(f"M-10 {y} Q500 {y+70} 1010 {y}", "#333", 2)
        for j in range(22):
            t = (j + .5) / 22; px = -10 + 1020 * t; py = (1 - t) ** 2 * y + 2 * (1 - t) * t * (y + 70) + t * t * y
            A.poly([(px - 14, py), (px + 14, py), (px, py + 30)], bunting_cols[(j + k) % 5])
    A.rect(0, 510, 1000, 490, A.lin([(0, "#C9A57A", 1), (1, "#8A6A48", 1)]))
    # crowd at the sides
    back_crowd(A, 520, 1, ["#5A3A2A"], seed=4, scale=.9, hands=.4, xs=(-40, 1040))
    # carnival dancers with feathered back-pieces
    def dancer(x, y, s, pose, top, pat, fan, hd="braids", fl=False, sk=P["skin2"]):
        cx, cy = x, y - 72 * s
        for k in range(9):
            a = math.radians(-170 + k * 20)
            A.path(f"M{cx} {cy} Q{cx+math.cos(a)*40*s} {cy+math.sin(a)*40*s - 10*s} {cx+math.cos(a)*78*s} {cy+math.sin(a)*78*s} Q{cx+math.cos(a+.12)*60*s} {cy+math.sin(a+.12)*60*s} {cx} {cy}Z",
                   [fan, lt(fan, .35), P["gold"]][k % 3])
        person(A, x, y, s, pose, skin=sk, top=top, dress=True, head=hd, pattern=pat, flip=fl)
    dancer(250, 900, 3.6, "dance", P["kola"], ("zig", P["gold"], P["kola"], 14), P["marigold"])
    dancer(560, 840, 2.9, "dance2", P["teal"], ("dots", P["gold"], P["teal"], 12), P["pink"], "afro", True, P["skin3"])
    dancer(810, 920, 3.8, "cheer", P["purple"], ("leaf", P["gold"], P["purple"], 14), P["green"], "gele", False, P["skin1"])
    person(A, 410, 990, 3.0, "hold", skin=P["skin3"], top=P["kola"], bottom="#2A2A2A", head="fila", headc=P["gold"], pattern=("aso", P["gold"], P["kola"], 12))
    A.path("M380 830 L436 841 L429 876 L436 911 L380 900 L387 865Z", A.shade("#8A5A33", .3))
    r = random.Random(9)
    for k in range(80):  # confetti
        A.rect(r.uniform(0, 1000), r.uniform(240, 700), 8, 4, r.choice([P["kola"], P["marigold"], P["green"], P["blue"], "#FFF"]), 1, .85, f'transform="rotate({r.uniform(0,180):.0f})"' if False else "")
    aso_trim(A)
    return A.svg("#8A6A48", warm="#FFC46B")


@scene("film-theatre")
def film():
    A = Art(141)
    A.rect(0, 0, 1000, 1000, "#120A0C")
    # screen showing a warm savanna sunset (no text)
    A.rect(120, 90, 760, 400, A.lin([(0, "#F6B36A", 1), (.6, "#E5703A", 1), (1, "#7A2E22", 1)]))
    A.circ(560, 330, 70, "#FFE3A8")
    A.path("M120 400 Q300 350 480 390 T880 370 L880 490 L120 490Z", "#3A1A14")
    for x in (240, 700): tree(A, x, 420, 70, "#2A120E", "#2A120E", int(x), True)
    A.glow(500, 300, 480, "#FFB07A", .3)
    for side in (0, 1):  # curtains
        x = 0 if side == 0 else 880
        A.rect(x, 0, 120, 620, A.shade("#8A1A22", .4))
        for k in range(5): A.stroke(f"M{x+12+k*24} 0 L{x+12+k*24} 620", "#5A0E14", 4, .6)
    # projector beam from the back
    A.beam(500, 1000, -90, 900, 20, 380, "#FFE9C9", .1)
    # seats and audience from behind
    for row in range(4):
        y = 600 + row * 95; s = 1 + row * .3
        for k in range(-1, 12):
            x = k * 95 * s * .78 + (row % 2) * 40 - row * 60
            A.rect(x - 38 * s, y + 18 * s, 76 * s, 70 * s, A.shade("#8A1A22", .35), 10 * s)
    back_crowd(A, 610, 4, ["#1E1014", "#160C10", "#10080A", "#0A0506"], seed=14, scale=1.0, rim="#FFB07A", hands=0, dens=.85)
    aso_trim(A)
    return A.svg("#0A0506", warm="#FFB07A")


@scene("careers-education")
def education():
    A = Art(151)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#7FB7D9", 1), (1, "#DCEBF0", 1)]))
    A.glow(180, 140, 180, "#FFF6D8", .9)
    # university hall with columns and clock tower
    A.rect(560, 160, 120, 200, A.shade("#E9DCC3", .25)); A.poly([(550, 160), (690, 160), (620, 90)], "#B9583A")
    A.circ(620, 220, 30, "#F7F3EA"); A.line(620, 220, 620, 200, "#333", 3); A.line(620, 220, 636, 226, "#333", 3)
    A.rect(200, 300, 760, 230, A.shade("#EADFC8", .2, "v"))
    A.poly([(180, 300), (980, 300), (580, 220)], A.shade("#C96B45", .25, "v"))
    for k in range(9):
        A.rect(240 + k * 82, 330, 30, 200, A.shade("#F7F3EA", .3))
    A.rect(190, 520, 780, 20, "#CFC2A8")
    palm(A, 110, 560, 330, -18, "#2E6A3A", "#5A4028", 8, 5)
    A.rect(0, 540, 1000, 460, A.lin([(0, "#6FAF55", 1), (1, "#3E7A34", 1)]))
    # graduates throwing caps
    for (x, y, s, sk, stole, hd, fl) in [(230, 960, 3.9, P["skin3"], P["green"], "braids", False), (450, 990, 4.4, P["skin2"], P["gold"], "cap", False),
                                          (680, 970, 4.0, P["skin1"], P["green"], "afro", True), (860, 930, 3.3, P["skin4"], P["gold"], "cap", True)]:
        person(A, x, y, s, "cheer", skin=sk, top="#15151C", bottom="#15151C", dress=True, head=hd, sleeve="#15151C", flip=fl)
        A.poly([(x - 7 * s, y - 70 * s), (x - 3 * s, y - 70 * s), (x - 6 * s, y - 30 * s), (x - 10 * s, y - 30 * s)], stole)
        A.poly([(x + 3 * s, y - 70 * s), (x + 7 * s, y - 70 * s), (x + 10 * s, y - 30 * s), (x + 6 * s, y - 30 * s)], stole)
    r = random.Random(5)
    for k in range(6):
        cx, cy = 200 + k * 130 + r.uniform(-30, 30), 120 + r.uniform(0, 140); a = r.uniform(-25, 25)
        A.group(f'<polygon points="{cx-34},{cy} {cx},{cy-14} {cx+34},{cy} {cx},{cy+14}" fill="#15151C"/><path d="M{cx} {cy} q20 6 22 30" stroke="{P["gold"]}" stroke-width="3" fill="none"/>', f'transform="rotate({a:.0f} {cx} {cy})"')
    aso_trim(A)
    return A.svg("#3E7A34", warm="#FFF0C0")


@scene("kids-family")
def kids():
    A = Art(161)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#9FD0E0", 1), (1, "#E9F2E0", 1)]))
    A.glow(820, 130, 160, "#FFF6D8", .9)
    for k, (x, y) in enumerate([(160, 120), (420, 80)]):
        for j in range(4): A.circ(x + j * 34, y + (j % 2) * 10, 30, "#FFFFFF", .85)
    A.rect(0, 500, 1000, 500, A.lin([(0, "#8CC063", 1), (1, "#4E8A3A", 1)]))
    for x in (60, 960): palm(A, x, 520, 260, 10 if x < 500 else -10, "#3A7A3A", "#5A4028", 8, x)
    tree(A, 230, 560, 230, "#3E7A34", "#4A3420", 3)
    A.shadow(300, 760, 300, 60, .35, "#1E3A14")
    # picnic mat with ankara cloth, food basket
    A.poly([(140, 700), (520, 680), (600, 820), (100, 850)], A.shade("#E9A21B", .2, "v"))
    A.poly([(140, 700), (520, 680), (600, 820), (100, 850)], A.pattern("ankara", P["kola"], P["indigo"], 34, "scale(1 .6)"), .6)
    A.path("M420 700 Q470 640 520 700Z", "none", 1, 'stroke="#8A5A2A" stroke-width="7"'); A.rect(410, 700, 120, 60, A.shade("#B98A4E", .3), 10)
    # parents sitting
    person(A, 230, 790, 3.0, "sit", skin=P["skin2"], top=P["teal"], dress=True, head="gele", headc=P["coral"], pattern=("leaf", P["cream"], P["teal"], 14))
    person(A, 340, 780, 3.0, "sit", skin=P["skin3"], top="#F2ECE0", bottom="#3A4A6A", head="cap", flip=True)
    # kids running with a kite
    person(A, 660, 900, 2.6, "run", skin=P["skin1"], top=P["marigold"], bottom="#2E5AAC", head="afro")
    person(A, 820, 880, 2.4, "cheer", skin=P["skin2"], top=P["pink"], dress=True, head="braids", pattern=("dots", P["cream"], P["pink"], 10), flip=True)
    A.stroke("M690 640 Q760 420 780 240", "#555", 1.6, .8)
    A.poly([(780, 170), (830, 230), (780, 300), (730, 230)], P["kola"]); A.poly([(780, 170), (830, 230), (780, 230)], P["marigold"])
    A.poly([(730, 230), (780, 230), (780, 300)], P["blue"])
    A.stroke("M780 300 Q760 340 790 370 Q820 400 800 440", "#E9A21B", 3)
    aso_trim(A)
    return A.svg("#4E8A3A", warm="#FFF0C0")


@scene("health-fitness")
def health():
    A = Art(171)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#F6B36A", 1), (.45, "#F9D9A8", 1), (.55, "#9FC3CF", 1), (1, "#E6C89A", 1)]))
    A.circ(640, 470, 90, "#FFE9B0"); A.glow(640, 470, 300, "#FFE0A0", .7)
    A.rect(0, 480, 1000, 140, A.lin([(0, "#7FB2C2", 1), (1, "#4E8A9A", 1)]))
    for k in range(14): A.rect(560 + random.Random(k).uniform(-60, 60), 490 + k * 9, 160 - k * 6, 3, "#FFE9B0", 1, .5)
    skyline(A, 480, 51, 0, 360, 40, 170, 30, 70, "#C08A6A", None, 0)  # distant Eko Atlantic towers
    A.haze(320, 480, "#F9D9A8", .7)
    A.rect(0, 600, 1000, 400, A.lin([(0, "#E9CFA0", 1), (1, "#C9A06A", 1)]))
    A.stroke("M0 620 Q500 600 1000 625", "#FFFFFF", 6, .5)
    for x in (80, 930): palm(A, x, 640, 380, 30 if x < 500 else -30, "#2A4A2E", "#4A3420", 8, x)
    # runners
    person(A, 700, 760, 2.0, "run", skin=P["skin1"], top="#2E5AAC", bottom="#1A1A2A", head="cap", flip=True)
    person(A, 330, 960, 4.6, "run", skin=P["skin3"], top=P["kola"], bottom="#1A1A2A", head="braids", shoes="#F2F2F2")
    person(A, 560, 900, 3.6, "run", skin=P["skin2"], top=P["marigold"], bottom="#2A2A3A", head="cap", shoes="#F2F2F2")
    aso_trim(A)
    return A.svg("#C9A06A", warm="#FFC07A")


@scene("expos-trade-fairs")
def expos():
    A = Art(181)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#2A3242", 1), (1, "#4A5262", 1)]))
    for k in range(10):  # roof trusses
        y = 40 + k * 26
        A.line(0, y, 1000, y + 30, "#5A6272", 3, .6)
    for x in range(0, 1000, 70): A.line(x, 0, 500 + (x - 500) * .4, 300, "#5A6272", 2, .5)
    for x in range(80, 1000, 140):
        A.glow(x, 280, 60, "#FFF2D0", .6); A.circ(x, 280, 7, "#FFF6E0")
    # hanging banners (colour only)
    for i, c in enumerate([P["kola"], P["teal"], P["marigold"], P["green"], P["blue"]]):
        x = 90 + i * 190; A.rect(x, 300, 90, 170, A.shade(c, .25)); A.rect(x + 14, 330, 62, 8, "#FFF", 2, .6); A.rect(x + 14, 350, 40, 6, "#FFF", 2, .45)
    A.rect(0, 520, 1000, 480, A.lin([(0, "#C9C2B6", 1), (1, "#8A8478", 1)]))
    floor_lines(A, 500, 420, 540, "#6A665E", 12, .3, 2)
    # booths left and right in perspective
    for side in (-1, 1):
        for k in range(3):
            x0 = 500 + side * (120 + k * 140); s = 1 + k * .45
            c = [P["kola"], P["teal"], P["marigold"]][k] if side < 0 else [P["green"], P["blue"], P["plum"]][k]
            bw = 120 * s; x = x0 if side > 0 else x0 - bw
            A.rect(x, 520 - 150 * s, bw, 150 * s, "#F2EEE6"); A.rect(x, 520 - 170 * s, bw, 26 * s, A.shade(c, .2, "v"))
            A.rect(x + 10 * s, 520 - 60 * s, bw - 20 * s, 60 * s, A.shade(c, .3)); A.rect(x + 10 * s, 520 - 64 * s, bw - 20 * s, 6 * s, "#FFF")
            for j in range(3): A.rect(x + 18 * s + j * 30 * s, 520 - 120 * s, 20 * s, 40 * s, [P["gold"], P["cream"], P["coral"]][j], 3)
    # visitors
    person(A, 330, 860, 3.3, "walk", skin=P["skin2"], top=P["coral"], dress=True, head="gele", headc=P["indigo"], pattern=("ankara", P["indigo"], P["gold"], 16))
    person(A, 600, 900, 3.6, "point", skin=P["skin3"], top="#F2F2F2", bottom="#2A3350", head="cap", flip=True)
    person(A, 480, 700, 2.0, "walk", skin=P["skin1"], top=P["teal"], bottom="#1A1A2A", head="fila", headc=P["kola"])
    aso_trim(A)
    return A.svg("#8A8478", warm="#FFF0D0")


@scene("workshops-classes")
def workshops():
    A = Art(191)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#F2E6D0", 1), (1, "#E2D2B4", 1)]))
    A.rect(60, 80, 180, 300, "#BFDCE4"); A.rect(60, 80, 180, 300, A.lin([(0, "#FFF", .6), (1, "#FFF", 0)])); A.line(150, 80, 150, 380, "#B0A48A", 5)
    A.beam(150, 230, 30, 900, 70, 260, "#FFF6DC", .22)
    # whiteboard with simple diagrams
    A.rect(330, 100, 520, 300, "#FBFBF8", 6); A.rect(330, 100, 520, 300, "none", 6, 1, 'stroke="#9A9A9A" stroke-width="10"')
    A.rect(380, 150, 110, 60, "none", 6, 1, f'stroke="{P["teal"]}" stroke-width="5"'); A.rect(560, 150, 110, 60, "none", 6, 1, f'stroke="{P["kola"]}" stroke-width="5"')
    A.stroke("M490 180 L560 180", "#333", 4); A.stroke("M615 210 L615 270 L470 270 L470 300", "#333", 4)
    A.circ(470, 330, 30, "none", 1, f'stroke="{P["marigold"]}" stroke-width="5"')
    for k in range(4): A.rect(700, 160 + k * 40, 110 - k * 15, 8, "#5A5A6A", 3, .7)
    person(A, 880, 700, 3.9, "point", skin=P["skin2"], top=P["kola"], dress=True, head="gele", headc=P["marigold"], pattern=("leaf", P["marigold"], P["kola"], 16), flip=True)
    A.rect(0, 600, 1000, 400, A.lin([(0, "#B98A5A", 1), (1, "#8A6040", 1)]))
    # tables and participants from behind
    A.poly([(40, 790), (960, 790), (1000, 860), (0, 860)], A.shade("#7A5232", .25, "v"))
    for x in (180, 470, 760):
        A.poly([(x - 60, 800), (x + 60, 800), (x + 50, 760), (x - 50, 760)], "#2A2E38")
    back_crowd(A, 780, 1, ["#2A3440"], seed=3, scale=1.7, rim="#FFF2D6", hands=.0, dens=.75)
    A.rect(0, 860, 1000, 140, A.lin([(0, "#6A4A30", 1), (1, "#4A3220", 1)]))
    aso_trim(A)
    return A.svg("#8A6040", warm="#FFF0D0")


@scene("gaming-esports")
def gaming():
    A = Art(201)
    A.rect(0, 0, 1000, 1000, "#0C0A1E")
    A.rect(0, 0, 1000, 1000, A.rad([(0, "#3A1A6A", .9), (1, "#0C0A1E", 0)], .5, .35, .7))
    # big TV with pixel game scene
    A.rect(170, 120, 660, 390, "#05050C", 10)
    A.rect(186, 136, 628, 358, A.lin([(0, "#6FC3FF", 1), (1, "#BFE9FF", 1)]))
    for k in range(30):
        A.rect(186 + k * 21, 400 - (k % 5) * 14 - (k % 3) * 10, 21, 94 + (k % 5) * 14 + (k % 3) * 10, "#3EA055")
    A.rect(186, 470, 628, 24, "#8A5A2A")
    A.rect(560, 200, 42, 42, "#FFD24A"); A.rect(420, 340, 28, 40, P["kola"]); A.rect(424, 330, 20, 14, P["skin2"])
    for k in range(4): A.rect(260 + k * 60, 180 + k % 2 * 20, 50, 18, "#FFFFFF", 0, .9)
    A.glow(500, 320, 420, "#7FD0FF", .35)
    A.rect(160, 520, 680, 8, "#7A3AFF", 0, .9); A.glow(500, 524, 340, "#7A3AFF", .3)
    # sofa and two friends from behind with controllers
    A.rect(0, 640, 1000, 360, "#100C1A")
    A.path("M60 760 Q60 690 140 690 L860 690 Q940 690 940 760 L940 1000 L60 1000Z", A.shade("#3A2A5A", .3, "v"))
    for x, c, hd in ((360, "#1A1430", "braids"), (640, "#1A1430", "cap")):
        A.circ(x, 610, 58, c); A.path(f"M{x-110} 760 Q{x-100} 650 {x} 650 Q{x+100} 650 {x+110} 760Z", c)
        A.stroke(f"M{x-50} 570 A58 58 0 0 1 {x+50} 570", "#7FD0FF", 5, .7); A.stroke(f"M{x-90} 690 Q{x} 655 {x+90} 690", "#7FD0FF", 4, .45)
        if hd == "braids":
            for k in range(-3, 4): A.line(x + k * 12, 600, x + k * 14, 700, "#0A0814", 7)
    A.limb(470, 740, 420, 700, 30, 22, "#1A1430"); A.ell(440, 690, 30, 16, "#2A2A3A"); A.glow(440, 690, 40, "#7A3AFF", .4)
    A.limb(560, 740, 600, 700, 30, 22, "#1A1430"); A.ell(590, 690, 30, 16, "#2A2A3A"); A.glow(590, 690, 40, "#3AE0FF", .4)
    aso_trim(A)
    return A.svg("#0C0A1E", warm="#7FD0FF")


@scene("books-literature")
def books():
    A = Art(211)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#3A2418", 1), (1, "#1E120C", 1)]))
    # tall bookshelves full of spines
    r = random.Random(7)
    for sx0 in (30, 690):
        A.rect(sx0, 60, 280, 720, "#5A3420")
        for sh in range(6):
            y = 80 + sh * 118; A.rect(sx0 + 10, y + 100, 260, 12, "#3A2014")
            x = sx0 + 14
            while x < sx0 + 262:
                bw = r.uniform(12, 26); bh = r.uniform(64, 98)
                A.rect(x, y + 100 - bh, bw - 2, bh, A.shade(r.choice([P["kola"], P["indigo"], P["ochre"], P["palm"], P["cream"], P["teal"], P["plum"], P["laterite"]]), .3))
                A.rect(x + 2, y + 100 - bh + 10, bw - 6, 3, "#FFF", 0, .35)
                x += bw
    # window with evening blue
    A.rect(370, 120, 260, 340, "#2A3A6A"); A.rect(370, 120, 260, 340, A.lin([(0, "#3A5A9A", 1), (1, "#E9A26A", 1)]))
    A.line(500, 120, 500, 460, "#3A2418", 8); A.line(370, 290, 630, 290, "#3A2418", 8)
    # lamp glow
    A.line(660, 300, 660, 800, "#2A1A10", 6); A.path("M610 300 L710 300 L690 240 L630 240Z", A.shade("#E9C27A", .2))
    A.glow(660, 330, 340, "#FFD9A0", .5)
    A.rect(0, 780, 1000, 220, A.lin([(0, "#6A3A24", 1), (1, "#3A2014", 1)]))
    A.ell(500, 880, 380, 70, A.pattern("zig", P["marigold"], P["kola"], 30), .5)
    # armchair and reader
    A.path("M320 860 L320 600 Q320 540 400 540 L600 540 Q680 540 680 600 L680 860Z", A.shade("#A2282A", .35))
    A.path("M280 880 L280 680 Q280 650 320 650 L340 650 L340 880Z", A.shade("#8A1E22", .3)); A.path("M660 880 L660 650 L680 650 Q720 650 720 680 L720 880Z", A.shade("#8A1E22", .3))
    person(A, 500, 870, 3.8, "read", skin=P["skin2"], top=P["marigold"], dress=True, head="gele", headc=P["teal"], pattern=("ankara", P["teal"], P["kola"], 18))
    A.poly([(468, 640), (500, 650), (532, 640), (532, 680), (500, 690), (468, 680)], "#F2EBDD"); A.line(500, 650, 500, 690, "#9A8A70", 2)
    A.rect(760, 820, 90, 26, A.shade(P["indigo"], .3), 3); A.rect(770, 796, 80, 24, A.shade(P["ochre"], .3), 3)
    aso_trim(A)
    return A.svg("#1E120C", warm="#FFC07A")


@scene("charity-volunteering")
def charity():
    A = Art(221)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#BFDDE6", 1), (1, "#F2E6CC", 1)]))
    # street behind
    for i, (x, w, h, c) in enumerate([(-20, 300, 260, "#E9C9A0"), (280, 260, 300, "#C9D3B9"), (540, 300, 250, "#E6B07A"), (840, 200, 290, "#D9A88A")]):
        A.rect(x, 470 - h, w, h, A.shade(c, .2, "v"))
        for fx in range(int(x + 24), int(x + w - 30), 64): A.rect(fx, 470 - h + 40, 34, 50, "#5A4A3A")
    A.haze(200, 480, "#F2E6CC", .5)
    A.rect(0, 470, 1000, 530, A.lin([(0, "#BFA27A", 1), (1, "#8A7050", 1)]))
    # canopy tent
    A.line(80, 260, 80, 760, "#C9C9C9", 8); A.line(920, 260, 920, 760, "#C9C9C9", 8)
    for k in range(6):
        x0 = 60 + k * 146
        A.path(f"M{x0} 260 L{x0+146} 260 L{x0+146} 300 Q{x0+73} 320 {x0} 300Z", P["blue"] if k % 2 else "#F7F3EA")
    A.poly([(60, 260), (940, 260), (840, 170), (160, 170)], A.lin([(0, "#E9EEF2", 1), (1, "#C9D2DA", 1)]))
    A.shadow(500, 760, 460, 50, .3)
    # volunteers (marigold T-shirts) and a queue
    for x, sk, hd in ((300, P["skin2"], "braids"), (520, P["skin3"], "cap")):
        person(A, x, 640, 2.9, "carry", skin=sk, top=P["marigold"], bottom="#2A3350", head=hd)
    # table with food bags and boxes
    A.rect(140, 640, 720, 30, "#F2EEE6"); A.rect(140, 670, 720, 110, A.shade("#3A5A9A", .2, "v"))
    for k in range(6):
        x = 180 + k * 110
        A.rect(x, 560, 70, 80, A.shade("#C9A06A", .3), 4); A.path(f"M{x+16} 560 Q{x+35} 530 {x+54} 560", "none", 1, 'stroke="#8A6A3A" stroke-width="4"')
    A.rect(700, 480, 120, 80, A.shade("#B98A5A", .3)); A.rect(720, 410, 100, 70, A.shade("#C99A6A", .3))
    A.path("M745 440 q15 -18 30 0 q-15 22 -30 0Z", P["kola"])
    person(A, 250, 980, 3.6, "hold", skin=P["skin1"], top=P["teal"], dress=True, head="wrap", headc=P["kola"], pattern=("leaf", P["cream"], P["teal"], 14))
    person(A, 470, 990, 3.8, "carry", skin=P["skin4"], top="#F2ECE0", bottom="#3A4A6A", head="cap", flip=True)
    person(A, 700, 970, 3.4, "stand", skin=P["skin2"], top=P["coral"], dress=True, head="gele", headc=P["indigo"], pattern=("dots", P["cream"], P["coral"], 12))
    aso_trim(A)
    return A.svg("#8A7050", warm="#FFE0A0")


@scene("agriculture")
def agriculture():
    A = Art(231)
    A.rect(0, 0, 1000, 1000, A.lin([(0, "#F2B06A", 1), (.4, "#FBDDA8", 1), (1, "#E9CFA0", 1)]))
    A.circ(560, 330, 110, "#FFE9B0"); A.glow(560, 330, 360, "#FFE0A0", .7)
    # distant hills and palms in mist
    A.path("M0 420 Q200 360 420 400 T1000 380 L1000 470 L0 470Z", "#C9A07A", .7)
    for k, x in enumerate((90, 200, 330, 760, 880, 960)):
        palm(A, x, 470, 180 + k % 3 * 30, (k % 2) * 10 - 5, "#7A6A4A", "#7A6A4A", 7, k)
    A.haze(340, 480, "#FBDDA8", .6)
    # field with yam heaps in rows (perspective)
    A.rect(0, 460, 1000, 540, A.lin([(0, "#A86A3A", 1), (1, "#6A3E1E", 1)]))
    for row in range(8):
        t = row / 7; y = 480 + (1000 - 480) * t ** 1.4; s = .35 + t * 1.3
        n = int(16 - row)
        for k in range(n + 2):
            x = (k - .5) * (1000 / n) + (row % 2) * (500 / n)
            A.path(f"M{x-48*s} {y} Q{x} {y-56*s} {x+48*s} {y}Z", A.shade("#9A5A2E", .35))
            A.stroke(f"M{x} {y-40*s} q{-6*s} {-30*s} {4*s} {-50*s}", "#3E7A34", 3 * s)
            A.ell(x + 6 * s, y - 92 * s, 10 * s, 6 * s, "#4E8A3A")
    # maize at the side
    for k in range(6):
        x = 880 + k * 22; A.stroke(f"M{x} 1000 Q{x-10} 760 {x+6} 560", "#5E8A3A", 7)
        for j in range(4): A.path(f"M{x} {900-j*90} q40 -30 60 -10 q-30 0 -60 10Z", "#6E9E3A")
    # farmer with hoe
    person(A, 420, 920, 4.3, "hoe", skin=P["skin3"], top="#3A5A3A", bottom="#5A4030", head="fila", headc="#8A5A2A")
    A.line(450, 690, 540, 900, "#5A3A1E", 9); A.poly([(530, 890), (580, 900), (560, 930), (520, 910)], "#7A7A7A")
    aso_trim(A)
    return A.svg("#6A3E1E", warm="#FFC07A")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "svg"); os.makedirs(out, exist_ok=True)
    only = sys.argv[1:]
    for k, f in S.items():
        if only and k not in only: continue
        open(os.path.join(out, k + ".svg"), "w").write(f())
        print("ok", k)
