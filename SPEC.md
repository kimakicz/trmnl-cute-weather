# cute-weather — zadání pro Claude Code

Postav kompletní TRMNL plugin **cute-weather**: displej v dětském pokoji ukazuje ilustraci krajiny, kde holčička se psem je oblečená a chová se podle aktuálního počasí, a pod ní krátký český text o počasí pro děti 4–8 let.

Než začneš psát kód, přečti si toto zadání celé, prostuduj aktuální dokumentaci TRMNL Private Plugins a nástroje `trmnlp` (gem `trmnl_preview`) a pokud je něco nejasné nebo v rozporu s dokumentací, zeptej se mě. Nic si nedomýšlej potichu.

## Cílové zařízení

- TRMNL X, e-ink 1872×1404 px, 16 odstínů šedi. Framework s ním pracuje jako s plochou 1040×780 CSS px zvětšenou poměrem 1,8 (`--pixel-ratio`); rozměry uvedené v tomto zadání jsou fyzické px a v CSS se dělí `--pixel-ratio`. Limit velikosti výsledného snímku je 750 kB (`image_size_limit` z `trmnl.com/api/models`).
- Plugin běží v oficiálním cloudu TRMNL jako Private Plugin se strategií **Polling**. Žádný vlastní server ani cron. Veškerá logika výběru je v Liquid šabloně.
- Obrázky a `texty.json` se hostují jako statické soubory na veřejné (neindexované) URL, kterou zadá uživatel.

## Struktura repozitáře

```
cute-weather/
  README.md
  LICENSE                  # MIT
  .gitignore               # public/img/, raw/, *.png mimo refs/
  plugin/                  # TRMNL plugin = kořen trmnlp projektu
    .trmnlp.yml            # lokální náhled: custom_fields, time_zone
    bin/trmnlp             # spouští gem nebo Docker image trmnl/trmnlp
    src/settings.yml       # strategy, polling URL, form fields, refresh
    src/shared.liquid      # klasifikace a výběr vět (trmnlp ho vkládá před každý layout)
    src/full.liquid        # layout
    src/half_*.liquid, quadrant.liquid   # jen hláška „potřebuje celou obrazovku"
  public/                  # obsah pro statický hosting
    texty.json
    img/                   # generované obrázky, NEcommitovat
  refs/                    # reference k promptům (postavička, základní krajina) – commitují se
  raw/                     # stažené vygenerované obrázky, NEcommitovat
  tools/
    common.py              # sdílené konstanty (kategorie, období, cesty)
    prompts.py             # vypíše prompty pro všechny kombinace
    collect.py             # hlídá Downloads a přejmenovává stažené obrázky
    process.py             # ořez 4:3, resize, šeď, dithering
    build_matrix.py        # doplní chybějící kombinace podle fallbacku
    validate_texts.py      # kontrola texty.json
    test_samples.py        # render všech vzorků přes trmnlp a kontrola výsledku
  samples/                 # ukázkové odpovědi Open-Meteo pro testy
```

## 1. Data o počasí

Open-Meteo, bez klíče:

```
https://api.open-meteo.com/v1/forecast?latitude={{ latitude }}&longitude={{ longitude }}&current=temperature_2m,weather_code,wind_speed_10m,is_day&timezone=Europe/Prague
```

Polling URLs (dva řádky, v tomto pořadí):
1. Open-Meteo → `IDX_0`
2. `{{ base_url }}/texty.json` → `IDX_1`

Form fields pluginu: `latitude` (výchozí 48.97), `longitude` (výchozí 14.47), `base_url` (bez koncového lomítka). Ověřeno v dokumentaci: form fields se do polling URL interpolují jako `{{ keyname }}`, více URL se odděluje koncem řádku (v `settings.yml` víceřádkový řetězec) a v šabloně jsou hodnoty polí pod `trmnl.plugin_settings.custom_fields_values`. Typy polí: `number` se `step: 0.01` a `url`.

Datum, měsíc a hodinu ber z `IDX_0.current.time` (je v lokálním čase díky parametru timezone), ne z `'now'`, protože renderer TRMNL může běžet v UTC.

## 2. Klasifikace

**Kategorie** z WMO `weather_code`:

| kód | kategorie |
|---|---|
| 0 | jasno |
| 1, 2 | polojasno |
| 3 | zatazeno |
| 45, 48 | mlha |
| 51–67, 80–82 | dest |
| 71–77, 85, 86 | snih |
| 95–99 | bourka |
| jiné | zatazeno |

**Doba (obrázek):** `is_day == 1` → `den`, jinak `noc`.

**Doba (text):** `is_day == 0` → `noc`; jinak hodina < 9 → `rano`, hodina ≥ 18 → `vecer`, jinak `den`.

