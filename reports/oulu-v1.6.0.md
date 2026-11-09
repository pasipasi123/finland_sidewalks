# Oulu 1.6.0 · määränpäärajoitus ja kokonaisreitin rakenne

Päivitetty 9.11.2026 käyttäjän kohteiden 970197335, 133019393, 130751536, 1206626750 ja 115094353 sekä ajoradan 24875910 perusteella. Käytössä on sama Geofabrikin OSM-otos 5.11.2026 kuin [versiossa 1.5.0](oulu-v1.5.0.md).

Lopullinen tulos on **82,878344 km** ja **0,3811 m/asukas** (edellinen 85,822729 km). Ajoratatägeistä 2,825982 km, erillisistä footwayistä 66,304815 km ja erotelluista pyöräväylistä 13,747547 km. Koko Oulun laskenta kesti 151,353 sekuntia.

## Muutokset

- Erillisen väylän `access=destination` sulkee reitin pois, jos tarkempi `foot`-tägi ei ohita rajoitusta. `foot=destination` sulkee pois myös yleisen `access=yes`-arvon yhteydessä. `foot=yes/designated/permissive/official` säilyy muiden ehtojen tarkastelussa. `motor_vehicle=destination` ei rajoita jalankulkua; ajoradan määränpäärajoitus ei poista sen jalkakäytäviä. Hylätty reitti ei toimi rinnakkaisen väylän estäjänä mutta säilyy lähtötasolla ja verkkokontekstissa. [OSM destination](https://wiki.openstreetmap.org/wiki/Tag:access%3Ddestination), [access-hierarkia](https://wiki.openstreetmap.org/wiki/Key:access).
- Sisäverkon päätepiste voi olla myös umpikuja yli 25 m päässä kadusta. Haarautumista ei enää vaadita. Tämä poistaa myös sisäalueelta kadun lähelle jatkuvan reitin hyväksytyn loppupätkän. Risteysten lähiympäristö, pitkät jatkot ja silmukat saavat aiemman suojan.
- Ajoradalta sivuun ja takaisin palaava haarautumaton reitti hylätään, kun ketjun molemmat päät ovat ajoradan solmuissa vähintään 55° kulmassa ajorataan ja reitti käy vähintään 6 m sivussa ajoradoista. Jos molemmat päät ovat risteysten 25 m lähiympäristössä, sääntö ei hylkää. Suuntatarkistus huomioi kaikki päätteen ajoradan haarat. Haarautumattomia jatkoja seurataan OSM-way-rajojen yli. Rakennuksia tai kiinteistörajoja ei tarvita tähän vihjeeseen.
- Lähimmän samansuuntaisen ajoradan eksplisiittinen `sidewalk=no` estää tavallisen footwayn hyväksynnän kyseisellä puolella pelkän geometrian perusteella. Puolikohtaiset tägit ohittavat yleiset. Puuttuva tieto ei hylkää; `sidewalk=left/right` kertoo vastakkaisen puolen puuttumisesta. Erillisen viivan `footway=sidewalk` tai `is_sidepath=yes` saa ristiriidassa etusijan. Eroteltu pyöräväylä käsitellään omilla ehdoillaan. Kauempaa ajorataa ei käytetä kiertämään lähimmän kadun kielteistä tietoa. [OSM sidewalk](https://wiki.openstreetmap.org/wiki/Key:sidewalk).
- Koko haarautumaton reitti ja jatkot way-rajojen yli arvioidaan yhdessä. Jos reitti käy yli 25 m etäisyydellä ajoradoista eikä välissä ole jalankulkuverkon haarautumista kadun 20 m lähiympäristössä, sen katua seuraavaa pätkää ei hyväksytä erikseen. Taitepisteiden välit näytteistetään 10 m välein, joten taitepisteiden harvuus ei ohita ehtoa. Hylkäyssyy on `ajoradasta_poikkeava_kokonaisreitti`. Yhden pään läheisyys ajoradan risteykseen ei yksin pelasta tällaista reittiä.
- Lähellä katua oleva umpiperäinen haara, jonka ainoa jatko on hylätty ja joka ei kohtaa ajoradan risteyksen 25 m lähiympäristöä, poistetaan. Aktiiviset wayt yhdistetään ensin degree-2-jatkoksista. Jatkuvan kadunvarsireitin sisäinen tonttihaara ei yksin aiheuta poissulkua. Eksplisiittinen sidewalk/sidepath tai jalankulkuun soveltuva pyöräväylä saa ristiriidassa etusijan. Hylkäyssyy on `irrallinen_haara_hylatysta_reitista`.

## Tarkistuskohteet

| OSM-way | Aiemmin mukana, m | Uuden poissulun peruste |
| --- | ---: | --- |
| 970197335 | 37,759 | `jalankulku_vain_maaranpaahan` |
| 133019393 | 60,765 | `ajoradalta_sivuun_ja_takaisin` |
| 130751536 | 18,407 | `ajoradalta_sivuun_ja_takaisin` |
| 1206626750 | 38,608 | `sisaverkon_paattyva_katuosuma` |
| 115094353 | 29,664 | `irrallinen_haara_hylatysta_reitista` |

`sidewalk=no`-ristiriidan hylkäyssyy on `ajoradan_puolella_ei_jalkakaytavaa`. Ajorata 24875910 (Vikiönkuja) säilyy fyysisenä sijaintiviitteenä. Sitä ja muita lähikatuja koskeva kielteinen tieto osallistuu erillisten footwayiden arviointiin; ajorataa ei poisteta vertailusta.

49 testiä läpäisty. Todelliset paikalliset OSM-otokset kattavat uudet muotoesimerkit ja seuraavat risteyskorjaukset. Testit kattavat myös useaan wayhin jaetun palaavan tai irrallisen reitin, kauas poikkeavan kokonaisreitin, taitepisteiden välisen poikkeaman, risteysten välillä säilyvän jalkakäytävän, kulkumuotokohtaiset poikkeukset, rinnakkaisen oikean jalkakäytävän säilymisen määränpäärajoitetun reitin takana sekä puolikohtaiset sidewalk-ehdot ja ristiriitojen käsittelyn. Aiempi testi, joka odotti kauas pihaan jatkuvan footwayn lähellä katua olevan pätkän hyväksyntää, on muutettu käyttäjän täsmennyksen mukaiseen kokoreittitulkintaan.

## Risteyskorjaukset

1201123082 on oikea, 13,757 m pitkä jalkakäytävän kulmalinkki hyväksyttyjen 60211657:n ja 1201123081:n välissä. Etäisyys ajorataan on vain noin 4,8–7,2 m; esteenä oli 15 m vähimmäisjakso. Nyt lyhyt, enintään 40 m linkki saa risteyspoikkeuksen, kun molemmat päät liittyvät eri hyväksyttyihin jalkakäytäviin yhteisissä alkuperäisissä solmuissa, linkki käy risteyksen 25 m lähiympäristössä ja etäisyys ajorataan on enintään normaaliraja + 10 m (katto 30 m). Muut poissulut ja rinnakkaisuustarkistus säilyvät.

1201123081 paljasti ristiriidan ajoradan `sidewalk=no`-tiedossa: käyttäjä vahvisti kyseessä olevan oikea pitkä jalkakäytävä. Ajoradan kielteinen tieto ei siksi kumoa myöskään vähintään 90-prosenttisesti geometriaehdot täyttävää reittiä, joka jatkuu todellisen, vähintään kolmihaaraisen ajoratojen risteyksen 25 m lähiympäristöön. Pelkkä ajoradan päätepiste ei anna tätä poikkeusta.

496915707:stä puuttui noin 20,14 m ja 58521570:stä noin 4,28 m risteyspäistä. Jo vähintään 70-prosenttisesti hyväksytty, eksplisiittinen sidewalk/sidepath voi saada enintään 30 m pään täydennyksen, kun koko puuttuva pää pysyy risteyksen 25 m lähiympäristössä ja ajoradan etäisyysrajassa. Kokonaisreittihylkäykset ja rinnakkaisuusehdot tehdään edelleen. Parametrit tallennetaan `corner_link_policy`-kenttään; uusien osuuksien auditointimerkintä on `junction_link=true`.

Koko Oulun ajossa kaikki yllä luetellut viisi pihareittiä ovat poissa. 1201123082 tulee mukaan noin 13,757 m, 1201123081 noin 469,607 m, 496915707 noin 201,968 m ja 58521570 noin 309,169 m. Millimetreihin pyöristettyjen osarivien summat eroavat alkuperäisen geometrian pituuksista muutamia millimetrejä. Aiemmat oikeiksi tarkistetut 47110040, 50118180, 50118181, 89930891 ja 798167183 säilyvät; 36729304 saa samalla risteyspään täydennyksen noin 101,290 metriin.

Menetelmä on edelleen heuristinen. OSM-tägien ristiriidat ja puuttuvat verkkoyhteydet voivat tuottaa virheitä. Viivan muoto ei yksin osoita hallinnollista katu- tai tonttialuetta. Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään riveittäin; edellinen versio säilyy tiedostossa `data/exports/oulu_analyysi_v1_5.gpkg` ja laskennan lähtötulokset hakemistossa `data/results/v1.5.0/`.
