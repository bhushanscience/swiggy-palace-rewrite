# 🏰 Swiggy Palace

Python Telegram bot for manual Swiggy order assistance and customer management.

## Development branch

All rewrite development is on **`rewrite`**. The original reference repository is read-only and is not modified.

## Features in the current foundation

- Telegram polling with a Render-compatible HTTP health endpoint
- Customer menu and one-active-order guard
- Address and cart screenshot submission
- Admin order queue and order detail view
- Admin-set final amount and Palace charge
- Customer UTR/reference submission
- Manual payment verification (no payment is treated as verified from a customer-provided screenshot or UTR alone)
- Swiggy order ID updates and completion notification
- Seller application intake
- Support ticket intake
- Environment-variable configuration for bot token and admin IDs

## Render deployment

Create a **Python Web Service** from this repository and select branch `rewrite`.

- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`
- Health check path: `/health`

Set these environment variables in Render:

| Variable | Required | Description |
|---|---:|---|
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather |
| `OWNER_ID` | Recommended | Telegram numeric owner ID |
| `ADMIN_IDS` | Optional | Comma-separated Telegram numeric admin IDs |
| `DATABASE_PATH` | No | Defaults to `palace.db` |
| `PORT` | No | Render supplies this automatically |

Never commit bot tokens, payment credentials, or private customer data.

**Database note:** the included free-tier configuration uses SQLite on Render's ephemeral filesystem. Data can be lost when the service is recreated or its filesystem is reset. For production use, configure persistent storage or migrate the database to a managed PostgreSQL service before accepting real customer orders.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

On Windows, activate the virtual environment with `.venv\\Scripts\\activate`.

## Admin commands

- `/admin` — review open orders
- `/setpaymentinfo TEXT` — set the payment instructions shown to customers
- `/setcharge AMOUNT` — configure the Palace service charge
- `/cancel` — cancel the current conversation step
- `/help` — show command help

Only verify a payment after confirming receipt through the actual payment provider or bank account. The bot does not automate or bypass payment authentication.

## Reference material

- Reference project: https://github.com/ZonerOffersBot/swiggy-palace-bot
- Uploaded source files and requirement notes: [UPLOADS_AND_REQUIREMENTS.md](UPLOADS_AND_REQUIREMENTS.md)
- Ticketing/wallet scaffold uploads are preserved under `reference_uploads/ticketing_wallet_scaffold/` and are not mixed into the ordering bot without an explicit feature decision.