**Období** (meteorologicky podle měsíce): 12–2 `zima`, 3–5 `jaro`, 6–8 `leto`, 9–11 `podzim`.

**Teplotní pásmo:** `mraz` < 0, `zima` 0–9, `chladno` 10–17, `teplo` 18–25, `horko` > 25 (°C, podle zaokrouhlené teploty).

**Vítr** (km/h): `slaby` < 15, `stredni` 15–35, `silny` > 35.

## 3. Obrázky

Pojmenování: `{kategorie}_{obdobi}_{doba}.png`, např. `dest_podzim_den.png`. Plná matice je 7 × 4 × 2 = 56 jmen.

Liquid neumí zjistit, jestli soubor existuje. Proto `build_matrix.py` po zpracování **vytvoří všech 56 souborů** tak, že chybějící kombinace doplní kopií podle fallbacku:

- den: přesná shoda → (`bourka` → `dest` stejné období a doby) → `zatazeno` stejné období → `vychozi_den.png`
- noc: přesná shoda → `noc_{obdobi}.png` → `noc.png` → nouzově denní obrázek téže kombinace (dokud noční obrázky neexistují; skript na to upozorní)

Skript vypíše tabulku, které soubory jsou originály a které fallback kopie. Šablona pak jen skládá jméno souboru a nic neověřuje.

Nereálné kombinace, které se negenerují: `snih_leto`, `bourka_zima`. První fáze generuje jen den, tedy 26 obrázků. Noc je volitelná pozdější fáze.

### 3a. prompts.py

Vypíše prompt pro každou kombinaci (volitelně jen pro chybějící). Prompt se skládá z pevných bloků a proměnných částí. Obrázky se generují ručně v ChatGPT se dvěma přiloženými referencemi: referenčním listem postavičky a základním obrázkem krajiny.

Prompt sestav z těchto bloků (anglicky, doslovně, jen doplň proměnné):

**Úvod a scéna (pevný):**
```
Children's picture book illustration, hand-drawn ink and grayscale
wash, {MOOD}. Same scene and composition as the reference landscape:
a South Bohemian pond with a curved stone dam running across the
lower half, a big oak tree framing the left side ({OAK}), rolling
hills behind, a small village with a church tower in the distance
on the right.
```

**Postava (pevný):**
```
Character (identical to the character reference): the little girl
about six years old with the short dark bob and her small white dog
with dark patches. Place her in the FOREGROUND slightly left of
center on the stone dam, seen from behind and slightly to the side,
taking up about one fifth of the total image height.
```

**Počasí, oblečení, akce (proměnný):**
```
{SEASON_NAME}, {WEATHER}, {DAYPART}. She wears {CLOTHING}. {ACTION}
{SEASON_SCENE} {WEATHER_SCENE}
```

**Styl (pevný):**
```
Style: bold black ink outlines, flat tonal areas, no gradients,
strong separation of light and dark between sky, hills and water.
Keep the girl and the dog clearly readable against the background.
Grayscale only, no color.
```

**Spodní třetina (pevný):**
```
Keep the LOWER THIRD of the image calm and simple — open water or
plain ground and dam stones only, no reeds, no animals, no detail there.
```

**Kompozice 4:3 (pevný):**
```
Composition: the image will later be cropped to a 4:3 aspect ratio
by removing about six percent from the left and right edges. Keep
all important elements — the girl, the dog, the church tower — well
inside the central area, at least ten percent away from the left and
right edges. Only background scenery may touch the sides.

No text, no signature, no frame. Landscape orientation, wide format.
```

**Oblečení** se řídí hlavně obdobím (teplota), doplňky a akce kategorií. Výchozí tabulka, kterou rozviň do všech 26 kombinací tak, aby to dávalo smysl (např. `jasno_zima` = zimní bunda a sluneční den):

| kategorie | doplňky | akce holčičky a psa |
|---|---|---|
| jasno | slaměný klobouk (léto), sluneční brýle | nohy nad vodou / sedí na slunci, pes leží na zádech |
| polojasno | tenká mikina kolem pasu (teplo) | ukazuje na mrak, pes se dívá stejným směrem |
| zatazeno | mikina s kapucí | sedí s bradou v dlaních, pes jí opírá hlavu o koleno |
| dest | žluté holínky, pláštěnka, deštník | skáče do louže, pes se krčí pod deštníkem |
| bourka | pláštěnka s kapucí | schovaná pod stromem, objímá psa kolem krku |
| snih | čepice s bambulí, šála, rukavice | staví malého sněhuláka, pes chytá vločky |
| mlha | bunda a šála, baterka | naklání se dopředu a mhouří oči, pes čichá k zemi |

