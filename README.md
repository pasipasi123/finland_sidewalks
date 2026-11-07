# Jalkakäytäväatlas

Suomen kuntien **kadunvarsien jalkakäytävät kilometreinä ja metreinä asukasta kohti**. Python-laskenta käyttää paikallista OSM-PBF:ää ja kuntakohtaista SQLite-välimuistia. Tulokset viedään GeoPackageen karttatarkistusta varten ja valmiiksi JSON-aineistoksi erillistä käyttöliittymää varten. Overpassia tai tietokantapalvelinta ei tarvita.

**Nykytila:** Oulun menetelmäversio **1.5.0**, 7.11.2026: **85,823 km ja 0,3946 m/asukas**. Verkkotopologia suodattaa sisäverkon satunnaisia katuosumia ja suojaa risteyksiin yltäviä reittejä. Jyrkät käännökset katkaisevat katua seuraavan vähimmäisjakson; lähempi saman kadunpuolen jalankulkuväylä sulkee pois kauemman rinnakkaisen viivan. Living street -varret on rajattu pois, ja puuttuva pinta oletetaan asfaltiksi. Välimuistissa on 694 255 väylää ja 308 kuntarajaa. [Nykyinen raportti](reports/oulu-v1.5.0.md), [edellinen ajo](reports/oulu-v1.4.0.md).

## Laskennan käyttöönotto Windowsissa

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

### 3. Lisää oikea väestöaineisto

