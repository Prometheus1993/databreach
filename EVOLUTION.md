# DATA BREACH — UX-evolutie

Een overzicht van hoe het ontwerp van **DATA BREACH** geëvolueerd is
doorheen drie volledige rewrites, gestuurd door playtester-feedback
op het scherm zelf — niet door technische redenen.

Drie versies, één missie:

| Fase | Bestand | UX-stack |
|---|---|---|
| 1 | `redact.py` | terminal / curses (ASCII) |
| 2 | `databreach.py` | desktop pygame-venster, 1024 × 768 |
| 3 | `databreach_server/databreach.py` | browserversie |

Het missieontwerp is door alle fasen heen hetzelfde gebleven: speel
**Agent Cipher**, voltooi drie security protocols (Access Code, Maze
Extraction, Node Link), en beantwoord de Intel-debrief vóór de klok
afloopt. Wat veranderde is **hoe spelers het lezen, begrijpen en
voelen**.

> *Quotes verderop in dit document zijn samengevatte playtester-
> reacties. Geen namen — gewoon de feedback die meermaals terugkwam
> tijdens sessies.*

---

## Fase 1 — `redact.py` (ASCII-prototype)

Het startpunt. Het hele spel paste binnen een terminalvenster en
draaide volledig op tekens.

**Wat de UX hier al goed deed:**
- Een duidelijke driedeling: briefing → drie protocols → debrief.
- Een redacted file dat geleidelijk onthuld wordt — visuele
  voortgangsmeter zonder extra UI nodig.
- Een matrix-rain-titelscherm dat meteen toon zet.

**Wat playtesters er van zeiden:**

> *"Het concept is duidelijk, maar het ziet er uit als een
> oefening, niet als een spel."*

> *"Ik snap niet altijd of ik aan zet ben of dat de game wacht."*

> *"Te veel tekst. Ik verlies waar ik moet kijken."*

> *"Bij Intel moet ik letterlijk het juiste woord intypen — ik maak
> typo's, raak gefrustreerd en verlies tijd. Een typfout = fout
> antwoord, ook al wist ik het wel."*

> *"Tussen de minigames zit niets — het ene scherm is gedaan en je
> zit instant in het volgende. Ik kreeg geen seconde om mijn hoofd
> te resetten."*

Vier terugkerende klachten dreven de stap naar fase 2:
1. Geen visueel onderscheid tussen *staten* (wachten / actief /
   fout / succes) — alles ziet er hetzelfde uit in een terminal.
2. Niet deelbaar / niet demonstrabel.
3. **Vrij intypen** in Intel was foutgevoelig en straft typevaardig-
   heid in plaats van inhoudelijke kennis.
4. **Instant overgangen** tussen minigames — geen ademruimte, geen
   uitleg over wat er nu komt.

---

## Fase 2 — `databreach.py` (desktop pygame-rewrite)

Een volledige visuele rewrite. Hetzelfde mechaniek, maar nu in een
echt venster met kleur, animatie en feedback.

**UX-toevoegingen ten opzichte van fase 1:**
- **Pixel-font titel + animated matrix rain** zodat de eerste 3
  seconden meteen de toon zetten ("dit is een hacker-game").
- **CRT scanlines + vignette** als constant overlay — zachte retro-
  identiteit, één esthetiek over alle schermen.
- Aparte tekst-/kleurstaten voor **wachten / actief / correct /
  fout** in elk minigame.
- **Save/load**: een sessie kon hervat worden vanaf het titelscherm.
- **Loading-/transitiescherm tussen minigames** — antwoordt direct op
  fase 1's *"er zit niets tussen de spellen"*-feedback. Een korte
  pauze met de naam van het komende protocol en een kort regelblok.

**Wat playtesters tijdens deze fase aankaartten en wat de respons was:**

> *"Ik wist niet meer hoeveel tijd ik had. De timer staat te klein
> in een hoek."*
>
> — *Reactie:* timer-blok groter gemaakt en gekleurd
> (**groen → geel → rood**) afhankelijk van de resterende tijd.
> Dit is meteen de eerste **urgency-cue** in het project.

