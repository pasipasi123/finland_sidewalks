# Oulu 1.5.0 · sisäverkon satunnaiset katuosumat

Päivitetty 7.11.2026 hautausmaan kohteen 1144437799 perusteella. Uusi tulos on **85,822729 km** ja **0,3946 m/asukas**. Edellinen versio 1.4.0 tuotti 86,781163 km. Laskenta käyttää samaa paikallista OSM-otosta; kiinteistörajoja tai API-avainta ei tarvita.

## Verkon tulkinta

Jalankulkuväylien yhteisistä koordinaattisolmuista muodostetaan verkko erikseen kullekin tasolle. Reittiä seurataan OSM-way-rajojen yli haarautumiseen, päätepisteeseen tai kadun risteyksen läheisyyteen asti. Pelkkä viivojen geometrinen risteäminen ei luo yhteyttä. Myös pintasäännöllä hylätty jalankulkuväylä voi kertoa sisäisen verkon rakenteesta.

Tavallinen footway hylätään, jos sen toinen pää liittyy yli 25 metrin päässä kadusta haarautuvaan sisäverkkoon ja toinen pää jää umpinaiseksi enintään 20 metrin päähän kadusta keskellä risteysväliä. Myös molemmista päistään tällaiseen sisäverkkoon liittyvä paikallinen katuosuma hylätään. Jos seurattu reitti saavuttaa kadun risteyksen tai päätepisteen 25 metrin lähiympäristön, tämä sääntö ei hylkää sitä. Yli 250 metrin haarautumaton jatko ja silmukka suojataan myös varovaisuuden vuoksi. Aiemmat pinta-, suunta-, pituus- ja rinnakkaisuusehdot koskevat edelleen säilyviä reittejä.

Koko kytkeytynyttä verkkoa ei hylätä yhden tonttihaaran vuoksi. Katua seuraava pääreitti voi säilyä, vaikka siitä erkanee sivuhaara tontille. Menetelmä ei vielä varmista, että jokainen hyväksytty osuus ulottuu koko korttelin halki: risteyskonteksti suojaa ilmeisiä tapauksia, ja poissulku vaatii yllä kuvatun vahvan sisäverkkovihjeen. Puutteelliset OSM-yhteydet voivat aiheuttaa virheitä molempiin suuntiin.

## Tarkistus

Kohteen **1144437799** aiemmin hyväksytty noin **102,675 m** poistuu. Lähtötasolla se säilyy tarkasteltavana arvolla `mukaan_m=0` ja syyllä `sisaverkon_paattyva_katuosuma`. Koko Oulun aiemmin hyväksytystä aineistosta vähenee tämän muutoksen vuoksi 21 OSM-wayn osuuksia, yhteensä noin 958,44 m.

**33 testiä läpäisty.** Mukana ovat oikea hautausmaaverkko, useaan OSM-wayhin jaettu sisäverkon haara, tonttihaaran sisältävä säilyvä kadunvarsijalkakäytävä ja kadun päätepisteen suoja. Koko Oulun ajossa aiemmin oikeiksi tarkistetut kohteet säilyivät: 36729304 noin 88,579 m; 89930891 noin 526,562 m; 47110040 noin 204,623 m; 50118180 noin 85,403 m; 50118181 noin 105,180 m; eroteltu väylä 798167183 noin 156,821 m. Aiemmat pihareittitapaukset 1209361514 ja 1272508397 ovat edelleen poissa tuloksista.

Kuntalaskenta kesti 153,627 sekuntia. Lähteet ja muut säännöt ovat [version 1.4.0](oulu-v1.4.0.md) mukaiset. Parametrit tallennetaan tuloksen `network_policy`-kenttään sekä GeoPackagen `laskentatiedot`-taulun laskentatulokseen.

Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään riveittäin samaan tiedostoon tasojen nimet säilyttäen. Edellinen paketti säilyy tiedostossa `data/exports/oulu_analyysi_v1_4.gpkg` ja lähtötulokset hakemistossa `data/results/v1.4.0/`.
