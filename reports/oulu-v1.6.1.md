# Oulu 1.6.1 · ylitysyhteydet lyhyiden linkkien tukena

Päivitetty 9.11.2026. Tulos on **82,861610 km** ja **0,3810 m/asukas**. [Versio 1.6.0](oulu-v1.6.0.md) tuotti 82,878344 km. Uusi tulos käyttää samaa Geofabrikin Suomen PBF-otosta ja samoja pääsääntöjä; välimuistiin lisättiin ylitysten yhteystiedot.

## Korjaus

Käyttäjän kohteet **1201123080** (noin 13,241 m) ja **1228692226** (noin 8,427 m) jäivät alle 15 metrin vähimmäisjakson. Niiden toisessa päässä on hyväksytty jalkakäytävä ja toisessa alkuperäisessä yhteisessä OSM-solmussa `footway=crossing`: vastaavasti **1201123079** ja **1228692227**. Ylitysviivat puuttuivat vanhan välimuistin yhteystiedoista.

Nyt enintään 40 m linkin toisen pään tueksi kelpaa hyväksytyn jalkakäytävän lisäksi jalankulkuun tarkoitettu ylitys. Ylitys voi olla myös ajoristeysten välissä; se itsessään osoittaa yhteyden katuverkkoon. Pinta-, pääsy-, taso-, kokonaisreitti- ja enintään 30 m etäisyysrajaukset säilyvät. Pelkkä viivojen läheisyys tai vapaaksi jäävä pää ei riitä.

Varmennetun linkin kanssa yhteisen OSM-solmun jakavaa jalkakäytävää ei käsitellä liittymäkaarteen rinnakkaisena kilpailijana. Tämä korjaa 1201123080:n liitoskohdan 496915707:ään. Muut lähempänä ajorataa olevat rinnakkaiset viivat voivat edelleen estää linkin.

Ylitykset säilytetään lähtötasolla luokkana `crossing_context`, `hylkayssyy=ylitys_konteksti`, `mukaan_m=0`. Niiden pituutta ei lasketa jalkakäytäviin. Sama koskee aiemmasta pyöräväyläluokituksesta erotettuja `cycleway=crossing`-viivoja. Kokonaissumma laskee hieman palautetuista footway-linkeistä huolimatta: footway-summa kasvaa 118,332 m ja erotellun jalankulun summa pienenee ylitysten poiston vuoksi 135,066 m.

## Tulos ja tarkistus

| Laskettava osuus | Kilometriä |
| --- | ---: |
| Ajoradan sidewalk-tägit | 2,825982 |
| Erilliset footwayt | 66,423147 |
| Eroteltu jalankulku ja pyöräily | 13,612481 |
| **Yhteensä** | **82,861610** |

Koko Oulun ajossa 1201123080 on mukana noin 13,240 m ja 1228692226 noin 8,426 m. Millimetreihin pyöristettyjen osarivien summa voi poiketa alkuperäisen viivan pituudesta muutamia millimetrejä. Niiden ylitysviivat eivät sisälly summaan. Aiemmat oikeiksi varmistetut risteyskohteet 1201123082, 1201123081, 496915707 ja 58521570 säilyvät, ja hylätyt pihareitit 970197335, 133019393, 130751536, 1206626750 ja 115094353 ovat edelleen poissa.

**52 testiä läpäisty.** Mukana ovat todelliset Oulun liitoskohdat, ylitykseen liittyvä linkki myös risteysten välissä, pelkän läheisyyden hylkääminen ja ylitysviivojen pitäminen poissa summasta. Koko Oulun ajo kesti 166,120 sekuntia, lähtöväyliä oli 31 351 ja auditointirivejä 128 044.

Väestö on 217 469, viitepäivä 31.12.2025, [StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/). OSM-päiväys on 2026-11-05T21:23:02Z ja PBF:n SHA256 `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`. Valintaversio on 4. `scripts.extend_crossing_context` lisäsi samalla otoksella koko Suomen välimuistiin 15 741 puuttuvaa ylitysviivaa ilman koko maan solmuindeksin rakentamista.

Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään riveittäin; edellinen katseluaineisto säilyy tiedostossa `data/exports/oulu_analyysi_v1_6.gpkg` ja laskentatulokset hakemistossa `data/results/v1.6.0/`. Samoilla säännöillä laskettu [Tampereen ensimmäinen aineisto](tampere-v1.6.1.md) on paikallisesti `data/exports/tampere_analyysi.gpkg`. Kuntien tulokset ovat karttatarkistusta varten; Tampereen tulosta ei ole vielä varmistettu käyttäjän paikallistuntemuksella.