> *"Bij de maze raapte ik niets op en zag plots dat de exit
> 'gesloten' was, maar ik wist niet hoe ik hem moest openen."*
>
> — *Reactie:* een gele sleutel toegevoegd, met een duidelijke
> kleurwijziging van de exit (rood → cyaan) zodra hij opgeraapt
> wordt.

> *"Bij Node Link begreep ik gewoon niet wát het spel van mij wilde."*
>
> — *Reactie:* mini-tutorial-board op het loading-scherm met
> genummerde nodes en een voorbeeldlijntje.

> *"Ik dacht dat ik een fout had gemaakt, maar er gebeurde niets.
> Ik wist niet of ik vooruit ging."*
>
> — *Reactie:* korte rode flash bij faal-acties, groene flash bij
> successen.

**Wat in deze fase nog rauw of incompleet was — en de basis voor
fase 3:**

> *"Als ik een protocol haal, krijg ik gewoon 'PROTOCOL COMPLETE'.
> Ik zie niet welk stuk van het bestand ik daarmee net heb
> vrijgespeeld."*
>
> — In fase 2 was het succes-/faalscherm letterlijk een melding
> ("YOU WON" / "YOU FAILED") zonder verdere feedback. Spelers
> begrepen niet wat hun handeling concreet had veranderd in het
> bestand.

> *"Er gebeuren midden in de minigame plots glitches: scanlijn-
> verschuivingen, controls die omkeren, een doodshoofd op het
> scherm. Ik dacht dat het spel kapot was."*
>
> — In fase 2 zaten er **disruption events** en **screen-hack
> overlays** ingebakken (intrusion detected, signal interference,
> red rain, glitch-effects). Bedoeld als sfeer; ervaren als bug.

> *"Het briefing-bestand is een dichtbedrukt blok. Ik scan het
> niet eens, ik klik gewoon door."*
>
> — De briefing-tekst werd consequent overgeslagen. Spelers landden
> in de eerste minigame zonder te weten wélk bestand ze redacten.

> *"Ik probeerde een paar keer te klikken op de game en er gebeurde
> niets."*
>
> — Geen muis-input, maar dat werd nergens gezegd; spelers ontdekten
> het door te falen.

> *"Antwoorden intypen tijdens Intel is nog steeds vervelend."*
>
> — Vrij intypen was meegenomen uit fase 1. Bleef foutgevoelig.

Die vijf punten werden de basis voor fase 3.

---

## Fase 3 — `databreach_server/` (browserversie + UX-overhaul)

De huidige versie. Dezelfde minigame-mechanieken, maar het hele
visuele frame is opnieuw uitgewerkt op basis van de openstaande
feedback uit fase 2.

### 3.1 — De intro werd niet gelezen

> *"Ik klik gewoon door de briefing-tekst — ik wil beginnen
> spelen."*
>
> *"Ik heb de redacted file niet eens gezien voor ik in het eerste
> minigame stond."*

**Reactie:** de briefing herwerkt zodat er **geen tekst-blok meer
is om te lezen** — de redacted file zelf *is* de intro. Eén veld
per regel, redacted balken in plaats van `#####`-tekens, één lijn
onderaan ("complete 3 protocols to unredact this file"). Spelers
*scannen* het bestand in plaats van te lezen, en weten meteen wát
ze gaan ontredact.

### 3.2 — Glitches en disruption-events verwijderd

> *"De random hack-events haalden me uit de flow — ik dacht dat
> mijn besturing kapot was."*
>
> *"De doodshoofd-overlay verraste me, maar niet op een leuke
> manier. Ik dacht: heb ik verloren?"*

**Reactie:** de **disruption events** (controls inverted, signal
interference, …) en **screen-hack overlays** (skull, red rain,
glitch slices) zijn uitgeschakeld in fase 3. De functies bleven
in de code als no-ops, maar worden niet meer afgevuurd. De CRT-
scanlines blijven (zachte sfeer), de plotse storingen niet.

