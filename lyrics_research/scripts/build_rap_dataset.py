#!/usr/bin/env python3
"""Build the dataset_10_songs_rap.json file from collected lyrics."""

from __future__ import annotations

import json
from pathlib import Path

SONGS = [
    {
        "id": 1,
        "artist": "Hurricane",
        "title": "Favorito",
        "year": 2019,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "pop rap",
        "lyrics_url": "https://tekstovi.net/2,5221,59369.html",
        "source": "tekstovi.net",
        "lyrics": (
            "Sijam kao milion, a ti si u mraku s njom\n"
            "Priznaj šta si skrivio, šta si to sad učinio?\n"
            "I direktnom linijom, dođi po mene, budi moj\n"
            "Da druge ne bi birao kada bi se kraj mene smirio\n\n"
            "Moj si favorito, ito, ito\n"
            "Tebi sve se oprašta\n"
            "Volim te, ali, samo smanji bar malo doživljaj\n"
            "Moj si favorito, ito, ito\n"
            "Nervni sistem pomeraš\n"
            "Stani malo, biće ti žao kad ljubav oteraš\n\n"
            "Ljubi me i dobro je\n"
            "Još me ljubi malo, ej\n"
            "Pusti svoje otrove\n"
            "Telo bez tebe boluje\n"
            "I direktnom linijom, dođi po mene, budi moj\n"
            "Da druge ne bi birao kada bi se kraj mene smirio\n\n"
            "Moj si favorito, ito, ito\n"
            "Tebi sve se oprašta\n"
            "Volim te, ali, samo smanji bar malo doživljaj\n"
            "Moj si favorito, ito, ito\n"
            "Nervni sistem pomeraš\n"
            "Stani malo, biće ti žao kad ljubav oteraš\n\n"
            "Moj si favorito, ito, ito\n"
            "Tebi sve se oprašta\n"
            "Volim te, ali, samo smanji bar malo doživljaj\n"
            "Moj si favorito, ito, ito\n"
            "Nervni sistem pomeraš\n"
            "Stani malo, biće ti žao kad ljubav oteraš\n\n"
            "Moj si favorito, ito, ito\n"
            "Nervni sistem pomeraš\n"
            "Nervni sistem pomeraš\n"
            "Nervni sistem pomeraš\n"
            "Stani malo, biće ti žao"
        ),
    },
    {
        "id": 2,
        "artist": "Breskvica",
        "title": "Sama",
        "year": 2024,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "drill pop",
        "lyrics_url": "https://tekstovi.net/2,5695,63917.html",
        "source": "tekstovi.net",
        "lyrics": (
            "Sama, u pola noći, pola dana\n"
            "A traži me pola grada\n"
            "Louis (Vuitton), Fendi, prava dama\n"
            "Đavo na ramenu mi spava\n"
            "Život zna da bude drama\n\n"
            "Broke up, switch mode\n"
            "Broke up, bitch mode\n"
            "I am with a gangsta squad\n"
            "I am nasty girl\n"
            "Nikad isto, ne bavim se kiksom\n"
            "U banci leže prihod\n"
            "Bitch znači bitch sa stilom\n"
            "Gledam u noć\n"
            "Znaš da imam moć\n"
            "Da ne osećam bol\n"
            "Dobro zna se 'ko je 'ko\n\n"
            "Sama, u pola noći, pola dana\n"
            "A traži me pola grada\n"
            "Louis (Vuitton), Fendi, prava dama\n"
            "Đavo na ramenu mi spava\n"
            "Život zna da bude drama\n\n"
            "Sama, u pola noći, pola dana\n"
            "A traži me pola grada\n"
            "Louis (Vuitton), Fendi, prava dama\n"
            "Đavo na ramenu mi spava\n"
            "Život zna da bude drama\n\n"
            "Oko mene ne znam\n"
            "Da li tišina, ili galama je\n"
            "Noga je na gasu jer\n"
            "Ne zanima me stajanje\n"
            "Digla se prašina oko mene\n"
            "Vode abrove\n"
            "Tvoj me dečko cima\n"
            "Mani me\n\n"
            "Sama, u pola noći, pola dana\n"
            "A traži me pola grada\n"
            "Louis (Vuitton), Fendi, prava dama\n"
            "Đavo na ramenu mi spava\n"
            "Život zna da bude drama\n\n"
            "Sama, u pola noći, pola dana\n"
            "A traži me pola grada\n"
            "Louis (Vuitton), Fendi, prava dama\n"
            "Đavo na ramenu mi spava\n"
            "Život zna da bude drama"
        ),
    },
    {
        "id": 3,
        "artist": "Senidah",
        "title": "Mišići",
        "year": 2019,
        "language": "Serbian",
        "country": "Slovenia/Serbia",
        "genre_tag": "trap",
        "lyrics_url": "https://tekstomanija.com/senidah-misici",
        "source": "tekstomanija",
        "lyrics": (
            "Kao da tonem u mrak, dozivam te\n"
            "Java mi se čini teškom kad nismo zajedno\n"
            "Kao da tonem u mrak, dozivam te\n"
            "I znaj da se prezivam neverom\n\n"
            "Jer kada odeš, iako me zebe\n"
            "Ja plešem, plešem\n"
            "Put me zove, nisam dete\n"
            "Tebi treba sestra, ti bi da me merkaš\n"
            "Ja plešem, plešem\n"
            "Put me zove (put me zove)\n\n"
            "Imaš mišiće da otvoriš vrata\n"
            "I pokažeš ceo stan, ti si tako jak\n"
            "I kada pređem preko praga, čini mi se da\n"
            "Pitaš me dal' imam ja nešto da dam\n"
            "Da ti dam, da ti dam\n"
            "Po stepenicama da divljam i zaključam\n"
            "Sile, sentiment i sram\n"
            "Da ti dam, da ti dam\n"
            "Po stepenicama da ja te vučem\n"
            "Luče, ti bi da se svučem, a?\n\n"
            "Treba mi jebeni magic\n"
            "Lažeš ko jebeni playback\n"
            "Ostaću kući u crveno obučena\n"
            "Kada sve uvene, vuče\n\n"
            "Jer kada odeš, iako me zebe\n"
            "Ja plešem, plešem\n"
            "Put me zove, nisam dete\n"
            "Tebi treba sestra, ti bi da me merkaš\n"
            "Ja plešem, plešem\n"
            "Put me zove (put me zove)\n\n"
            "Imaš mišiće da otvoriš vrata\n"
            "I pokažeš ceo stan, ti si tako jak\n"
            "I kada pređem preko praga, čini mi se da\n"
            "Pitaš me dal' imam ja nešto da dam\n"
            "Da ti dam, da ti dam\n"
            "Po stepenicama da divljam i zaključam\n"
            "Sile, sentiment i sram\n"
            "Da ti dam, da ti dam\n"
            "Po stepenicama da ja te vučem\n"
            "Luče, ti bi da se svučem, a?\n\n"
            "Treba mi jebeni magic\n"
            "Lažeš ko jebeni playback\n"
            "Ostaću kući u crveno obučena\n"
            "Kada sve uvene, vuče\n\n"
            "Treba mi jebeni magic\n"
            "Lažeš ko jebeni playback\n"
            "Ostaću kući u crveno obučena\n"
            "Kada sve uvene, vuče"
        ),
    },
    {
        "id": 4,
        "artist": "Jala Brat x Buba Corelli",
        "title": "Bebi",
        "year": 2018,
        "language": "Bosnian",
        "country": "Bosnia",
        "genre_tag": "pop rap",
        "lyrics_url": "https://tekstomanija.com/jala-brat-x-buba-corelli-bebi",
        "source": "tekstomanija",
        "lyrics": (
            "JALA BRAT:\n"
            "Bebo, ne znam šta je reč\n"
            "To tijelo je ooh-la-la\n"
            "I na prvu si me već smuvala, oduvala\n"
            "Ni malo nisi dumala, nisi se čuvala\n"
            "Kažeš da cijelu si večer pila i duvala\n"
            "Mala na ritam rola gandžu sa malo duhana\n"
            "Mala k'o Rita Ora, plava, ten kao Kubana\n"
            "I opet namjerno mi to radiš\n"
            "Spušta k'o da pio sam lean\n"
            "I sekunde rade o glavi\n"
            "Da sa mene svuče Supreme\n"
            "Mala ti si beton, mala ti si sve to\n"
            "Jala ovdje hara k'o Pac '95-om\n"
            "To lice lijepo, ko mu ne bi tep'o\n"
            "Ko mu ne bi laži vjerovao slijepo\n\n"
            "A ti bi u moj trezor\n"
            "A ja se ne bi' vez'o\n"
            "A ti bi na moj prijesto\n"
            "I radila bi to često\n\n"
            "REF. I sve što želi je Gucci enterijer, e\n"
            "Nema šta, bebi je k'o sa revije, e\n"
            "Oči pune sjaja, taje jako vaja\n"
            "A pogled leden kao vrh Himalaja\n\n"
            "BUBA CORELLI:\n"
            "Ja petnaest soma, bona, bebo, puk'o sam na čuku, je\n"
            "Kajla moja tozla bijelo, koštala me bruku je\n"
            "Boca Cîroca, Louis torba, ona lumpuje\n"
            "Boca Cîroca, hoće mala da lumpuje\n"
            "Šteka, šteka, šteka keš za Benza\n"
            "Nakon seksa širi miris Kenza\n"
            "Zove na Facetime, ne zna gdje sam, je\n"
            "Džep pun keša, sef pun VVS-a je\n"
            "Nisi Esma, ne, ali bit' ćeš pjesma, ej\n"
            "Daje, ne staje, najjača je, svjesna je\n"
            "Srce komad leda je, gleda me, al' ne haje\n"
            "Eh, što nije tuga snijeg da kad svane nestane\n\n"
            "A ti bi u moj trezor\n"
            "A ja se ne bi' vez'o\n"
            "A ti bi na moj prijesto\n"
            "I radila bi to često\n\n"
            "REF. I sve što želi je Gucci enterijer, e\n"
            "Nema šta, bebi je k'o sa revije, e\n"
            "Oči pune sjaja, taje jako vaja\n"
            "A pogled leden kao vrh Himalaja\n\n"
            "E-e-e-e-to!\n"
            "To bebi, mmm\n"
            "E-e-e-to!\n"
            "To bebi, mmm\n"
            "E-e!\n"
            "Mmm\n"
            "E!"
        ),
    },
    {
        "id": 5,
        "artist": "Buba Corelli",
        "title": "Balenciaga",
        "year": 2018,
        "language": "Bosnian",
        "country": "Bosnia",
        "genre_tag": "trap",
        "lyrics_url": "https://tekstovi-pesama.com/buba-corelli/balenciaga/980028/1",
        "source": "tekstovi-pesama.com",
        "lyrics": (
            "Leti avionom, al' nikad sebi nije platila let\n"
            "K'o lopov u sitne sate svrati uzme ti sve\n"
            "Moj si otrov, u isto vreme si moj ti lijek\n"
            "Cijepa na dva dela me ko more Mojsije\n"
            "Ima sve, tijelo boginje, vredno robije\n"
            "Snima se kako skida se, igra sporije\n"
            "Ona zna, s kim sam ja, ide prati mi storije\n"
            "Želim je, krevet njen moj teritorij je\n"
            "Po 5 dana, nocima ne spava, nema osjecanja jee\n"
            "Pogled ko led hladan\n"
            "Iza tamnih stakala, Balenciaga dzala ee\n"
            "Jedva stoji na nogama, sinoc mjesala alkohol je sa drogama\n"
            "Jedva stoji na nogama, sinoc mjesala alkohol je sa drogama\n"
            "Čitav klub navija za nju, pun mjesec ja ko vuk zavijam na nju\n"
            "Čitav klub navija za nju, pun mjesec ja ko vuk zavijam na nju\n"
            "Nokte nalakiraš, sve mi daš, nasminkaš, na stikle se nabijaš ee\n"
            "Foliraš, mafijaš, zna te svaki mafijaš, dobro znaš da planiraš ee\n"
            "A ta muškarca brada krasi znam to znaš\n"
            "Znaš kakav ti pakaš imaš bebo\n"
            "Drago mi je da si baš tako loša\n"
            "Noćas ti je love vreća\n"
            "Po 5 dana, nocima ne spava, nema osjecanja jee\n"
            "Pogled ko led hladan\n"
            "Iza tamnih stakala, Balenciaga dzala ee\n"
            "Jedva stoji na nogama, sinoc mjesala alkohol je sa drogama\n"
            "Jedva stoji na nogama, sinoc mjesala alkohol je sa drogama\n"
            "Čitav klub navija za nju, pun mjesec ja ko vuk zavijam na nju\n"
            "Čitav klub navija za nju, pun mjesec ja ko vuk zavijam na nju"
        ),
    },
    {
        "id": 6,
        "artist": "Sajsi MC",
        "title": "Nadrkano hodanje",
        "year": 2021,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "hip-hop",
        "lyrics_url": "https://tekstovi.net/2,2738,45834.html",
        "source": "tekstovi.net",
        "lyrics": (
            "Kada spremam se za šou, treba nešto da me digne\n"
            "Pijem ispred Dragstora, a pijem i sa bine\n"
            "Kada spremam se za šou, treba nešto da me digne\n"
            "Pijem ispred Dragstora, a pijem i sa bine\n"
            "Sabina, Sabina, vao\n"
            "Vinu dobro stoji moj osmeh\n"
            "Razvučem ga, dok cakle mi se oke\n"
            "Pro Corde, Pro Corde vino ne umara\n"
            "Zalij me njime, Sajsi fon tizerka\n"
            "Ja nisam boss, ja sam bossa nova\n"
            "Latino ciganče iz noćnih mora\n"
            "U belim pantalonama, u parkić na pivo\n"
            "Paulaner, svetlo, mutno\n"
            "Dok Taš je pun dece\n"
            "Polugoli muškarci rade vežbe\n"
            "To je taj Tašmajdan style\n"
            "Isto kô Bežanija, kad vreo je maj\n"
            "Jer šta će mi šnjaci, ako majica nije kratka\n"
            "I ako nema sunca kod crkve Svetog Marka\n"
            "Klinke u fejk kožnim jašama\n"
            "Kad će da se raspadnu, meri se satima\n\n"
            "Nadrkano hodanje, gazim limenke Red bula\n"
            "Izlazim sa žurke u stilu, ja fensi, ti nula\n"
            "Nadrkano hodanje, gazim limenke, sve puca\n"
            "Izlazim sa žurke u stilu, nestala vam struja\n\n"
            "Hvatam se za šank\n"
            "Hvatam, hvatam se za šank\n"
            "Silazim u pakao, Red bul i kožni sako\n"
            "I hvatam se za šank - Džek je drugar, Džek je jak\n"
            "Noćas svi su toples, vreli kao models\n"
            "I love Fashion TV, samo, samo progres\n"
            "Osiona, nadobudna, prava žena, skoteks\n"
            "Danas sve marksice nose maksice\n"
            "Novi puritanci gade se na platforme\n"
            "Šljokice, porno i moje okice\n\n"
            "Nadrkano hodanje, gazim limenke Red bula\n"
            "Izlazim sa žurke u stilu, ja fensi, ti nula\n"
            "Nadrkano hodanje, gazim limenke, sve puca\n"
            "Izlazim sa žurke u stilu, nestala vam struja\n\n"
            "Nadrkano hodanje, gazim limenke Red bula\n"
            "Izlazim sa žurke u stilu, ja fensi, ti nula\n"
            "Nadrkano hodanje, gazim limenke, sve puca\n"
            "Izlazim sa žurke u stilu, nestala vam struja\n\n"
            "Nadrkano hodanje, gazim limenke Red bula\n"
            "Izlazim sa žurke u stilu, sve mi se leluja"
        ),
    },
    {
        "id": 7,
        "artist": "Voyage x Nucci",
        "title": "Balkan",
        "year": 2024,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "drill pop",
        "lyrics_url": "https://tekstomanija.com/voyage-nucci-balkan",
        "source": "tekstomanija",
        "lyrics": (
            "(Je l' ovo Popov?)\n"
            "Ha, ha, ha\n"
            "(Woo-woo)\n"
            "Nucci, Voyage, Balkan\n"
            "(Woo-woo)\n\n"
            "Dve-tri lajne rade me, o mi amor\n"
            "Sve dizajner, na meni sija Dior\n"
            "Žene lagane, dame se lože na bol\n"
            "Vole mi mane, joj-joj, joj-joj\n\n"
            "Ave, ave, a Balkan daje sve\n"
            "Ave, ave, a pije, ne staje\n"
            "Ave, ave, a Balkan daje sve\n"
            "Tu sam rođen, ali morô sam da nestanem\n\n"
            "S tobom doggy sanjali bi mnogi\n"
            "Svi su hteli, ali retki su to mogli\n"
            "Taman ten, karamel kô Naomi\n"
            "Sve mi je dala kad sam je slagô da je volim\n"
            "Htela bi roming, da telo lomi na koki\n"
            "Oko vrata je stežem, bre tebra, kô da sam choky\n"
            "Za moj Paciotti, m-majka, suzu mi prolij\n"
            "Mama, nismo mi krivi, već naši loši idoli\n\n"
            "Kako dobro radi mi to\n"
            "Skini stvari, kad joj kažem dupe baci na pod\n"
            "Kako dobro radi mi to\n"
            "Polup'jana, na dva grama, moli, pita za još\n\n"
            "Dve-tri lajne rade me, o mi amor\n"
            "Sve dizajner, na meni sija Dior\n"
            "Žene lagane, dame se lože na bol\n"
            "Vole mi mane, joj-joj, joj-joj\n"
            "A ti mi—\n\n"
            "Ave, ave, a Balkan daje sve\n"
            "Ave, ave, a pije, ne staje\n"
            "Ave, ave, a Balkan daje sve\n"
            "Tu sam rođen, ali morô sam da nestanem\n\n"
            "Ave, ave, a Balkan daje sve\n"
            "Ave, ave, a pije, ne staje\n"
            "Ave, ave, a Balkan daje sve\n"
            "Tu sam rođen, ali morô sam da nestanem\n\n"
            "A majko, morô sam da nestanem\n"
            "A majko, morô sam da nestanem\n"
            "A majko, morô sam da nestanem\n"
            "Balkan"
        ),
    },
    {
        "id": 8,
        "artist": "Maya Berović",
        "title": "Neka stvar",
        "year": 2018,
        "language": "Bosnian",
        "country": "Bosnia",
        "genre_tag": "pop rap",
        "lyrics_url": "https://tekstomanija.com/maya-berovic-neka-stvar",
        "source": "tekstomanija",
        "lyrics": (
            "Šta se treb'o je\n"
            "Ko te poslao\n"
            "Oči kao nebo je\n"
            "Ma dobro došao\n\n"
            "Mene male nevolje\n"
            "A to me koštalo\n"
            "Kao oči njegove\n"
            "I sve ostalo\n\n"
            "Ti lutaš bebo\n"
            "Skrenuo si s puta, bebo\n"
            "To nije ljubav, bebo\n"
            "Samo sam luda\n"
            "Samo sam luda\n\n"
            "Ludima luda, bebo\n"
            "Neću iz kluba, bebo\n"
            "Šta je to tuga bebo\n"
            "Sada sam druga\n"
            "Neka druga\n\n"
            "Ova mala u redu je\n"
            "I kada nije, i kada nije\n"
            "A njeno srce u redu je\n"
            "Ko da nikad volelo nije\n"
            "Ova mala u redu je\n"
            "Ko nikad pre, ko nikad pre\n"
            "Njeno srce u redu je\n"
            "Ma boli me neka stvar\n\n"
            "Bebo, ma nema tih para\n"
            "I ne postoji taj dar\n"
            "Da me vrati magija\n"
            "Odavno nema čar\n\n"
            "Ma neka sam dama\n"
            "Uopšte nije me sram\n"
            "Što ti srce slamam\n"
            "Zaboli me neka stvar\n\n"
            "Ti lutaš bebo\n"
            "Skrenuo si s puta, bebo\n"
            "To nije ljubav, bebo\n"
            "Samo sam luda\n"
            "Samo sam luda\n\n"
            "Ludima luda, bebo\n"
            "Neću iz kluba, bebo\n"
            "Šta je to tuga bebo\n"
            "Sada sam druga\n"
            "Neka druga\n\n"
            "Ova mala u redu je\n"
            "I kada nije, i kada nije\n"
            "A njeno srce u redu je\n"
            "Ko da nikad volelo nije\n"
            "Ova mala u redu je\n"
            "Ko nikad pre, ko nikad pre\n"
            "Njeno srce u redu je\n"
            "Ma boli me neka stvar\n\n"
            "Ova mala u redu je\n"
            "U redu je, u redu je\n"
            "Njeno srce u redu je\n"
            "U redu je, u redu je\n"
            "Ova mala u redu je\n"
            "Ko nikad pre, ko nikad pre\n"
            "Njeno srce u redu je\n\n"
            "Ova mala u redu je\n"
            "I kada nije, i kada nije\n"
            "A njeno srce u redu je\n"
            "Ko da nikad volelo nije\n"
            "Ova mala u redu je\n"
            "Ko nikad pre, ko nikad pre\n"
            "Njeno srce u redu je\n"
            "Ma boli me neka stvar"
        ),
    },
    {
        "id": 9,
        "artist": "Edita",
        "title": "Dilema",
        "year": 2024,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "pop rap",
        "lyrics_url": "https://azlyrics.biz/e/edita-lyrics/edita-dilema-lyrics/",
        "source": "azlyrics.biz",
        "lyrics": (
            "Mi smo ta dilema\n\n"
            "Ja sve bih ostavila\n"
            "Kada bi doš'o ti\n"
            "Što ne bi probali\n"
            "Makar i bilo minut il' dva\n"
            "Režija tarantino\n"
            "Svi drugi wannabe\n"
            "U podne pospani\n"
            "Ma neka ide život na keca\n\n"
            "Koža ježi se koža\n"
            "A ja kao lancima vezana\n"
            "Jer mi smo ko biser i školjka\n"
            "Jedna duša dva tela\n"
            "Neraskidiva veza\n"
            "Odma priđi mi odma\n"
            "Oči u oči dok niko ne gleda\n"
            "Ko da je priča ova\n"
            "Ona koju niko ni ne zna\n\n"
            "Mi smo ta dilema\n"
            "Glavna tabo tema, a o nama ništa nema\n"
            "Taxi čeka spreman\n"
            "Stakla zatamnjena, vozi nas gde svetla nema\n"
            "Mi smo ta dilema\n"
            "Moj si deo trena\n"
            "Senka što mi čuva leđa\n"
            "Šta nas sutra čeka?\n"
            "Šta nas sutra čeka\n"
            "Uvek može ispočetka\n\n"
            "Sve o tebi bih zapamtila\n"
            "Sunce dok nam sad zalazi\n"
            "Opet skrivaju nas talasi\n"
            "Neka pitaju se svi gde se nalazimo\n"
            "Hvataj i poslednji zrak ti\n"
            "Sjaj taj za svaki moj mrak si\n"
            "Dah si oduzeo svaki\n\n"
            "Mi smo ta dilema\n"
            "Glavna tabo tema, a o nama ništa nema\n"
            "Taxi čeka spreman\n"
            "Stakla zatamnjena, vozi nas gde svetla nema\n"
            "Mi smo ta dilema\n"
            "Moj si deo trena\n"
            "Senka što mi čuva leđa\n"
            "Šta nas sutra čeka?\n"
            "Šta nas sutra čeka\n"
            "Uvek može ispočetka"
        ),
    },
    {
        "id": 10,
        "artist": "Nucci",
        "title": "Vroom",
        "year": 2024,
        "language": "Serbian",
        "country": "Serbia",
        "genre_tag": "drill pop",
        "lyrics_url": "https://tekstovi.net/2,5569,62589.html",
        "source": "tekstovi.net",
        "lyrics": (
            "Je l' ovo Popov?\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Vroom, kad se opije nestane i trema\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Kukove uvije kad krene Makarena\n\n"
            "Noći su joj spontane\n"
            "Oči k'o od Sotone\n"
            "Zna koga da zove kada nema\n"
            "Ali brzo potone\n"
            "Prošle su tu stotine\n"
            "Ti si tu, bebi, samo još jedna\n"
            "Namaži gel, pa skini XL\n"
            "I postaje mi tesno\n"
            "Brzo popij koktel\n"
            "Pa pravac hotel, ma pravi model\n"
            "Ma takvo telo juri, bebo, svaki bordel\n\n"
            "En-den-dini-sava-raka-tini\n"
            "Nisi prava dama, džabe piješ taj Martini\n"
            "En-den-dini-sava-raka-tini\n"
            "Sava-raka-tika-taka, skinula bikini\n\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Vroom, kad se opije nestane i trema\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Kukove uvije kad krene Makarena\n\n"
            "Meni svega puna vena\n"
            "A okrene mi um, mala kao da je felna\n"
            "I stalno pravi drame, evo ide nova scena\n"
            "A toliko je lepa, mala kao da je Brena\n"
            "I glumi da je časna, sudbina je jasna\n"
            "Opije, pa dobije šamare bulja masna\n"
            "Opet noć je kasna, ona opet glasna\n"
            "Ribo, ti si s ulice, bre, nisi kuja rasna\n\n"
            "En-den-dini-sava-raka-tini\n"
            "Nisi prava dama, džabe piješ taj Martini\n"
            "En-den-dini-sava-raka-tini\n"
            "Sava-raka-tika-taka, skinula bikini\n\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Vroom, kad se opije nestane i trema\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Kukove uvije kad krene Makarena\n\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Vroom, kad se opije nestane i trema\n"
            "Vroom, kad me opije, glumi da je stena\n"
            "Kukove uvije kad krene Makarena"
        ),
    },
]


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    dataset = {
        "project": "Serbian/Bosnian Hip-Hop/Drill Lyrics Research",
        "collection_date": "2026-06-22",
        "song_count": len(SONGS),
        "songs": SONGS,
    }
    output_path = project_root / "data" / "dataset_10_songs_rap.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Dataset saved to {output_path}")


if __name__ == "__main__":
    main()