**Období ve scéně:** jaro — kvetoucí stromy, svěží tráva, dub s mladými listy; léto — bujná zeleň, plný dub; podzim — padající listí, dub napůl holý; zima — holý dub, šedá tráva nebo sníh, zamrzlý nebo ledový rybník.

Ke skriptu přidej samostatný prompt na **referenční list postavičky** (tři pohledy na holčičku: zepředu, ze tří čtvrtin zezadu, z profilu; tři pohledy na psa; prázdné světlé pozadí; stejný styl).

### 3b. collect.py

- Sleduje `~/Downloads` (cesta nastavitelná argumentem), bere `.png` a `.webp`.
- Vede frontu kombinací, pro které ještě neexistuje soubor v `raw/`.
- Vypíše aktuální jméno a prompt (z `prompts.py`), počká na nový soubor, počká na dokončení stahování (stabilní velikost), přesune ho do `raw/` pod správným jménem a ukáže další prompt.
- Lze přerušit a znovu spustit, pokračuje tam, kde skončil.
- Bez externích závislostí, jen polling složky.

### 3c. process.py

Z `raw/` do `public/img/`:
1. převod do šedi,
2. centrovaný ořez na 4:3 a resize na 1872×1404 v jednom kroku (`ImageOps.fit`, LANCZOS; z 1536×1024 odebere zhruba 86 px z každé strany, ořízne správně i obrázek vyšší než 4:3),
3. autokontrast (`ImageOps.autocontrast`, `cutoff=0.5`, přepínač `--no-autocontrast`), aby obrázek využil celý rozsah černá–bílá,
4. jemné doostření po zvětšení (`UnsharpMask(radius=1.5, percent=60, threshold=2)`, přepínač `--no-sharpen`),
5. volitelná korekce středních tónů `--gamma` (výchozí `1.0` = beze změny; hodnoty 0.8–0.9 zesvětlí, pokud bude obrázek na panelu působit ztmavle — doladit až podle skutečného displeje),
6. kvantizace do **pevné palety 16 rovnoměrných úrovní šedi** displeje (0, 17, 34 … 255), dithering volitelný přepínačem (`--dither none|fs|bayer`, výchozí `fs`),
7. uložení jako 8bit PNG v režimu `L` s `optimize=True`,
8. volitelně `--preview`: vygeneruje kontaktní arch všech obrázků pro kontrolu.

Poznámky ke kvantizaci (ověřeno na vzorech `leto-vzor.png` a `zima-vzor.png`):

- **Nepoužívat `im.quantize(colors=16, dither=…)` bez palety.** Pillow parametr `dither` respektuje jen tehdy, když dostane i `palette=`; bez ní proběhne median cut bez ditheringu a výstup je posterizovaný (flekatá obloha, ostrý kruh kolem slunce).
- Adaptivní paleta navíc vybere 16 odstínů podle obrázku (u zimní scény např. 30, 67, 102 … 243, 248 — většina ve světlých tónech). Displej si je znovu převede na své rovnoměrné úrovně a jemné rozdíly splynou. Proto vždy pevná paleta.
- Správný postup pro `fs`: paletový obrázek se 16 šedými (zbylých 240 slotů vyplnit bílou), pak `im.convert("RGB").quantize(palette=pal, dither=Image.FLOYDSTEINBERG)` a zpět `convert("L")`.
- `none`: zaokrouhlení na nejbližší úroveň (`round(v / 17) * 17`), `bayer`: uspořádaný dithering maticí 8×8 s amplitudou jednoho kroku (17) před zaokrouhlením.
- Výstup musí obsahovat jen hodnoty z množiny {0, 17, … 255}; `process.py` to po uložení ověří.

`process.py` zpracovává dávkově `raw/` → `public/img/` a u každého obrázku vypíše odhad velikosti výsledného 4bit snímku (limit TRMNL X je 750 kB; FS dithering vychází na cca 660–700 kB, `bayer` a `none` méně).

Ověřeno renderem přes `trmnlp` v rozlišení 1872×1404: obrázek se v šabloně vykreslí přesně 1:1 (100% shoda pixelů se zdrojem), dithering se tedy cestou nerozmaže.

Pillow, nic dalšího.

## 4. Texty

Vygeneruj `public/texty.json` **ty sám** (Claude Code) s touto strukturou:

```json
{
  "pocasi":   { "<kategorie>": { "rano": [20 vět], "den": [20 vět], "vecer": [20 vět], "noc": [20 vět] } },
  "obleceni": { "<pasmo>": [20 vět] },
  "vitr":     { "stredni": [20 vět], "silny": [20 vět] }
}
```

