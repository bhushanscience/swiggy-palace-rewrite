import logging
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    ADMIN_IDS, STATE_ADDRESS, STATE_CART, STATE_UTR, STATE_SUPPORT,
    STATE_ADMIN_AMOUNT, STATE_ADMIN_SWIGGY_ID, STATE_SELLER_NAME, STATE_SELLER_DETAILS
)
import db

log = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Place an order", callback_data="new_order")],
        [InlineKeyboardButton("📦 My orders", callback_data="my_orders"),
         InlineKeyboardButton("👤 My profile", callback_data="profile")],
        [InlineKeyboardButton("🏪 Apply as seller", callback_data="seller_apply"),
         InlineKeyboardButton("🆘 Help & support", callback_data="support")]
    ])

def role_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Continue as customer", callback_data="customer")],
        [InlineKeyboardButton("🏪 Apply as seller", callback_data="seller_apply")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user)
    context.user_data.clear()
    await update.effective_message.reply_text(
        f"🏰 Welcome to Swiggy Palace, {escape(user.first_name or 'there')}!\n\n"
        "Manual ordering assistance with clear order updates. "
        "Choose how you want to continue:",
        reply_markup=role_keyboard()
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Admin access only.")
        return
    orders = await db.pending_orders()
    keyboard = [
        [InlineKeyboardButton(f"{o['id']} · {o['status']}", callback_data=f"adm_order:{o['id']}")]
        for o in orders
    ]
    keyboard += [[InlineKeyboardButton("⚙️ Payment instructions", callback_data="adm_payment_info")]]
    await update.effective_message.reply_text(
        f"⚙️ Admin panel\nOpen orders: {len(orders)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def setpaymentinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    value = " ".join(context.args).strip()
    if not value:
        await update.effective_message.reply_text("Usage: /setpaymentinfo your verified payment instructions")
        return
    await db.set_setting("payment_info", value[:1000])
    await update.effective_message.reply_text("✅ Payment instructions saved.")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, data = q.from_user.id, q.data or ""

    if data == "customer":
        await q.message.reply_text("Customer menu:", reply_markup=home_keyboard())
        return
    if data == "seller_apply":
        context.user_data["state"] = STATE_SELLER_NAME
        await q.message.reply_text("🏪 Seller application\n\nPlease send your full name. Send /cancel to stop.")
        return
    if data == "new_order":
        order_id = await db.create_order(uid)
        if not order_id:
            await q.message.reply_text("You already have an active order. Open My Orders to check its status.")
            return
        context.user_data.clear()
        context.user_data.update({"state": STATE_ADDRESS, "order_id": order_id})
        await q.message.reply_text(
            f"🛒 Order <b>{escape(order_id)}</b> created.\n\n"
            "Step 1/3: Send your Swiggy delivery address or a shareable address link.",
            parse_mode="HTML"
        )
        return
    if data == "my_orders":
        orders = await db.customer_orders(uid)
        if not orders:
            await q.message.reply_text("You have no orders yet.", reply_markup=home_keyboard())
            return
        lines = ["📦 <b>Your recent orders</b>"]
        for o in orders:
            lines.append(
                f"\n<b>{escape(o['id'])}</b> · {escape(o['status'])}"
                f"\nTotal: ₹{o['total'] if o['total'] is not None else 'Pending'}"
            )
        await q.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=home_keyboard())
        return
    if data == "profile":
        await q.message.reply_text(
            f"👤 Telegram ID: <code>{uid}</code>",
            parse_mode="HTML", reply_markup=home_keyboard()
        )
        return
    if data == "support":
        context.user_data["state"] = STATE_SUPPORT
        await q.message.reply_text("🆘 Describe your issue in one message. Send /cancel to stop.")
        return

    if data.startswith("adm_") and not is_admin(uid):
        await q.message.reply_text("⛔ Admin access only.")
        return
    if data == "adm_payment_info":
        info = await db.get_setting("payment_info", "")
        await q.message.reply_text(info or "No payment instructions configured. Use /setpaymentinfo.")
        return
    if data.startswith("adm_order:"):
        order_id = data.split(":", 1)[1]
        order = await db.get_order(order_id)
        if not order:
            await q.message.reply_text("Order not found.")
            return
        keyboard = [
            [InlineKeyboardButton("💰 Set amount", callback_data=f"adm_amount:{order_id}")],
            [InlineKeyboardButton("✅ Verify payment", callback_data=f"adm_verify:{order_id}")],
            [InlineKeyboardButton("🧾 Set Swiggy order ID", callback_data=f"adm_swiggy:{order_id}")],
            [InlineKeyboardButton("🎉 Mark completed", callback_data=f"adm_complete:{order_id}")]
        ]
        summary = (
            f"📦 <b>{escape(order_id)}</b>\nCustomer: <code>{order['customer_id']}</code>"
            f"\nStatus: {escape(order['status'])}"
            f"\nPayment: {escape(order['payment_status'])}"
            f"\nAmount: {order['total'] if order['total'] is not None else 'Not set'}"
            f"\nUTR: {escape(order['payment_utr'] or '-')}"
            f"\nAddress: {escape(order['address'] or '-')}"
        )
        await q.message.reply_text(summary, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        if order.get("cart_file_id"):
            await q.message.reply_photo(order["cart_file_id"], caption=f"Cart screenshot · {order_id}")
        return
    if data.startswith("adm_amount:"):
        order_id = data.split(":", 1)[1]
        context.user_data.update({"state": STATE_ADMIN_AMOUNT, "admin_order_id": order_id})
        await q.message.reply_text(f"Send final Swiggy amount for {order_id} (numbers only).")
        return
    if data.startswith("adm_verify:"):
        order_id = data.split(":", 1)[1]
        order = await db.get_order(order_id)
        if not order or not order["payment_utr"]:
            await q.message.reply_text("No UTR has been submitted for this order.")
            return
        await db.update_order(order_id, payment_status="verified", status="payment_verified")
        await db.audit(uid, "payment_verified_manually", order_id)
        await context.bot.send_message(order["customer_id"], f"✅ Payment for {order_id} has been verified by the Palace team.")
        await q.message.reply_text("Payment marked verified. Confirm the actual receipt before using this action.")
        return
    if data.startswith("adm_swiggy:"):
        order_id = data.split(":", 1)[1]
        context.user_data.update({"state": STATE_ADMIN_SWIGGY_ID, "admin_order_id": order_id})
        await q.message.reply_text(f"Send the Swiggy order ID for {order_id}.")
        return
    if data.startswith("adm_complete:"):
        order_id = data.split(":", 1)[1]
        order = await db.get_order(order_id)
        if not order:
            await q.message.reply_text("Order not found.")
            return
        if order["payment_status"] != "verified":
            await q.message.reply_text("Verify the received payment before completing this order.")
            return
        await db.update_order(order_id, status="completed")
        await db.audit(uid, "order_completed", order_id)
        await context.bot.send_message(order["customer_id"], f"🎉 Order {order_id} is marked completed. Thank you!")
        await q.message.reply_text(f"✅ {order_id} completed.")
        return

async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    order_id = context.user_data.get("order_id")
    if state != STATE_CART or not order_id:
        recent = await db.customer_orders(update.effective_user.id, limit=1)
        if recent and recent[0]["status"] == "awaiting_cart":
            order_id = recent[0]["id"]
            context.user_data.update({"state": STATE_CART, "order_id": order_id})
        else:
            await update.effective_message.reply_text("No order is currently waiting for a photo.")
            return
    file_id = update.effective_message.photo[-1].file_id
    await db.update_order(order_id, cart_file_id=file_id, status="cart_received")
    context.user_data.pop("state", None)
    await update.effective_message.reply_text(
        f"✅ Cart screenshot received for {order_id}. The team will review it and share the final amount."
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, f"📥 New cart screenshot received for {order_id}. Use /admin.")
        except Exception:
            log.warning("Unable to notify admin %s", admin_id)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    uid = update.effective_user.id
    state = context.user_data.get("state")
    value = (message.text or "").strip()
    if not value:
        return

    # Restore the next customer step from the database after a bot restart.
    if not state:
        recent = await db.customer_orders(uid, limit=1)
        if recent:
            latest = recent[0]
            if latest["status"] == "awaiting_address":
                state = STATE_ADDRESS
                context.user_data.update({"state": state, "order_id": latest["id"]})
            elif latest["status"] == "payment_pending" and latest["payment_status"] != "verified":
                state = STATE_UTR
                context.user_data.update({"state": state, "order_id": latest["id"]})

    if state == STATE_ADDRESS:
        order_id = context.user_data.get("order_id")
        await db.update_order(order_id, address=value[:1500], status="awaiting_cart")
        context.user_data["state"] = STATE_CART
        await message.reply_text("📸 Step 2/3: Now upload a clear screenshot of your Swiggy cart.")
        return
    if state == STATE_UTR:
        order_id = context.user_data.get("order_id")
        await db.update_order(order_id, payment_utr=value[:120], payment_status="pending_verification", status="payment_review")
        context.user_data.pop("state", None)
        await message.reply_text("✅ UTR received. Payment is pending manual verification; this message is not a payment confirmation.")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"💳 UTR submitted for {order_id}. Use /admin to review.")
            except Exception:
                log.warning("Unable to notify admin %s", admin_id)
        return
    if state == STATE_SUPPORT:
        ticket_id = await db.create_ticket(uid, value)
        context.user_data.pop("state", None)
        await message.reply_text(f"🆘 Support ticket #{ticket_id} created. The team will review it.")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"🆘 Support ticket #{ticket_id} from {uid}:\n{value[:800]}")
            except Exception:
                log.warning("Unable to notify admin %s", admin_id)
        return
    if state == STATE_SELLER_NAME:
        context.user_data["seller_name"] = value[:120]
        context.user_data["state"] = STATE_SELLER_DETAILS
        await message.reply_text("Send a short description of your seller experience and service.")
        return
    if state == STATE_SELLER_DETAILS:
        name = context.user_data.get("seller_name", "Not provided")
        app_id = await db.save_seller_application(uid, name, value)
        context.user_data.clear()
        await message.reply_text(f"✅ Seller application #{app_id} submitted for review.")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"🏪 Seller application #{app_id}\nUser: {uid}\nName: {name}\nDetails: {value[:800]}")
            except Exception:
                log.warning("Unable to notify admin %s", admin_id)
        return
    if is_admin(uid) and state == STATE_ADMIN_AMOUNT:
        order_id = context.user_data.get("admin_order_id")
        try:
            amount = float(value)
            if amount <= 0 or amount > 100000:
                raise ValueError
        except ValueError:
            await message.reply_text("Enter a valid amount greater than ₹0 and at most ₹100,000.")
            return
        charge = float(await db.get_setting("palace_charge", "0") or 0)
        total = round(amount + charge, 2)
        await db.update_order(order_id, amount=amount, palace_charge=charge, total=total, status="payment_pending")
        order = await db.get_order(order_id)
        info = await db.get_setting("payment_info", "")
        context.user_data.pop("state", None)
        await context.bot.send_message(
            order["customer_id"],
            f"💰 Final amount for {order_id}\nSwiggy amount: ₹{amount:.2f}\nPalace charge: ₹{charge:.2f}\nTotal: ₹{total:.2f}\n\n"
            + (f"Payment instructions:\n{info}\n\n" if info else "Please contact the Palace team for payment instructions.\n\n")
            + "After paying, send your UTR/reference number here. Payment is confirmed only after manual verification."
        )
        await message.reply_text(f"Amount saved. Customer has been notified: ₹{total:.2f}.")
        return
    if is_admin(uid) and state == STATE_ADMIN_SWIGGY_ID:
        order_id = context.user_data.get("admin_order_id")
        await db.update_order(order_id, swiggy_order_id=value[:120], status="placed")
        order = await db.get_order(order_id)
        context.user_data.pop("state", None)
        await context.bot.send_message(order["customer_id"], f"🧾 Swiggy order ID for {order_id}: {value[:120]}")
        await message.reply_text("Swiggy order ID saved and customer notified.")
        return

    await message.reply_text("Use /start to open the menu, or /help for help.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text("Current action cancelled. Use /start to open the menu.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "/start — Open the menu\n/admin — Admin order panel\n"
        "/setpaymentinfo TEXT — Set payment instructions (admin)\n"
        "/cancel — Cancel the current step\n\n"
        "Payments are checked manually. Never share your OTP, password, or UPI PIN."
    )
