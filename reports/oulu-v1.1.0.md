# Oulu · karttatarkistuksen jälkeinen laskenta 1.1.0

Päivitetty 7.11.2026 käyttäjän QGIS-tarkistuksessa ilmoittamien havaintojen perusteella. OSM-otos ja väestölähde ovat samat kuin ensimmäisessä pilotissa: Geofabrik Finland **2026-11-05T21:23:02Z**, väestö **217 469 / 31.12.2025**, [StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/).

**Uusi alustava tulos: 70,438434 km, eli 0,3239 m/asukas.**

## Tulokset

| Luokka | Ensimmäinen ajo 1.0.0, km | Uusi ajo 1.1.0, km |
| --- | ---: | ---: |
| Ajorataan merkityt jalkakäytävät, kaksoislaskentaa vähennetty | 2,748813 | 3,027852 |
| Erilliset jalkakäytävät | 92,132277 | 53,730024 |
| Pyörätiestä eroteltu jalankulku | 12,572162 | 13,680558 |
| **Mukaan yhteensä** | **107,453252** | **70,438434** |
| Yhdistetyt väylät, pois summasta | 393,496317 | 401,710219 |
| Erottelu tuntematon, pois summasta | 90,714585 | 93,022272 |

Muutos johtuu sekä tiukemmasta pinta- ja geometriaehdosta että puuttuneiden ajorataviitteiden korjaamisesta. Yhdistettyjen ja tuntemattomien vertailusummia ei suodateta pinnan perusteella; niidenkin muutos aiheutuu ajorataviitteiden korjauksesta ja path-/liikennesaarekerajauksesta.

## Korjatut virhelähteet

- Ajoradan `foot=no` oli virheellisesti poistanut ajoradan sijaintiviitteistä. Kielto koskee ajorataa, eikä siitä seuraa erillisen viereisen jalkakäytävän puuttuminen.
- Torikadun `access=no` sisältää sallivia kulkumuotokohtaisia poikkeuksia. Nämä kadut otetaan sijaintiviitteiksi; yksityisiä ajoratoja ja rajoituksia ilman sallivia poikkeuksia ei lisätty.
- Suomen välimuistiin lisättiin samasta alkuperäisestä PBF:stä **3 514** aiemmin puuttunutta ajorataa. Välimuistissa on nyt **694 053** väylää. Oulun rajauslaatikon lähtöväylien määrä kasvoi 30 856 → **31 232**.
- Erillinen footway tarvitsee sallitun tunnetun kovan pinnan. `compacted`, maa-ainekset ja muut sallittuun listaan kuulumattomat tai puuttuvat pinnat jäävät pois.
- Erillisen footwayn suuntaero ajorataan on enintään **20°**, etäisyys enintään **20 m** ja yhtenäisen hyväksytyn jakson vähimmäispituus **15 m**. Tämä vähentää lyhyiden kiinteistöyhteyksien päiden hyväksymistä. Hyväksyntä tehdään jaksoittain, ei koko OSM-wayn hyväksymisprosentin perusteella.
- `footway=sidewalk` **ei ole pakollinen**, eikä sen puuttumista käytetä poissulkusyynä. Samat pinta- ja geometriaehdot koskevat kaikkia tavallisia footwayitä.
- `highway=path` jätetään tämän analyysin ulkopuolelle. Tämä on analyysin rajaus: [OSM:ssa path voi myös olla eksplisiittisesti jalkakäytäväksi merkitty](https://wiki.openstreetmap.org/wiki/Tag:footway%3Dsidewalk).

Sallitut pintamateriaalit, puuttuvan pinnan käsittely ja muut yksityiskohdat löytyvät [README:stä](../README.md#menetelmä-v110). Pyörätiestä eroteltu jalankulku tarvitsee edelleen `foot=designated` ja `segregated=yes`; sen jalankulkupinnalle sovelletaan kovapintaisuusvaatimusta. Ajoratatägeistä laskettaessa ajoradan `surface`-arvoa ei tulkita jalkakäytävän pintamateriaaliksi.

## Käyttäjän ilmoittamat vertailukohteet

| OSM-way | Ensimmäisessä tuloksessa, m | Korjatussa tuloksessa, m | Huomio |
| --- | ---: | ---: | --- |
| 47110040 | 32,126 | 204,623 | `footway`, `paving_stones`; ei `bicycle`-tägiä eikä pyörätieluokitusta |
| 50118180 | 14,541 | 85,403 | `footway`, `paving_stones`; Pakkahuoneenkadun puuttunut ajorataviite |
| 50118181 | 31,213 | 105,344 | `footway`, `paving_stones`, `bicycle=no` |
| 75718122 | Mukana vanhassa aineistossa | 0 | Franzénin puiston `surface=compacted`; poissuljettu pintasäännöllä |

Kolme ensimmäistä kohdetta ovat nyt `jalkakaytavat_erilliset`-tasolla. Pituudet ovat auditointirivien summia ja sisältävät millimetripyöristykset. Ensimmäiset kolme ovat myös pysyvässä OSM-otosperusteisessa regressiotestissä.

## Tiedostot ja tarkistus

- Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään **rivi kerrallaan yhdessä transaktiossa samaan tiedostoon**, nykyiset tasojen nimet säilyttäen.
- Edellinen GeoPackage säilytetään tiedostossa `data/exports/oulu_analyysi_v1_0.gpkg`. Vanha JSON ja auditointi ovat `data/results/v1.0.0/`-hakemistossa.
- Lähtöväylätasoilla näkyvät nyt `surface`, `footway_surface` ja `hylkayssyy`. Kaikki alkuperäiset OSM-tägit ovat edelleen kentässä `tags_json`.
- `osm_jalankulku_pyora` on yhteinen lähtöaineistotaso. Nimi ei ilmaise yksittäisen viivan pyöräilyoikeutta; tarkista `highway`, `bicycle` ja `luokka`.
- Laskennan hylkäyssyyt tallentuvat myös tiedostoon `data/results/564.rejections.json`.

Kuntalaskenta kesti **123,711 s**. Auditointiosuuksia on **125 674**. 14 automaattista testiä kattavat muun muassa kovapintaisuuden, ajoradan kulkurajoitukset, käyttäjän esimerkit, kiinteistöyhteyden lyhyen rinnakkaisen pään sekä jo avoimen GeoPackagen rivipäivityksen. Menetelmä on edelleen heuristinen: pitkä kovapintainen pihaväylä voi muistuttaa jalkakäytävää, ja puuttuva pintatieto sekä lyhyet todelliset jalkakäytävät aiheuttavat aliarviota. Koko kunnan mittari ei kuvaa erikseen keskustaa.
