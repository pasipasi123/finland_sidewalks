# Oulun ensimmäinen laskenta · 7.11.2026

**Alustava OSM-pohjainen tulos: 107,453252 km kadunvarsien jalkakäytäviä, eli 0,4941 m/asukas.** Tämä on ensimmäinen menetelmän koeajo. Automaattiset laskenta- ja summatarkistukset on tehty, mutta osuuksia ei ole vielä auditoitu kartalta tai maastossa. Luku kuvaa koko Oulun kuntaa, ei keskustaa.

## Erittely

| Luokka | Kilometriä | Sisältyy jalkakäytäväsummaan |
| --- | ---: | --- |
| Ajoradan sidewalk-tägit, kaksoislaskentaa vähennetty | 2,748813 | Kyllä |
| Erilliset footwayt / jalankululle osoitetut polut | 92,132277 | Kyllä |
| Pyörätiestä erotellut jalankulkuosuudet | 12,572162 | Kyllä |
| **Jalkakäytävät yhteensä** | **107,453252** | **Kyllä** |
| Yhdistetyt jalankulku- ja pyörätiet (`segregated=no`) | 393,496317 | Ei |
| Pyörätiet, joiden erottelutieto puuttuu tai on tuntematon | 90,714585 | Ei |

Kaikille erillisille väylille käytetään samaa kadunvarsisuodatusta. Poissuljettujen summat eivät siis kuvaa kaikkia Oulun pyöräteitä. Erottelutiedoltaan tuntematon väylä ei ole varmasti yhdistetty väylä. Tägit, geometrinen vastaavuus ja läheisyys ovat kaikki OSM-aineistoon perustuvia havaintoja.

## Lähtöaineistot

- OSM: [Geofabrik Finland](https://download.geofabrik.de/europe/finland.html), PBF-otsakkeen aikaleima **2026-11-05T21:23:02Z**. Tiedosto 775 037 137 tavua.
- PBF:n MD5: `b20206e4ba0b8ab398e983e2f5fa6e18` (tarkistettu Geofabrikin ilmoittamaa summaa vasten).
- PBF:n SHA-256: `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`.
- Väestö: [Tilastokeskus, StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/), **217 469 asukasta, 31.12.2025**, alue `KU564`. API-kysely ja vastaus tallessa tiedostossa `data/raw/population-564-2025.json`. Taulukko käyttää 1.1.2026 kuntajakoa.
- Kuntaraja: samasta OSM-otoksesta, `boundary=administrative`, `admin_level=8`, kuntakoodi `564`, nimi `Oulu`. Geometria on validi ja sisältää Oulun keskustan tarkistuspisteen 25,47° E / 65,01° N. OSM-polygonin pinta-ala EPSG:3067:ssa noin 3 804,10 km². Raja ei ole virallinen kuntaraja-aineisto.

## Ajo ja tarkistukset

Menetelmäversio **1.0.0**, ajoradan keskilinjan etäisyysraja **20 metriä**, suurin suuntaero **30 astetta**. Pituudet leikataan kuntarajaan. Jalankulun erottelu pyörätiestä vaatii `foot=designated` ja `segregated=yes`. Tarkemmat säännöt ja tunnetut virhelähteet ovat [README:ssä](../README.md).

Valtakunnallisen välimuistin valmistelu poimi **690 539 väylää ja 308 kuntarajaa**. Välimuistin SQLite-tiedosto on noin 293 MiB; Suomen PBF noin 739 MiB. Valmistelun väliaikainen solmuindeksi poistettiin valmistumisen jälkeen.

Oulun laskenta haki kunnan puskuroidusta rajauslaatikosta **30 856 lähtöväylää** ja muodosti **229 558 ajoradan osaa**. Hyväksyttyjä erillisen jalankulkuväylän osia oli **24 953**. Varsinaiseen kuntalaskentaan kului **128,886 sekuntia**, ilman koko maan latausta ja valmistelua. Auditointiaineistossa on **132 914 featurea**, noin 30 MB.

Tarkistettu:

- Jalkakäytävien summa vastaa kolmen mukaan otetun luokan summaa.
- Asukaskohtainen luku vastaa jakolaskua 107 453,252 m / 217 469 asukasta.
- Tarkistus-GeoJSONin luokkakohtaiset pituussummat vastaavat varsinaisia tuloksia auditointirivien millimetripyöristysten tarkkuudella.
- Lähtöaineiston tarkistussumma, kuntakoodi, rajan validius ja keskustan sisältyminen rajaan on tarkistettu.

## Tulostiedostot ja toistaminen

- `data/results/564.json`: täydellinen kuntatulos lähdetietoineen ja kuntageometrioineen.
- `data/results/564.segments.geojson`: QGISissä tarkasteltavat mukaan lasketut ja poissuljetut osuudet OSM-way-tunnuksineen.
- `web/data/municipalities.json`: dashboardin valmis, noin 28 kilotavun aineisto, jossa nyt vain Oulu.
- `data/exports/oulu_analyysi.gpkg`: paikallinen karttatarkistusaineisto EPSG:3067-koordinaatistossa. Eri tulosluokat, välimuistin alkuperäiset väylät tägeineen, kuntaraja ja laskentametatiedot. Ajoratatägien osuudet ovat ajoradan keskilinjalla; `puoli` kertoo lasketun puolen.

Suuret lähtöaineistot, välimuistit ja tarkistusgeometriat on rajattu Gitin ulkopuolelle; dashboardin valmis JSON sekä väestö-CSV sisältyvät projektiin.

```powershell
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 564 --population data/population.csv
./.venv/Scripts/python.exe -m pipeline.cli publish
```

Samoilla lähtötiedoilla uusi `compute` ohittaa valmiin tuloksen. `--force` pakottaa uuden ajon. Etäisyysrajan herkkyyttä ja erillisten viivojen tunnistusta ei ole vielä arvioitu tällä pilotilla. Vertailevia tai keskustojen käyttöä koskevia johtopäätöksiä ei pidä perustaa tähän ensimmäiseen koko kunnan ajoon ilman jatkotarkastelua.
