#!/usr/bin/env python3
"""Doplní v public/img/ všech 56 kombinací {kategorie}_{obdobi}_{doba}.png.

Liquid neumí ověřit existenci souboru, proto chybějící kombinace vzniknou jako
kopie podle fallbacku. Originál = obrázek, který má zdroj v raw/.

  den: přesná shoda → (bourka → dest stejného období) → zatazeno stejného období → vychozi_den
  noc: přesná shoda → noc_{obdobi} → noc → (nouzově) denní obrázek téže kombinace
"""

import shutil
import sys

from common import DOBY_OBRAZKU, IMG_DIR, KATEGORIE, NOC_OBECNA, OBDOBI, VYCHOZI_DEN, jmeno, matice, najdi_raw


def je_original(stem):
    return najdi_raw(stem) is not None and (IMG_DIR / f"{stem}.png").exists()


def retezec(kat, obd, doba):
    if doba == "den":
        kandidati = [jmeno(kat, obd, "den")]
        if kat == "bourka":
            kandidati.append(jmeno("dest", obd, "den"))
        kandidati += [jmeno("zatazeno", obd, "den"), VYCHOZI_DEN]
        return kandidati
    return [jmeno(kat, obd, "noc"), f"noc_{obd}", NOC_OBECNA]


def zdroj_pro(kat, obd, doba):
    """Vrátí (stem zdroje, je_nouzovy)."""
    for kandidat in retezec(kat, obd, doba):
        if je_original(kandidat):
            return kandidat, False
    if doba == "noc":   # první fáze bez nočních obrázků: raději den než rozbitý obrázek
        for kandidat in retezec(kat, obd, "den"):
            if je_original(kandidat):
                return kandidat, True
    return None, False


def main():
    if not IMG_DIR.is_dir():
        sys.exit(f"{IMG_DIR} neexistuje, spusť nejdřív process.py")

    radky, chybi, nouzove = [], [], 0
    for kat in KATEGORIE:
        for obd in OBDOBI:
            for doba in DOBY_OBRAZKU:
                cil = jmeno(kat, obd, doba)
                zdroj, nouzovy = zdroj_pro(kat, obd, doba)
                if zdroj is None:
                    chybi.append(cil)
                    continue
                if zdroj != cil:
                    shutil.copyfile(IMG_DIR / f"{zdroj}.png", IMG_DIR / f"{cil}.png")
                nouzove += nouzovy
                radky.append((cil, "originál" if zdroj == cil else f"kopie ← {zdroj}" + (" (!)" if nouzovy else "")))

    sirka = max(len(c) for c, _ in radky) if radky else 0
    for cil, popis in radky:
        print(f"{cil:<{sirka}}  {popis}")

    originalu = sum(1 for _, popis in radky if popis == "originál")
    print(f"\n{originalu} originálů, {len(radky) - originalu} fallback kopií, {len(chybi)} chybí")
    if nouzove:
        print(f"(!) {nouzove} nočních kombinací používá denní obrázek – chybí noc.png / noc_<obdobi>.png")

    if chybi:
        print(f"\nCHYBA: nelze doplnit {len(chybi)} kombinací, chybí originál {VYCHOZI_DEN}.png "
              f"(raw/{VYCHOZI_DEN}.png → process.py)")
        return 1

    existuje = [j for j in matice() if (IMG_DIR / f"{j}.png").exists()]
    assert len(existuje) == 56, f"existuje jen {len(existuje)} z 56 souborů"
    if not (IMG_DIR / f"{VYCHOZI_DEN}.png").exists():
        print(f"\nCHYBA: chybí {VYCHOZI_DEN}.png – šablona ho zobrazuje při výpadku dat")
        return 1
    print("OK: všech 56 souborů matice existuje")
    return 0


if __name__ == "__main__":
    sys.exit(main())