Vie esimerkiksi [Tilastokeskuksen](https://stat.fi/) kuntakohtaiset väestöluvut UTF-8 CSV:ksi `data/population.csv`. Sarakkeet:

```csv
code,population,date,source
```

Yksi rivi per laskettava kunta: kolminumeroinen kuntakoodi, positiivinen kokonaisluku, väestön viitepäivä ja täsmällinen lähde (taulukon tunniste tai URL). Erotin on pilkku. Asukaskohtainen mittari on `1000 * jalkakäytäväkilometrit / väestö`. Nollaa tai puuttuvaa väestöä ei esitetä asukaskohtaisena tuloksena. `data/population.example.csv` näyttää muodon **keksityllä testiarvolla**, jota ei pidä käyttää oikeaan laskentaan.

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

Komento päivittää `web/data/municipalities.json`-aineiston lasketuilla tuloksilla. Se laskee valmiiksi myös asukaskohtaiset luvut, sijoitukset ja EPSG:3067-karttapolut. Selain vain suodattaa, järjestää ja piirtää niitä. Eri lähtöaineistoilla laskettuja tuloksia ei voi yhdistää vahingossa: julkaisu tarkistaa yhteisen lähtötietojen tarkisteen. Sijoitus lasketaan vain mukana olevista kunnista. Laskematon kunta ei tarkoita nollaa.


### Tarkastele paikallisessa GeoPackagessa

Oulun pilotin karttatarkistusta varten on tehty `data/exports/oulu_analyysi.gpkg` (EPSG:3067). Avaa se esimerkiksi QGISissä. Tiedosto sisältää omat tasot ajoratatägeistä lasketuille jalkakäytäville, erillisille jalkakäytäville, pyörätiestä erotelluille osuuksille, poissuljetuille yhdistetyille väylille ja tuntemattomalle erottelulle.

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

## Menetelmä v1.5.0

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

Ajotien luokat: primary, secondary, tertiary, unclassified, residential sekä primary/secondary/tertiary_link. Pihakadut (`living_street`), huoltotiet (`service`), ajourat, moottoritiet ja trunk-luokka eivät kuulu laskentaan. Living street säilytetään sijaintikontekstina, jotta sen footway ei tulisi mukaan toisen lähellä olevan tavallisen kadun kautta. **Ajoradan `foot=no` ei estä sen käyttämistä erillisen jalkakäytävän sijaintiviitteenä.** `access=no`-ajorata hyväksytään sijaintiviitteeksi, jos sillä on salliva kulkumuotokohtainen poikkeus esimerkiksi busseille, pyörille tai kiinteistölle ajoon. `access=private`-ajorata jää pois. Säännöt ovat tiedostossa `pipeline/rules.py`.

Jos käytössä on alkuperäinen 1.0-välimuisti, päivitä puuttuvat ajorataviitteet kerran komennolla `python -m scripts.extend_reference_roads`. Skripti tarkistaa alkuperäisen PBF:n SHA-256-summan ja lisää vanhan valinnan vuoksi puuttuneet ajoradat samasta otoksesta; koko välimuistia ei tarvitse rakentaa uudelleen. Aja tämän jälkeen `python -m scripts.extend_walking_candidates`, joka lisää footwayt, joiden jalankulkutarkoitus sisältyy jo highway-tägiin mutta jotka jäivät aiemmin pois puuttuvan erillisen foot-tägin vuoksi. `compute` tarkistaa välimuistin valintaversion (nyt 3).

Erilliset viivat pilkotaan alkuperäisiä taitepisteitä kunnioittaen enintään 5 metrin paloiksi ja ajoradat enintään 25 metrin paloiksi. `layer`, `bridge` ja `tunnel` vastaavat toisiaan. Tavallisten footwayiden suuntaero on enintään 20° ja hyväksyttyjen viivojen yhtenäisen jakson vähimmäispituus 15 m; muut analyysin väyläluokat käyttävät edelleen 30° suuntaeroa. Pituus leikataan täsmällisesti ajoradan etäisyyspuskurin ja kuntarajan sisään. Poikittaiset osuudet ja lyhyet kiinteistöyhteyksien rinnakkaiset päät vähenevät. Koko OSM-wayn hyväksymisprosenttia ei vaadita: vain osa samasta waysta voi olla jalkakäytävää.

Erillisten mukaan otettavien jalankulkuväylien pintojen sallittu lista on `asphalt`, `paved`, `paving_stones`, `paving_stones:30`, `concrete`, `concrete:plates`, `concrete:lanes`, `sett`, `cobblestone`, `cobblestone:flattened`, `unhewn_cobblestone`, `bricks`, `tiles`. `footway:surface` ohittaa yleisen `surface`-tägin. Puuttuva pintatieto oletetaan asfaltiksi. `compacted`, sorat, maa-ainekset, puu ja muut pintatietoon merkityt sallittuun listaan kuulumattomat arvot jäävät pois mukaan otettavista erillisistä väylistä. Moniarvoisen `;`-listan jokaisen arvon on oltava sallittu. Asfalttioletus ei muuta OSM-tägejä eikä ole havainto todellisesta pintamateriaalista. Sen osuus lasketaan valmiiksi tuloksen `assumed_asphalt_km`-kenttään (erilliset mukaan otetut jalankulkuväylät). Yhdistettyjen ja erottelultaan tuntemattomien poissuljettuja vertailusummia ei rajata pinnan perusteella.

### Suuntauksen jatkuvuus

15 metrin vähimmäisjakso tarkoittaa myös suunnaltaan jatkuvaa jaksoa. Yli 45 asteen äkillinen suunnanmuutos katkaisee jakson ennen pituuden tarkistusta. Näin tontin mutkitteleva yhteys ei voi koota vähimmäispituutta vuorotellen kahden risteävän kadun suuntaisista lyhyistä pätkistä. Ehto koskee tavallisia footwayitä ja niiden fyysistä estekontekstia; loivasti kaartuva viiva säilyy jatkuvana. Aidon kadunkulman kaksi riittävän pitkää sivua voidaan hyväksyä erikseen. Sama sääntö tarkistetaan lähempien väylien takaa poistettujen osuuksien jälkeen.

`hylkayssyy=jyrkat_kaanteet_katkaisevat_jakson` kertoo tapauksesta, jossa yhtenäinen yhdistetty geometria olisi riittävän pitkä mutta sen suunnaltaan jatkuvat jaksot eivät ole. Käyttäjän kohde 1272508397 on tämän säännön regressiotestinä. Tämän lisäksi tarvitaan edelleen etäisyys-, kadunsuuntaisuus-, pinta- ja lähimmän kulkureitin ehdot; viivan muoto ei yksin todista sen hallinnollista käyttötarkoitusta.

### Sisäverkon satunnaiset katuosumat

Geometrioiden yhteisistä alkuperäisistä taitepisteistä muodostetaan jalankulkuverkko, tasotiedot erotellen. Koordinaatit yhdistetään millimetrin tarkkuudella; kyse on välimuistin geometrioista johdetusta verkosta. Yksittäisen OSM-wayn päissä seurataan haarautumattomia jatkoja myös seuraaviin wayhin.

Vahva sisäverkkoepäily hylätään, kun katuun osuvan reitin toinen pää liittyy haarautuvaan polkuverkkoon yli 25 m etäisyydellä kadusta ja toinen pää jää umpinaiseksi kadun lähelle keskellä risteysväliä. Myös molemmista päistään etäämpään haarautuvaan sisäverkkoon liittyvä katuosuma hylätään. 25 m vastaa oletusetäisyyttä 20 m + sisäverkon marginaalia 5 m. Risteyksen tai kadun päätepisteen 25 m lähiympäristö suojaa hylkäykseltä. Pitkä, yli 250 m haarautumaton jatko ja sulkeutuvat ketjut säilytetään varovaisuusperiaatteella.

Koko kytkeytynyttä komponenttia ei luokitella samalla tavalla. Kadunvarsireitistä tontille lähtevä sivuhaara ei itsessään hylkää pääreittiä. `hylkayssyy=sisaverkon_paattyva_katuosuma` tai `sisaverkon_lapi_kulkeva_katuosuma` näyttää hylkäysperusteen. Hautausmaan kohde 1144437799 on pysyvässä regressiotestissä. Tässä vaiheessa ei käytetä kiinteistörajoja, hautausmaapolygoneja tai uutta API-avainta. OSM-verkon puutteet voivat silti vaikuttaa tulkintaan.

### Lähin saman kadunpuolen jalankulkuväylä

Jos ajoradan ja erillisen jalankulkuväyläehdokkaan välissä on jo toinen samansuuntainen jalankulkuväylä, kauemman viivan rinnakkainen osuus poistetaan. Este voi olla footway tai jalankululle osoitettu pyöräväylä; `foot=designated`-pyöräväylä estää kauemman footwayn myös erottelutiedon puuttuessa. Fyysisen sisemmän kulkureitin pinta- tai path-rajaus ei itsessään mahdollista sen takaisen kiinteistövaylän laskemista jalkakäytäväksi.

Lähin samansuuntainen ja samalla tasolla oleva katu valitaan paikallisesti. Kadunpuoli ja väylien etäisyysjärjestys ratkaistaan sen suunnasta. Sisemmän viivan ulkopuolelle kadun normaalisuunnassa muodostettu alue leikataan kauemmasta viivasta: suodatus ei jatku sisemmän viivan päädyn yli. Vastakkainen kadunpuoli, eri tasolla kulkeva väylä ja viereisen rinnakkaisen kadun oma lähin jalkakäytävä säilyvät. Sivuttaisen järjestyksen toleranssi on 0,25 m koordinaattikohinan varalta. Suodatuksen jälkeen jäljelle jääville tavallisten footwayiden jaksoille sovelletaan edelleen 15 m vähimmäispituutta.

Jos ehdokkaan lähin fyysinen katu on `living_street`, osuus jää pois. Ajoradan sidewalk-tägeistä ei myöskään lasketa living street -pituuksia. Tämä on projektin laskentarajaus.

Lähtötasojen `varjossa_m` kertoo suoraan leikatun osuuden metreinä, `estaja_osm` sisemmän kulkureitin OSM-tunnisteet ja `viitekatu_osm` vertailukadut. `hylkayssyy=lahempi_jalankulkuvayla` kertoo kokonaan poissuljetusta ja `osittain_lahempi_jalankulkuvayla` osittain poissuljetusta lähdeviivasta. `pihakadun_varsi` kertoo living street -rajauksesta. Tarkat poistetut geometriat löytyvät tiedostosta `data/results/564.corridor_exclusions.geojson`, jonka voi avata erikseen QGISissä. Lyhyiden jäljelle jääneiden jaksojen poisto voi pienentää summaa enemmän kuin `varjossa_m`.

Kaksoislaskennan vähennys: erillinen mukaan kelpaava jalkakäytävä ohittaa samalla puolella olevan ajoradan sidewalk-pituuden läheisen, samansuuntaisen ja samalla tasolla kulkevan osuutensa kohdalta. Puoli päätellään OSM-ajoradan viivan suunnasta. Vastakkainen puoli säilyy. Tämä on geometrinen heuristiikka, ei todistettu samaa fyysistä väylää koskeva tunnistus.

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
