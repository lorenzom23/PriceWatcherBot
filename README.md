# PriceWatcherBot

Bot Telegram che tiene traccia del prezzo di prodotti online e avvisa gli utenti quando scende (sotto l'ultimo prezzo o sotto una soglia impostata da loro).

## Come funziona

- Ogni utente traccia URL di prodotto tramite comandi Telegram; il bot fa scraping della pagina e salva nome/prezzo su SQLite.
- Un job periodico (`check_prices_job`, ogni `CHECK_INTERVAL_HOURS` ore) ricontrolla tutti i prodotti tracciati, uno scraper per sito, in parallelo tra siti e in sequenza (con jitter) dentro lo stesso sito per non farsi bloccare.
- Se il prezzo scende sotto l'ultimo rilevato (o sotto la soglia impostata) manda un alert a tutti gli iscritti a quel prodotto.
- Se un prodotto fallisce lo scraping per 3 controlli di fila, avvisa una volta sola che il tracking è rotto e continua a riprovare in silenzio.

## Comandi

- `/track <url> [prezzo_soglia]` — inizia a tracciare un prodotto (soglia opzionale, altrimenti chiede via conversazione)
- `/list` — elenco prodotti tracciati con ultimo prezzo
- `/untrack <id>` — smette di tracciare un prodotto
- `/show_history <id>` — storico prezzi e media
- `/set_target <id> <prezzo>` — imposta/aggiorna la soglia di alert
- `/reset_target <id>` — rimuove la soglia
- `/cancel` — annulla una conversazione in corso

Il primo `/track` di una ricerca Immobiliare.it salva le case trovate. I controlli successivi notificano le case nuove e i ribassi. `/untrack <url-ricerca>` rimuove una ricerca Immobiliare.it.

## Struttura del progetto

```
main.py               entry point: setup handler, comandi, job periodico
config.py              variabili d'ambiente (token, DB, intervalli, limiti)
bot/
  handlers.py          comandi Telegram e ConversationHandler
  language.py           traduzioni (it/en)
core/
  models.py            dataclass di dominio (Product, PricePoint, ScrapeResult)
  checker.py           logica del job periodico: batch per sito, alert, retry
scrapers/
  base.py              interfaccia Scraper + eccezione ScrapeBlocked
  registry.py           auto-discovery degli scraper in scrapers/sites
  sites/amazon.py       scraper Amazon (con protezioni SSRF/anti-bot)
storage/
  database.py          schema SQLite e migrazioni
  repository.py         query di accesso ai dati
```

Aggiungere un sito nuovo = aggiungere una classe `Scraper` in `scrapers/sites/`: viene rilevata automaticamente.

## Setup

```bash
uv sync
cp .env.example .env   # BOT_TOKEN obbligatorio
uv run python main.py
```

`uv.lock` pins the complete dependency tree. Use `uv sync` to create or update
the local environment, and `uv run` to execute commands inside it.

Variabili d'ambiente (`.env`):

| Nome                     | Default                     | Descrizione                                                     |
| ------------------------ | --------------------------- | --------------------------------------------------------------- |
| `BOT_TOKEN`              | —                           | token del bot Telegram (obbligatorio)                           |
| `DB_PATH`                | `./data/prices.db`          | percorso del database SQLite                                    |
| `CHECK_INTERVAL_HOURS`   | `6`                         | ogni quante ore ricontrollare i prezzi                          |
| `HISTORY_RETENTION_DAYS` | `365`                       | giorni di storico prezzi conservati                             |
| `MAX_TRACKED_PER_CHAT`   | `25`                        | limite di prodotti tracciabili per chat                         |
| `BYPARR_URL`             | `http://192.168.1.234:8191` | URL del servizio Byparr                                         |
| `BYPARR_TIMEOUT`         | `60`                        | timeout delle richieste Byparr in secondi                       |
| `PROXY_RESPONSE_TIMEOUT` | `120`                       | timeout in secondi per la risposta HTTP di Byparr               |
| `BYPARR_MAX_PAGES`       | `5`                         | numero massimo di pagine Immobiliare.it                         |
| `AUTHORIZED_USER_IDS`    | vuoto                       | user ID Telegram autorizzati separati da virgola; vuoto = tutti |

## Docker

```bash
docker compose up -d
```

Usa l'immagine `ghcr.io/lorenzom23/pricewatcherbot:latest` (o la builda in locale), monta `data/` come volume persistente e legge `.env`.

## Test

```bash
uv run pytest
```
