#!/usr/bin/env python3
"""Kontrola souboru texty.json: struktura, počty, délka vět, duplicity."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

KATEGORIE = ["jasno", "polojasno", "zatazeno", "dest", "bourka", "snih", "mlha"]
DOBY = ["rano", "den", "vecer", "noc"]
PASMA = ["mraz", "zima", "chladno", "teplo", "horko"]
SILY = ["slaby", "stredni", "silny"]

POCET_VET = 20
MAX_SLOV = 12
MAX_STEJNY_ZACATEK = 3

ZAKAZANE = re.compile(r"\d|°|\bstup(eň|ně|ňů|ních)\b", re.IGNORECASE)


def normalizuj(veta):
    """Věta bez interpunkce a velikosti písmen – pro hledání duplicit."""
    return " ".join(re.findall(r"\w+", veta.lower()))


def prvni_slovo(veta):
    slova = re.findall(r"\w+", veta.lower())
    return slova[0] if slova else ""


def zkontroluj_klice(nazev, slovnik, ocekavane, chyby):
    if not isinstance(slovnik, dict):
        chyby.append(f"{nazev}: očekáván objekt, nalezen {type(slovnik).__name__}")
        return False
    chybi = [k for k in ocekavane if k not in slovnik]
    navic = [k for k in slovnik if k not in ocekavane]
    if chybi:
        chyby.append(f"{nazev}: chybí klíče {chybi}")
    if navic:
        chyby.append(f"{nazev}: neznámé klíče {navic}")
    return True


def zkontroluj_skupinu(nazev, vety, chyby, vsechny):
    if not isinstance(vety, list):
        chyby.append(f"{nazev}: očekáván seznam vět")
        return
    if len(vety) != POCET_VET:
        chyby.append(f"{nazev}: {len(vety)} vět místo {POCET_VET}")

    zacatky = Counter()
    for i, veta in enumerate(vety, 1):
        kde = f"{nazev}[{i}]"
        if not isinstance(veta, str) or not veta.strip():
            chyby.append(f"{kde}: prázdná nebo neplatná věta")
            continue
        if veta != veta.strip() or "  " in veta:
            chyby.append(f"{kde}: nadbytečné mezery: {veta!r}")
        pocet_slov = len(veta.split())
        if pocet_slov > MAX_SLOV:
            chyby.append(f"{kde}: {pocet_slov} slov (max {MAX_SLOV}): {veta}")
        if ZAKAZANE.search(veta):
            chyby.append(f"{kde}: číslo nebo teplota v textu: {veta}")
        if not veta[0].isupper():
            chyby.append(f"{kde}: nezačíná velkým písmenem: {veta}")
        if veta[-1] not in ".!?":
            chyby.append(f"{kde}: chybí koncová interpunkce: {veta}")
        zacatky[prvni_slovo(veta)] += 1
        vsechny.setdefault(normalizuj(veta), []).append(kde)

    for slovo, pocet in zacatky.items():
        if pocet > MAX_STEJNY_ZACATEK:
            chyby.append(
                f"{nazev}: {pocet} vět začíná slovem „{slovo}“ (max {MAX_STEJNY_ZACATEK})"
            )


def main():
    cesta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("texty.json")
    try:
        data = json.loads(cesta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"CHYBA: {cesta} nelze načíst: {e}")
        return 1

    chyby = []
    vsechny = {}  # normalizovaná věta -> seznam výskytů (duplicity napříč celým souborem)

    if zkontroluj_klice("kořen", data, ["pocasi", "obleceni", "vitr"], chyby):
        pocasi = data.get("pocasi", {})
        if zkontroluj_klice("pocasi", pocasi, KATEGORIE, chyby):
            for kat in KATEGORIE:
                doby = pocasi.get(kat)
                if doby is None:
                    continue
                if zkontroluj_klice(f"pocasi.{kat}", doby, DOBY, chyby):
                    for doba in DOBY:
                        if doba in doby:
                            zkontroluj_skupinu(f"pocasi.{kat}.{doba}", doby[doba], chyby, vsechny)

        for sekce, klice in (("obleceni", PASMA), ("vitr", SILY)):
            obsah = data.get(sekce, {})
            if zkontroluj_klice(sekce, obsah, klice, chyby):
                for klic in klice:
                    if klic in obsah:
                        zkontroluj_skupinu(f"{sekce}.{klic}", obsah[klic], chyby, vsechny)

    for veta, vyskyty in vsechny.items():
        if len(vyskyty) > 1:
            chyby.append(f"duplicita: „{veta}“ v {', '.join(vyskyty)}")

    pocet = sum(len(v) for v in vsechny.values())
    if chyby:
        print(f"NALEZENO {len(chyby)} CHYB ({pocet} vět):")
        for ch in chyby:
            print(f"  - {ch}")
        return 1

    print(f"OK: {pocet} vět, {len(vsechny)} unikátních, struktura i pravidla v pořádku.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
