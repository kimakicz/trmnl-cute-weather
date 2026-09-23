#!/usr/bin/env python3
"""Vyrenderuje šablonu přes trmnlp pro každý vzorek ze samples/ a zkontroluje výsledek.

Pro každý vzorek vznikne dočasná kopie pluginu, jejíž polling URL míří na lokální
HTTP server (samples/<vzorek>.json + public/texty.json). Očekávané hodnoty se
počítají nezávisle v Pythonu, takže test hlídá shodu Liquid logiky se zadáním.

Vyžaduje trmnlp (gem trmnl_preview) nebo Docker (image trmnl/trmnlp).
"""

import argparse
import functools
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from common import ROOT, TEXTY

PLUGIN = ROOT / "plugin"
SAMPLES = ROOT / "samples"
# každý běh má vlastní, dosud neexistující podsložku, kterou mountujeme do kontejneru:
# Docker Desktop po smazání a znovuvytvoření stejné cesty občas chvíli vidí starý
# (prázdný) obsah a build pak selže; .test_samples/ samotnou proto nikdy nemažeme
WORK_BASE = ROOT / ".test_samples"
WORK = WORK_BASE / f"run-{os.getpid()}"
NEUTRALNI = "Podívej se z okna, jaké je dnes venku počasí."
DNY_PRED = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

# trmnlp build neumí zvolit zařízení; pro PNG náhled doplníme třídy, které TRMNL X dostává v cloudu
TRIDY_TRMNL_X = """
<script>
  document.querySelector(".screen").classList.add("screen--v2", "screen--lg", "screen--density-2x");
</script>
"""

# vzorky renderované navíc s nedostupným texty.json
BEZ_TEXTU = ["snih_den_zima_minus5"]


class TichyHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def zaokrouhli(x):
    """Jako Ruby/Liquid round: polovina od nuly."""
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def kategorie(kod):
    if kod == 0:
        return "jasno"
    if kod in (1, 2):
        return "polojasno"
    if kod in (45, 48):
        return "mlha"
    if 51 <= kod <= 67 or 80 <= kod <= 82:
        return "dest"
    if 71 <= kod <= 77 or kod in (85, 86):
        return "snih"
    if 95 <= kod <= 99:
        return "bourka"
    return "zatazeno"


def ocekavani(vzorek, texty):
    cur = vzorek.get("current")
    if not cur:
        return {"obrazek": "vychozi_den", "text": NEUTRALNI}

    cas = cur["time"]
    mesic, den, hodina = int(cas[5:7]), int(cas[8:10]), int(cas[11:13])
    den_v_roce = DNY_PRED[mesic - 1] + den

    kat = kategorie(cur["weather_code"])
    obd = {12: "zima", 1: "zima", 2: "zima", 3: "jaro", 4: "jaro", 5: "jaro",
           6: "leto", 7: "leto", 8: "leto"}.get(mesic, "podzim")
    doba = "den" if cur["is_day"] == 1 else "noc"
    if hodina < 5 or hodina >= 21:
        doba_textu = "noc"
    elif hodina < 9:
        doba_textu = "rano"
    elif hodina >= 18 or doba == "noc":
        doba_textu = "vecer"
    else:
        doba_textu = "den"

    t = zaokrouhli(cur["temperature_2m"])
    pasmo = "mraz" if t < 0 else "zima" if t <= 9 else "chladno" if t <= 17 else "teplo" if t <= 25 else "horko"
    teplota = f"mínus {abs(t)}" if t < 0 else str(t)
    stupne = "stupeň" if abs(t) == 1 else "stupně" if 2 <= abs(t) <= 4 else "stupňů"

    rychlost = cur["wind_speed_10m"]
    vitr = "silny" if rychlost > 35 else "stredni" if rychlost >= 15 else "slaby"

    casti = []
    if texty:
        vety = texty["pocasi"][kat][doba_textu]
        casti.append(vety[(den_v_roce * 24 + hodina) % len(vety)])
    else:
        casti.append(NEUTRALNI)
    casti.append(f"Venku je {teplota} {stupne}.")
    if texty:
        vety = texty["obleceni"][pasmo]
        casti.append(vety[(hodina * 3 + den_v_roce * 7 + 5) % len(vety)])
        if vitr != "slaby":
            vety = texty["vitr"][vitr]
            casti.append(vety[(hodina * 7 + den_v_roce * 3 + 11) % len(vety)])

    return {"obrazek": f"{kat}_{obd}_{doba}", "text": " ".join(casti), "kat": kat, "obdobi": obd,
            "doba": doba, "doba-textu": doba_textu, "pasmo": pasmo, "vitr": vitr}


