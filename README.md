# PriceWatcherBot

A Telegram bot that tracks the price of products from e-commerce sites and alerts subscribers when the price drops — either below the last known price or below a custom threshold they set.

## How it works

- Users track a product URL via Telegram commands; the bot scrapes the page and stores name/price in SQLite.
- A periodic job rechecks every tracked product every `CHECK_INTERVAL_HOURS`.
- If the price drops below the last recorded value (or below the user's target), subscribers get an alert.
- If a product fails to scrape 3 times in a row, subscribers are notified once and the bot keeps retrying silently.

## Commands

- `/track <url> [target_price]` — start tracking a product
- `/list` — list tracked products with their last known price
- `/untrack <id>` — stop tracking a product
- `/show_history <id>` — price history and average
- `/set_target <id> <price>` — set or update the alert threshold
- `/reset_target <id>` — remove the threshold
- `/cancel` — cancel an ongoing command

## Project structure

```
main.py                entry point: handlers, bot commands, periodic job
config.py              environment-based configuration
bot/
  handlers.py          Telegram commands and conversation flows
  language.py          translations (en/it)
core/
  models.py            domain dataclasses
  checker.py           periodic price-check job
scrapers/
  base.py              Scraper interface
  registry.py          auto-discovers scrapers in scrapers/sites
  sites/amazon.py       Amazon scraper
storage/
  database.py          SQLite schema
  repository.py        data-access queries
```

Adding a new site means adding one `Scraper` class under `scrapers/sites/` — it's picked up automatically.

## Tech stack

Python 3.12 · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) · SQLite · BeautifulSoup4/lxml · Docker · GitHub Actions

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Create a `.env` file in the project root with at least `BOT_TOKEN` (the rest have defaults):

| Name | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `DB_PATH` | `./data/prices.db` | SQLite database path |
| `CHECK_INTERVAL_HOURS` | `6` | how often to recheck prices |
| `HISTORY_RETENTION_DAYS` | `365` | days of price history kept |
| `MAX_TRACKED_PER_CHAT` | `25` | max products trackable per chat |

## Docker

```bash
docker compose up -d
```

Uses the `ghcr.io/lorenzom23/pricewatcherbot:latest` image (or builds it locally), mounts `data/` as a persistent volume, and reads config from `.env`.

## CI/CD

On every push to `main`, GitHub Actions builds an image and pushes it to GHCR. The bot runs on a Raspberry Pi, where Watchtower pulls updates automatically.

## Tests

```bash
pytest
```
