# Oulu 1.4.0 · jyrkkien käännösten katkaisemat jaksot

Päivitetty 7.11.2026 käyttäjän tarkistuskohteen 1272508397 perusteella. Uusi tulos on **86.781163 km** ja **0.3991 m/asukas**. Edellinen versio 1.3.0 tuotti 87,371265 km.

## Korjaus

Aiemmin kaksi toisiinsa liittyvää hyväksyttyä pätkää saattoi muodostaa vähintään 15 metrin jakson, vaikka niiden suunta vaihtui lähes suorakulmaisesti. Pihayhteyden eri osat saattoivat vastata vuorotellen kahden risteävän kadun suuntia. Kytkeytyneisyys ei tällöin tarkoittanut yhtenäistä kadun suuntaista jaksoa.

Nyt **yli 45 asteen äkillinen suunnanmuutos katkaisee jakson** ennen 15 metrin vähimmäispituuden tarkistusta. Ehto koskee tavallisia footwayitä ja vastaavia fyysisiä estereittejä. Loiva kaartuminen säilyy jatkuvana; aidon kadunkulman kaksi riittävän pitkää sivua voivat tulla mukaan erillisinä. Samat ehdot tarkistetaan myös lähempien reittien takaa poistettujen osuuksien jälkeen.

Kohde **1272508397** on noin 20,5 m pitkä. Siitä hyväksyttiin aiemmin auditointisummana noin 19,681 m. Nyt sen noin 2,6, 6,6 ja 10,6 metrin eri suuntaiset osat eivät muodosta yhtä kelpaavaa jaksoa ja tulos on **0 m**. Lähtötasolla `hylkayssyy=jyrkat_kaanteet_katkaisevat_jakson` ilmaisee syyn. Kohde ja ympäröivät kadut ovat pysyvässä OSM-otosperusteisessa regressiotestissä.

## Varmennus

29 testiä läpäisty. Mukana ovat todellinen mutkitteleva pihayhteys, vastaava tapaus kahden risteävän kadun välissä sekä aito kadunkulman jalkakäytävä, jonka pitkät sivut säilyvät. Aiemmat oikeiksi tarkistetut esimerkit säilyivät myös koko Oulun ajossa: 36729304 noin 88,579 m, 89930891 noin 526,562 m, 47110040 noin 204,623 m, 50118180 noin 85,403 m ja 50118181 noin 105,180 m.

Lähteet ja muut säännöt säilyvät [version 1.3.0](oulu-v1.3.0.md) mukaisina. Kuntalaskenta kesti 152.408 sekuntia. Viivan muoto on geometrinen vihje, ei yksin varma tieto kadun tai kiinteistön käyttötarkoituksesta. Muutkin pihapolut voivat edelleen vaatia tarkastelua.

Nykyinen `data/exports/oulu_analyysi.gpkg` päivitetään samaan tiedostoon tasojen nimet säilyttäen. Edellinen paketti säilyy tiedostossa `data/exports/oulu_analyysi_v1_3.gpkg` ja lähtötulokset hakemistossa `data/results/v1.3.0/`.
