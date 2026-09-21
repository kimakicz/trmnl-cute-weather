#!/usr/bin/env python3
"""Převod obrázků z raw/ do public/img/ pro TRMNL X (1872×1404, 16 odstínů šedi).

Postup: šeď → středový ořez na 4:3 + resize → autokontrast → doostření → gamma
→ kvantizace do pevné palety 16 rovnoměrných šedí (0, 17, … 255).
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from common import IMG_DIR, NOC_OBECNA, OBDOBI, PRIPONY, RAW_DIR, ROOT, VYCHOZI_DEN, matice

SIRKA, VYSKA = 1872, 1404               # TRMNL X, 4:3
KROK = 17
LIMIT_SNIMKU = 750_000                  # image_size_limit modelu TRMNL X (trmnl.com/api/models)
UROVNE = [i * KROK for i in range(16)]  # 16 rovnoměrných šedí displeje: 0, 17, … 255

BAYER_8 = [
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]


def _paleta():
    # quantize() dithruje jen s předanou paletou; zbytek 256 slotů vyplní bílá
    pal = Image.new("P", (1, 1))
    hodnoty = UROVNE + [255] * (256 - len(UROVNE))
    pal.putpalette([v for v in hodnoty for _ in range(3)])
    return pal


def _bayer_maska(velikost):
    dlazdice = Image.new("L", (8, 8))
    dlazdice.putdata([int((m + 0.5) / 64 * KROK) for radek in BAYER_8 for m in radek])
    maska = Image.new("L", velikost)
    for y in range(0, velikost[1], 8):
        for x in range(0, velikost[0], 8):
            maska.paste(dlazdice, (x, y))
    return maska


def kvantizuj(im, dither):
    if dither == "fs":
        q = im.convert("RGB").quantize(palette=_paleta(), dither=Image.FLOYDSTEINBERG)
        return q.convert("L")
    if dither == "bayer":
        # práh 0–16 podle matice, pak zaokrouhlení dolů na úroveň
        im = ImageChops.add(im, _bayer_maska(im.size))
        return im.point(lambda v: (v // KROK) * KROK)
    return im.point(lambda v: min(15, (v + KROK // 2) // KROK) * KROK)


def na_trmnl(cesta, cil, dither="fs", autocontrast=True, sharpen=True, gamma=1.0):
    im = Image.open(cesta).convert("L")
    im = ImageOps.fit(im, (SIRKA, VYSKA), Image.LANCZOS)    # středový ořez na 4:3 + resize
    if autocontrast:
        im = ImageOps.autocontrast(im, cutoff=0.5)          # využít celý rozsah černá–bílá
    if sharpen:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2))
    if gamma != 1.0:
        im = im.point(lambda v: round(255 * (v / 255) ** gamma))
    im = kvantizuj(im, dither)
    im.save(cil, optimize=True)

    navic = {v for _, v in Image.open(cil).getcolors()} - set(UROVNE)
    if navic:
        raise ValueError(f"{cil}: výstup obsahuje úrovně mimo paletu: {sorted(navic)}")


def velikost_4bit(cesta):
    """Odhad velikosti finálního 4bit PNG, které cloud TRMNL pošle do zařízení."""
    q = Image.open(cesta).convert("RGB").quantize(palette=_paleta(), dither=Image.NONE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True, bits=4)
    return buf.tell()


def nahled(cil):
    """Kontaktní arch všech obrázků v public/img/."""
    soubory = sorted(IMG_DIR.glob("*.png"))
    if not soubory:
        print("náhled: v public/img/ nejsou žádné obrázky")
        return
    sloupcu, tw, th, popisek = 6, 312, 234, 18
    radku = -(-len(soubory) // sloupcu)
    arch = Image.new("L", (sloupcu * tw, radku * (th + popisek)), 255)
    kresli = ImageDraw.Draw(arch)
    for i, soubor in enumerate(soubory):
        x, y = (i % sloupcu) * tw, (i // sloupcu) * (th + popisek)
        arch.paste(Image.open(soubor).convert("L").resize((tw, th), Image.LANCZOS), (x, y))
        kresli.text((x + 4, y + th + 3), soubor.stem, fill=0)
    arch.save(cil)
    print(f"náhled: {cil} ({len(soubory)} obrázků)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("soubory", nargs="*", type=Path, help="vstupy (výchozí: vše v raw/)")
    p.add_argument("--out", type=Path, default=IMG_DIR, help="výstupní složka (výchozí public/img/)")
    p.add_argument("--dither", choices=["none", "fs", "bayer"], default="fs")
    p.add_argument("--gamma", type=float, default=1.0, help="<1 zesvětlí střední tóny (např. 0.85)")
    p.add_argument("--no-autocontrast", action="store_true")
    p.add_argument("--no-sharpen", action="store_true")
    p.add_argument("--preview", action="store_true", help="vytvořit kontaktní arch preview.png")
    args = p.parse_args()

    vstupy = args.soubory or sorted(f for f in RAW_DIR.glob("*") if f.suffix.lower() in PRIPONY)
    if not vstupy:
        sys.exit(f"žádné vstupy (hledáno v {RAW_DIR})")

    zname = set(matice()) | {VYCHOZI_DEN, NOC_OBECNA} | {f"noc_{o}" for o in OBDOBI}
    args.out.mkdir(parents=True, exist_ok=True)
    for vstup in vstupy:
        cil = args.out / f"{vstup.stem}.png"
        na_trmnl(vstup, cil, args.dither, not args.no_autocontrast, not args.no_sharpen, args.gamma)
        varovani = "" if vstup.stem in zname else "  (pozor: jméno není v matici, šablona ho nepoužije)"
        odhad = velikost_4bit(cil)
        if odhad > LIMIT_SNIMKU * 0.95:
            varovani += f"  (pozor: blízko limitu {LIMIT_SNIMKU // 1000} kB, zkus --dither bayer nebo none)"
        print(f"{vstup.name} -> {cil}  {cil.stat().st_size // 1024} kB, 4bit ~{odhad // 1024} kB{varovani}")

    if args.preview:
        nahled(ROOT / "preview.png")


if __name__ == "__main__":
    main()