def priprav(pripad, vzorek, host, port, s_texty=True, png=False):
    cil = WORK / pripad
    shutil.copytree(PLUGIN / "src", cil / "src")
    if png:
        with open(cil / "src" / "full.liquid", "a", encoding="utf-8") as f:
            f.write(TRIDY_TRMNL_X)
    base = f"http://{host}:{port}/public"
    (cil / ".trmnlp.yml").write_text(
        f'---\nwatch: false\ntime_zone: Europe/Prague\ncustom_fields:\n  latitude: "48.97"\n'
        f'  longitude: "14.47"\n  base_url: "{base}"\n'
    )
    settings = (cil / "src" / "settings.yml").read_text(encoding="utf-8")
    druha = "{{ base_url }}/texty.json" if s_texty else f"http://{host}:{port}/samples/neexistuje.json"
    settings, n = re.subn(
        r"polling_url: \|-\n(?:  .*\n)+",
        f"polling_url: |-\n  http://{host}:{port}/samples/{vzorek}.json\n  {druha}\n",
        settings,
    )
    assert n == 1, "v settings.yml nenalezen blok polling_url"
    (cil / "src" / "settings.yml").write_text(settings, encoding="utf-8")


def spust_trmnlp(lokalni, extra):
    smycka = ('for d in {koren}/*/; do cd "$d" && {bin} build {extra} > build.log 2>&1 '
              '|| echo "BUILD SELHAL: $d"; done')
    if lokalni:
        prikaz = ["sh", "-c", smycka.format(koren=WORK, bin="trmnlp", extra=extra)]
    else:
        prikaz = ["docker", "run", "--rm", "--entrypoint", "sh", "--volume", f"{WORK}:/work",
                  "trmnl/trmnlp", "-c", smycka.format(koren="/work", bin="/app/bin/trmnlp", extra=extra)]
    vystup = subprocess.run(prikaz, capture_output=True, text=True)
    if vystup.stdout.strip() or vystup.returncode:
        print(vystup.stdout, vystup.stderr, file=sys.stderr)


