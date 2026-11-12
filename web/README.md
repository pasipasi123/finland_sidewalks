# Jalkakäytäväatlas: taulukkosivu

Komennot ajetaan projektin juuresta.

## Esikatselu

Node.js 20+:

```powershell
node scripts/serve.mjs
```

Avaa http://127.0.0.1:5174 (portin voi vaihtaa ympäristömuuttujalla `PORT`). Ei npm-riippuvuuksia tai build-vaihetta. Selain tarvitsee HTTP-palvelimen; `file://` ei riitä JSON-hakuun. Sivu käyttää järjestelmäfontteja eikä lataa kolmannen osapuolen skriptejä, fontteja tai analytiikkaa.

Jos npm on asennettu, myös `npm run dev` toimii.

## Toiminnot

- Suomi ja englanti; kielen voi vaihtaa sivun yläreunasta.
- Jalkakäytävät oletuksena. Muut välilehdet: yhdistetyt, erotellut ja erottelultaan tuntemattomat kadunvarsien jalankulku- ja pyöräväylät.
- Haku kunnan nimellä tai kuntakoodilla; useita kuntia voi hakea pilkuilla, esimerkiksi `oulu, vantaa`. Kirjainkoko ja tarkkeet eivät estä hakua. Aineistossa olevat vaihtoehtoiset kuntanimet huomioidaan.
- Nimen, kilometrien, metrien/asukas ja väkiluvun lajittelu molempiin suuntiin otsikkoa napsauttamalla. Oletus: metriä/asukas laskevasti.
- Ensimmäinen sarake on sija valitussa lajittelussa koko vertailuryhmän kesken. Nimihaku säilyttää tämän sijan. Tasatulokset jakavat sijan (1, 1, 3).
- Vertailuryhmä: kaikki kunnat tai väkiluvun mukaan suuret (vähintään 100 000), keskisuuret (20 000–99 999) ja pienet (alle 20 000). Sijat lasketaan valitun ryhmän sisällä. Luokkarajat näkyvät valikossa.
- Hakua, kieltä, väylätyyppiä ja lajittelua vastaavan näkymän voi jakaa osoiteriviltä. Kielivalinta säilyy myös selaimessa.
- Välilehdissä toimivat nuolinäppäimet ja Home/End; taulukon otsikoissa on lajittelun ruudunlukijatiedot. Kapealla näytöllä taulukkoa voi vierittää sivusuunnassa.
- CSV- ja JSON-aineiston lataus, laskentasäännöt, rajoitteet ja lähteistetty perustelu jalankulun oman tilan tarkastelulle.

Selain ei laske väyläpituuksia tai asukaskohtaisia tunnuslukuja. Se vain hakee, muotoilee ja järjestää valmiit tulokset. Eroteltu jalankulku sisältyy jo jalkakäytäväsummaan.

## Aineiston tuottaminen

Projektin juuresta:

```powershell
./.venv/Scripts/python.exe scripts/fetch-population.py --codes all --year 2025 --output data/population-finland.csv
./.venv/Scripts/python.exe -m pipeline.cli compute --population data/population-finland.csv --output data/results/national --summary-only
./.venv/Scripts/python.exe -m pipeline.cli publish --results data/results/national --table-only --expected-count 308 --names-from data/raw/population-finland-2025.json --output web/data/municipalities.json --csv-output web/data/municipalities.csv
```

`--summary-only` tuottaa vain kuntayhteenvedot. `--expected-count 308` estää osittaisen ajon julkaisun. Tiivis JSON jättää geometriat pois ja säilyttää yhteiset lähdetiedot kerran tiedoston juuressa. Kuntien väkiluvut ovat 31.12.2025; StatFinin aluejako on 1.1.2026. Kuntakoodit on sovitettu OSM-rajoihin.

## Tarkistukset ja GitHub Pages

```powershell
node --test tests/web.test.mjs
node scripts/validate-web-data.mjs
```

GitHub Actionsin `Publish dashboard` testaa taulukon logiikan ja tarkistaa, että mukana on 308 yksilöllistä kuntaa, kaikki väylätyypit ja valmiit asukaskohtaiset luvut. Sen jälkeen se julkaisee `web/`-hakemiston GitHub Pagesiin. Työnkulku käynnistyy main-haaran web-muutoksista tai käsin. Repon Pages-lähteeksi valitaan GitHub Actions.

Julkaisuosoite: https://pasipasi123.github.io/finland_sidewalks/

OSM-pohjainen tietokanta: ODbL 1.0, © OpenStreetMap contributors. Väkiluvut: Tilastokeskus, StatFin 11ra, CC BY 4.0. Muunnos: kuntakohtaiset pituudet ja asukaskohtaiset tunnusluvut.
