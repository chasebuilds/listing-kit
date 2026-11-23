"""Draw the sample listing photos.

The demo homes are invented, so the pictures are illustrations drawn here with Pillow instead of
photos of real houses. Run: py scripts/make_sample_photos.py
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H, S = 1600, 1067, 2
OUT = Path(__file__).resolve().parent.parent / "examples" / "photos"

PALETTES = {
    "maple": {
        "sky_top": (150, 196, 232), "sky_bot": (232, 240, 238), "grass": (96, 140, 78),
        "siding": (112, 138, 126), "trim": (246, 240, 228), "roof": (84, 70, 64),
        "door": (176, 84, 52), "wall": (236, 224, 206), "floor": (176, 132, 92),
        "accent": (176, 84, 52), "cabinet": (88, 112, 104), "counter": (238, 234, 226),
        "wood": (150, 104, 66), "style": "craftsman", "fabric": (196, 120, 84),
    },
    "alder": {
        "sky_top": (132, 170, 214), "sky_bot": (226, 232, 240), "grass": (84, 128, 74),
        "siding": (156, 78, 62), "trim": (250, 248, 244), "roof": (52, 56, 66),
        "door": (30, 52, 96), "wall": (226, 228, 232), "floor": (150, 112, 82),
        "accent": (30, 52, 96), "cabinet": (236, 238, 240), "counter": (70, 74, 82),
        "wood": (120, 86, 60), "style": "colonial", "fabric": (60, 84, 130),
    },
}


class Canvas:
    def __init__(self) -> None:
        self.img = Image.new("RGB", (W * S, H * S), "white")
        self.d = ImageDraw.Draw(self.img)

    def sc(self, *v: float) -> list[int]:
        return [round(x * S) for x in v]

    def rect(self, x0, y0, x1, y1, fill, r=0, outline=None, width=1):
        box = self.sc(x0, y0, x1, y1)
        if r:
            self.d.rounded_rectangle(box, radius=r * S, fill=fill, outline=outline, width=width * S)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=width * S)

    def ellipse(self, x0, y0, x1, y1, fill):
        self.d.ellipse(self.sc(x0, y0, x1, y1), fill=fill)

    def poly(self, pts, fill):
        self.d.polygon([tuple(self.sc(x, y)) for x, y in pts], fill=fill)

    def line(self, x0, y0, x1, y1, fill, width=2):
        self.d.line(self.sc(x0, y0, x1, y1), fill=fill, width=width * S)

    def vgrad(self, x0, y0, x1, y1, top, bot):
        h = round((y1 - y0) * S)
        for i in range(h):
            t = i / max(1, h - 1)
            c = tuple(round(top[k] + (bot[k] - top[k]) * t) for k in range(3))
            y = round(y0 * S) + i
            self.d.line([round(x0 * S), y, round(x1 * S), y], fill=c)

    def glow(self, cx, cy, rx, ry, color, strength=0.5, blur=60):
        layer = Image.new("RGBA", self.img.size, (*color, 0))
        ImageDraw.Draw(layer).ellipse(self.sc(cx - rx, cy - ry, cx + rx, cy + ry),
                                      fill=(*color, int(255 * strength)))
        layer = layer.filter(ImageFilter.GaussianBlur(blur * S / 2))
        self.img.paste(layer, (0, 0), layer)
        self.d = ImageDraw.Draw(self.img)

    def shadow(self, box, blur=18, alpha=90):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle(self.sc(*box), fill=(0, 0, 0, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(blur * S / 2))
        self.img.paste(layer, (0, 0), layer)
        self.d = ImageDraw.Draw(self.img)

    def finish(self, path: Path, seed: int) -> None:
        small = self.img.resize((W, H), Image.Resampling.LANCZOS)
        rng = random.Random(seed)
        noise = Image.effect_noise((W, H), 9).convert("RGB")
        small = Image.blend(small, Image.blend(small, noise, 0.5), 0.05)
        vignette = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vignette).ellipse((-W // 4, -H // 4, W + W // 4, H + H // 4), fill=255)
        vignette = vignette.filter(ImageFilter.GaussianBlur(160))
        dark = Image.new("RGB", (W, H), (20, 14, 10))
        small = Image.composite(small, Image.blend(small, dark, 0.35), vignette)
        d = ImageDraw.Draw(small)
        d.text((W - 250, H - 32), "Sample illustration", fill=(255, 255, 255))
        rng.random()
        small.save(path, "JPEG", quality=84, optimize=True, progressive=True)


def tint(c, k):
    return tuple(max(0, min(255, round(v * k))) for v in c)


def window(c: Canvas, x, y, w, h, p, curtains=False, sun=True):
    c.rect(x - 8, y - 8, x + w + 8, y + h + 8, p["trim"], r=3)
    c.vgrad(x, y, x + w, y + h, (190, 222, 244), (250, 246, 226) if sun else (200, 214, 226))
    c.line(x + w / 2, y, x + w / 2, y + h, p["trim"], 6)
    c.line(x, y + h / 2, x + w, y + h / 2, p["trim"], 6)
    if curtains:
        c.rect(x - 30, y - 20, x + 34, y + h + 30, tint(p["fabric"], 1.05), r=8)
        c.rect(x + w - 34, y - 20, x + w + 30, y + h + 30, tint(p["fabric"], 1.05), r=8)


def tree(c: Canvas, x, base, s, leaf):
    c.rect(x - 14 * s, base - 150 * s, x + 14 * s, base, (92, 66, 44))
    for dx, dy, r in ((0, -250, 120), (-80, -190, 90), (80, -190, 90), (0, -170, 100)):
        c.ellipse(x + (dx - r) * s, base + (dy - r) * s, x + (dx + r) * s, base + (dy + r) * s,
                  tint(leaf, 0.9 + (dx % 3) * 0.05))


def exterior(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.vgrad(0, 0, W, 640, p["sky_top"], p["sky_bot"])
    c.glow(1250, 170, 260, 90, (255, 255, 255), 0.7)
    c.glow(420, 230, 220, 70, (255, 255, 255), 0.6)
    c.poly([(0, 600), (260, 520), (560, 590), (900, 500), (1250, 580), (1600, 520), (1600, 700), (0, 700)],
           tint(p["grass"], 0.62))
    c.vgrad(0, 640, W, H, tint(p["grass"], 1.08), tint(p["grass"], 0.82))
    siding = p["siding"]
    if p["style"] == "craftsman":
        c.shadow((250, 650, 1370, 700), 20, 120)
        c.rect(260, 400, 1340, 660, siding)
        for y in range(420, 660, 26):
            c.line(260, y, 1340, y, tint(siding, 0.9), 2)
        c.poly([(220, 410), (800, 190), (1380, 410)], p["roof"])
        c.poly([(540, 400), (800, 270), (1060, 400)], p["trim"])
        c.poly([(580, 400), (800, 290), (1020, 400)], tint(siding, 1.05))
        c.rect(700, 330, 900, 400, p["trim"])
        window(c, 330, 460, 150, 130, p)
        window(c, 1120, 460, 150, 130, p)
        c.rect(520, 520, 1080, 540, p["roof"])
        c.poly([(480, 520), (800, 440), (1120, 520)], tint(p["roof"], 1.1))
        for x in (540, 1040):
            c.rect(x - 22, 520, x + 22, 650, p["trim"])
            c.rect(x - 34, 600, x + 34, 650, tint(p["trim"], 0.9))
        c.rect(520, 650, 1080, 668, tint(p["trim"], 0.85))
        c.rect(730, 540, 870, 650, p["door"], r=4)
        c.rect(752, 560, 848, 610, (250, 232, 190))
        c.rect(752, 622, 848, 636, tint(p["door"], 0.8))
    else:
        c.shadow((250, 650, 1370, 700), 20, 120)
        c.rect(300, 330, 1300, 660, siding)
        for y in range(340, 660, 22):
            c.line(300, y, 1300, y, tint(siding, 0.84), 2)
            for x in range(300 + (y // 22 % 2) * 30, 1300, 60):
                c.line(x, y, x, y + 22, tint(siding, 0.84), 2)
        c.poly([(260, 340), (800, 180), (1340, 340)], p["roof"])
        c.rect(260, 335, 1340, 350, p["trim"])
        c.rect(1130, 170, 1190, 300, tint(siding, 0.8))
        for x in (360, 560, 1000, 1200):
            for y in (380, 520):
                c.rect(x - 22, y - 6, x - 6, y + 126, (30, 36, 46))
                window(c, x, y, 110, 120, p)
                c.rect(x + 116, y - 6, x + 132, y + 126, (30, 36, 46))
        c.rect(690, 480, 910, 660, p["trim"], r=4)
        c.rect(715, 510, 885, 660, p["door"], r=4)
        c.rect(740, 530, 860, 580, (250, 232, 190))
        c.rect(650, 470, 950, 485, p["trim"])
        c.rect(1320, 340, 1480, 640, tint(siding, 0.9))
        c.rect(1320, 340, 1480, 355, p["trim"])
        window(c, 1360, 420, 90, 110, p)
    c.poly([(740, 668), (860, 668), (1000, 1067), (600, 1067)], (214, 206, 196))
    c.poly([(780, 668), (820, 668), (860, 1067), (740, 1067)], (226, 219, 209))
    for x in (330, 420, 1180, 1280):
        c.ellipse(x - 55, 620, x + 55, 700, tint(p["grass"], 0.7))
        c.ellipse(x - 40, 610, x + 40, 680, tint(p["grass"], 0.95))
    tree(c, 150, 760, 1.5, p["grass"])
    tree(c, 1480, 720, 1.15, tint(p["grass"], 1.1))
    return c


def living(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, 760, p["wall"])
    c.vgrad(0, 760, W, H, p["floor"], tint(p["floor"], 0.78))
    for x in range(-200, W + 200, 140):
        c.line(x, 760, x - 90 + (x // 20 % 3) * 10, H, tint(p["floor"], 0.7), 2)
    c.rect(0, 740, W, 770, p["trim"])
    window(c, 1010, 150, 380, 360, p, curtains=True)
    c.glow(1200, 330, 340, 300, (255, 244, 214), 0.55, 90)
    c.rect(150, 190, 430, 410, p["trim"], r=3)
    c.rect(170, 210, 410, 390, tint(p["accent"], 1.0), r=2)
    c.ellipse(230, 250, 350, 360, tint(p["accent"], 1.25))
    c.shadow((120, 700, 1000, 790), 24, 110)
    c.rect(130, 520, 1000, 720, tint(p["fabric"], 0.9), r=46)
    c.rect(170, 440, 960, 610, p["fabric"], r=40)
    for x in (190, 420, 650):
        c.rect(x, 560, x + 220, 700, tint(p["fabric"], 1.15), r=28)
    c.rect(140, 580, 240, 730, tint(p["fabric"], 0.8), r=30)
    c.rect(890, 580, 990, 730, tint(p["fabric"], 0.8), r=30)
    c.rect(250, 600, 360, 690, tint(p["wall"], 0.95), r=14)
    c.glow(800, 920, 520, 90, (60, 40, 30), 0.35, 40)
    c.rect(300, 830, 1100, 1000, tint(p["accent"], 0.9), r=40)
    c.rect(340, 850, 1060, 980, tint(p["accent"], 1.15), r=30)
    c.rect(520, 800, 880, 840, p["wood"], r=8)
    c.rect(540, 840, 560, 905, tint(p["wood"], 0.7))
    c.rect(840, 840, 860, 905, tint(p["wood"], 0.7))
    c.rect(1420, 260, 1436, 700, (70, 60, 56))
    c.ellipse(1340, 190, 1516, 300, (250, 232, 180))
    c.glow(1428, 245, 170, 100, (255, 230, 150), 0.5, 50)
    c.ellipse(1320, 640, 1400, 740, (120, 90, 70))
    for dx, dy in ((0, -90), (-30, -60), (30, -60), (0, -140)):
        c.ellipse(1330 + dx, 560 + dy, 1390 + dx, 640 + dy, (74, 128, 76))
    return c


def kitchen(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, p["wall"])
    c.rect(0, 0, W, 130, tint(p["wall"], 0.92))
    cab = p["cabinet"]
    for x in range(40, 1200, 190):
        c.shadow((x, 90, x + 180, 460), 14, 80)
        c.rect(x, 100, x + 180, 440, cab, r=6)
        c.rect(x + 14, 114, x + 166, 426, tint(cab, 1.1), r=4)
        c.rect(x + 78, 400, x + 102, 408, (210, 200, 180))
    c.rect(40, 470, 1240, 520, p["trim"])
    for y in range(520, 640, 40):
        for x in range(40, 1240, 80):
            c.rect(x + 2, y + 2, x + 78, y + 38, tint((236, 238, 238), 0.96 + ((x + y) % 3) * 0.02))
    c.rect(40, 640, 1240, 690, p["counter"])
    c.shadow((40, 690, 1240, 700), 8, 90)
    for x in range(40, 1240, 200):
        c.rect(x, 700, x + 190, 1067, tint(cab, 0.95), r=6)
        c.rect(x + 16, 716, x + 174, 900, tint(cab, 1.08), r=4)
        c.rect(x + 16, 916, x + 174, 1050, tint(cab, 1.08), r=4)
        c.rect(x + 80, 740, x + 108, 750, (210, 200, 180))
    c.rect(1000, 700, 1200, 1067, (190, 192, 196))
    c.rect(1020, 740, 1180, 900, (60, 62, 68), r=6)
    window(c, 1300, 140, 240, 320, p)
    c.glow(1400, 300, 260, 240, (255, 244, 214), 0.5, 80)
    c.shadow((260, 860, 1260, 880), 8, 60)
    c.rect(320, 800, 1220, 840, p["counter"], r=4)
    c.rect(320, 840, 1220, 1000, tint(p["accent"], 1.0), r=10)
    for x in range(340, 1220, 150):
        c.rect(x, 860, x + 130, 985, tint(p["accent"], 1.2), r=6)
    for x in (450, 760, 1070):
        c.line(x, 0, x, 230, (40, 40, 40), 4)
        c.poly([(x - 60, 300), (x + 60, 300), (x + 36, 230), (x - 36, 230)], p["accent"])
        c.glow(x, 310, 100, 50, (255, 226, 150), 0.7, 40)
    for x in (480, 730, 980):
        c.ellipse(x - 50, 1010, x + 50, 1040, (40, 30, 24))
        c.rect(x - 8, 930, x + 8, 1020, (50, 40, 32))
        c.rect(x - 50, 900, x + 50, 940, p["wood"], r=14)
    return c


def bedroom(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, 780, tint(p["wall"], 0.98))
    c.vgrad(0, 780, W, H, p["floor"], tint(p["floor"], 0.75))
    c.rect(0, 760, W, 790, p["trim"])
    window(c, 1130, 160, 330, 330, p, curtains=True)
    c.glow(1290, 330, 300, 280, (255, 244, 214), 0.5, 80)
    c.rect(480, 130, 1080, 590, p["wood"], r=30)
    c.rect(510, 160, 1050, 560, tint(p["fabric"], 0.85), r=22)
    for x in range(540, 1040, 110):
        c.rect(x, 190, x + 90, 530, tint(p["fabric"], 0.95), r=14)
    c.shadow((420, 700, 1140, 820), 26, 110)
    c.rect(450, 560, 1110, 830, tint(p["wood"], 0.8), r=14)
    c.rect(470, 520, 1090, 760, (246, 244, 240), r=24)
    c.rect(470, 650, 1090, 790, p["fabric"], r=18)
    c.rect(470, 690, 1090, 712, tint(p["fabric"], 1.25))
    for x in (500, 800):
        c.rect(x, 500, x + 270, 610, (252, 252, 250), r=34)
    c.rect(260, 600, 400, 800, p["wood"], r=6)
    c.rect(1180, 600, 1320, 800, p["wood"], r=6)
    for x in (330, 1250):
        c.rect(x - 6, 500, x + 6, 600, (60, 50, 44))
        c.poly([(x - 60, 500), (x + 60, 500), (x + 36, 420), (x - 36, 420)], (250, 236, 200))
        c.glow(x, 470, 120, 90, (255, 226, 150), 0.6, 50)
    c.glow(780, 930, 620, 110, tint(p["accent"], 0.8), 0.45, 60)
    c.rect(120, 150, 360, 350, p["trim"], r=3)
    c.rect(140, 170, 340, 330, tint(p["accent"], 1.2), r=2)
    return c


def bath(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, (232, 236, 238))
    for y in range(0, 760, 60):
        for x in range(0, W, 120):
            c.rect(x + 2, y + 2, x + 118, y + 58, tint((236, 240, 241), 0.97 + ((x // 120 + y // 60) % 3) * 0.015))
    c.rect(0, 760, W, H, tint(p["floor"], 0.95))
    for x in range(0, W, 160):
        c.line(x, 760, x, H, tint(p["floor"], 0.7), 2)
    c.rect(0, 750, W, 770, p["trim"])
    c.shadow((100, 600, 760, 770), 18, 90)
    c.rect(100, 560, 760, 760, (250, 250, 250), r=70)
    c.rect(130, 580, 730, 700, (226, 232, 236), r=60)
    c.rect(850, 120, 960, 740, (200, 204, 208))
    c.rect(820, 150, 880, 190, (180, 184, 188))
    window(c, 1230, 140, 250, 300, p, sun=False)
    c.glow(1350, 290, 260, 220, (255, 244, 214), 0.45, 80)
    c.shadow((1000, 760, 1560, 820), 12, 80)
    c.rect(1000, 560, 1560, 780, p["wood"], r=8)
    c.rect(1000, 540, 1560, 580, p["counter"], r=6)
    c.rect(1010, 600, 1280, 760, tint(p["wood"], 1.12), r=5)
    c.rect(1290, 600, 1550, 760, tint(p["wood"], 1.12), r=5)
    c.ellipse(1180, 515, 1380, 560, (252, 252, 252))
    c.rect(1270, 470, 1290, 520, (200, 204, 208))
    c.rect(1060, 120, 1500, 470, (210, 218, 222), r=10)
    c.rect(1072, 132, 1488, 458, (236, 244, 248), r=6)
    c.glow(1280, 290, 250, 150, (255, 255, 255), 0.5, 60)
    c.rect(1520, 430, 1580, 560, p["accent"], r=8)
    return c


def backyard(p: dict, seed: int) -> Canvas:
    c = Canvas()
    c.vgrad(0, 0, W, 620, p["sky_top"], p["sky_bot"])
    c.glow(300, 200, 240, 80, (255, 255, 255), 0.65)
    c.glow(1100, 140, 260, 80, (255, 255, 255), 0.55)
    c.poly([(0, 560), (300, 470), (700, 540), (1100, 470), (1600, 540), (1600, 640), (0, 640)],
           tint(p["grass"], 0.55))
    for x in range(0, W, 70):
        c.rect(x, 380, x + 62, 700, tint(p["wood"], 0.95 + (x // 70 % 3) * 0.04))
        c.poly([(x, 380), (x + 31, 350), (x + 62, 380)], tint(p["wood"], 0.95 + (x // 70 % 3) * 0.04))
    c.shadow((0, 690, W, 710), 14, 100)
    c.vgrad(0, 700, W, H, tint(p["grass"], 1.1), tint(p["grass"], 0.78))
    tree(c, 1250, 780, 1.7, p["grass"])
    tree(c, 230, 760, 1.3, tint(p["grass"], 1.15))
    c.poly([(400, 800), (1500, 800), (1600, 1067), (300, 1067)], tint(p["wood"], 1.0))
    for i, y in enumerate(range(800, 1067, 38)):
        c.line(400 - i * 14, y, 1500 + i * 14, y, tint(p["wood"], 0.72), 3)
    c.shadow((500, 880, 1100, 900), 12, 100)
    c.ellipse(560, 880, 1040, 960, tint(p["wood"], 0.9))
    c.rect(780, 830, 820, 980, (60, 50, 44))
    c.poly([(460, 790), (800, 640), (1140, 790)], tint(p["accent"], 1.05))
    c.line(800, 640, 800, 700, (60, 50, 44), 6)
    for x in (560, 1040):
        c.ellipse(x - 60, 940, x + 60, 1000, tint(p["accent"], 0.8))
    for i in range(14):
        x = 120 + i * 100
        c.ellipse(x, 395 + (i % 2) * 14, x + 12, 407 + (i % 2) * 14, (255, 232, 160))
        c.glow(x + 6, 405 + (i % 2) * 14, 30, 24, (255, 226, 140), 0.55, 16)
    return c


SCENES = {
    "front": exterior, "living": living, "kitchen": kitchen,
    "bedroom": bedroom, "bath": bath, "yard": backyard,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, palette in PALETTES.items():
        for i, (scene, fn) in enumerate(SCENES.items(), 1):
            canvas = fn(palette, i)
            path = OUT / f"{name}-{i}-{scene}.jpg"
            canvas.finish(path, i)
            print("wrote", path.name, path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
