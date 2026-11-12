# Kuusi kaupunkia · menetelmä 1.6.5

Päivitetty 12.11.2026. Ajoradan sidewalk-tägeistä johdetun pituuden päällekkäisyys erillisten jalankulkuväylien kanssa korjattiin. OSM-otos, kuntarajat, väkiluvut ja erillisten väylien hyväksymissäännöt ovat samat kuin [version 1.6.4 ajossa](six-cities-v1.6.4.md). Luvut kattavat kuntien koko alueiden kadunvarret.

## Korjaus

Vanha poisto vähensi viisimetrisiksi pilkottujen jalkakäytäväosien tasapäiset puskurit ajoradasta. Suunnanvaihdokset ja kulmat jättivät ajoradalle pieniä kiiloja ja lyhyitä jäännöksiä, vaikka vieressä oli erillinen jalkakäytävä. Myös erillisen yhdistetyn tai erottelultaan tuntemattoman väylän kohdalle saattoi jäädä ajoratatägistä laskettua jalkakäytävää.

Versio 1.6.5 projisoi erillisten väylien peiton ajoradan pituussijainniksi ja yhdistää sen alkuperäisen OSM-ajoratawayn koko pituudella, puolikohtaisesti. `left/right` tarkoittaa ajorataviivan digitointisuuntaan vasenta/oikeaa; vastakkainen puoli säilyy. Etäisyysraja ja tasotiedon vaatimus säilyvät. Suuntaeron enimmäisarvo on 30°.

Tavalliset toleranssit ovat 1 m peittoväleissä ja 2 m wayn päädyissä. Kun vähintään 85 % tietyn kadunpuolen pituudesta on katettu erillisgeometrialla, enintään 15 m väli- ja päätyjäännökset poistetaan ajoratatägeistä saman jalkakäytävän jatkumona. Pidemmät ja laajemmat kattamattomat osuudet säilyvät. Toleranssit ovat geometrisia oletuksia.

Kuvan Sukkavartaankadulla (OSM-way **23360060**) vanhalla ajoratatägitasolla oli 16 riviä: vasemmalla 22,057 m ja oikealla 14,290 m, yhteensä **36,347 m**. Uudessa aineistossa jäännöksiä on **0 m**. Erilliset jalkakäytävät säilyivät mukana. Esimerkki on tallennettu regressioaineistoksi `tests/fixtures/tampere_tagged_overlap.json`.

## Tulokset

Vain ajoratatägeistä laskettu luokka muuttui. Footway-, eroteltu-, yhdistetty- ja tuntemattoman erottelun luokat säilyivät täsmälleen ennallaan.

| Kunta | Ajoratatägit ennen, km | Ajoratatägit nyt, km | Jalkakäytävät nyt, km | JK, m/asukas |
| --- | ---: | ---: | ---: | ---: |
| Helsinki | 10,700 | 8,053 | 1 185,959 | 1,7079 |
| Espoo | 1,319 | 0,865 | 265,476 | 0,8151 |
| Tampere | 22,572 | 19,935 | 333,974 | 1,2682 |
| Vantaa | 2,209 | 1,137 | 173,463 | 0,6857 |
| Oulu | 2,805 | 0,793 | 82,544 | 0,3796 |
| Turku | 10,133 | 9,120 | 365,698 | 1,7445 |

Yhdistettyjen ja eroteltujen asukasmittarit säilyivät ennallaan. Ne ovat metrejä asukasta kohti:

| Kunta | Yhdistetty | Eroteltu |
| --- | ---: | ---: |
| Oulu | 1,8421 | 0,0626 |
| Vantaa | 1,7562 | 0,0719 |
| Espoo | 1,4902 | 0,1130 |
| Tampere | 1,1238 | 0,2442 |
| Turku | 1,0486 | 0,2434 |
| Helsinki | 0,2712 | 0,2976 |

Erotellun väylän jalankulku sisältyy jalkakäytävien summaan. Yhdistetty ja erottelultaan tuntematon eivät sisälly siihen. Oulun 91,819 km tuntematonta erottelua pysyy omana luokkanaan.

## Paikalliset aineistot ja varmennus

Kaikki kuusi `data/exports/<kaupunki>_analyysi.gpkg`-tiedostoa päivitettiin samoihin tiedostoihin. Ajoratatägien taso, lähdeajoratojen pituusattribuutit, kuntayhteenveto ja laskentametadata päivitettiin. Seitsemän muun tason geometriat säilyivät ennallaan. QGISin karttanäkymän päivitys näyttää uudet rivit.

Kuntatulokset ovat edelleen `data/results/<koodi>.json`; paikallinen kooste on `data/results/municipalities.json`. Koosteen summat, asukasmittarit ja sijoitukset on päivitetty. Erillisiä väyliä ei laskettu uudelleen: päivitys käytti niiden valmiita auditointigeometrioita. Diagnostiikan `separate_geometry_method_version=1.6.4` kertoo tämän ja `tagged_refresh_seconds` uuden peittolaskennan ajan. Uusi normaali `compute` käyttää samaa peittolaskentaa suoraan.

Varmuuskopiot: `data/results/v1.6.4-before-tagged-dedup/` ja `data/exports/<kaupunki>_analyysi_before_v1_6_5.gpkg`. Suuret paikalliset aineistot pysyvät Gitin ulkopuolella.

70 regressiotestiä läpäistiin. Testit kattavat suunnanvaihdokset, digitointisuunnan kääntämisen, vastakkaisen puolen ja eri tasojen säilymisen, aidot pidemmät aukot, yhdistettyjen/tuntemattomien väylien peiton, tallennetuista auditointiviivoista tehdyn päivityksen vastaavuuden sekä avoimen GeoPackagen päivityksen ja GDAL/Fiona-luettavuuden. Kuuden kaupungin tulokset, GeoPackage-summat, eheys, viiteavaimet ja muuttumattomat geometriatasot tarkistettiin.

Nopea päivityskomento ja tarkat säännöt ovat [käyttöohjeessa](../README.md). Lähteet ovat [edellisen ajon raportissa](six-cities-v1.6.4.md#lähteet-ja-asetukset).