### 3.3 — Alles groter, keyboard-first expliciet gemaakt

> *"De UI is te klein. Ik mis details."*
>
> *"Ik probeerde te klikken op een knop — niets gebeurde."*

**Reactie:** schaalvergroting over de hele interface:
- Timer-blok: een groot eigen kader met grote cijfers, niet meer
  een rand-strook.
- Fonts opgeschaald in menu's, briefing en minigame-status.
- Een expliciete regel op het titelscherm: **"KEYBOARD ONLY ·
  ARROW KEYS · ENTER · SPACE · ESC"**, in een gele pulserende
  rand zodat het de eerste boodschap is die de speler ziet.

Geen muis-verwarring meer.

### 3.4 — Intel: vrij intypen vervangen door multiple choice

> *"Het Intel-typen is hetzelfde probleem als in de eerste
> versie — typo's straffen me, niet mijn kennis."*

**Reactie:** voor elk veld dat nog redacted is krijgt de speler
**4 opties** (UP/DOWN, ENTER). Velden die al ontredact zijn
vragen enkel een ENTER-bevestiging. Het Intel-scherm gebruikt
nu **dezelfde verticale bestandslayout** als de briefing, zodat
spelers herkennen dat het over hetzelfde bestand gaat.

### 3.5 — Resultaatscherm (was: "YOU WON")

> *"'PROTOCOL COMPLETE' is leuk, maar wat heb ik nu eigenlijk
> ontredact? Ik wil het zien."*
>
> *"Bij 'PROTOCOL FAILED' weet ik wel dat het mis ging, niet
> wát ik daarmee kwijt ben."*

**Reactie:** het succes-/faalscherm gebruikt nu **dezelfde
verticale-bestandslayout** als de briefing en de Intel-fase. Bij
**succes** verschijnen de net-onthulde velden in cyaan op hun rij;
bij **falen** blijven ze als redacted balken staan. De speler ziet
in één blik welk concreet stuk informatie is vrijgespeeld of
verloren — niet enkel een meldingstekst.

### 3.6 — Sidebar: timer + redaction file altijd in beeld

> *"Er is veel lege ruimte links en rechts van het minigame."*
>
> *"De timer wordt soms bedekt door de maze of door het connect-
> veld."*

**Reactie:** een **linker-sidebar** toegevoegd voor de drie action-
protocols (Roulette, Maze, Node Link). De sidebar bevat:
- de **timer** (groot, met de bestaande groen/geel/rood-cue uit
  fase 2),
- een **compacte redaction file** met alle 10 velden, waarbij de
  velden uit het *huidige* protocol een pulserend gele rand
  krijgen — de speler ziet *terwijl hij speelt* welk stuk hij
  probeert te ontredact.

De Intel-fase houdt zijn gecentreerde layout omdat dat scherm
inherent file-gericht is.

### 3.7 — Loading-schermen tonen gameplay, niet enkel regels

> *"De loading-schermen vertellen me wat de regels zijn, maar ik
> kan ze me niet voorstellen tot ik effectief in het spel sta."*

**Reactie:** elk loading-scherm kreeg een **geanimeerde mini-
preview** die de kern-actie van het komende protocol *toont*:

- **Roulette** — digit-rollen draaien continu en locken één voor
  één op de target met de witte lock-pijl.
- **Maze Extraction** — een speler-blip wandelt de gang van start
  naar de gele sleutel, met als duidelijk middenpunt het moment
  van oprapen (gele ring-flash + "+ KEY"-callout) en daarna de
  exit die ontzegelt van rood naar pulsend cyaan met een felle
  "EXIT OPEN"-callout.
- **Node Link** — een trail wandelt van node 1 naar 2, threadt door
  de gleuf van een gele gate; de gate flasht cyaan en de eerder
  vergrendelde node 3 (rode X) springt naar geel/cyaan.
- **Intel Phase** — een mini-bestand met één onthulde rij, één
  actieve rij waar tekens letter per letter ingetypt worden, en
  één redacted rij — toont in één beeld de drie statussen die
  spelers in de echte fase zullen tegenkomen.

