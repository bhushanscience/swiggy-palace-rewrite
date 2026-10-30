# Uploaded files and project notes

This document records the files and requirements supplied in the ChatGPT project conversation. The original uploaded files are preserved under `reference_uploads/ticketing_wallet_scaffold/`.

## Main rewrite target

- New repository: `bhushanscience/swiggy-palace-rewrite`
- Development branch: `rewrite`
- Reference project: https://github.com/ZonerOffersBot/swiggy-palace-bot
- The requested rewrite is based on the Swiggy Palace Telegram bot reference. Its visible project areas include customer ordering, seller applications, admin order handling, payment-reference/UTR review, QR configuration, priority requests, refunds, support tickets and order history.
- Keep the original reference repository unchanged. Use secure environment variables for credentials and payment configuration. Payment workflows must use legitimate provider confirmation and must fail closed when not configured; never bypass authentication or payment controls.

## Uploaded files preserved

### `test_repository_sanity.py`
A unittest-based repository sanity test. It expects:
- A PostgreSQL schema with users, orders, tickets, ticket types/files, user menu, support tickets, wallet deposits and wallet transactions.
- A Render root health response identifying the service as `swiggy-swagger-bot`.
- Transactional and idempotent wallet-deposit review.
- A single owner for the `menu:buy` callback.
- PhonePe integration to fail closed until configured.
- A PostgreSQL advisory lock to prevent multiple polling workers.
- Validation of Telegram Stars payment states.
- Reconciliation to retry only tickets that have not been delivered.
- Parameterized SQL for user-controlled values.

### `config.py`
Environment-based configuration for Telegram bot token, admin IDs, PostgreSQL database URL, PhonePe settings, webhook base URL, event metadata, INR/Stars ticket prices and Render port. It includes validation for required bot/database configuration and positive ticket prices. No actual credentials were supplied in the uploaded file.

### `db.py`
An asyncpg PostgreSQL connection-pool helper. It initializes the pool, loads `schema.sql`, exposes the initialized pool and closes it cleanly.

## Important compatibility note

The three uploaded Python files describe a separate ticketing/wallet-oriented scaffold (including event tickets, wallet deposits and PhonePe), while the selected Swiggy Palace reference is an ordering/customer-management bot. They are preserved verbatim as reference material, not silently mixed into the Palace implementation. Their applicable engineering requirements can be evaluated during design; ticketing-only and wallet-only behavior should not be added to the Palace bot unless explicitly requested.

## Original uploaded test status

The uploaded test file is a specification/checklist at this stage. It cannot pass in this repository merely by being copied: its expected implementation files and schema are not all present yet. Run it only after the relevant modules and schema are intentionally implemented.
