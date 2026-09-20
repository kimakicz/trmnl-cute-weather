import sys

from PIL import Image, ImageFilter, ImageOps

SIRKA, VYSKA = 1872, 1404               # TRMNL X, 4:3
UROVNE = [i * 17 for i in range(16)]    # 16 rovnoměrných šedí displeje: 0, 17, … 255


def _paleta():
    # quantize() dithruje jen s předanou paletou; zbytek 256 slotů vyplní bílá
    pal = Image.new("P", (1, 1))
    hodnoty = UROVNE + [255] * (256 - len(UROVNE))
    pal.putpalette([v for v in hodnoty for _ in range(3)])
    return pal


def na_trmnl(cesta, cil):
    im = Image.open(cesta).convert("L")
    im = ImageOps.fit(im, (SIRKA, VYSKA), Image.LANCZOS)    # středový ořez na 4:3 + resize
    im = ImageOps.autocontrast(im, cutoff=0.5)              # využít celý rozsah černá–bílá
    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2))
    im = im.convert("RGB").quantize(palette=_paleta(), dither=Image.FLOYDSTEINBERG)
    im.convert("L").save(cil, optimize=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("použití: python3 na_trmnl.py <vstup> <výstup>")
    na_trmnl(sys.argv[1], sys.argv[2])
