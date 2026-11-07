# Oulu 1.3.0 · lähin kadunpuolen kulkureitti ja pihakaturajaus

Päivitetty 7.11.2026 käyttäjän karttatarkistuksen perusteella. **Yhteensä 87.371265 km, eli 0.4018 m/asukas.** Edellinen tulos oli 94,659870 km.

## Laskentasäännöt

- Lähin samalla tasolla oleva samansuuntainen katu toimii sijaintiviitteenä. Saman kadunpuolen lähempi footway tai jalankululle osoitettu pyöräväylä sulkee pois sen takaisen rinnakkaisen osuuden. Vastakkainen puoli ja viereisen toisen kadun oma jalkakäytävä säilyvät.
- `foot=designated`-pyöräväylä toimii esteenä myös erottelutiedon puuttuessa. Pyöräväylä ilman jalankulkutarkoitusta ei estä erillistä jalkakäytävää.
- Sisemmän reitin fyysinen sijainti huomioidaan myös silloin, kun se ei kuulu jalkakäytävämittariin oman pinta- tai path-rajauksensa vuoksi.
- Alue poistetaan sisemmän viivan päätyjen väliseltä osuudelta, ilman pyöreiden puskuripäätyjen jatkamista sen yli. Sivuttaisen järjestyksen toleranssi on 0,25 m. Jäljelle jääviin tavallisten footwayiden jaksoihin sovelletaan 15 m vähimmäispituutta.
- `living_street` ei ole laskentakatu eikä sen sidewalk-tägeistä lasketa pituutta. Pihakadut säilyvät sijaintikontekstina: niiden vierustat eivät pääse mukaan läheisen toisen kadun kautta. Tämä on projektin laskentarajaus.
- Puuttuvan pinnan asfalttioletus ja version 1.2.0 tunnettuja pintoja koskevat rajaukset säilyvät.

Lähempien väylien ja pihakatujen vuoksi suoraan leikatut osuudet: **6168.188 m**. Lyhyiden jäljelle jääneiden jaksojen poisto ja muut laskentavaikutukset selittävät osan kokonaismuutoksesta tämän lisäksi.

## Tulosluokat

| Luokka | km |
| --- | ---: |
| Ajorataan merkityt jalkakäytävät | 2.862658 |
| Erilliset jalkakäytävät | 70.761060 |
| Eroteltu jalankulku pyöräväylällä | 13.747547 |
| **Mukaan yhteensä** | **87.371265** |
| Yhdistetyt, pois summasta | 401.307671 |
| Erottelu tuntematon, pois summasta | 91.936527 |

Asfalttioletuksen osuus erillisistä mukaan otetuista väylistä on 19.384945 km. Lähteet ovat edelleen Geofabrik Finland 2026-11-05T21:23:02Z ja Tilastokeskuksen väestö 217 469 / 31.12.2025.

## Tarkistuskohteet

**1209361514** on poistettu kokonaan jalkakäytävätasolta. Sen ja ajoradan välissä kulkee **41672560**, jolla on `highway=cycleway`, `foot=designated`, `bicycle=designated`, mutta erottelutieto puuttuu. Tämä riittää sisemmän jalankulkureitin tunnistukseen; sen 69,023 m säilyy erottelultaan tuntemattomien poissuljetussa luokassa.

**Kirkkokadun 29107579**, johon liittyy 880486292, puuttui aikaisemmin jo lähtöpoiminnasta. Alkuperäisen saman PBF-otoksen tägit ovat `highway=footway`, `bicycle=designated`, `segregated=no`, `surface=paved`, `is_sidepath=yes`. [OSM:n footway-tägi sisältää jo jalankulkutarkoituksen](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dfootway), joten erillistä `foot=designated`-tägiä ei vaadita. Poiminta korjattiin koko Suomen osalta; välimuistiin lisättiin 202 puuttunutta footwayta. Oulun kohde on nyt lähtötasolla ja **320,309 m yhdistettyjen poissuljetulla tasolla**. Kohteen takia ei tarvinnut kasvattaa 20 m etäisyysrajaa. Pysäköintikäytävät eivät ole jalankulkuesteitä.

Aiemmat jalkakäytäväesimerkit säilyivät: 36729304 noin 88,579 m, 89930891 noin 526,562 m, 47110040 noin 204,623 m, 50118180 noin 85,403 m ja 50118181 noin 105,180 m. Auditointirivien pituudet on pyöristetty millimetreihin.

## QGIS ja toistettavuus

Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään saman tiedoston riveihin yhtenä transaktiona. Tasonimet ja olemassa olevat tyylitaulut säilyvät. Edellinen GeoPackage jää tiedostoon `data/exports/oulu_analyysi_v1_2.gpkg`, vanhat laskentatulokset hakemistoon `data/results/v1.2.0/`.

Lähtöviivojen kentät:

- `hylkayssyy`: esimerkiksi `lahempi_jalankulkuvayla`, `osittain_lahempi_jalankulkuvayla`, `pihakadun_varsi` tai `living_street_rajattu_pois`.
- `estaja_osm`: sisemmän kulkureitin OSM-tunnisteet.
- `viitekatu_osm`: sijaintiviitteenä käytetty katu.
- `varjossa_m`: suoraan peittyvä pituus; lisäksi voi poistua alle 15 m pituisia loppujaksoja.
- `pinnan_tila` ja `laskenta_pinta`: asfalttioletus erillään alkuperäisistä tägeistä.

Tarkat poistetut geometriaosuudet ovat erikseen tiedostossa `data/results/564.corridor_exclusions.geojson`. Alkuperäiset OSM-tägit säilyvät myös `tags_json`-kentässä.

Kuntalaskenta kesti 152.572 s. Kaikki 26 testiä läpäisty, mukaan lukien oikeat Oulu-esimerkit, vastakkainen puoli, kaksi rinnakkaista katua, sisemmän väylän päättymiskohta, pysäköintikäytävä, living street sekä avoimen GeoPackagen rivipäivitys. Geometrinen katuun yhdistäminen on edelleen heuristiikka: risteykset ja puuttuva OSM-kartoitus voivat vaikuttaa tulokseen.
