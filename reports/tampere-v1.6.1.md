# Tampere 1.6.1 · ensimmäinen vertailuajo

Laskettu 9.11.2026 samoilla säännöillä kuin Oulun menetelmäversio 1.6.1. Tulos on **331,496874 km** ja **1,2588 m/asukas**. Tämä on koko kunnan analyysi, ei keskustan rajaus. Tarkoitus on arvioida Oulussa kehitettyjen sääntöjen siirtymistä toiseen kaupunkiin karttatarkastelulla.

| Osuus | Kilometriä | Mukana summassa |
| --- | ---: | --- |
| Ajoradan sidewalk-tägit kaksoislaskennan poiston jälkeen | 22,672266 | Kyllä |
| Erilliset footwayt | 244,798045 | Kyllä |
| Eroteltu jalankulku ja pyöräily | 64,026563 | Kyllä |
| Yhdistetty jalankulku ja pyöräily | 295,935750 | Ei |
| Pyöräväylän erottelu tuntematon | 9,430170 | Ei |

Mukana lasketusta pituudesta **35,929036 km** käyttää puuttuvan pintatiedon asfalttioletusta (noin 10,84 %). Tunnetut pehmeät pinnat ja highway=path ovat edelleen poissa. Puuttuva footway=sidewalk ei ole poissulkuehto.

## Lähteet ja toistaminen

- Kunta 837, OSM:n kuntaraja.
- Geofabrikin `finland.osm.pbf`, OSM-päiväys **2026-11-05T21:23:02Z**, SHA256 `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`.
- Väkiluku **263 337**, viitepäivä **31.12.2025**, [Tilastokeskus StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/). Raakavastaus on paikallisesti `data/raw/population-837-2025.json`, laskentarivi repossa `data/population.csv`.
- Ylitysviivat ovat yhteystietoa (`crossing_context`), eivät mukana pituuksissa. Välimuistin valintaversio on 4.

```powershell
./.venv/Scripts/python.exe scripts/fetch-population.py --codes 837 --year 2025
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 837 --population data/population.csv
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 837 --output data/exports/tampere_analyysi.gpkg
```

Paikalliset tulokset ovat `data/results/837.json`, `837.segments.geojson`, `837.rejections.json` ja `837.corridor_exclusions.geojson`. Tarkistusaineisto on **`data/exports/tampere_analyysi.gpkg`**, EPSG:3067, samoilla tasoilla kuin Oulussa. Suuret lähtö-, tulos- ja GeoPackage-tiedostot eivät kuulu Gitiin.

## Varmennus ja karttatarkistus

Ajossa oli 29 993 lähtöväylää ja 143 458 auditointiriviä. Kuntalaskenta kesti **230,597 sekuntia**. Osarivien summat täsmäävät laskentatulokseen alle metrin pyöristyserolla. GeoPackagen eheys ja viiteavaimet on tarkistettu; ylitysviivat, highway=path ja living_street eivät esiinny summan kolmella tulostasolla. Analyysikoodin 52 testiä läpäistiin.

Tampereelle ei muutettu parametreja eikä tehty kohdekohtaisia poikkeuksia. Säännöt ovat [menetelmäkuvauksessa](../README.md#menetelmä-v161); Oulun taustalla olevat tapaukset ovat pysyvissä testeissä. Tämä ei vielä varmista Tampereen tuloksen oikeellisuutta: tarkista ainakin ydinkeskustan korttelit, tavalliset asuntokadut, yhdistettyjen väylien rinnakkaiset footwayt ja kiinteistöjen reittiverkot. Tarkastele myös pois jääneitä lyhyitä linkkejä lähdetasolla `hylkayssyy`-kentän avulla. Mahdolliset korjaukset tulee tehdä yleisiin sääntöihin ja testata molemmissa kaupungeissa.
