# Tampere 1.6.4 · molemmista päistä tuetut sivusiirtymät

Päivitetty 11.11.2026 Näsinlinnankadun kohteen **197195792** perusteella. Tampereen uusi tulos on **336,610320 km** ja **1,2782 m/asukas**. Edellinen [versio 1.6.3](oulu-tampere-v1.6.3.md) tuotti 335,743281 km.

## Havainto ja korjaus

197195792 on noin 99,542 m pitkä asfalttinen `footway=sidewalk`. Siitä hyväksyttiin noin 72,666 m. Kaksi pois jäävää sivusiirtymää ovat pituussijainneissa noin 33,832–50,788 m ja 71,182–81,101 m. Niiden molemmat päät liittyvät saman wayn jo hyväksyttyihin osuuksiin. Reitti pysyy noin 3–18 m päässä ajoradasta, mutta lähin ajoratojen risteys on aukkojen kohdalla noin 49–77 m päässä.

Aiempi lyhyiden ketjujen täydennys vaati lisäksi risteyksen läheisyyden, ylityksen tai yhteisen solmun ajoradan kanssa. Nyt kaksi eri hyväksyttyä tukikohtaa voivat tukea enintään 40 m puuttuvaa ketjua myös korttelin keskellä. Tällöin koko ketjun on pysyttävä tavallisessa kadunvarsikäytävässä: etäisyys enintään `min(--distance,20 m)`. Pelkkä kytkeytyneisyys ei anna risteyksen 10 m lisäetäisyyttä.

Tukikohtien on oltava eri verkkokohdissa; samaa kosketusta ei lasketa kahdeksi tueksi. Umpinaiset tukemattomat haarat karsitaan, epäselviä silmukoita ei täydennetä, ja aiemmat pinta-, pääsy-, kokonaisreitti- ja rinnakkaisuussäännöt säilyvät. Pysäkkilaiturin yhteydet eivät kelpaa tueksi. Korjaus koskee samaan wayhin sisältyviä aukkoja ja lyhyiden wayiden ketjuja.

## Varmennus ja katselu

Koko Tampereen ajossa 197195792 tulee mukaan noin **99,543 m**. Osarivien millimetripyöristys aiheuttaa noin millimetrin eron alkuperäiseen geometriaan. Hylkäyssyy poistuu, koska viiva on käytännössä kokonaan mukana.

**62 testiä läpäisty.** Mukana on oikea Näsinlinnankadun ympäristö sekä vastaavat molemmista päistä tuetut sivulenkit: 18 m päässä kadusta oleva lenkki palautetaan, 22 m päässä käyvä korttelin keskellä oleva lenkki jää pois. Aiemmat pihareittien, laituriyhteyksien ja lyhyiden risteyslinkkien regressiotestit säilyvät.

Tampereen ajossa oli 30 004 lähtöväylää ja 145 048 auditointiriviä. Kuntalaskenta kesti **218,362 sekuntia**. Aiemmat tarkistuskohteet 553272448, 67295429, 1144968837, 88200539, 379163743 ja 592800179 säilyvät, ja Tuulensuun laituriyhteydet ovat edelleen poissa pituussummasta. Tulososuuksien `junction_link=true`-auditointimerkintä kattaa nyt myös tämän verkkoyhteyteen perustuvan sivusiirtymän täydennyksen.

Samalla versiolla laskettu Oulu tuottaa **84,555755 km / 0,3888 m/asukas**, ja ajo kesti 144,923 sekuntia. Aiemmat pihareittiesimerkit 970197335, 133019393, 130751536, 1206626750, 115094353, 1144437799, 1272508397 ja 1209361514 ovat edelleen poissa koko kunnan tuloksesta. Kuntien lähtötietojen ja menetelmän tarkiste on sama.

Katseluaineisto päivitetään riveittäin samaan `data/exports/tampere_analyysi.gpkg`-tiedostoon. Edellinen aineisto säilyy tiedostossa `tampere_analyysi_v1_6_3.gpkg` ja laskentatulokset hakemistossa `data/results/v1.6.3/`. Oulu lasketaan ja sen GeoPackage päivitetään samalla menetelmäversiolla. Web-osuutta ei muutettu.

Lähtöaineisto on edelleen Geofabrikin PBF 5.11.2026, SHA256 `97fca99fdcf8e78597d4aa72eeadaf924b82181ee5e856fd4c1470745b47e218`. Tampereen väestö on 263 337, viitepäivä 31.12.2025. Välimuistin valintaversio säilyy kuutosena; uutta datapoimintaa ei tarvita. Uusi ehto on tuloksen `corner_link_policy.two_anchor_midblock_distance_m`-kentässä.
