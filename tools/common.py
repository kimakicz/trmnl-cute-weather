"""Sdílené konstanty a cesty pro nástroje cute-weather."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
IMG_DIR = ROOT / "public" / "img"
TEXTY = ROOT / "public" / "texty.json"

KATEGORIE = ["jasno", "polojasno", "zatazeno", "dest", "bourka", "snih", "mlha"]
OBDOBI = ["jaro", "leto", "podzim", "zima"]
DOBY_OBRAZKU = ["den", "noc"]

# kombinace, které se negenerují (doplní je fallback v build_matrix.py)
NEREALNE = {("snih", "leto"), ("bourka", "zima")}

VYCHOZI_DEN = "vychozi_den"
NOC_OBECNA = "noc"

PRIPONY = (".png", ".webp")


def jmeno(kategorie, obdobi, doba):
    return f"{kategorie}_{obdobi}_{doba}"


def matice():
    """Všech 56 jmen, která šablona může poskládat."""
    return [jmeno(k, o, d) for k in KATEGORIE for o in OBDOBI for d in DOBY_OBRAZKU]


def generovane(doba="den"):
    """Jména, která se skutečně generují (bez nereálných kombinací)."""
    doby = DOBY_OBRAZKU if doba == "vse" else [doba]
    return [
        jmeno(k, o, d)
        for d in doby
        for k in KATEGORIE
        for o in OBDOBI
        if (k, o) not in NEREALNE
    ]


def specialni(doba="den"):
    """Fallback obrázky mimo matici."""
    nocni = [f"noc_{o}" for o in OBDOBI] + [NOC_OBECNA]
    if doba == "den":
        return [VYCHOZI_DEN]
    if doba == "noc":
        return nocni
    return [VYCHOZI_DEN] + nocni


def najdi_raw(stem):
    """Vrátí cestu ke staženému obrázku v raw/ (png nebo webp), nebo None."""
    for pripona in PRIPONY:
        cesta = RAW_DIR / f"{stem}{pripona}"
        if cesta.exists():
            return cesta
    return None