Onderaan elke preview zit een **cyaan parameter-pil**
(bv. `TIME 50s · DIGITS 4 · ON MISS: KEEP CORRECT`), zodat de
moeilijkheidsgraad en sleutel-cijfers niet uit het zicht verdwijnen
in een kleine letter ergens anders.

### 3.8 — Unlock-dynamiek in de previews

Toen spelers een eerste versie van die animaties zagen, kwam er nog
één feedback-punt:

> *"De preview toont dat ik door de gate moet, maar niet dat de
> gate opent. Ik dacht dat het een gewone muur was met een gat in."*
>
> *"In de maze-preview rapen ze de sleutel op, maar ik zie niet
> dat dát *de exit opent*. Het lijken twee losse acties."*

**Reactie:** de previews tonen nu expliciet de **oorzaak-gevolg-
keten**:
- In de maze: bij key-pickup verschijnt een uitdijende gele ring
  + "+ KEY"-tekst die opwaarts vervaagt; tegelijkertijd wisselt
  de exit van een dim-rode "X" naar pulsend cyaan met een felle
  cyaan ring + "EXIT OPEN"-callout van ±1 seconde. Eén beat,
  twee zichtbare staten.
- In Node Link: zolang de gate nog gesloten is, draagt node 3 een
  rode "X". Wanneer de trail door de gate-gleuf passeert, flashen
  de gate-balken naar cyaan én verandert de "X" op node 3 in een
  "3" met de standaard target-kleur (geel) — zichtbaar dat **het
  passeren van de gate is wat node 3 vrijgeeft**, niet het later
  bereiken ervan.

---

## Per minigame: wat de UX heeft geleerd

### Roulette — "Access Code"
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Visuele cue voor lock | kleurverandering in cell | witte border + pijl | witte border + pijl + bonus-tekst |
| Wat doet een correcte/foute lock? | tekstregel onderaan | korte flash | flash + cijfer-status |
| Loading-scherm | geen — instant overgang | korte loading + regelblok | geanimeerde reels lock één voor één |

### Maze — "Maze Extraction"
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Hoe weet ik dat ik de sleutel nodig heb? | enkel uit tekst | gele diamant + sealed exit | sealed exit met "X" + sleutel met pulsende ring |
| Hoe weet ik dat de exit nu open is? | tekst | kleurwijziging | kleurwijziging + "EXIT OPEN"-flash |
| Iconen-uitleg | n.v.t. | enkel in help-scherm | preview-animatie net vóór de maze |

### Connect — "Node Link"
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Wat is het doel? | uitleg in tekst | uitleg + voorbeeldlijntje | uitleg + geanimeerde trail |
| Wat doen gates? | n.v.t. | gele bars; vergrendelde node = rood | gele bars worden cyaan na passage; node X → 3 |

### Intel + Debrief
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Hoe antwoord ik? | vrij intypen | vrij intypen | multiple choice (UP/DN, ENTER) |
| Bestandsweergave | gepakt monospace | gepakt monospace | verticaal — zelfde als briefing |
| Cue voor actieve rij | onderlijnd | onderlijnd | gele pulserende rand |

### Resultaatscherm (succes / faal)
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Wat zie ik na een protocol? | tekst | "PROTOCOL COMPLETE" / "FAILED" | verticaal bestand met onthulde / redacted velden |
| Begrijp ik wát ik gewonnen of verloren heb? | enkel rang | enkel status | concrete velden zichtbaar in cyaan / redacted |

### Algemeen
| | redact.py | databreach.py | huidig |
|---|---|---|---|
| Tussen minigames | instant overgang | korte loading + regels | loading + geanimeerde preview |
| Briefing-bestand | gepakt monospace | gepakt monospace | verticaal, één veld per rij |
| Timer | klein in hoek | groter blok, groen → geel → rood | groot in sidebar, zelfde kleurcue |
| Sidebar tijdens spel | n.v.t. | n.v.t. | timer + live redaction file |
| Random glitches / hack-events | n.v.t. | aanwezig | uitgeschakeld |
| Intel-input | typen | typen | multiple choice |
| Input-cue | impliciet | impliciet | expliciet "KEYBOARD ONLY · …" op titelscherm |

