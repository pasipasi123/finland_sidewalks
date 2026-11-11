# Kuusi kaupunkia · menetelmä 1.6.4

Laskettu 11.11.2026 samalla OSM-otoksella, samalla menetelmällä ja yhteisellä lähtötietojen tarkisteella. Uudet kaupungit ovat Helsinki, Turku, Espoo ja Vantaa. Oulu ja Tampere ajettiin uudelleen kuuden kaupungin väestötaulukolla; niiden pituustulokset säilyivät ennallaan. Luvut kattavat kuntien koko alueet.

## Tulokset

| Kunta | Koodi | Väestö 31.12.2025 | Jalkakäytävät, km | m/asukas |
| --- | --- | ---: | ---: | ---: |
| Helsinki | 091 | 694 392 | 1 188,606 | 1,7117 |
| Espoo | 049 | 325 716 | 265,929 | 0,8164 |
| Tampere | 837 | 263 337 | 336,610 | 1,2782 |
| Vantaa | 092 | 252 956 | 174,536 | 0,6900 |
| Oulu | 564 | 217 469 | 84,556 | 0,3888 |
| Turku | 853 | 209 633 | 366,711 | 1,7493 |

## Pituuksien luokat

Vain kolme ensimmäistä pituusluokkaa sisältyvät summaan. Asfalttioletus on mukana olevien erillisväylien puuttuva pintatieto, ei erillinen lisättävä luokka.

| Kunta | Ajoratatägit, km | Footwayt, km | Eroteltu, km | Yhdistetty, km (pois) | Erottelu tuntematon, km (pois) | Asfalttioletus, km |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Helsinki | 10,700 | 971,285 | 206,621 | 188,328 | 7,766 | 11,771 |
| Espoo | 1,319 | 227,790 | 36,821 | 485,390 | 25,534 | 12,040 |
| Tampere | 22,572 | 249,723 | 64,315 | 295,936 | 9,430 | 36,369 |
| Vantaa | 2,209 | 154,140 | 18,186 | 444,231 | 21,836 | 6,048 |
| Oulu | 2,805 | 68,138 | 13,612 | 400,589 | 91,819 | 16,977 |
| Turku | 10,133 | 305,557 | 51,020 | 219,825 | 11,140 | 16,344 |

## Lähteet ja asetukset

- Geofabrikin `finland.osm.pbf`, OSM-päiväys **2026-11-05T21:23:02Z**. SHA256 `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`.
- Kuntarajat samasta OSM-otoksesta, `admin_level=8`, `ref:FI`-kuntakoodit. Pituudet leikataan kuntapolygoneilla.
- Väkiluvut: [Tilastokeskus StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/), viitepäivä **31.12.2025**. Repon `data/population.csv` sisältää kaikki kuusi riviä. API-raakavastaukset ovat paikallisesti `data/raw/population-<koodi>-2025.json`.
- Menetelmä 1.6.4, välimuistin valintaversio 6. Parametreja ei muutettu kaupunkikohtaisesti. Perusetäisyys 20 m, tavallisen footwayn suuntaero 20 astetta, vähimmäisjakso 15 m. Puuttuva pinta oletetaan asfaltiksi; tunnetut pehmeät pinnat, highway=path, living_street-varret ja yhdistetyt väylät jäävät pois.
- Samat kokonaisreitti-, rinnakkaisuus-, pysäkkilaituri- ja molemmista päistä tuettujen lyhyiden sivusiirtymien säännöt kuin Oulun ja Tampereen karttatarkistuksissa.

Yhteinen laskentatarkiste: `aaeb54036b97c32c2f8a243231b46542f70cec632251b4330c0e1572b6b04fda`.

## Paikalliset katseluaineistot

Jokaisessa GeoPackagessa on sama tasorakenne ja koordinaatisto EPSG:3067. Uudet kaupungit ovat ensimmäistä paikallista karttatarkistusta varten.