def precti(pripad):
    soubor = WORK / pripad / "_build" / "full.html"
    if not soubor.exists():
        log = WORK / pripad / "build.log"
        return None, log.read_text() if log.exists() else "chybí _build/full.html"
    stranka = soubor.read_text(encoding="utf-8")
    m = re.search(r'<div class="cw"([^>]*)>', stranka)
    if not m:
        return None, "ve výstupu chybí .cw (chyba Liquidu?): " + re.sub(r"\s+", " ", stranka[-400:])
    atributy = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', m.group(1)))
    src = re.search(r'<img class="cw__img" src="([^"]*)"', stranka).group(1)
    text = re.search(r'<span class="cw__text">(.*?)</span>\s*</div>', stranka, re.S).group(1)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text))).strip()
    return {"atributy": atributy, "src": src, "text": text}, None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", help="jen jeden vzorek (jméno souboru bez .json)")
    p.add_argument("--png", action="store_true",
                   help="vyrenderovat i PNG 1872×1404 jako na TRMNL X do preview-<vzorek>.png (v Dockeru trvá minuty)")
    p.add_argument("--color-depth", type=int, default=4,
                   help="bitová hloubka PNG náhledu (8 = bez kvantizace, pro kontrolu vykreslení 1:1)")
    p.add_argument("--keep", action="store_true", help="nemazat .test_samples/")
    p.add_argument("-v", "--verbose", action="store_true", help="vypsat výsledný text každého vzorku")
    args = p.parse_args()

    lokalni = shutil.which("trmnlp") is not None
    if not lokalni and not shutil.which("docker"):
        sys.exit("chybí trmnlp i docker")
    host = "localhost" if lokalni else "host.docker.internal"

    texty = json.loads(TEXTY.read_text(encoding="utf-8"))
    vzorky = sorted(f.stem for f in SAMPLES.glob("*.json"))
    if args.only:
        vzorky = [v for v in vzorky if v == args.only] or sys.exit(f"neznámý vzorek: {args.only}")

    handler = functools.partial(TichyHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("0.0.0.0", 0), handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    for stary in WORK_BASE.glob("run-*"):
        shutil.rmtree(stary, ignore_errors=True)
    WORK.mkdir(parents=True)
    pripady = []    # (případ, vzorek, s_texty)
    for v in vzorky:
        pripady.append((v, v, True))
        if v in BEZ_TEXTU:
            pripady.append((f"{v}__bez_textu", v, False))
    for pripad, vzorek, s_texty in pripady:
        priprav(pripad, vzorek, host, port, s_texty, args.png)

    print(f"renderuji {len(pripady)} případů přes {'trmnlp' if lokalni else 'Docker (trmnl/trmnlp)'}…")
    spust_trmnlp(lokalni, f"--png --width 1872 --height 1404 --color-depth {args.color_depth}" if args.png else "")

    chyb = 0
    for pripad, vzorek, s_texty in pripady:
        data = json.loads((SAMPLES / f"{vzorek}.json").read_text(encoding="utf-8"))
        ocek = ocekavani(data, texty if s_texty else None)
        vysledek, chyba = precti(pripad)
        problemy = [chyba] if chyba else []
        if vysledek:
            if vysledek["atributy"].get("obrazek") != ocek["obrazek"]:
                problemy.append(f"obrázek {vysledek['atributy'].get('obrazek')} ≠ {ocek['obrazek']}")
            if not vysledek["src"].endswith(f"/public/img/{ocek['obrazek']}.png"):
                problemy.append(f"src obrázku: {vysledek['src']}")
            if not (ROOT / "public" / "img" / f"{ocek['obrazek']}.png").exists():
                problemy.append(f"public/img/{ocek['obrazek']}.png neexistuje (spusť build_matrix.py)")
            for klic in ("kat", "obdobi", "doba", "doba-textu", "pasmo", "vitr"):
                if klic in ocek and vysledek["atributy"].get(klic) != ocek[klic]:
                    problemy.append(f"{klic}: {vysledek['atributy'].get(klic)} ≠ {ocek[klic]}")
            if vysledek["text"] != ocek["text"]:
                problemy.append(f"text:\n      je:     {vysledek['text']}\n      má být: {ocek['text']}")
        chyb += bool(problemy)
        print(f"{'CHYBA' if problemy else 'ok   '} {pripad:<40} {ocek['obrazek']}")
        if args.verbose and vysledek:
            print(f"      {vysledek['text']}")
        for pr in problemy:
            print(f"    - {pr}")
        if args.png and (WORK / pripad / "_build" / "full.png").exists():
            shutil.copyfile(WORK / pripad / "_build" / "full.png", ROOT / f"preview-{pripad}.png")

    server.shutdown()
    if not args.keep:
        shutil.rmtree(WORK, ignore_errors=True)
    print(f"\n{len(pripady) - chyb}/{len(pripady)} v pořádku")
    return 1 if chyb else 0


if __name__ == "__main__":
    sys.exit(main())
