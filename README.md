# DATA BREACH

> Een retro hacker-game voor het UX-design-vak. Eén missie, drie security
> protocols, een redacted file om te ontredact vóór de klok afloopt.

**Live om te spelen:** <https://databreach.fly.dev/>

---

## Voor het team — wat zit hier?

| Bestand / map | Wat is het |
|---|---|
| [`databreach.py`](./databreach.py) | De **huidige** versie van het spel — Python + pygame, draait in de browser via [pygbag](https://pypi.org/project/pygbag/). Dit is wat live staat op fly.io. |
| [`versions/redact.py`](./versions/redact.py) | **Fase 1** — het oorspronkelijke prototype, draait in een terminal (curses). |
| [`versions/databreach_desktop.py`](./versions/databreach_desktop.py) | **Fase 2** — de eerste pygame-rewrite. Desktop-only. |
| [`EVOLUTION.md`](./EVOLUTION.md) | **Voor het rapport** — de UX-evolutie van fase 1 naar nu, met playtester-feedback per iteratie. |
| `build/`, `Dockerfile`, `fly.toml`, `serve.py` | Deploy-bestanden voor fly.io — niet belangrijk voor het rapport. |

---

## Online spelen

Niets te installeren. Open <https://databreach.fly.dev/>, klik in het
canvas zodat het toetsenbord wordt opgepikt, en speel. **Toetsen:**
pijltjestoetsen, Enter, Space, Escape.

> *Eerste keer opent: de Fly-machine wordt opgewarmd, geef hem
> ±5 seconden voor het canvas verschijnt.*

---

## Lokaal spelen — per fase

Handig als je screenshots wil maken van een specifieke fase.

### Fase 1 — `redact.py` (terminal-versie)

```bash
python3 versions/redact.py
```

Werkt in elke terminal die kleur ondersteunt (Terminal.app, iTerm2,
Windows Terminal, …). Geen extra dependencies — `curses` zit in de
Python-standaardbibliotheek.

### Fase 2 — `databreach_desktop.py` (pygame-desktop)

```bash
pip install pygame==2.5.2
python3 versions/databreach_desktop.py
```

Opent een 1024×768 pygame-venster met de matrix-rain-titel,
CRT-scanlines, etc.

### Fase 3 — `databreach.py` (de huidige versie)

Online: gewoon <https://databreach.fly.dev/>.

Lokaal in pygame-venster:

```bash
pip install pygame==2.5.2
python3 databreach.py
```

> *Lokaal worden de eye-tracking-overlay en het session-report niet
> getoond — die leven in de webwrapper rond het canvas, niet in de
> game zelf. Voor de UX-screenshots van het hele scherm: gebruik
> de online-versie in de browser.*

---

## Screenshots maken voor het rapport

Een paar suggesties voor schermen die de UX-evolutie het beste
vertellen:

- **Titelscherm** — matrix-rain, dan de pixel-titel "DATA BREACH"
  + de gele "KEYBOARD ONLY · ARROW KEYS · ENTER · SPACE · ESC"-
  cue (alleen in fase 3).
- **Briefing** — verticale redacted file, één veld per rij. Toon
  fase 1 (ASCII) → fase 3 (verticaal) naast elkaar.
- **Loading-scherm** — de geanimeerde mini-preview is alleen in
  fase 3 zichtbaar; goede gif-kandidaten:
  - Roulette: digit-rollen die één voor één locken
  - Maze: blip die de sleutel oppakt → exit ontzegelt met
    "EXIT OPEN"-flash
  - Connect: trail door de gate → node 3 X → 3
- **In-game minigame** met de sidebar (timer + redaction file)
  links. Idealiter ook eens met de gele urgency-vignette
  (onder 30 s) en de rode flikker (onder 10 s).
- **Resultaatscherm** — succes vs faal met de verticale
  bestandslayout. Mooi om "PROTOCOL COMPLETE" + de net onthulde
  velden in cyaan te tonen.
- **Intel-fase** — multiple choice in actie, dezelfde verticale
  layout als de briefing.

Voor *vergelijkende* screenshots fase per fase: open elke
versie naast elkaar (terminal, pygame-venster, browser) en
maak het zelfde scherm in elke versie. Briefing en Intel zijn
de meest sprekende vergelijkingen.

---

*Project voor UX-design — `databreach.py` is een leeropdracht over
UX-iteratie op basis van playtester-feedback. Zie [`EVOLUTION.md`](./EVOLUTION.md)
voor het hele verhaal.*
