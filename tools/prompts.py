#!/usr/bin/env python3
"""Vypíše prompty pro generování obrázků (ChatGPT + dvě reference).

Ke každému promptu přilož refs/holcicka-vzor.png (referenční list postavičky)
a refs/leto-vzor.png (základní krajina).
"""

import argparse
import sys

from common import NOC_OBECNA, OBDOBI, VYCHOZI_DEN, generovane, najdi_raw, specialni

UVOD = """Children's picture book illustration, hand-drawn ink and grayscale
wash, {MOOD}. Same scene and composition as the reference landscape:
a South Bohemian pond with a curved stone dam running across the
lower half, a big oak tree framing the left side ({OAK}), rolling
hills behind, a small village with a church tower in the distance
on the right."""

POSTAVA = """Character (identical to the character reference): the little girl
about six years old with the short dark bob and her small white dog
with dark patches. Place her in the FOREGROUND slightly left of
center on the stone dam, seen from behind and slightly to the side,
taking up about one fifth of the total image height."""

PROMENNY = """{SEASON_NAME}, {WEATHER}, {DAYPART}. She wears {CLOTHING}. {ACTION}
{SEASON_SCENE} {WEATHER_SCENE}"""

STYL = """Style: bold black ink outlines, flat tonal areas, no gradients,
strong separation of light and dark between sky, hills and water.
Keep the girl and the dog clearly readable against the background.
Grayscale only, no color."""

SPODNI_TRETINA = """Keep the LOWER THIRD of the image calm and simple — open water or
plain ground and dam stones only, no reeds, no animals, no detail there."""

KOMPOZICE = """Composition: the image will later be cropped to a 4:3 aspect ratio
by removing about six percent from the left and right edges. Keep
all important elements — the girl, the dog, the church tower — well
inside the central area, at least ten percent away from the left and
right edges. Only background scenery may touch the sides.

No text, no signature, no frame. Landscape orientation, wide format."""

REFERENCNI_LIST = """Character reference sheet for a children's picture book, hand-drawn
ink and grayscale wash. Top row: three views of the same little girl,
about six years old, short dark bob haircut, simple light summer dress:
front view, three-quarter view from behind, side profile. Bottom row:
three views of her small white dog with dark patches: front view,
three-quarter view from behind, side profile. Neutral standing poses,
consistent proportions across all views, plain empty light background,
no scenery, no shadows on the ground.

Style: bold black ink outlines, flat tonal areas, no gradients.
Grayscale only, no color. No text, no labels, no signature, no frame.
Landscape orientation."""

ZAKLADNI_KRAJINA = """Children's picture book illustration, hand-drawn ink and grayscale
wash, calm sunny summer day. A South Bohemian pond with a curved stone
dam running across the lower half, a big oak tree with a full lush
canopy framing the left side, rolling hills behind, a small village
with a church tower in the distance on the right. No people, no animals.

""" + STYL.replace("Keep the girl and the dog clearly readable against the background.\n", "") + "\n\n" \
    + SPODNI_TRETINA + "\n\n" + KOMPOZICE

OBDOBI_DATA = {
    "jaro": {
        "name": "Spring",
        "oak": "young fresh leaves",
        "scene": "Blossoming trees, fresh grass, the oak with young light leaves.",
        "top": "a light jacket over a long-sleeved shirt and leggings",
        "boty": "sneakers",
    },
    "leto": {
        "name": "Summer",
        "oak": "full lush canopy",
        "scene": "Lush greenery everywhere, the oak in full leaf.",
        "top": "a light sleeveless summer dress",
        "boty": "bare feet",
    },
    "podzim": {
        "name": "Autumn",
        "oak": "half bare, leaves falling",
        "scene": "Falling leaves drifting in the air, the oak half bare, leaves scattered on the dam.",
        "top": "a warm knitted sweater and corduroy trousers",
        "boty": "ankle boots",
    },
    "zima": {
        "name": "Winter",
        "oak": "bare branches",
        "scene": "Bare oak, grey grass or snow on the ground, the pond frozen or icy.",
        "top": "a padded winter jacket and warm trousers",
        "boty": "winter boots",
    },
}