---

## Patroon: feedback → respons

Een korte tabel om in de presentatie te tonen.

| Feedback (samengevat) | UX-respons |
|---|---|
| *"Een typo bij Intel straft me, niet mijn kennis."* | Vrij intypen → multiple choice (UP/DN/ENTER); reeds onthulde velden auto-confirm |
| *"Het ene minigame eindigt en ik zit instant in het volgende — geen ademruimte."* | Loading-/transitiescherm met preview tussen elke minigame |
| *"Ik klik door de briefing — ik wil beginnen."* | Briefing-tekst weg; de redacted file zelf is de intro, scanbaar in één blik |
| *"De random glitches halen me uit de flow."* | Disruption events / hack-overlays uitgeschakeld |
| *"De UI is te klein, en ik probeerde te klikken."* | Alles opgeschaald; expliciete cue "KEYBOARD ONLY · ARROW KEYS · ENTER · SPACE · ESC" op het titelscherm |
| *"'PROTOCOL COMPLETE' zegt me niet wat ik concreet heb vrijgespeeld."* | Resultaatscherm gebruikt dezelfde verticale layout als de briefing; onthulde velden in cyaan, redacted velden als balken |
| *"Het Intel-scherm ziet er totaal anders uit dan de briefing."* | Identieke verticale layout op briefing → intel → resultaat |
| *"Veel lege ruimte; de timer is soms bedekt."* | Linker-sidebar met timer + live redaction file |
| *"Ik kan de regels lezen maar pas in het spel weet ik wat het echt vraagt."* | Geanimeerde mini-preview per protocol op het loading-scherm |
| *"De preview toont dat ik door de gate moet, maar niet dat de gate opent."* | Maze-preview: key-collect-ring + 'EXIT OPEN'-flash. Node Link-preview: gate flasht cyaan, node X → 3 |
| *"Tijd loopt af en ik schrik me dood."* | Timer-kleurovergang groen → geel → rood (al sinds fase 2) |

---

## Voor de talk

Een suggestie van structuur (~5 min):

1. **De missie in één slide** (redacted file + de vier fasen) —
   blijft constant doorheen de drie versies.
2. **Fase 1 demo** (`redact.py`): toon kort dat het werkt, leid de
   pijnpunten in (geen visuele staten, intypen werkt niet, geen
   ademruimte tussen minigames).
3. **Fase 2 demo** (`databreach.py`): focus op de *visuele
   identiteit* — pixel-titel, matrix rain, CRT, faal-/successcue,
   timer-kleurcue (de eerste urgency-laag), loading-scherm tussen
   minigames. Eindig met de pijnpunten die overbleven (intro werd
   niet gelezen, glitches afleidend, "you won" zonder context,
   Intel-typen, klein UI).
4. **Fase 3 demo** (browserversie): focus op de **UX-iteraties**:
   - alles groter + keyboard-first expliciet gemaakt,
   - briefing → intel → resultaat met dezelfde verticale layout,
   - Intel multiple choice,
   - sidebar met timer + redaction file,
   - geanimeerde loading-previews,
   - unlock-dynamiek zichtbaar in de previews,
   - disruption events / glitches eruit.
5. **Feedback-tabel** (3 sterkste voorbeelden) — verbind elke
   wijziging met de speler-uitspraak die ze veroorzaakte.
6. **Wat ik heb geleerd** — de rode draad: spelers lezen niet,
   ze scannen; UX is een opeenvolging van *zichtbare staten*,
   niet van *uitleg*.

---

*Dit document beschrijft de UX-evolutie van DATA BREACH op basis
van terugkerende feedback uit playtest-sessies. De geciteerde
uitspraken zijn samengevatte representaties van die feedback —
geen letterlijke citaten van geïdentificeerde personen.*
