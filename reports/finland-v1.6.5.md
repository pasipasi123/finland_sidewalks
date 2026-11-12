# Koko Suomi · menetelmä 1.6.5

Valmistunut 12.11.2026. Aineisto kattaa kaikki **308 kuntaa** Manner-Suomessa ja Ahvenanmaalla. Näistä 302 laskettiin uutena yhteenvetoajona; kuuden jo karttatarkistetun kaupungin muuttumattomien tulosten uudelleenkäyttö varmennettiin. Säännöt ovat samat koko maassa.

## Aineistot ja kattavuus

- OSM-otos: **5.11.2026 klo 21.23.02 UTC**, Geofabrikin `finland.osm.pbf`.
- PBF:n SHA256: `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`.
- Kuntarajat: saman OSM-otoksen `admin_level=8`-rajat ja kuntakoodit. Kaikki 308 koodia vastaavat väestöaineiston kuntia; geometrioiden kelvollisuus tarkistettiin.
- Väkiluvut: **31.12.2025**, [Tilastokeskus, StatFin 11ra](https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/), aluejako 1.1.2026. `data/population-finland.csv` sisältää kaikki 308 riviä. Summa **5 652 881** täsmää erikseen haettuun StatFinin koko maan lukuun.
- Menetelmä **1.6.5**, asukasmittarit **1.1.0**, välimuistin valintaversio 6, oletusetäisyys 20 m.
- Yhteinen laskentatarkiste: `3ea594ea3955815aa23f9a9a480f839567d2a8f0e7b48e6bb52f4157ccf072bb`.

Kuntien summat ja asukasmittarit laskettiin etukäteen. Selain vain hakee, järjestää ja muotoilee valmiita arvoja. Erillisiä kadunvarren viivoja ei sisällytetä verkkosivun aineistoon.

## Aineiston pituussummat

Summat kuvaavat menetelmän OSM:stä tunnistamia kadun- ja tienvarsien osuuksia koko kuntien alueilta, eivät koko kävely- tai pyörätieverkkoa.

| Luokka | km | Sisältyy jalkakäytäväsummaan |
| --- | ---: | --- |
| Ajoratatägeistä johdettu jalankulku | 142,47 | Kyllä |
| Erilliset footwayt | 3 478,80 | Kyllä |
| Pyörätiestä eroteltu jalankulku | 598,62 | Kyllä |
| **Jalkakäytävät yhteensä** | **4 219,89** | |
| Yhdistetyt jalankulku- ja pyöräväylät | 9 599,76 | Ei |
| Erottelultaan tuntemattomat pyöräväylät | 3 393,90 | Ei |

34 kunnan jalkakäytävätulos on nolla. Se tarkoittaa, ettei menetelmä tunnistanut kyseistä luokkaa lähdeaineistosta; fyysistä puuttumista ei voi päätellä siitä. Kartoituksen kattavuus, tagit, reitistön tulkinta ja kokonaisen kunnan väestö vaikuttavat vertailuun. Pituus ei mittaa keskustan käveltävyyttä, väylien leveyttä, esteettömyyttä tai laatua. Kuuden kaupungin karttatarkistukset eivät korvaa valtakunnallista maastovarmennusta.

## Tulostiedostot ja verkkosivu

- Paikalliset tulokset: `data/results/national/<koodi>.json`, yhteensä 308 JSON-tiedostoa. Uusille kunnille ei tuotettu osuusgeometrioita tai GeoPackageja.
- Julkaistava taulukko: `web/data/municipalities.json`, **145 726 tavua**, ja `web/data/municipalities.csv`, **61 920 tavua**. Yhteiset lähdetiedot ovat JSONin juuressa; kuntarivien geometriat on poistettu.
- [GitHub Pages -sivu](https://pasipasi123.github.io/finland_sidewalks/): oletuksena jalkakäytävät; lisäksi yhdistetyt, erotellut ja erottelultaan tuntemattomat. Haku kunnan nimellä ja kuntakoodilla, kaikki keskeiset sarakkeet lajiteltavissa molempiin suuntiin, suomi ja englanti, CSV/JSON-lataus sekä laskentasäännöt ja perustelu oman jalankulkutilan tarkastelulle.
- OSM-pohjainen tietokanta: ODbL 1.0, © OpenStreetMap contributors. Väkiluvut: Tilastokeskus, CC BY 4.0.

## Varmennus

Kattavuus, kuntakoodien yksikäsitteisyys, väkilukujen vastaavuus lähde-CSV:hen, luokkasummat, asukaskohtaisten lukujen kaavat ja CSV:n rivimäärä tarkistettiin. Kuuden uudelleenkäytetyn kaupungin kilometrit, kokonaissummat ja väkiluvut säilyivät täsmälleen ennallaan. Kaikilla kunnilla on sama laskentatarkiste ja menetelmäversio.

Laskennan 73 Python-testin kokonaisuus ja kahdeksan selainlogiikan Node-testiä läpäistiin. Testit kattavat myös yhteenvetotilan ja auditointitilan pituuksien vastaavuuden, vanhan menetelmäversion julkaisukiellon, keskeneräisen kattavuuden hylkäämisen, pilkkuhaun, haussa säilyvät sijat, tasatulokset ja kokoluokkien rajat. Selaimessa tarkistettiin suomi/englanti, kuntahaku, väylätyypit, lajittelu, tyhjän haun tulos, näppäimistökäyttö ja puhelinasettelu. Julkaisutyönkulku tarkistaa 308 kunnan aineiston uudelleen ennen Pages-julkaisua.

Laskenta- ja julkaisukomennot: [README](../README.md#valtakunnallinen-taulukkoaineisto). Taulukon toiminta ja GitHub Pages: [web/README](../web/README.md). Geometrisen korjauksen tausta: [kuuden kaupungin menetelmä 1.6.5](six-cities-v1.6.5.md).
