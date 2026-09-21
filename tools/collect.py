#!/usr/bin/env python3
"""Hlídá složku se staženými soubory a přejmenovává vygenerované obrázky do raw/.

Pro každou chybějící kombinaci vypíše jméno a prompt (a zkopíruje ho do schránky),
počká na nový .png/.webp ve sledované složce, přesune ho do raw/ pod správným
jménem a pokračuje další kombinací. Lze přerušit (Ctrl+C) a spustit znovu.
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import PRIPONY, RAW_DIR, najdi_raw
from prompts import jmena, prompt

INTERVAL = 1.0          # s mezi kontrolami složky
STABILNI_KONTROL = 3    # kolikrát po sobě musí být velikost stejná


def obrazky(slozka):
    return {f for f in slozka.iterdir() if f.is_file() and f.suffix.lower() in PRIPONY}


def pockej_na_stazeni(soubor):
    """Počká, až se velikost souboru přestane měnit."""
    posledni, stejne = -1, 0
    while stejne < STABILNI_KONTROL:
        time.sleep(INTERVAL)
        if not soubor.exists():     # prohlížeč soubor ještě přejmenovává
            return False
        velikost = soubor.stat().st_size
        stejne = stejne + 1 if velikost == posledni and velikost > 0 else 0
        posledni = velikost
    return True


def do_schranky(text):
    if shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input=text.encode(), check=False)
        return True
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("slozka", nargs="?", type=Path, default=Path.home() / "Downloads")
    p.add_argument("--doba", choices=["den", "noc", "vse"], default="den")
    p.add_argument("--no-clipboard", action="store_true", help="nekopírovat prompt do schránky")
    args = p.parse_args()

    if not args.slozka.is_dir():
        sys.exit(f"složka neexistuje: {args.slozka}")
    RAW_DIR.mkdir(exist_ok=True)

    fronta = [j for j in jmena(args.doba) if najdi_raw(j) is None]
    celkem = len(jmena(args.doba))
    if not fronta:
        print(f"hotovo, v raw/ je všech {celkem} obrázků")
        return

    print(f"sleduji {args.slozka}, zbývá {len(fronta)} z {celkem}; přerušení Ctrl+C\n")
    zname = obrazky(args.slozka)
    try:
        for poradi, jmeno in enumerate(fronta, 1):
            text = prompt(jmeno)
            print(f"===== [{poradi}/{len(fronta)}] {jmeno} =====\n{text}\n")
            if not args.no_clipboard and do_schranky(text):
                print("(prompt je ve schránce)")
            print("čekám na stažený obrázek…")
            while True:
                time.sleep(INTERVAL)
                nove = sorted(obrazky(args.slozka) - zname, key=lambda f: f.stat().st_mtime)
                if nove and pockej_na_stazeni(nove[0]):
                    cil = RAW_DIR / f"{jmeno}{nove[0].suffix.lower()}"
                    shutil.move(str(nove[0]), cil)
                    print(f"uloženo: {cil.name}\n")
                    break
    except KeyboardInterrupt:
        print("\npřerušeno, příště se pokračuje od chybějících")


if __name__ == "__main__":
    main()
