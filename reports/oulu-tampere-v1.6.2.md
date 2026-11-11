# Oulu ja Tampere 1.6.2 · bussikadut ja puuttuvat kaarreketjut

Päivitetty 11.11.2026 Tampereen käyttäjätarkistusten perusteella. Molemmat kaupungit laskettiin samoilla säännöillä ja lähtötietojen tarkisteella. Geofabrikin PBF-otos on edelleen 5.11.2026; väestön viitepäivä on 31.12.2025.

| Kunta | Jalkakäytävät, km | m/asukas | Edellinen 1.6.1, km |
| --- | ---: | ---: | ---: |
| Oulu | 84,214169 | 0,3872 | 82,861610 |
| Tampere | 336,000706 | 1,2759 | 331,496874 |

## Ajorataviitteiden korjaus

Insinöörinkadun koko katu ei puuttunut, mutta sen bussiliikenteelle varatuissa osuuksissa oli `access=no` + `bus=yes`. Koodi tunnisti `psv=yes`-poikkeuksen mutta ei `bus=yes`-tägiä. Tämä jätti muun muassa ajoradat 31022799, 31022801 ja 794251023 pois ja esti jalkakäytävän 1144968837 tunnistamisen.

Nyt `bus` kuuluu ajoradan pääsyrajoituksen salliviin kulkumuotopoikkeuksiin. Ajoradan `foot=no` ei edelleenkään kiellä sen erillistä jalkakäytävää. `access=private` ja `access=no` ilman sallivaa kulkumuotopoikkeusta jäävät pois. Tie- ja katuluokkien joukkoa ei laajennettu.

`scripts.extend_bus_references` tarkistaa alkuperäisen PBF:n SHA256-summan ja lisää puuttuvat ajoradat valintaversion 4 välimuistiin. Nykyisestä koko Suomen otoksesta lisättiin 42 ajorataviitettä. Tampereen ajon rajauslaatikkoon tuli 11 lisäystä ja Oulun laatikkoon yksi. Valintaversio on nyt 5; uusi `prepare` sisältää korjauksen suoraan. GeoPackagen `osm_ajoradat` näyttää myös alkuperäiset `bus`- ja `psv`-arvot omissa sarakkeissaan.

## Kaarreketjujen korjaus

Puuttuva kaarre voi olla pitkän OSM-wayn sisällä tai usean lyhyen wayn ketju. Hyväksytyt osat erottavat puuttuvien viivaosien verkon. Verkosta karsitaan tukemattomat umpihaarat; enintään 40 m puuttuva ketju voidaan lisätä, kun sen päissä on hyväksytyt kohdat tai hyväksytty kohta ja ylitys.

Ketjun pitää pysyä ajoratojen etäisyysrajassa (normaaliraja + 10 m, katto 30 m). Ilman ylitystä vaaditaan risteyksen läheisyys tai alkuperäinen yhteinen solmu ajoradan kanssa. Epäselviä silmukoita ei täydennetä. Pinta-, pääsy- ja kokonaisreittihylkäykset säilyvät. Päällekkäiset korjaukset yhdistetään alkuperäisen wayn pituussijainnin mukaan, ja lähempien rinnakkaisten jalankulkuväylien tarkistus tehdään täydennyksillekin.

## Tampereen tarkistuskohteet

| OSM-way | Edellinen, m | Nyt, m | Tulkinta |
| --- | ---: | ---: | --- |
| 1144968837 | 0 | 123,094 | Insinöörinkadun ajorataviitteet palautettu; lähemmän 915815452:n takainen osuus on edelleen pois |
| 42274329 | 582,207 | 594,499 | Pitkän wayn risteyskaarre palautettu; toisesta päästä puuttuu edelleen noin 10,8 m |
| 88200539 | 15,008 | 29,802 | Koko viiva mukana, myös seuraavaan lyhyeen wayhin jatkuva kaarre |
| 1095271885 | 0 | 11,388 | Edelliseen liittyvä lyhyt yhteys mukana |
| 379163743 | 216,062 | 246,720 | Hämeenkadun koko jalkakäytävä mukana |
| 592800179 | 60,556 | 91,392 | Hämeenkadun koko jalkakäytävä mukana |

Osarivien millimetripyöristys voi muuttaa koko viivan pituussummaa muutamia millimetrejä. Osittain hyväksytyn footwayn tai erotellun väylän `hylkayssyy` on nyt vähintään `osittain_poissuljettu`, jos kunnan sisäisestä pituudesta jää yli 0,1 m pois eikä tarkempaa syytä ole. Näin osittainen hyväksyntä ei enää peitä muita aukkoja NULL-arvolla. 1144968837:n tarkempi syy on `osittain_lahempi_jalankulkuvayla`, ja `estaja_osm=915815452` osoittaa estävän jalkakäytävän.

## Varmennus ja katselu

**57 testiä läpäisty.** Mukana ovat oikeat paikalliset OSM-otokset Insinöörinkadulta, Hämeenkadulta ja kaarreketjuista, bussipoikkeus sekä aiemmat Oulun väärät ja oikeat esimerkit. Tampereen kuntalaskenta kesti 260,029 sekuntia ja Oulun 162,239 sekuntia. Tarkat pituudet leikataan edelleen kunnan rajalla; luvut koskevat koko kuntia.

Paikalliset katseluaineistot ovat `data/exports/tampere_analyysi.gpkg` ja `data/exports/oulu_analyysi.gpkg`. Ne päivitetään riveittäin samoihin tiedostoihin. Edelliset paketit säilyvät nimillä `tampere_analyysi_v1_6_1.gpkg` ja `oulu_analyysi_v1_6_1.gpkg`, ja edelliset JSON-/GeoJSON-tulokset hakemistossa `data/results/v1.6.1/`. Web-osuutta ei muutettu.

```powershell
./.venv/Scripts/python.exe -m scripts.extend_bus_references
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 564,837 --population data/population.csv
```

PBF:n SHA256 on `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`. Väestöt ja lähdeviitteet ovat repossa `data/population.csv`. Aiemmat menetelmä- ja lähdetiedot: [Oulu 1.6.1](oulu-v1.6.1.md), [Tampere 1.6.1](tampere-v1.6.1.md).