SEDI_NA_SLUNCI = ("She sits on the dam in the sun with her face turned up to the light; "
                  "the dog lies on its back beside her.")

KATEGORIE_DATA = {
    "jasno": {
        "mood": "bright, cheerful sunny mood",
        "weather": "clear sunny sky without a single cloud",
        "weather_night": "clear night sky full of stars with a bright moon",
        "scene": "A big simple sun high in the sky, crisp short shadows.",
        "scene_night": "Moonlight reflecting on the water, soft moon shadows.",
        "doplnky": {
            "leto": "a straw hat with a ribbon and sunglasses",
            "zima": "a knitted hat and sunglasses",
            "*": "sunglasses",
        },
        "action": {
            "leto": ("She sits on the dam dangling her bare feet above the water; "
                     "the dog lies on its back beside her."),
            "*": SEDI_NA_SLUNCI,
        },
    },
    "polojasno": {
        "mood": "light, breezy mood",
        "weather": "partly cloudy sky with a few big puffy clouds and the sun peeking out",
        "weather_night": "night sky with a few clouds drifting across the moon",
        "scene": "Cloud shadows drifting over the hills.",
        "scene_night": "The moon half hidden behind a cloud.",
        "doplnky": {
            "jaro": "a thin hoodie tied around her waist",
            "leto": "a thin hoodie tied around her waist",
            "*": "",
        },
        "action": {"*": "She points up at a cloud; the dog looks in the same direction."},
    },
    "zatazeno": {
        "mood": "quiet, soft overcast mood",
        "weather": "fully overcast sky, an even blanket of clouds, no sun",
        "weather_night": "overcast night, dark even sky without stars",
        "scene": "Soft even light, no cast shadows.",
        "scene_night": "Only the village windows glow in the dark.",
        "doplnky": {
            "zima": "a hoodie under the jacket with the hood sticking out",
            "*": "a hoodie with the hood down",
        },
        "action": {"*": "She sits with her chin in her hands; the dog rests its head on her knee."},
    },
    "dest": {
        "mood": "cosy rainy mood",
        "weather": "steady rain",
        "weather_night": "steady rain at night",
        "scene": {
            "zima": "Streaks of cold rain, wet shiny ice on the pond, puddles on the dam stones.",
            "*": "Streaks of rain, rippled water, puddles on the dam stones.",
        },
        "scene_night": "Rain streaks catching the light from the village windows.",
        "doplnky": {"*": "a raincoat and an umbrella"},
        "boty": "yellow rubber boots (light-toned in grayscale)",
        "action": {"*": ("She jumps into a puddle holding the umbrella out to the side; "
                         "the dog crouches under the umbrella.")},
    },
    "bourka": {
        "mood": "dramatic but safe and cosy mood, not scary",
        "weather": "thunderstorm with heavy rain",
        "weather_night": "thunderstorm at night with heavy rain",
        "scene": "Dark towering clouds, one distant lightning bolt far over the hills, wind-blown rain.",
        "scene_night": "One distant lightning bolt briefly lighting the clouds far over the hills.",
        "doplnky": {"*": "a raincoat with the hood up"},
        "boty": "rubber boots",
        "action": {"*": "She shelters under the oak tree, hugging the dog around its neck."},
    },
    "snih": {
        "mood": "quiet, joyful snowy mood",
        "weather": "gentle snowfall",
        "weather_night": "gentle snowfall at night",
        "scene": "Big soft snowflakes, snow covering the dam, the hills and the village roofs.",
        "scene_night": "Snow glowing softly in the dark, snowflakes lit by the village windows.",
        "doplnky": {"*": "a knitted hat with a pom-pom, a scarf and mittens"},
        "top": "a padded winter jacket and warm trousers",
        "boty": "winter boots",
        "action": {"*": "She builds a small snowman on the dam; the dog tries to catch snowflakes."},
    },
    "mlha": {
        "mood": "quiet, mysterious but friendly foggy mood",
        "weather": "thick fog",
        "weather_night": "thick fog at night",
        "scene": ("The hills and the village fade into pale mist, only the oak, the dam "
                  "and the girl stay dark and clear."),
        "scene_night": "The flashlight beam makes a soft cone of light in the fog.",
        "doplnky": {
            "leto": "a light jacket and a thin scarf, holding a flashlight",
            "*": "a jacket and a scarf, holding a flashlight",
        },
        "action": {"*": "She leans forward squinting into the fog; the dog sniffs the ground."},
    },
}

