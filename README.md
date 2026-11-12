# Jalkakäytäväatlas

Suomen kuntien **kadunvarsien jalkakäytävät sekä yhdistetyt ja erotellut jalankulku- ja pyöräväylät kilometreinä ja metreinä asukasta kohti**. Python-laskenta käyttää paikallista OSM-PBF:ää ja kuntakohtaista SQLite-välimuistia. Verkkosivulle viedään valmiit JSON- ja CSV-yhteenvedot. GeoPackage-vienti on erillinen mahdollisuus karttatarkistuksiin. Overpassia tai tietokantapalvelinta ei tarvita.

**Nykytila 12.11.2026:** menetelmä **1.6.5**, kaikki **308 kuntaa** käsitelty samalla OSM-otoksella ja samoilla säännöillä. Väestön viitepäivä on kaikissa 31.12.2025. Asukasmittarien versio **1.1.0** sisältää myös erottelultaan tuntemattomat väylät. Uusia katselupaketteja ei tehty valtakunnallisessa ajossa.

**[Jalkakäytäväatlas / Sidewalk Atlas · GitHub Pages](https://pasipasi123.github.io/finland_sidewalks/)** — pilkuilla useita kuntia hakeva haku, lajittelussa määräytyvät vertailusijat, väkiluvun kokoluokat, neljä väylätyyppiä ja suomen- sekä englanninkielinen käyttöliittymä. [Valtakunnallisen ajon raportti](reports/finland-v1.6.5.md).

Ensimmäisen karttatarkistusjoukon kuusi kaupunkia:

| Kunta | Jalkakäytävät, km | JK, m/asukas | Yhdistetty, m/asukas | Eroteltu, m/asukas |
| --- | ---: | ---: | ---: | ---: |
| Helsinki | 1 185,959 | 1,7079 | 0,2712 | 0,2976 |
| Espoo | 265,476 | 0,8151 | 1,4902 | 0,1130 |
| Tampere | 333,974 | 1,2682 | 1,1238 | 0,2442 |
| Vantaa | 173,463 | 0,6857 | 1,7562 | 0,0719 |
| Oulu | 82,544 | 0,3796 | 1,8421 | 0,0626 |
| Turku | 365,698 | 1,7445 | 1,0486 | 0,2434 |

Erotellun väylän jalankulku sisältyy myös jalkakäytävien summaan. Yhdistetyt ja erottelultaan tuntemattomat eivät sisälly siihen. Kaikki luvut koskevat kadunvarsia, eivät koko pyörätieverkkoa. Näistä kuudesta Oulussa on vähiten jalkakäytäviä ja eniten yhdistettyä väylää asukasta kohti.

[Lähteet, laskentaluokat ja katseluaineistot: kuuden kaupungin raportti](reports/six-cities-v1.6.5.md).

Kokonaisreitin rakenne, määränpäärajoitus ja ajoradan sidewalk-tieto karsivat pihareittien katuosumia. Lyhyet linkit voivat saada tukea hyväksytyistä jalkakäytävistä ja ylityksistä; itse ylityspituuksia ei lasketa. Living street -varret on rajattu pois, ja puuttuva pinta oletetaan asfaltiksi. Välimuistissa on 710 038 väylää, 308 kuntarajaa ja erillisenä kontekstina 4 933 laiturialuetta. Tampereen tarkistukset korjasivat bussikatujen valintaa, risteyskaarreaukkoja ja laiturille päättyvien footwayiden aiheuttamaa varsinaisen jalkakäytävän varjostusta. Luvut koskevat koko kuntia, eivät keskustoja.

## Laskennan käyttöönotto Windowsissa

### Valtakunnallinen taulukkoaineisto

Verkkosivu käyttää kuntakohtaisia yhteenvetoja hakemistosta `data/results/national`. Koko maan ajossa ei tarvita uusia katselupaketteja:

```powershell
./.venv/Scripts/python.exe scripts/fetch-population.py --codes all --year 2025 --output data/population-finland.csv
./.venv/Scripts/python.exe -m pipeline.cli compute --population data/population-finland.csv --output data/results/national --summary-only
./.venv/Scripts/python.exe -m pipeline.cli publish --results data/results/national --table-only --expected-count 308 --names-from data/raw/population-finland-2025.json --output web/data/municipalities.json --csv-output web/data/municipalities.csv
node --test tests/web.test.mjs
node scripts/validate-web-data.mjs
```

Jokainen kunta tallentuu heti valmistuessaan; kesken jäänyttä ajoa voi jatkaa samalla komennolla. `--summary-only` käyttää samoja laskentasääntöjä ja jättää tarkistusgeometrioiden viennin pois. Kuuden jo tarkistetun kaupungin tulokset voitiin käyttää uudelleen `python -m scripts.seed-national` -komennolla: se tarkistaa, että niiden menetelmä, kuntaraja, väkiluku, lähteet ja aiempi laskentatarkiste täsmäävät. Vanhoja tuloksia tai niiden GPKG-tiedostoja ei muuteta.

Tiivis julkaisu sisältää valmiit kilometrit ja metriä/asukas-luvut jalkakäytäville, yhdistetyille, erotelluille ja erottelultaan tuntemattomille väylille. Kuntageometrioita ei siirretä taulukkosivulle. Julkaisun oletus on nyt valtakunnallinen taulukko: `data/results/national`, 308 kunnan kattavuusvaatimus ja CSV JSONin rinnalle. `--with-map` tuottaa tarvittaessa laajan koosteen erilliseen jatkokäyttöön.

GitHub Pages julkaisee `web/`-hakemiston. Työnkulku tarkistaa kaikki 308 kuntakoodia ja väkilukua lähde-CSV:stä sekä valmiiden asukasmittarien vastaavuuden ennen julkaisua. Suomen- ja englanninkielisen sivun käyttö- ja julkaisuohje on [web/README.md](web/README.md).

### Python-ympäristö

Python 3.11+:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Tämän työympäristön varmennetut versiot löytyvät tiedostosta `requirements-lock.txt`.

Lähtöaineistot voi hakea myös mukana olevilla apuskripteillä:

```powershell
./.venv/Scripts/python.exe scripts/fetch-finland.py
./.venv/Scripts/python.exe scripts/fetch-population.py --codes 564
```

PBF-lataus tarkistaa Geofabrikin MD5-summan ja lukee otoksen OSM-päiväyksen tiedoston otsakkeesta. Tiedot tallentuvat `data/raw/finland-source.json`-tiedostoon. Osittainen lataus säilytetään `.part`-tiedostossa jatkamista varten. Väestöskripti hakee oletuksena viimeisimmän vuositiedon StatFin-taulukosta 11ra, tallentaa raakavastauksen lähdetietoineen ja päivittää kuntarivin `data/population.csv`-tiedostoon. Vuoden voi kiinnittää esimerkiksi `--year 2025`.

### 1. Lataa OSM kerran

Käytä [Geofabrikin Suomen PBF-otosta](https://download.geofabrik.de/europe/finland.html), älä shapefile-pakettia: laskenta tarvitsee alkuperäiset OSM-tägit ja kuntarajarelaatiot. Lataus on satoja megatavuja. Varaa lisäksi useita gigatavuja tilaa solmuindeksille, välimuistille ja tarkistusgeometrioille.

```powershell
New-Item -ItemType Directory -Force data/raw
Invoke-WebRequest 'https://download.geofabrik.de/europe/finland-latest.osm.pbf' -OutFile data/raw/finland.osm.pbf
```

Merkitse alla olevaan komentoon **ladatun otoksen oikea OSM-päiväys** Geofabrikin metatiedoista. Päiväystä ei päätellä latausajasta. Säilytä alkuperäinen PBF toistettavuutta varten.

### 2. Valmistele valtakunnallinen välimuisti kerran

```powershell
./.venv/Scripts/python.exe -m pipeline.cli prepare --pbf data/raw/finland.osm.pbf --osm-date YYYY-MM-DD
```

Tämä on ainoa pakollinen koko Suomen läpikäynti (Pyosmium voi lukea tiedoston useamman kerran relaatioiden kokoamiseksi). Se poimii käyttökelpoiset väylät SQLiteen, tekee R-tree-sijainti-indeksin ja kokoaa kuntarajat. Solmukoordinaattien indeksi on levyllä RAM-muistin säästämiseksi. SQLite ei vaadi erillistä palvelinta.

Rajat poimitaan ehdoilla `boundary=administrative`, `admin_level=8` ja kolminumeroinen `ref:FI` tai `ref`. **Tarkista kuntakoodit, rajojen kattavuus ja ajantasaisuus** tiedostosta `data/cache/municipalities.geojson`. Vaihtoehtoinen WGS84-GeoJSON käy `--boundaries`-valinnalla: FeatureCollection, jokaisen Polygon/MultiPolygon-featuren properties-kentissä `code` (kolminumeroinen merkkijono) ja `name`. Kuntarajat ja väestöluvut on sovitettava samaan kuntajakoon. OSM-kuntarajat eivät ole virallinen kuntajakolähde.

Windowsissa Pyosmium voi pitää `.nodes`-indeksin varattuna prosessin loppuun. Jos ohjelma ilmoittaa säilytetystä indeksistä, sen voi poistaa komennon päätyttyä. Uusi OSM-otos valmistellaan **uuteen välimuistitiedostoon**; vanhaa ei ylikirjoiteta.

Menetelmästä 1.6.1 alkaen ylitysviivat säilytetään yhteystietona (`crossing_context`), vaikka niiden pituutta ei lasketa jalkakäytäviin. Jos välimuistin `cache_selection_version` on 3, lisää puuttuvat ylitykset samalla alkuperäisellä PBF:llä:

```powershell
./.venv/Scripts/python.exe -m scripts.extend_crossing_context
```

Laajennus tarkistaa PBF:n SHA256-summan, lukee vain ylitysten tarvitsemat solmut muistiin ja päivittää valintaversion neloseen. Uusi `prepare` sisältää tämän suoraan. Aiemmat valintaversiot tarvitsevat ensin myös `scripts.extend_reference_roads`- ja `scripts.extend_walking_candidates`-laajennukset tai uuden valmistelun.

Menetelmä 1.6.2 korjaa myös `access=no` + `bus=yes` -ajoradat. Päivitä valintaversio 4 versioon 5 samalla alkuperäisellä PBF:llä:

```powershell
./.venv/Scripts/python.exe -m scripts.extend_bus_references
```

Tämä lisäsi nykyiseen koko Suomen otokseen 42 puuttuvaa fyysistä ajorataviitettä. Tavallisten tie- ja katuluokkien valikoima säilyy samana; bussiliikenteen salliva poikkeus estää väärän poissulun. Uusi `prepare` tekee myös tämän suoraan.

Menetelmä 1.6.3 tarvitsee lisäksi suljettuina OSM-wayhinä kartoitetut laiturialueet. Päivitä valintaversio 5 versioon 6:

```powershell
./.venv/Scripts/python.exe -m scripts.extend_platform_context
```

Samasta PBF:stä löytyi 4 933 kelvollista laituripolygonia. Ne tallentuvat erillisiin `platforms`- ja `platform_bounds`-tauluihin; alkuperäisten footwayiden tägejä ei muuteta. Uusi `prepare` sisältää myös tämän. Pelkkiä pysäkkipisteitä tai avoimia laituriviivoja ei tulkita laiturialueeksi.

### 3. Lisää oikea väestöaineisto

Vie esimerkiksi [Tilastokeskuksen](https://stat.fi/) kuntakohtaiset väestöluvut UTF-8 CSV:ksi `data/population.csv`. Sarakkeet:

```csv
code,population,date,source
```

Yksi rivi per laskettava kunta: kolminumeroinen kuntakoodi, positiivinen kokonaisluku, väestön viitepäivä ja täsmällinen lähde (taulukon tunniste tai URL). Erotin on pilkku. Asukaskohtainen mittari on `1000 * jalkakäytäväkilometrit / väestö`. Nollaa tai puuttuvaa väestöä ei esitetä asukaskohtaisena tuloksena. `data/population.example.csv` näyttää muodon **keksityllä testiarvolla**, jota ei pidä käyttää oikeaan laskentaan.

Kuntatuloksen `shared_m_per_resident` lasketaan vastaavasti luokasta `km.shared` ja `segregated_m_per_resident` luokasta `km.segregated`. Versio 1.1.0 lisää `unknown_m_per_resident`-kentän luokasta `km.unknown`. Yksikkö on m/asukas, tarkkuus neljä desimaalia. Luokittelu perustuu jalankulkuun tarkoitettujen pyöräväylien `segregated=no/yes`-tietoon; puuttuvaa erottelutietoa ei arvata kumpaankaan ryhmään. `metrics_version` kertoo johdettujen mittareiden version erillään geometrian `method_version`-versiosta.

### 4. Aloita yhdestä kunnasta

Oulun kuntakoodi on 564:

```powershell
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 564 --population data/population.csv
```

Useita kuntia: `--codes 564,091,837`. Ilman `--codes`-valintaa lasketaan kaikki raja-aineiston kunnat; tällöin kaikille tarvitaan väestörivi. Laskenta tapahtuu yksi kunta kerrallaan. Tulokset tallennetaan heti kunnittain; saman ajon voi käynnistää uudelleen, jolloin muuttumattomat tulokset ohitetaan. Muuttunut OSM-metadata, raja-aineisto, väestö-CSV, etäisyysraja tai menetelmäversio käynnistää uudelleenlaskennan. `--force` pakottaa laskennan.

Laskenta hakee SQLite-välimuistista vain kunnan rajauslaatikon ja puskurin väylät. Tarkat pituudet leikataan kunnan polygonilla, myös kun väylä ylittää rajan. Tiheiden kuntien muisti- ja laskentatarve voi silti olla huomattava; koko maan geometrioita ei ladata kerralla muistiin. Suurta kuntaluetteloa voi jatkaa toisella koneella kopioimalla PBF:n tai valmistellun välimuistin, rajat, väestöaineiston ja tuloshakemiston.

Tulokset:

- `data/results/564.json`: summat, väestöluku, lähteet, laskentaversio ja lähtötietojen tarkiste.
- `data/results/564.segments.geojson`: laskettujen ja poissuljettujen osuuksien tarkistusgeometriat OSM-way-tunnuksineen; avattavissa esim. QGISissä. Ajorataan merkityt jalkakäytävät esitetään ajoradan keskilinjalla ja puoli kertoo laskennan kohteen.

### 5. Vie valmiit tiedot dashboardiin

```powershell
./.venv/Scripts/python.exe -m pipeline.cli publish
```

Komento päivittää `web/data/municipalities.json`- ja `.csv`-aineiston valtakunnallisista tuloksista. Oletuksena vaaditaan kaikki 308 kuntaa ja tuotetaan tiivis taulukko ilman geometrioita. Selain vain suodattaa, järjestää ja muotoilee valmiita arvoja. Eri lähtöaineistoilla laskettuja tuloksia ei voi yhdistää vahingossa: julkaisu tarkistaa yhteisen lähtötietojen tarkisteen ja menetelmäversion. Sijoitus lasketaan vain mukana olevista kunnista. Laskematon kunta ei tarkoita nollaa. Suppeampaa erillistä koostetta varten anna `--results` ja `--expected-count`; `--with-map` lisää EPSG:3067-karttapolut laajaan JSONiin.

Yhdistettyjen ja eroteltujen asukasmittareiden sijoitukset ovat `rank_shared_m_per_resident` ja `rank_segregated_m_per_resident` (suurin saa sijoituksen 1). Koosteen voi tehdä paikallisesti koskematta web-aineistoon: `--output data/results/municipalities.json`.

Vanhojen kuntatulosten asukasmittarit voi päivittää ilman geometrian uudelleenlaskentaa. Valitut olemassa olevat GeoPackaget päivitetään samassa tiedostossa, myös QGISin pitäessä niitä auki:

```powershell
./.venv/Scripts/python.exe -m pipeline.refresh_metrics --gpkg data/exports/oulu_analyysi.gpkg data/exports/tampere_analyysi.gpkg
./.venv/Scripts/python.exe -m pipeline.cli publish --results data/results --with-map --expected-count 6 --output data/results/municipalities.json
```

Ilman `--gpkg`-valintaa päivitetään vain kuntatulokset. GeoPackagen `kuntaraja` saa sarakkeet `yhdistetty_m_asukas` ja `eroteltu_m_asukas`; mittarit päivittyvät myös `laskentatiedot`-taulukon tulos-JSONiin. Komento tarkistaa paketin kunnan ja lähtötietojen vastaavuuden. Geometrioita, tulostasoja tai pituuksia ei muuteta. Uudet laskennat ja viennit sisältävät mittarit suoraan.


### Tarkastele paikallisessa GeoPackagessa

Oulun pilotin karttatarkistusta varten on tehty `data/exports/oulu_analyysi.gpkg` (EPSG:3067). Avaa se esimerkiksi QGISissä. Tiedosto sisältää omat tasot ajoratatägeistä lasketuille jalkakäytäville, erillisille jalkakäytäville, pyörätiestä erotelluille osuuksille, poissuljetuille yhdistetyille väylille ja tuntemattomalle erottelulle.

Tampereen vastaava aineisto on `data/exports/tampere_analyysi.gpkg`, samalla koordinaatistolla ja tasorakenteella. Laskenta ja vienti:

```powershell
./.venv/Scripts/python.exe -m pipeline.cli compute --codes 564,837 --population data/population.csv
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 837 --output data/exports/tampere_analyysi.gpkg
```

Vertailutasoilla `osm_ajoradat` ja `osm_jalankulku_pyora` ovat laskennan välimuistin lähtöväylät myös niiltä osin, joilla kadunvarsisuodatus ei tuottanut osumia. Ne on leikattu kunnan rajaan ja 30 metrin puskuriin (20 metrin laskentaetäisyydellä). Nämä eivät sisällä kaikkia OSM:n highway-luokkia tai ennen laskentaa tagisäännöillä hylättyjä väyliä. Mukana ovat lisäksi `kuntaraja` ja lähteet sekä tulkintaohjeet sisältävä `laskentatiedot`-taulukko.

Tulososuuksien `pituus_m` on laskettu pituus ja `osm_url` linkittää alkuperäiseen OSM-wayhin. Yleisimmät tägit ovat erillisissä sarakkeissa; kaikki lähtöväylän tägit ovat kentässä `tags_json`. Ajoratatägien geometria on **ajoradan keskilinja**, ei jalkakäytävän tarkka sijainti; `puoli` kertoo OSM-viivan suunnan mukaisen vasemman tai oikean puolen. Kummankin puolen osuudet voivat siksi piirtyä päällekkäin.

`osm_jalankulku_pyora` on yhteinen lähtöaineistotaso, ei luokitus yksittäisen viivan pyöräilyoikeudesta. `luokka` ja alkuperäiset `highway`/`bicycle`-tägit kertovat kohteen tyypin. `surface` ja `footway_surface` näyttävät alkuperäiset pintatiedot. Puuttuva pinta oletetaan asfaltiksi: `pinnan_tila=oletus_asfaltti` ja `laskenta_pinta=asphalt` näyttävät oletuksen erillään alkuperäisistä tägeistä. `hylkayssyy` näyttää esimerkiksi pehmeän/ei-hyväksytyn pinnan, `highway=path`-rajauksen tai liian lyhyen kadunvarsijakson. `footway=sidewalk` ei ole pakollinen eikä sen puuttuminen ole poissulkusyy.

Viennin voi toistaa uuteen tiedostoon:

```powershell
./.venv/Scripts/python.exe -m pipeline.export_gpkg --code 564 --output data/exports/oulu_analyysi_uusi.gpkg
```

Vienti ei muuta laskentatuloksia, yhdistä auditointirivejä tai yksinkertaista viivoja. Täsmälleen nollapituuteen romahtaneet geometriajäänteet, joiden kirjattu pituuskin on nolla, ohitetaan ja niiden määrä tallennetaan metatietoihin. GeoPackage on paikallinen tarkistusaineisto ja rajattu Gitin ulkopuolelle.

QGISissä jo auki olevan GeoPackagen rivit voi päivittää valmiista vientitiedostosta:

```powershell
./.venv/Scripts/python.exe -m pipeline.sync_gpkg --staged data/exports/oulu_analyysi_uusi.gpkg --target data/exports/oulu_analyysi.gpkg --backup data/exports/oulu_analyysi_edellinen.gpkg
```

Päivitys säilyttää tiedoston identiteetin, tasojen nimet, nykyiset tyylitaulut ja muut ylimääräiset taulut. Tulosrivit ja metatiedot vaihtuvat yhdessä SQLite-transaktiossa, ja paikkatietoindeksit päivittyvät. Uudet sarakkeet lisätään tasoille. Päivitä tämän jälkeen QGISin näkymä; uusien sarakkeiden näkeminen voi vaatia tason uudelleenlatauksen. Aktiivinen kirjoitustransaktio voi estää päivityksen; virheessä tapahtuma perutaan.

`publish` tässä tarkoittaa paikallisen käyttöliittymäaineiston muodostamista; se ei siirrä mitään verkkoon. Varsinainen web-käyttöliittymä on erillinen toteutus.

## Menetelmä v1.6.5

Kaikki pituudet ja etäisyydet lasketaan metreinä **ETRS-TM35FIN / EPSG:3067** -koordinaatistossa. Kuntarajan ulkopuoliset pituudet leikataan pois. Oletusetäisyys on **20 m ajoradan keskilinjasta**, muutettavissa `--distance 15` jne. Tämä on tutkimusparametri, ei OSM-standardin sääntö. Vertaa esimerkiksi 10 / 15 / 20 / 25 metrin ajoja erillisissä tuloshakemistoissa ennen johtopäätöksiä.

| Tapaus | Laskenta |
| --- | --- |
| Ajoradan `sidewalk=left` / `right` | Pituus kerran |
| Ajoradan `sidewalk=both` | Pituus kaksi kertaa |
| `sidewalk:left/right/both=yes` | Vastaava puoli mukaan; puolikohtainen tägi ohittaa yleisen |
| `sidewalk=separate`, `no`, puuttuva tai epäselvä `yes` | Ei ajoratapituutta; `yes` ei kerro puolten määrää |
| `highway=footway` | Sallittu kova pinta tai pintatiedon puuttuessa asfalttioletus, etäisyys enintään 20 m, suuntaero enintään 20°, yhtenäinen hyväksytty jakso vähintään 15 m |
| `footway=sidewalk` | Lisätieto, jonka puuttuminen ei vaikuta hyväksyntään; sama geometria- ja pintasuodatus |
| `cycleway` tai footway, jolla `bicycle=designated` | Pyörätie vaatii `foot=designated`; footway sisältää jo jalankulun tarkoituksen. Molemmille `segregated=yes` ja sallittu kova pinta tai asfalttioletus |
| `highway=path` | Tässä analyysissä pois; OSM:n yleinen path-tägi ei kuitenkaan itsessään tarkoita pehmeää tai metsän polkua |
| Edellinen + `segregated=no` | Oma poissuljettujen yhdistettyjen väylien summa |
| Edellinen, erottelutieto puuttuu tai muu arvo | Oma tuntemattoman erottelun summa, ei mukaan |
| Suojatie (`footway=crossing`), `access_aisle`, aluegeometria, `access/foot=private/no` | Pois |
| Jalankulku vain määränpäähän: `foot=destination` tai `access=destination` ilman ohittavaa `foot`-tägiä | Pois summasta ja rinnakkaisreittien estäjistä; säilyy lähtötasolla ja verkkokontekstissa |

Ajotien luokat: primary, secondary, tertiary, unclassified, residential sekä primary/secondary/tertiary_link. Pihakadut (`living_street`), huoltotiet (`service`), ajourat, moottoritiet ja trunk-luokka eivät kuulu laskentaan. Living street säilytetään sijaintikontekstina, jotta sen footway ei tulisi mukaan toisen lähellä olevan tavallisen kadun kautta. **Ajoradan `foot=no` ei estä sen käyttämistä erillisen jalkakäytävän sijaintiviitteenä.** `access=no`-ajorata hyväksytään sijaintiviitteeksi, jos sillä on salliva kulkumuotokohtainen poikkeus esimerkiksi busseille, pyörille tai kiinteistölle ajoon. `access=private`-ajorata jää pois. Säännöt ovat tiedostossa `pipeline/rules.py`.

`destination` tarkoittaa kulkua vain väylän varrella olevaan määränpäähän, ei tiettyä väylätyyppiä. Erillisellä jalankulkuväylällä se toimii tässä analyysissä poissulkuehtona. Tarkempi `foot`-tägi ohittaa yleisen `access`-arvon: esimerkiksi `access=destination` + `foot=yes/designated/permissive/official` säilyy muiden ehtojen tarkastelussa. `foot=destination` sulkee pois myös silloin, kun `access=yes`. `motor_vehicle=destination` ei rajoita jalankulkua, eikä ajoradan `access=destination` poista sen jalkakäytäviä. Lähtötason hylkäyssyy on `jalankulku_vain_maaranpaahan`. Perusta: [OSM destination](https://wiki.openstreetmap.org/wiki/Tag:access%3Ddestination) ja [access-tägien hierarkia](https://wiki.openstreetmap.org/wiki/Key:access).

Jos käytössä on alkuperäinen 1.0-välimuisti, päivitä puuttuvat ajorataviitteet kerran komennolla `python -m scripts.extend_reference_roads`. Skripti tarkistaa alkuperäisen PBF:n SHA-256-summan ja lisää vanhan valinnan vuoksi puuttuneet ajoradat samasta otoksesta; koko välimuistia ei tarvitse rakentaa uudelleen. Aja tämän jälkeen `python -m scripts.extend_walking_candidates`, joka lisää footwayt, joiden jalankulkutarkoitus sisältyy jo highway-tägiin mutta jotka jäivät aiemmin pois puuttuvan erillisen foot-tägin vuoksi. `compute` tarkistaa välimuistin valintaversion (nyt 3).

Erilliset viivat pilkotaan alkuperäisiä taitepisteitä kunnioittaen enintään 5 metrin paloiksi ja ajoradat enintään 25 metrin paloiksi. `layer`, `bridge` ja `tunnel` vastaavat toisiaan. Tavallisten footwayiden suuntaero on enintään 20° ja hyväksyttyjen viivojen yhtenäisen jakson vähimmäispituus 15 m; muut analyysin väyläluokat käyttävät edelleen 30° suuntaeroa. Pituus leikataan täsmällisesti ajoradan etäisyyspuskurin ja kuntarajan sisään. Poikittaiset osuudet ja lyhyet kiinteistöyhteyksien rinnakkaiset päät vähenevät. Koko OSM-wayn hyväksymisprosenttia ei vaadita: vain osa samasta waysta voi olla jalkakäytävää.

Erillisten mukaan otettavien jalankulkuväylien pintojen sallittu lista on `asphalt`, `paved`, `paving_stones`, `paving_stones:30`, `concrete`, `concrete:plates`, `concrete:lanes`, `sett`, `cobblestone`, `cobblestone:flattened`, `unhewn_cobblestone`, `bricks`, `tiles`. `footway:surface` ohittaa yleisen `surface`-tägin. Puuttuva pintatieto oletetaan asfaltiksi. `compacted`, sorat, maa-ainekset, puu ja muut pintatietoon merkityt sallittuun listaan kuulumattomat arvot jäävät pois mukaan otettavista erillisistä väylistä. Moniarvoisen `;`-listan jokaisen arvon on oltava sallittu. Asfalttioletus ei muuta OSM-tägejä eikä ole havainto todellisesta pintamateriaalista. Sen osuus lasketaan valmiiksi tuloksen `assumed_asphalt_km`-kenttään (erilliset mukaan otetut jalankulkuväylät). Yhdistettyjen ja erottelultaan tuntemattomien poissuljettuja vertailusummia ei rajata pinnan perusteella.

### Suuntauksen jatkuvuus

15 metrin vähimmäisjakso tarkoittaa myös suunnaltaan jatkuvaa jaksoa. Yli 45 asteen äkillinen suunnanmuutos katkaisee jakson ennen pituuden tarkistusta. Näin tontin mutkitteleva yhteys ei voi koota vähimmäispituutta vuorotellen kahden risteävän kadun suuntaisista lyhyistä pätkistä. Ehto koskee tavallisia footwayitä ja niiden fyysistä estekontekstia; loivasti kaartuva viiva säilyy jatkuvana. Aidon kadunkulman kaksi riittävän pitkää sivua voidaan hyväksyä erikseen. Sama sääntö tarkistetaan lähempien väylien takaa poistettujen osuuksien jälkeen.

`hylkayssyy=jyrkat_kaanteet_katkaisevat_jakson` kertoo tapauksesta, jossa yhtenäinen yhdistetty geometria olisi riittävän pitkä mutta sen suunnaltaan jatkuvat jaksot eivät ole. Käyttäjän kohde 1272508397 on tämän säännön regressiotestinä. Tämän lisäksi tarvitaan edelleen etäisyys-, kadunsuuntaisuus-, pinta- ja lähimmän kulkureitin ehdot; viivan muoto ei yksin todista sen hallinnollista käyttötarkoitusta.

### Sisäverkon satunnaiset katuosumat

Geometrioiden yhteisistä alkuperäisistä taitepisteistä muodostetaan jalankulkuverkko, tasotiedot erotellen. Koordinaatit yhdistetään millimetrin tarkkuudella; kyse on välimuistin geometrioista johdetusta verkosta. Yksittäisen OSM-wayn päissä seurataan haarautumattomia jatkoja myös seuraaviin wayhin.

Vahva sisäverkkoepäily hylätään, kun katuun osuvan reitin toinen pää liittyy haarautuvaan polkuverkkoon tai päättyy yli 25 m etäisyydellä kadusta ja toinen pää jää umpinaiseksi kadun lähelle keskellä risteysväliä. Myös molemmista päistään etäämpään sisäalueeseen liittyvä katuosuma hylätään. 25 m vastaa oletusetäisyyttä 20 m + sisäverkon marginaalia 5 m. Risteyksen tai kadun päätepisteen 25 m lähiympäristö suojaa tältä sisäverkkohylkäykseltä. Pitkä, yli 250 m haarautumaton jatko ja sulkeutuvat ketjut säilytetään varovaisuusperiaatteella.

Toinen kokonaisreitin ehto tunnistaa haarautumattoman yhteyden, jonka molemmat päät liittyvät ajoradan solmuihin vähintään 55° kulmassa ja joka käy vähintään 6 m sivussa ajoradoista. Pelkkä läheisyys ei riitä: päiden on oltava yhteisiä ajoradan kanssa, eikä sisällä saa olla haarautumista. Jos molemmat seuratut päät ovat risteysten 25 m lähiympäristössä, reitti säilyy tämän ehdon osalta. Ehto toimii myös OSM-way-rajojen yli jatkavissa ketjuissa; hylkäyssyy on `ajoradalta_sivuun_ja_takaisin`. Esimerkit 133019393, 130751536 ja 1206626750 ovat todellisen paikallisen OSM-aineiston regressiotestissä. Rakennusgeometrioita ei vielä käytetä.

Koko kytkeytynyttä komponenttia ei luokitella samalla tavalla. Kadunvarsireitistä tontille lähtevä sivuhaara ei itsessään hylkää pääreittiä. `hylkayssyy=sisaverkon_paattyva_katuosuma` tai `sisaverkon_lapi_kulkeva_katuosuma` näyttää hylkäysperusteen. Hautausmaan kohde 1144437799 on pysyvässä regressiotestissä. Tässä vaiheessa ei käytetä kiinteistörajoja, hautausmaapolygoneja tai uutta API-avainta. OSM-verkon puutteet voivat silti vaikuttaa tulkintaan.

Lisäksi koko haarautumatonta jatkoa tarkastellaan enintään 250 m way-rajojen yli. Jos reitti käy yli 25 m päässä ajoradoista eikä siihen liity kadun 20 m lähiympäristössä toista jalankulkuväylää, sen kadun lähellä olevaa osaa ei irroteta mukaan. Myös reitin alkuperäisten taitepisteiden välit tarkistetaan 10 m näytteillä. Pelkkä ajoradan risteyksen läheisyys yhdessä päässä ei kumoa kokonaisreitin poikkeamista. Hylkäyssyy on `ajoradasta_poikkeava_kokonaisreitti`.

Geometrisen tarkastelun jälkeen poistetaan myös irrallinen umpiperäinen haara, jonka ainoa jatko on jo hylätty reitti ja joka ei kohtaa ajoradan risteyksen 25 m lähiympäristöä. Aktiiviset wayt yhdistetään ensin haarautumattomista jatkokohdista, joten reitin jakaminen useaan wayhin ei mahdollista pätkien keskinäistä perustelua. Ehto koskee haaran päähän liittyvää hylättyä jatkoa: jatkuvan kadunvarsireitin sisäinen tonttihaara ei riitä. Eksplisiittisesti jalkakäytäväksi/sivuväyläksi merkitty tai erottelutiedon sisältävä jalankulun ja pyöräilyn reitti saa tässä ristiriitatilanteessa etusijan. Kohde 115094353 on pysyvässä regressiotestissä; hylkäyssyy on `irrallinen_haara_hylatysta_reitista`.

### Lähin saman kadunpuolen jalankulkuväylä

Lähimmän samansuuntaisen ajoradan eksplisiittinen tieto jalkakäytävän puuttumisesta estää tavallisen footwayn päättelemisen jalkakäytäväksi kyseisellä puolella. Puolikohtainen `sidewalk:left/right` ohittaa `sidewalk:both`- ja yleisen `sidewalk`-arvon; myös `sidewalk=left/right` ilmaisee vastakkaisen puolen puuttumisen. Puuttuva tägi ei ole poissulkusyy. Poikkeuksena erillisen väylän `footway=sidewalk` tai `is_sidepath=yes` saa ristiriidassa etusijan; myös eroteltu pyöräväylä käsitellään sen omilla ehdoilla. Myös vähintään 90-prosenttisesti geometriaehdot täyttävä, todellisen ajoratojen haarautumisristeyksen 25 m lähiympäristöön jatkuva reitti saa etusijan: esimerkin 1201123081 kohdalla ajoradan tieto oli ristiriidassa käyttäjän varmistaman jalkakäytävän kanssa. Pelkkä ajoradan päätepiste ei riitä tähän poikkeukseen. Hylkäyssyy on `ajoradan_puolella_ei_jalkakaytavaa`. Kauempaa toista ajorataa ei käytetä tämän kiertämiseen. Ajoradan `sidewalk=no` ei poista fyysistä ajorataa sijaintiviitteistä.

### Risteyslinkit ja jalkakäytävien päät

Alle 40 m linkki voi alittaa 15 m vähimmäisjakson tai kaartaa enemmän, jos molemmat päät liittyvät eri hyväksyttyihin jalkakäytäväviivoihin yhteisissä OSM-solmuissa. Pelkkä läheisyys tai yhteys poissuljettuun yhdistettyyn väylään ei riitä. Linkin on käytävä risteyksen 25 m lähiympäristössä ja pysyttävä enintään 30 m päässä ajoradoista (normaaliraja + 10 m, katto 30 m). Pinta-, pääsy-, kokonaisreitti-, pihakatu- ja rinnakkaisuussäännöt säilyvät. Kohde 1201123082 on tällainen 13,757 m pitkä linkki; sitä ei aiemmin hyväksytty 15 m vähimmäispituuden vuoksi, vaikka se on alle 8 m päässä ajoradasta.

Jo vähintään 70-prosenttisesti hyväksytyn `footway=sidewalk`- tai `is_sidepath=yes`-viivan korkeintaan 30 m pitkä pää voidaan täydentää, kun koko puuttuva pää on todellisen risteyksen 25 m lähiympäristössä ja ajoratojen etäisyysrajan sisällä. Kokonaisreitin suodatus on tehty tätä ennen, ja rinnakkaisuusehdot tarkistetaan täydennyksillekin. Kohteet 496915707 ja 58521570 ovat pysyvissä regressiotesteissä. Auditointi-GeoJSONin uusien osuuksien `junction_link=true` erottaa risteyspoikkeuksen normaalista hyväksynnästä; parametrit ovat tuloksen `corner_link_policy`-kentässä.

Toisen pään tukena kelpaa myös yhteiseen alkuperäiseen OSM-solmuun liittyvä `footway=crossing` tai jalankulkuun tarkoitettu `cycleway=crossing`. Toinen pää vaatii edelleen hyväksytyn jalkakäytävän. Ylitys toimii katuverkon yhteyden osoituksena myös risteysten välisellä suojatiellä. Pelkkä läheisyys tai vapaa pää ilman ylitysyhteyttä ei riitä. Ylitysviivat ovat lähtötasolla luokkaa `crossing_context`, `hylkayssyy=ylitys_konteksti` ja `mukaan_m=0`. Varsinaisten viivojen pinta-, pääsy- ja etäisyysrajaukset säilyvät.

Varmennetun risteys-/ylityslinkin kanssa yhteisen OSM-solmun jakava jalkakäytävä ei varjosta sen liittymäkaarretta kilpailevana rinnakkaisena pihaviivana. Muut lähempänä ajorataa olevat rinnakkaiset väylät voivat edelleen estää linkin. Esimerkit 1201123080 → 1201123079 ja 1228692226 → 1228692227 kattavat tämän; suojatieosuuksia ei lisätä summaan.

Puuttuva kaarre voi olla myös pitkän OSM-wayn keskellä tai jatkua useaan lyhyeen wayhin. Hyväksytyt osuudet katkaisevat puuttuvien osuuksien verkon myös saman wayn sisältä. Tukemattomat umpihaarat karsitaan, ja enintään 40 m puuttuva ketju voidaan täydentää, jos se yhdistää kaksi hyväksyttyä kohtaa tai hyväksytyn kohdan ylitykseen. Ketjun pitää pysyä ajoratojen etäisyysrajassa, eikä se saa muodostaa epäselvää silmukkaa. Ilman ylitystä vaaditaan risteyksen läheisyys tai alkuperäinen yhteinen solmu ajoradan kanssa. Pinta-, pääsy- ja kokonaisreittihylkäykset tehdään ennen täydentämistä. Päällekkäiset täydennykset yhdistetään alkuperäisen viivan pituussijainnin mukaan kaksoislaskennan välttämiseksi.

Versiossa 1.6.4 kaksi eri hyväksyttyä kohtaa voivat tukea lyhyttä sivusiirtymäketjua myös ilman risteystä tai yhteistä ajoratasolmua. Tällöin koko puuttuvan ketjun on pysyttävä tavallisessa kadunvarsikäytävässä: etäisyys enintään `min(--distance,20 m)`. Risteyksen 10 m lisäetäisyyttä ei myönnetä pelkän kytkeytyneisyyden perusteella. 40 m enimmäispituus, yhteiset verkon solmut, kaksi erillistä tukikohtaa, umpihaarojen karsinta, pinta- ja pääsysäännöt sekä kokonaisreitin ja rinnakkaisuuden tarkistus säilyvät. Näsinlinnankadun 197195792 kattaa tämän regressiotestissä.

Tampereen 42274329 ja 88200539 kattavat sisäisen kaarteen ja useaan wayhin jaetun ketjun. `hylkayssyy=osittain_poissuljettu` kertoo nyt myös yleisesti, kun kunnan sisäisestä footwaystä tai erotellusta väylästä jää yli 0,1 m pois eikä tarkempaa hylkäyssyytä ole. Hyväksytty osa ei siten enää peitä muuta poisjääntiä NULL-arvolla. Tämä ei muuta laskentaa, vaan tekee lähdetasosta paremman tarkistuksessa.

### Pysäkkilaituriin päättyvät yhteydet

Lyhyt, enintään 100 m pitkä tavallinen footway voidaan tunnistaa laiturille johtavaksi yhteydeksi, kun sen umpinaisessa päässä ei ole muuta jalankulkujatkoa ja pää osuu kartoitetun laiturialueen sisään tai enintään 0,25 m päähän sen reunasta. Toisen pään pitää olla vähintään 3 m laiturialueen ulkopuolella tai vähintään 80 % reitistä alueella. Tasotietojen on vastattava toisiaan. `footway=sidewalk` ja `is_sidepath=yes` suojaavat varsinaisen jalkakäytävän tältä tulkinnalta; laiturin ohi jatkuva reitti ei ole umpiyhteys.

Laituriyhteys ei lisää jalkakäytäväpituutta eikä varjosta varsinaista jalkakäytävää. Sitä ei myöskään käytetä kaarretäydennysten tukena. Lähdetasolla `hylkayssyy=pysakkilaiturin_yhteys` ja `pysakkilaituri_osm` kertovat tulkinnan ja laiturin OSM-way-tunnisteen. Tunnistus käyttää aluegeometriaa ja verkon päättymistä, ei pelkkää pysäkin läheisyyttä. Tämä korjaa Tampereen Tuulensuun molemmat puolet, joilla laiturille päättyvä noin 42 m viiva oli aiemmin peittänyt ulomman jalkakäytävän.

Laskenta kirjoittaa myös `data/results/564.platforms.geojson`- ja `837.platforms.geojson`-tiedostot alueiden visuaalista tarkistamista varten. Ne voi avata QGISissä GeoPackagen rinnalle. Laiturialueet ovat alkuperäisiä OSM-geometrioita kunnan analyysin rajauslaatikosta.

### Lähempien reittien varjostus

Jos ajoradan ja erillisen jalankulkuväyläehdokkaan välissä on jo toinen samansuuntainen jalankulkuväylä, kauemman viivan rinnakkainen osuus poistetaan. Este voi olla footway tai jalankululle osoitettu pyöräväylä; `foot=designated`-pyöräväylä estää kauemman footwayn myös erottelutiedon puuttuessa. Fyysisen sisemmän kulkureitin pinta- tai path-rajaus ei itsessään mahdollista sen takaisen kiinteistövaylän laskemista jalkakäytäväksi.

Lähin samansuuntainen ja samalla tasolla oleva katu valitaan paikallisesti. Kadunpuoli ja väylien etäisyysjärjestys ratkaistaan sen suunnasta. Sisemmän viivan ulkopuolelle kadun normaalisuunnassa muodostettu alue leikataan kauemmasta viivasta: suodatus ei jatku sisemmän viivan päädyn yli. Vastakkainen kadunpuoli, eri tasolla kulkeva väylä ja viereisen rinnakkaisen kadun oma lähin jalkakäytävä säilyvät. Sivuttaisen järjestyksen toleranssi on 0,25 m koordinaattikohinan varalta. Suodatuksen jälkeen jäljelle jääville tavallisten footwayiden jaksoille sovelletaan edelleen 15 m vähimmäispituutta.

Jos ehdokkaan lähin fyysinen katu on `living_street`, osuus jää pois. Ajoradan sidewalk-tägeistä ei myöskään lasketa living street -pituuksia. Tämä on projektin laskentarajaus.

Lähtötasojen `varjossa_m` kertoo suoraan leikatun osuuden metreinä, `estaja_osm` sisemmän kulkureitin OSM-tunnisteet ja `viitekatu_osm` vertailukadut. `hylkayssyy=lahempi_jalankulkuvayla` kertoo kokonaan poissuljetusta ja `osittain_lahempi_jalankulkuvayla` osittain poissuljetusta lähdeviivasta. `pihakadun_varsi` kertoo living street -rajauksesta. Tarkat poistetut geometriat löytyvät tiedostosta `data/results/564.corridor_exclusions.geojson`, jonka voi avata erikseen QGISissä. Lyhyiden jäljelle jääneiden jaksojen poisto voi pienentää summaa enemmän kuin `varjossa_m`.

Kaksoislaskennan vähennys (1.6.5): erillinen kadunvarsisuodatuksen hyväksymä jalankulkuväylä ohittaa samalla puolella olevan ajoradan sidewalk-pituuden läheisen, samansuuntaisen ja samalla tasolla kulkevan osuutensa kohdalta. Myös erillinen yhdistetty tai erottelultaan tuntematon väylä estää ajoratatägiä tuottamasta sen kohdalle ylimääräistä jalkakäytävää; se ei silti itse siirry jalkakäytäväsummaan. Puoli päätellään paikallisen ajoratasegmentin digitointisuunnasta: vasen on `left`, oikea `right`. Vastakkainen puoli säilyy.

Peitto projisoidaan ajoradan pituussijainniksi ja yhdistetään alkuperäisen OSM-ajoratawayn koko pituudella. Erillisten viiden metrin footway-osien tasapäisiä puskureita ei vähennetä toisistaan: niiden suuntien vaihdellessa syntyneet kiilat aiheuttivat pistemäisiä jäännöksiä ajoratatasolle. Tavallinen peittovälin toleranssi on 1 m ja wayn päädyn toleranssi 2 m. Kun vähintään 85 % tietystä kadunpuolesta on jo erillisgeometrialla katettu, enintään 15 m väli- ja päätyjäännökset tulkitaan saman jalkakäytävän jatkumoksi ja poistetaan ajoratatägeistä. Pidemmät ja laajemmat ilman erillisgeometriaa olevat osuudet säilyvät. Suuntaeron yläraja on 30° ja sivuttaisen merkin toleranssi 0,25 m. Tämä on geometrinen heuristiikka, ei todistettu samaa fyysistä väylää koskeva tunnistus.

Version 1.6.4 tulokset voi päivittää nopeasti laskemalla vain ajoratatägien peiton uudelleen. Komento tarkistaa vanhan lähtötietojen tarkisteen, käyttää muuttumattomia erillisten väylien auditointigeometrioita ja päivittää myös katselupaketin samassa tiedostossa. Kuntatulosten varmuuskopiot tallentuvat hakemistoon `data/results/v1.6.4-before-tagged-dedup/` ja katselupaketin rinnalle syntyy `*_before_v1_6_5.gpkg`.

```powershell
./.venv/Scripts/python.exe -m pipeline.refresh_tagged --code 837 --population data/population.csv --gpkg data/exports/tampere_analyysi.gpkg
```

Normaali `compute` käyttää samaa peittolaskentaa suoraan. Nopeaa päivitystä ei käytetä, jos lähtötiedot tai erillisten väylien säännöt ovat muuttuneet.

## Epävarmuudet ja jatkokehitys

- Aloita oikean kunnan visuaalisella auditoinnilla, erityisesti kaksoiskirjausten ja etäisyysrajan osalta. Nykyversiota ei ole kalibroitu maastototuuteen.
- Ajoradan suuntainen pihapolku voi päästä mukaan. Fyysisiä esteitä, kiinteistörajoja tai kadun nimiä ei vielä käytetä.
- Kaksi erillistä OSM-viivaa voi kuvata samaa väylää; niitä ei yhdistetä toisiinsa. Lähekkäiset rinnakkaiset ajoradat voivat tuottaa virheellisiä vastaavuuksia. Yhdistetyn väylän kanssa ristiriidassa olevaa ajoradan sidewalk-tägiä ei ratkaista automaattisesti.
- Tasotietojen puute tai eri tavalla ilmaistut `bridge`-arvot voivat vääristää läheisyysvertailua. Kuntarajaa täsmälleen seuraava viiva voi tulla mukaan molempiin kuntiin.
- Ajoratatägien pituus on ajoradan keskilinjan pituuden approksimaatio: se ei seuraa kaarteen sisä- ja ulkoreunan eroja.
- Puuttuva OSM-tieto ei ole puuttuvan jalkakäytävän todiste. Tuntematon erottelu ei tarkoita varmasti yhdistettyä väylää. Kartoituserot voivat hallita kuntien välisiä eroja.
- **Koko kunnan mittari ei vastaa keskustojen vertailua.** Alkuperäisen keskustahypoteesin tutkimiseen tarvitaan yhdenmukaiset keskustarajat ja niiden sisään leikatut jalkakäytävät sekä väestö tai muu sopiva nimittäjä.
- Rajojen karttapolkuja ei vielä yksinkertaisteta: koko Suomen JSON voi kasvaa suureksi. Tarkistus-GeoJSON on yksityiskohtainen ja voi olla huomattavasti dashboard-aineistoa suurempi.

## Testit

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Testit kattavat puolikohtaiset tägit, yhdistettyjen väylien poissulun, läheisyyden, suunnan, tasoerot, kuntarajaleikkauksen, kaksoislaskennan saman/vastakkaisen puolen sekä koko pienen OSM → SQLite → kunta → selain-JSON -ketjun ja muuttumattoman tuloksen ohittamisen.

## Lähteet ja käyttöehdot

- [OSM sidewalk](https://wiki.openstreetmap.org/wiki/Key:sidewalk): puolten ja erillisen kartoituksen tägit.
- [OSM segregated](https://wiki.openstreetmap.org/wiki/Key:segregated): eroteltu vs. yhdistetty väylä.
- [Geofabrik Finland](https://download.geofabrik.de/europe/finland.html): alkuperäinen OSM-PBF.
- [Pyosmium](https://docs.osmcode.org/pyosmium/latest/): paikallinen OSM-luenta.
- OSM-aineisto: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright). Säilytä attribuutio julkaistaessa ja tarkista johdetun tietokannan jakamiseen soveltuvat ODbL-velvoitteet. Väestöaineiston lähde ja käyttöehdot lisätään valitun aineiston mukaan.

Kirkkokadun tarkistuskohde **29107579** osoitti, että `highway=footway` implikoi jo `foot=designated` ([OSM-dokumentaatio](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dfootway)). Jos samalla on `bicycle=designated` ja `segregated=no`, viiva kuuluu yhdistettyihin poissuljettuihin väyliin. Alkuperäiset foot- ja bicycle-tägit säilytetään muuttamattomina GeoPackagessa. Pysäköintikäytävä ei ole suodatuksen jalankulkueste eikä tämän havainnon vuoksi kasvatettu 20 m etäisyysrajaa.