| Kunta | GeoPackage | Laskentatulos |
| --- | --- | --- |
| Helsinki | `data/exports/helsinki_analyysi.gpkg` | `data/results/091.json` |
| Espoo | `data/exports/espoo_analyysi.gpkg` | `data/results/049.json` |
| Tampere | `data/exports/tampere_analyysi.gpkg` | `data/results/837.json` |
| Vantaa | `data/exports/vantaa_analyysi.gpkg` | `data/results/092.json` |
| Oulu | `data/exports/oulu_analyysi.gpkg` | `data/results/564.json` |
| Turku | `data/exports/turku_analyysi.gpkg` | `data/results/853.json` |

Osuusgeometriat, hylkäyssyyt, rinnakkaisuudessa poistetut geometriat ja laiturialueet ovat vastaavissa `<koodi>.segments.geojson`, `.rejections.json`, `.corridor_exclusions.geojson` ja `.platforms.geojson` -tiedostoissa. Lähdetason `mukaan_m` ja `hylkayssyy` auttavat vertaamaan myös pois jääneitä osuuksia. Suuret paikalliset lähtö- ja katseluaineistot on rajattu Gitin ulkopuolelle.

Oulun ja Tampereen GeoPackage-rivit päivitettiin samoihin tiedostoihin. Niiden edelliset paketit säilyvät `*_analyysi_before_six_cities.gpkg`-tiedostoissa ja edelliset laskentatulokset hakemistossa `data/results/v1.6.4-two-cities/`.

Valmis kuuden kaupungin kooste on `data/results/municipalities.json` (coverage_count=6). Siinä on valmiit summat, asukaskohtaiset luvut, tämän kuuden kaupungin joukon sijoitukset ja karttapolut. Web-tiedostoja ei muutettu.

## Varmennus ja suoritus

62 regressiotestiä läpäistiin ennen ajoa. Kaikkien kuuden kaupungin tulosversio, lähtötietojen tarkiste ja sääntöparametrit ovat samat. Osarivien summat täsmäävät kuntatuloksiin millimetripyöristyksen sallimissa rajoissa. GeoPackagejen eheys ja viiteavaimet sekä tulostasoille päätyvät tagiluokat on tarkistettu. Oulun ja Tampereen vanhat pituustulokset säilyivät täsmälleen ennallaan.

| Kunta | Lähtöväyliä rajauslaatikossa | Auditointirivejä | Laskenta, s |
| --- | ---: | ---: | ---: |
| Helsinki | 111 257 | 321 395 | 653,4 |
| Espoo | 74 205 | 180 583 | 398,9 |
| Tampere | 30 004 | 145 048 | 227,9 |
| Vantaa | 51 586 | 145 973 | 308,0 |
| Oulu | 31 352 | 128 560 | 147,6 |
| Turku | 35 177 | 136 611 | 240,2 |

Laskenta-aikaa oli yhteensä noin 32,9 minuuttia, yksi kunta kerrallaan. GeoPackage-vientien aika ei sisälly kuntalaskennan lukuihin.

Uusien neljän kaupungin tekniset tarkistukset eivät korvaa paikallista karttatarkastelua. OSM-kartoituksen kattavuus ja tagikäytännöt voivat vaikuttaa kuntien välisiin eroihin.

## Toistaminen

```powershell
./.venv/Scripts/python.exe scripts/fetch-population.py --codes 091,853,049,092,564,837 --year 2025
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 091,853,049,092,564,837 --population data/population.csv
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 091 --output data/exports/helsinki_analyysi.gpkg
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 853 --output data/exports/turku_analyysi.gpkg
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 049 --output data/exports/espoo_analyysi.gpkg
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 092 --output data/exports/vantaa_analyysi.gpkg
./.venv/Scripts/python.exe -m pipeline.cli publish --output data/results/municipalities.json
```

Vienti vaatii uuden tiedostonimen, jos GeoPackage on jo olemassa. Auki olevan Oulu-/Tampere-tiedoston rivitys tehdään `pipeline.sync_gpkg`-komennolla [käyttöohjeen](../README.md) mukaan.