DAYPART = {
    "den": "daytime",
    "noc": "night time, dark sky, the scene still clearly readable, warm lit windows in the village",
}


def _podle_obdobi(tabulka, obdobi):
    if isinstance(tabulka, str):
        return tabulka
    return tabulka.get(obdobi, tabulka["*"])


def _sloz(kat, obd, doba):
    o, k = OBDOBI_DATA[obd], KATEGORIE_DATA[kat]
    obleceni = [k.get("top", o["top"]), k.get("boty", o["boty"])]
    doplnky = _podle_obdobi(k["doplnky"], obd)
    if doplnky:
        obleceni.append(doplnky)
    noc = doba == "noc"
    promenny = PROMENNY.format(
        SEASON_NAME=o["name"],
        WEATHER=k["weather_night"] if noc else k["weather"],
        DAYPART=DAYPART[doba],
        CLOTHING=", ".join(obleceni),
        ACTION=_podle_obdobi(k["action"], obd),
        SEASON_SCENE=o["scene"],
        WEATHER_SCENE=k["scene_night"] if noc else _podle_obdobi(k["scene"], obd),
    )
    mood = k["mood"] + (", calm night-time atmosphere" if noc else "")
    uvod = UVOD.format(MOOD=mood, OAK=o["oak"])
    return "\n\n".join([uvod, POSTAVA, promenny, STYL, SPODNI_TRETINA, KOMPOZICE])


def prompt(jmeno):
    """Prompt pro jméno souboru bez přípony (např. dest_podzim_den)."""
    if jmeno == VYCHOZI_DEN:
        # neutrální obrázek pro případ chybějících dat: mírné počasí, pozdní jaro
        return _sloz("polojasno", "jaro", "den")
    if jmeno == NOC_OBECNA:
        return _sloz("polojasno", "jaro", "noc")
    if jmeno.startswith("noc_") and jmeno[4:] in OBDOBI:
        return _sloz("polojasno", jmeno[4:], "noc")
    kat, obd, doba = jmeno.split("_")
    return _sloz(kat, obd, doba)


def jmena(doba="den"):
    return specialni(doba) + generovane(doba)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--doba", choices=["den", "noc", "vse"], default="den",
                   help="první fáze je jen den (26 obrázků + vychozi_den)")
    p.add_argument("--missing", action="store_true", help="jen kombinace, které ještě nejsou v raw/")
    p.add_argument("--name", help="jen jeden prompt, např. dest_podzim_den")
    p.add_argument("--list", action="store_true", help="vypsat jen jména")
    p.add_argument("--reference", action="store_true", help="prompt na referenční list postavičky")
    p.add_argument("--landscape", action="store_true", help="prompt na základní krajinu")
    args = p.parse_args()

    if args.reference:
        print(REFERENCNI_LIST)
        return
    if args.landscape:
        print(ZAKLADNI_KRAJINA)
        return

    seznam = [args.name] if args.name else jmena(args.doba)
    if args.missing:
        seznam = [j for j in seznam if najdi_raw(j) is None]
    for j in seznam:
        if args.list:
            print(j)
            continue
        try:
            text = prompt(j)
        except (KeyError, ValueError):
            sys.exit(f"neznámé jméno: {j}")
        print(f"===== {j}.png =====\n{text}\n")
    if not args.list:
        print(f"celkem: {len(seznam)}", file=sys.stderr)


if __name__ == "__main__":
    main()
