# cute-weather

TRMNL plugin pro displej v dětském pokoji. Ukazuje ilustraci krajiny, ve které je holčička se psem
oblečená a chová se podle aktuálního počasí, a pod ní krátký český text o počasí pro děti 4–8 let:

> Sníh je měkký jako peřina, skoč do něj. Venku je **mínus 5** stupňů. Nezapomeň rukavice, ať prstíky nejsou studené jako rampouchy.

*(snímek obrazovky doplníme, až bude hotová sada obrázků)*

- Cílové zařízení: **TRMNL X** (e-ink 1872×1404 px, 16 odstínů šedi).
- Běží v oficiálním cloudu TRMNL jako **Private Plugin** se strategií **Polling** – žádný vlastní server ani cron.
  Veškerá logika (klasifikace počasí, výběr obrázku a vět, skloňování) je v Liquid šabloně.
- Počasí: [Open-Meteo](https://open-meteo.com/), bez API klíče.
- Obrázky a `texty.json` jsou statické soubory na veřejné URL, kterou zadáš v nastavení pluginu.

V `public/img/` je hotová sada obrázků pro displej (zatím jen den, noc používá denní obrázek).
Originály z ChatGPT (`raw/`) se necommitují; vlastní sadu vygeneruješ podle promptů z `tools/prompts.py`
s referencemi v `refs/`.

## Struktura

```
plugin/            TRMNL plugin (projekt pro trmnlp): src/settings.yml, src/shared.liquid, src/full.liquid
public/            obsah pro statický hosting: texty.json + img/ (hotová sada 56 + vychozi_den)
refs/              referenční list postavičky a základní krajina pro generování
raw/               stažené originály z ChatGPT (necommituje se)
samples/           ukázkové odpovědi Open-Meteo pro testy
tools/             prompts.py, collect.py, process.py, build_matrix.py, validate_texts.py, test_samples.py
```

## Postup

Potřebuješ Python 3.9+ a Pillow (`pip install pillow`). Pro náhled a testy šablony navíc Docker
(nebo Ruby ≥ 3.4 a `gem install trmnl_preview`).

### 1. Referenční list postavičky a základní krajina

```
python3 tools/prompts.py --reference    # prompt na referenční list (holčička + pes, tři pohledy)
python3 tools/prompts.py --landscape    # prompt na základní krajinu bez postav
```

Výsledky ulož jako `refs/holcicka-vzor.png` a `refs/leto-vzor.png` (nebo použij ty přiložené).

### 2. Generování obrázků – `collect.py`

Obrázky se generují ručně v ChatGPT; ke každému promptu přilož **obě reference** z `refs/`.

```
python3 tools/collect.py                # sleduje ~/Downloads
python3 tools/collect.py ~/Stažené --doba vse
```

Skript vypíše jméno a prompt další chybějící kombinace (na macOS ho rovnou zkopíruje do schránky),
počká na nový `.png`/`.webp` ve sledované složce, přesune ho do `raw/` pod správným jménem a pokračuje.
Dá se kdykoli přerušit (Ctrl+C) a spustit znovu.

První fáze je jen den: **26 kombinací + `vychozi_den`** (neutrální obrázek pro případ výpadku dat).
Negenerují se nereálné kombinace `snih_leto` a `bourka_zima`. Noc (`--doba noc`) je volitelná pozdější fáze
a kromě 26 kombinací obsahuje i obecné `noc_<obdobi>` a `noc`.

Jména souborů: `{kategorie}_{obdobi}_{doba}.png`, např. `dest_podzim_den.png`.

### 3. Zpracování – `process.py`

```
python3 tools/process.py --preview
```

Z `raw/` do `public/img/`: šeď → středový ořez na 4:3 a resize na 1872×1404 → autokontrast → jemné doostření
→ kvantizace do **pevné palety 16 úrovní šedi** displeje (0, 17, … 255). `--preview` vytvoří kontaktní arch `preview.png`.

| přepínač | význam |
|---|---|
| `--dither fs` (výchozí) | Floyd–Steinberg, nejplynulejší přechody |
| `--dither bayer` | uspořádaný dithering 8×8, o něco menší soubory |
| `--dither none` | bez ditheringu (posterizace), nejmenší soubory |
| `--gamma 0.85` | zesvětlí střední tóny, pokud obrázek na panelu působí ztmavle |
| `--no-autocontrast`, `--no-sharpen` | vypnutí jednotlivých kroků |

Skript u každého obrázku vypíše i odhad velikosti výsledného 4bit snímku. TRMNL X má limit
**750 kB na snímek obrazovky**; pokud se k němu obrázek blíží, skript na to upozorní (pomůže `bayer` nebo `none`).

### 4. Doplnění matice – `build_matrix.py`

```
python3 tools/build_matrix.py
```

Liquid neumí zjistit, jestli soubor existuje, proto skript vytvoří **všech 56 souborů** (7 kategorií × 4 období × den/noc).
Chybějící kombinace doplní kopií podle fallbacku a vypíše tabulku originálů a kopií:

- den: přesná shoda → (`bourka` → `dest` stejného období) → `zatazeno` stejného období → `vychozi_den.png`
- noc: přesná shoda → `noc_{obdobi}.png` → `noc.png` → nouzově denní obrázek (dokud nejsou noční obrázky)

Po každém dalším generování stačí znovu spustit `process.py` a `build_matrix.py`.

### 5. Hosting

Nahraj obsah složky `public/` (`texty.json` + `img/`) na libovolný statický hosting. Adresu bez koncového
lomítka pak zadáš do pluginu jako **Adresa s obrázky a texty**; musí platit `<adresa>/texty.json` a `<adresa>/img/jasno_leto_den.png`.

> Soubory musí být **dostupné z internetu** – šablonu renderuje cloud TRMNL, ne zařízení v domácí síti.
> Adresa nemusí být nikde odkazovaná (stačí „neindexovaná" URL). `texty.json` se musí posílat jako `application/json`.

### 6. Private Plugin v TRMNL

Buď přes `trmnlp` (`cd plugin && bin/trmnlp login && bin/trmnlp push`), nebo ručně na
[trmnl.com](https://trmnl.com) → Plugins → Private Plugin → New:

| pole | hodnota |
|---|---|
| Strategy | Polling |
| Polling URL(s) | dva řádky v tomto pořadí (viz níže) |
| Polling verb | GET |
| Refresh rate | 60 minut (text se mění po hodinách; nabízené hodnoty jsou 15 / 60 / 360 / 720 / 1440) |
| Remove bleed margin | ano (`no_screen_padding`) |
| Form fields | YAML ze `plugin/src/settings.yml` (klíč `custom_fields`) |
| Markup – Shared | obsah `plugin/src/shared.liquid` |
| Markup – Full | obsah `plugin/src/full.liquid` |

```
https://api.open-meteo.com/v1/forecast?latitude={{ latitude }}&longitude={{ longitude }}&current=temperature_2m,weather_code,wind_speed_10m,is_day&timezone=Europe/Prague
{{ base_url }}/texty.json
```

První odpověď je v šabloně dostupná jako `IDX_0`, druhá jako `IDX_1`. Po uložení vyplň form fields:
zeměpisnou šířku a délku (výchozí České Budějovice, 48.97 / 14.47) a adresu z kroku 5.
Plugin zatím podporuje jen layout **full**.

## Jak šablona vybírá

| | pravidlo |
|---|---|
| kategorie | WMO `weather_code`: 0 jasno · 1–2 polojasno · 3 zataženo · 45, 48 mlha · 51–67, 80–82 déšť · 71–77, 85–86 sníh · 95–99 bouřka · jiné zataženo |
| období | podle měsíce: 12–2 zima, 3–5 jaro, 6–8 léto, 9–11 podzim |
| obrázek | `{kategorie}_{obdobi}_{den\|noc}.png`, den/noc podle `is_day` |
| doba textu | `is_day = 0` → noc, jinak do 9 h ráno, od 18 h večer, jinak den |
| teplotní pásmo | mráz < 0 · zima 0–9 · chladno 10–17 · teplo 18–25 · horko > 25 (zaokrouhlená teplota) |
| vítr | slabý < 15 km/h (nic se nepíše) · střední 15–35 · silný > 35 |
| text | `{věta počasí} Venku je {teplota} {stupeň/stupně/stupňů}. {věta oblečení} {věta o větru}` |

Datum a hodina se berou z `IDX_0.current.time` (lokální čas díky `timezone=Europe/Prague`), ne z `now`.
Věty se vybírají indexem z dne v roce a hodiny, takže jsou v rámci hodiny stabilní. Když data chybí,
zobrazí se `vychozi_den.png` s neutrální větou; když chybí jen `texty.json`, zůstane správný obrázek a teplota.

## Texty

`public/texty.json` obsahuje 700 vět: počasí (7 kategorií × ráno/den/večer/noc × 20), oblečení (5 pásem × 20)
a vítr (střední, silný × 20). Pravidla (max 12 slov, žádná čísla, žádné duplicity, max 3 stejné začátky
ve skupině, oblečení neodporuje pásmu) hlídá:

```
python3 tools/validate_texts.py
```

## Lokální náhled a testy

```
python3 tools/test_samples.py            # vyrenderuje všechny vzorky ze samples/ a ověří obrázek i text
python3 tools/test_samples.py --only snih_den_zima_minus5 --png   # navíc PNG 1872×1404 jako na zařízení
```

Test pro každý vzorek vyrenderuje šablonu přes `trmnlp build` (lokálně nebo v Dockeru) proti lokálnímu HTTP
serveru a porovná jméno obrázku, klasifikaci i celý text s nezávislým výpočtem v Pythonu.

Živý náhled s reálným počasím:

```
python3 -m http.server 8000 --directory public     # v jednom terminálu
cd plugin && bin/trmnlp serve                        # ve druhém → http://localhost:4567
```

Adresa obrázků a textů pro náhled je v `plugin/.trmnlp.yml` (`custom_fields.base_url`), výchozí
`http://host.docker.internal:8000` funguje uvnitř Dockeru (texty a `build --png`). Aby se obrázky načetly
i v prohlížeči na hostiteli, přepiš ji na adresu dostupnou z obou stran – IP počítače v síti
(`http://192.168.1.10:8000`) nebo rovnou hosting z kroku 5. S lokálně nainstalovaným gemem stačí `http://localhost:8000`.

## Poznámky k TRMNL X

- Displej má 1872×1404 fyzických px, framework s ním ale pracuje jako s plochou 1040×780 CSS px zvětšenou
  poměrem 1,8. Rozměry v `full.liquid` jsou proto psané jako fyzické px dělené `--pixel-ratio`
  (okraj 40 px, rámeček 3 px, text 46 px, teplota 60 px).
- Obrázky z `process.py` obsahují přesně 16 úrovní šedi displeje (0, 17, … 255) a šablona je vykresluje přesně 1:1
  (ověřeno: render 1872×1404 v 8bit hloubce je se zdrojovým obrázkem shodný na 100 % pixelů).
- 4bit PNG náhled z `trmnlp build --png` je jen orientační: lokální kvantizér (ImageMagick) slučuje některé úrovně
  a výsledek je hrubší než zdroj. Jak přesně převádí snímek cloud TRMNL, dokumentace neuvádí – rozhodne až pohled
  na zařízení. Kdyby tam dithering působil rušivě, přegeneruj obrázky s `--dither bayer` nebo `--dither none`.

## Data a licence

- Data o počasí: [Open-Meteo.com](https://open-meteo.com/), licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Kód a texty: MIT, viz `LICENSE`.
