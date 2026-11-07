# Oulu 1.2.0 · puuttuvan pinnan asfalttioletus

Päivitetty 7.11.2026. Käyttäjän tarkistuskohteista 36729304 ja 89930891 puuttuu OSM-pintatieto, ja ne olivat jääneet pois version 1.1.0 liian tiukassa pintasuodatuksessa. **Puuttuva pinta oletetaan nyt asfaltiksi**, kuten käyttäjä täsmensi. Tunnetut `compacted`-, sora- ja muut hyväksymättömät pinnat jäävät edelleen pois. Muut 1.1.0:n geometria- ja ajorataviitteiden säännöt säilyvät.

## Tulos

- Yhteensä **94.659870 km**, **0.4353 m/asukas**.
- Erilliset footwayt 77.946422 km.
- Pyörätiestä eroteltu jalankulku 13.867134 km.
- Ajoratatägeistä, kaksoislaskentaa vähennettynä 2.846314 km.
- Mukaan lasketuista erillisistä väylistä **24.402973 km** perustuu puuttuvan pintatiedon asfalttioletukseen. Tämä on osajoukko kokonaismäärästä.
- Yhdistetyt väylät 401.710219 km ja erottelu tuntematon 93.022272 km eivät sisälly summaan.

Lähteet ovat samat kuin [edellisessä ajossa](oulu-v1.1.0.md): Geofabrik Finland 2026-11-05T21:23:02Z ja Tilastokeskuksen väestö 217 469 / 31.12.2025.

## Tarkistuskohteet

| OSM-way | Mukaan laskettu pituus, m |
| --- | ---: |
| 36729304 | 88.579 |
| 89930891 | 526.913 |
| 47110040 | 204.623 |
| 50118180 | 85.403 |
| 50118181 | 105.344 |

36729304:n koko OSM-way on noin 101 m. Uudessa aineistossa hyväksytty pituus on pienempi, koska myös 20 asteen suuntaero ja 15 metrin yhtenäisen jakson vähimmäispituus vaikuttavat tulokseen. 89930891:n noin 527 metrin katujakso tunnistuu kokonaan pyöristyksen tarkkuudella.

## GeoPackage ja oletuksen näkyvyys

Sama `data/exports/oulu_analyysi.gpkg` päivitetään transaktiona tasojen nimiä ja tiedostoa vaihtamatta. Edellinen versio säilytetään tiedostossa `data/exports/oulu_analyysi_v1_1.gpkg` ja vanhat laskentatulokset hakemistossa `data/results/v1.1.0/`.

- `surface` ja `footway_surface` ovat edelleen alkuperäisiä OSM-arvoja. Puuttuvia arvoja ei muuteta asfalttitiedoksi.
- `pinnan_tila=oletus_asfaltti` ilmaisee laskennassa käytetyn oletuksen; `pinnan_tila=osm_tieto` tarkoittaa OSM:ään kirjattua pintaa.
- `laskenta_pinta=asphalt` näyttää käytetyn pintaoletuksen.
- `hylkayssyy` näyttää mahdollisen muun poissulun. Pintatiedon puuttuminen ei enää ole poissulkusyy.
- Ajoradoilla näitä pintakenttiä ei tulkita erillisen jalkakäytävän pinnaksi (`pinnan_tila=ei_sovelleta`).

15 automaattista testiä kattavat nyt myös puuttuvan pinnan hyväksymisen asfalttioletuksella, alkuperäisen pintatiedon säilymisen, kompaktipinnan poissulun sekä molemmat uudet käyttäjän esimerkit. Tulos on edelleen OSM-pohjainen heuristinen arvio.
