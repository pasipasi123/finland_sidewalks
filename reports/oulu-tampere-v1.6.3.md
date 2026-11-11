# Oulu ja Tampere 1.6.3 · pysäkkilaiturin yhteys ei peitä jalkakäytävää

Päivitetty 11.11.2026 käyttäjän kohteen 553272448 ja vastakkaisen puolen tilanteen perusteella. Oulun tulos säilyy **84,214169 km / 0,3872 m/asukas**. Tampereen tulos on **335,743281 km / 1,2750 m/asukas**; edellinen 1.6.2 tuotti 336,000706 km.

## Havainto samasta OSM-otoksesta

Jalkakäytävän 553272448 noin 42 m osuus jäi pois, koska lähempänä ajorataa oleva 1538890560 tulkittiin kilpailevaksi rinnakkaiseksi footwayksi. Vastakkaisella puolella 1538890557 peitti vastaavasti jalkakäytävää 67295429.

Lähempien viivojen omissa tägeissä on vain `highway=footway`, joten pelkät viivat eivät kerro pysäkkikäytöstä. PBF:stä löytyvät kuitenkin suljetut alueet **Tuulensuu A (849224795)** ja **Tuulensuu B (849224794)**, joilla on `public_transport=platform` ja `railway=platform`. Viivat eivät kulje polygonien sisällä, vaan päättyvät täsmälleen niiden reunaan. Päättymiskohdassa ei ole muuta jalankulkujatkoa. Toinen pää liittyy varsinaiseen jalkakäytävään. Tämä tunnistaa laiturille johtavan yhteyden, ei kadun varressa jatkuvaa jalkakäytävää.

## Rajattu sääntö

- Enintään 100 m tavallinen footway, joka ei ole merkitty `footway=sidewalk` tai `is_sidepath=yes`.
- Umpinainen jalankulkuverkon pää enintään 0,25 m päässä kartoitetusta laiturialueesta tai sen sisällä.
- Toinen pää vähintään 3 m alueen ulkopuolella, tai vähintään 80 % viivasta alueella.
- Samat layer/bridge/tunnel-tiedot ja sama level kuin laiturialueella.

Tällainen laituriyhteys jätetään pois jalkakäytäväpituudesta, rinnakkaisten reittien varjostuksesta ja kaarretäydennysten tuesta. Pelkkä pysäkkipiste, laiturin läheisyys tai laiturin ohi jatkuva reitti ei riitä. Eksplisiittisesti jalkakäytäväksi merkitty reitti säilyy muiden sääntöjen tarkastelussa.

## Tulokset ja katselu

| OSM-way | Versio 1.6.2, m | Nyt, m | Tulkinta |
| --- | ---: | ---: | --- |
| 553272448 | 65,073 | 106,918 | Varsinainen jalkakäytävä kokonaan mukana |
| 67295429 | 64,979 | 113,581 | Vastakkaisen puolen jalkakäytävä kokonaan mukana |
| 1538890560 | 41,868 | 0 | Tuulensuu A:n laituriyhteys |
| 1538890557 | 41,904 | 0 | Tuulensuu B:n laituriyhteys |
| 1144968837 | 123,094 | 138,966 | Insinöörinkadun aiempi peittävä 915815452 tunnistuu myös laituriyhteydeksi |

Millimetreihin pyöristettyjen osarivien summa voi poiketa alkuperäisestä geometriasta joitakin millimetrejä. 915815452 päättyy laiturialueeseen 773825265. Aiemmat bussikatu-, kaarre- ja Hämeenkadun korjaukset säilyvät [version 1.6.2](oulu-tampere-v1.6.2.md) mukaisina.

Lähdetasolla `hylkayssyy=pysakkilaiturin_yhteys` ja uusi `pysakkilaituri_osm` kertovat poissulun ja alueen OSM-tunnisteen. Alkuperäisiä footway-tägejä ei muuteta. Oulun ja Tampereen GeoPackage-rivit päivitetään samoihin tiedostoihin, ja versio 1.6.2 säilyy varmuuskopioissa. Laiturialueet voi lisätä QGISiin tiedostoista `data/results/837.platforms.geojson` ja `564.platforms.geojson`.

**60 testiä läpäisty.** Mukana ovat Tuulensuun molemmat puolet sekä vastatapaukset, joissa reitti jatkuu alueen ohi, osuu vain lähelle tai on eri tasolla. Koko Oulun ajossa laituriyhteyksiksi luokittui 5 waytä ja Tampereella 126. Oulun hyväksytty pituus ei muuttunut. Kuntalaskennat kestivät 156,836 ja 255,004 sekuntia.

## Lähtötiedot ja toistaminen

Sama Geofabrikin PBF 5.11.2026 ja samat vuoden 2025 lopun väestöt kuin aiemmin. SHA256 `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`. Paikalliseen välimuistiin lisättiin 4 933 kelvollista suljettuna OSM-waynä kartoitettua laiturialuetta erillisiin `platforms`- ja `platform_bounds`-tauluihin. Valintaversio on 6. Avoimet laituriviivat ja pelkät pysäkkipisteet eivät tuota aluetulkintaa.

```powershell
./.venv/Scripts/python.exe -m scripts.extend_platform_context
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 564,837 --population data/population.csv
```

Uusi `prepare` sisältää alueiden keruun suoraan. Pysäkkipolygonien kattavuus ja reittien päättymistä kuvaavat OSM-yhteydet voivat vaihdella; sääntö ei luokittele jokaista pysäkin läheistä kävelyviivaa laituriyhteydeksi.