Pravidla pro věty:
- děti 4–8 let, spisovná čeština bez chyb, max 12 slov na větu,
- přirovnání z dětského světa (hračky, zvířátka, jídlo),
- bouřka a silný vítr uklidňujícím tónem, nestrašit,
- noc: klidné, uspávací věty,
- žádná čísla ani teploty v textu,
- ve skupině se věty nesmí opakovat a nesmí víc než 3× začínat stejným slovem,
- věty o oblečení nesmí odporovat počasí (v `horko` nezmiňovat bundu apod.) a nesmí záviset na slunci ani posílat dítě ven – kombinují se s libovolným počasím včetně bouřky a noci,
- věty o počasí netvrdí nic o teplotě ani ročním období (teplotu řeší jen `obleceni`).

`validate_texts.py` zkontroluje strukturu, počty, délky, duplicity (napříč celým souborem), začáteční slova, čísla v textu a rozpor oblečení s pásmem. Po vygenerování si texty ještě jednou přečti a oprav gramatiku a nepřirozená přirovnání.

## 5. Liquid šablona

Výsledný text: `{věta počasí} Venku je {teplota} {stupeň/stupně/stupňů}. {věta oblečení}` a pokud je vítr `stredni` nebo `silny`, přidej ještě větu o větru.

- Skloňování: absolutní hodnota 1 → stupeň, 2–4 → stupně, jinak stupňů. Záporné teploty „mínus 3 stupně".
- Výběr věty: počasí index = (den v roce × 24 + hodina) mod n; oblečení (hodina × 3 + den × 7 + 5) mod n; vítr (hodina × 7 + den × 3 + 11) mod n. Různé násobky místo pouhého posunu, aby se nepárovaly stále stejné indexy. V rámci jedné hodiny musí být text stabilní. Den v roce se počítá z `current.time` ručně (bez filtru `date`, který může přepočítávat časovou zónu).
- Obrázek: `{{ base_url }}/img/{{ kat }}_{{ obd }}_{{ doba }}.png` přes celou plochu (`object-fit: cover`).
- Textový box dole: bílé pozadí, černý rámeček 3 px, odsazení 40 px od krajů, teplota tučně a větší, text min. 40 px (fyzické px, viz Cílové zařízení), dobře čitelné bezpatkové písmo. Obálku `screen` a `view view--full` doplňuje platforma, markup začíná až `layout`; okraje vypíná `no_screen_padding: 'yes'`.
- Pokud `IDX_0` chybí nebo je chybné, zobraz `vychozi_den.png` a neutrální větu. Pokud chybí jen `IDX_1`, zůstane správný obrázek a teplota a místo věty o počasí je neutrální věta. Nikdy prázdná obrazovka ani chyba Liquidu.
- Zatím jen layout `full`, mashup layouty ne.

## 6. Testy

- Do `samples/` dej ukázkové odpovědi Open-Meteo pro každou kategorii, den i noc, několik teplot (−5, 3, 12, 22, 30 °C) a silný vítr.
- Ověř přes `trmnlp`, že šablona pro každý vzorek vyrenderuje správné jméno obrázku a smysluplný text se správným skloňováním. `trmnlp` neumí podstrčit lokální JSON, proto `tools/test_samples.py` pro každý vzorek vytvoří dočasnou kopii pluginu s polling URL na lokální HTTP server, spustí `trmnlp build` (lokálně nebo v Dockeru) a výsledek porovná s nezávislým výpočtem v Pythonu.
- `build_matrix.py` musí po běhu garantovat existenci všech 56 souborů.

## 7. README

- Co plugin dělá, snímek obrazovky (až bude).
- Postup: vygenerovat referenční list postavičky → základní krajinu → `collect.py` → `process.py` → `build_matrix.py` → nahrát `public/` na hosting → vytvořit Private Plugin v TRMNL (polling URLs, form fields, markup) → refresh 60 min (TRMNL nabízí jen 15 / 60 / 360 / 720 / 1440 min; text se stejně mění po hodinách).
- Obrázky nejsou součástí repa, každý si generuje vlastní sadu podle promptů.
- Atribuce dat Open-Meteo (CC BY 4.0).
- Poznámka, že obrázky musí být dostupné z internetu, protože šablonu renderuje cloud TRMNL.

## Postup práce

1. Prostuduj dokumentaci TRMNL a trmnlp, ověř předpoklady tohoto zadání a nahlas rozpory.
2. Navrhni strukturu `plugin/` podle trmnlp a nech mě ji odsouhlasit.
3. Implementuj tools, pak texty, pak šablonu, pak testy.
4. Na konci vypiš, co je hotové, co zbývá udělat ručně a jak to otestovat na zařízení.
