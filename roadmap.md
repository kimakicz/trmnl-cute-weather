Plugin cute-weather je postavený a prochází všemi lokálními testy. Na samotném zařízení se ale ověřit nedal a nic z dnešní práce není commitnuté ani pushnuté.

Co je hotové

- SPEC.md: je v něm ověřené nastavení ditheringu i rozhodnutí z vašich odpovědí, tedy čtyři denní doby textů, refresh 60 minut a složka refs/.
- plugin/: šablony a nastavení Private Pluginu. Verze pro půlenou a čtvrtinovou obrazovku jen píší, že plugin potřebuje celou plochu.
- tools/: generování promptů, hlídání stažených obrázků, převod pro displej, doplnění všech 56 souborů, kontrola textů a testy šablony.
- public/texty.json: má teď 700 vět. Odstranil jsem slabý vítr a přepsal věty o oblečení, které počítaly se sluncem nebo posílaly dítě ven. V testu se totiž bouřka potkala s větou „utíkej ven".
- samples/, README.md, LICENSE, .gitignore: 30 ukázkových odpovědí Open-Meteo a dokumentace. Do MIT licence jsem jako držitele práv uvedl kimakicz, odhadnuté z adresy repozitáře. Pokud to tak nemá být, řekněte.

Výsledky testů

- Šablona: všech 31 případů vyšlo správně, tedy jméno obrázku, klasifikace i celý text. Patří sem skloňování („mínus 1 stupeň", „3 stupně", „0 stupňů"), hranice teplotních pásem a větru, chybová odpověď Open-Meteo i nedostupný texty.json.
- Živá data: se skutečným Open-Meteo plugin ukázal zataženo a 11 stupňů s obrázkem zatazeno_podzim_den.
- Vykreslení obrázku: náhled v rozlišení 1872×1404 se se zdrojovým obrázkem shoduje na 100 % pixelů. Dithering se tedy cestou nerozmaže.
- Ostatní: trmnlp lint i kontrola textů prošly.

Odchylky od zadání

- Rozměry: TRMNL X pracuje s plochou 1040×780 CSS pixelů zvětšenou poměrem 1,8. Hodnoty ze zadání (okraj 40 px, rámeček 3 px) jsem proto vzal jako fyzické pixely a v šabloně je přepočítávám. Text má 46 px místo zadaných minimálně 40.
- Chybějící texty: když je počasí v pořádku a chybí jen texty.json, zůstane správný obrázek a teplota. Zadání pro ten případ chtělo výchozí obrázek.
- Noční obrázky: dokud neexistují, doplní se na jejich místo denní obrázek téže kombinace a skript na to upozorní. Jinak by se v noci zobrazil rozbitý obrázek.

Co zbývá udělat ručně

1. Vygenerovat obrázky pomocí python3 tools/collect.py. Je to 26 denních kombinací a k nim vychozi_den. Ke každému promptu přiložte obě reference z refs/.
2. Spustit python3 tools/process.py --preview a pak python3 tools/build_matrix.py.
3. Nahrát obsah složky public/ na hosting dostupný z internetu.
4. Vytvořit Private Plugin. Buď příkazem cd plugin && bin/trmnlp login && bin/trmnlp push, nebo ručně podle tabulky v README. Potom vyplnit souřadnice a adresu hostingu.

V raw/ jsou zatím jen tři zkušební soubory a jeden z nich slouží jako vychozi_den. Pravý výchozí obrázek teprve vznikne.

Co sledovat na zařízení

- Dithering: dokumentace neříká, jak cloud převádí snímek na 16 odstínů. Kdyby dithering na zařízení rušil, přegenerujte obrázky s --dither bayer nebo --dither none.
- Velikost snímku: limit TRMNL X je 750 kB a s Floyd–Steinbergem vychází odhad na 663–697 kB. Je to těsné, process.py na to u každého obrázku upozorní.
- Tmavost: pokud budou střední tóny na panelu moc tmavé, zkuste --gamma 0.85.
- Textový box: na starých vzorech zakrývá dolní část hráze. Nové prompty drží spodní třetinu obrázku prázdnou, s novými obrázky by to tedy mělo sedět.

Náhled v plném rozlišení (test_samples.py --png) trvá v Dockeru několik minut na jeden obrázek. Testy bez PNG doběhnou asi za 12 sekund.

Řekněte, jestli mám změny commitnout a pushnout.

✻ Baked for 27m 1s · done 9:12 AM

※ recap: Stavíme TRMNL plugin cute-weather s dětskými texty o počasí a ilustracemi; plugin, nástroje, texty i testy jsou hotové a lokálně prošly, ale nic není commitnuté. Další krok: řekněte, zda mám změny commitnout a pushnout.

❯ commit a push

  Pushed to main, ran 1 shell command

Commitnuto a pushnuto. Commit 32703b2 „Postavit TRMNL plugin cute-weather podle SPEC.md" je na origin/main a pracovní strom je čistý.

V commitu je plugin/, tools/, samples/, public/texty.json, refs/, SPEC.md, README.md, LICENSE a .gitignore. Git zachoval historii přesunutých souborů (texty.json, validate.py a obou referencí).

Z repozitáře zmizely soubory zima-vzor.png, leto-trmnl.png a zima-trmnl.png. Zimní vzor máte dál lokálně jako raw/snih_zima_den.png. Převedené obrázky jsem smazal, znovu je vytvoří tools/process.py.

Složky raw/ a public/img/ se necommitují, takže zkušební obrázky zůstaly jen na vašem počítači.

Obrázky z prvních commitů zůstávají v historii gitu, celkem asi 9 MB. Kdyby vám to vadilo, dá se historie přepsat. Znamenalo by to force push, takže bych to dělal jen na vaše výslovné přání.

Dál můžete pokračovat generováním obrázků příkazem python3 tools/collect.py.
