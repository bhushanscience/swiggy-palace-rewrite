import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}
if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)

DATABASE_PATH = os.getenv("DATABASE_PATH", "palace.db")
PORT = int(os.getenv("PORT", "10000") or 10000)

# Conversation states stored in Telegram's per-user context.
STATE_ADDRESS = "awaiting_address"
STATE_CART = "awaiting_cart"
STATE_UTR = "awaiting_utr"
STATE_SUPPORT = "awaiting_support"
STATE_ADMIN_AMOUNT = "admin_amount"
STATE_ADMIN_SWIGGY_ID = "admin_swiggy_id"
STATE_SELLER_NAME = "seller_name"
STATE_SELLER_DETAILS = "seller_details"
