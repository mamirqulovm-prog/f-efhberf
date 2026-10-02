"""
Telegram Admin Bot — To'liq Admin Panel
Pella.app uchun — keep_alive yo'q, faqat bot
"""

import logging
import json
import os
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATA_FILE = "admin_data.json"
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── DATA LAYER ───────────────────────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bans": {}, "mutes": {}, "warns": {}, "logs": []}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


def log_action(action: str, admin: str, target: str, reason: str = "", extra: str = ""):
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "admin": admin,
        "target": target,
        "reason": reason,
        "extra": extra,
    }
    data["logs"].append(entry)
    if len(data["logs"]) > 500:
        data["logs"] = data["logs"][-500:]
    save_data(data)


# ─── HELPERS ──────────────────────────────────────────────────────────────────
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    admins = await context.bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)


async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        arg = context.args[0]
        if arg.startswith("@"):
            try:
                return await context.bot.get_chat(arg)
            except Exception:
                return None
        elif arg.isdigit():
            try:
                return await context.bot.get_chat(int(arg))
            except Exception:
                return None
    return None


def user_key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"


def parse_duration(text: str) -> int | None:
    if not text:
        return None
    units = {"m": 60, "h": 3600, "d": 86400}
    if text[-1] in units and text[:-1].isdigit():
        return int(text[:-1]) * units[text[-1]]
    return None


# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Ban", callback_data="menu_ban"),
         InlineKeyboardButton("🔇 Mute", callback_data="menu_mute")],
        [InlineKeyboardButton("⚠️ Warn", callback_data="menu_warn"),
         InlineKeyboardButton("📋 Ro'yxat", callback_data="menu_list")],
        [InlineKeyboardButton("🔓 Unban", callback_data="menu_unban"),
         InlineKeyboardButton("🔊 Unmute", callback_data="menu_unmute")],
        [InlineKeyboardButton("📜 Log Tarixi", callback_data="menu_logs"),
         InlineKeyboardButton("❌ Yopish", callback_data="menu_close")],
    ])


def ban_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔨 Reply ga Ban", callback_data="action_ban_reply")],
        [InlineKeyboardButton("⏳ Vaqtli Ban", callback_data="action_ban_temp")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")],
    ])


def mute_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔇 Reply ga Mute", callback_data="action_mute_reply")],
        [InlineKeyboardButton("30 daqiqa", callback_data="mute_30m"),
         InlineKeyboardButton("1 soat", callback_data="mute_1h")],
        [InlineKeyboardButton("1 kun", callback_data="mute_1d"),
         InlineKeyboardButton("7 kun", callback_data="mute_7d")],
        [InlineKeyboardButton("♾️ Doimiy", callback_data="mute_perm")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")],
    ])


def warn_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Ogohlantirish ber", callback_data="action_warn")],
        [InlineKeyboardButton("🗑️ Warnlarni tozala", callback_data="action_unwarn")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")],
    ])


# ─── COMMANDS ─────────────────────────────────────────────────────────────────
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    await update.message.reply_text(
        "🛡️ *Admin Panel* — Kerakli bo'limni tanlang:",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text(
            "❗ Misol: `/ban @username sabab` yoki xabarga reply qiling.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Sabab ko'rsatilmagan"
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        data["bans"][key] = {
            "user_id": target.id,
            "username": target.username or target.first_name,
            "reason": reason,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "permanent",
        }
        save_data(data)
        log_action("BAN", update.effective_user.full_name, target.username or str(target.id), reason)
        await update.message.reply_text(
            f"🔨 *Banned:* @{target.username or target.first_name}\n"
            f"📝 *Sabab:* {reason}\n🕐 *Vaqt:* Doimiy",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_tempban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❗ Misol: `/tempban @username 1h sabab`\nVaqt: `30m`, `1h`, `1d`, `7d`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchi topilmadi.")
        return
    dur_arg = context.args[1]
    seconds = parse_duration(dur_arg)
    if not seconds:
        await update.message.reply_text("❗ Noto'g'ri vaqt. Misol: `1h`, `30m`, `1d`", parse_mode=ParseMode.MARKDOWN)
        return
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Sabab ko'rsatilmagan"
    chat_id = update.effective_chat.id
    until = datetime.now() + timedelta(seconds=seconds)
    key = user_key(chat_id, target.id)
    try:
        await context.bot.ban_chat_member(chat_id, target.id, until_date=until)
        data["bans"][key] = {
            "user_id": target.id,
            "username": target.username or target.first_name,
            "reason": reason,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "temp",
            "until": until.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_data(data)
        log_action("TEMPBAN", update.effective_user.full_name, target.username or str(target.id), reason, dur_arg)
        await update.message.reply_text(
            f"⏳ *Vaqtli Ban:* @{target.username or target.first_name}\n"
            f"📝 *Sabab:* {reason}\n🕐 *Muddat:* {dur_arg}\n"
            f"📅 *Tugaydi:* {until.strftime('%Y-%m-%d %H:%M')}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchini ko'rsating.")
        return
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    try:
        await context.bot.unban_chat_member(chat_id, target.id)
        data["bans"].pop(key, None)
        save_data(data)
        log_action("UNBAN", update.effective_user.full_name, target.username or str(target.id))
        await update.message.reply_text(
            f"🔓 *Unban:* @{target.username or target.first_name} guruhga qaytishi mumkin.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text(
            "❗ Misol: `/mute @username 1h sabab`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    duration_str = None
    reason = "Sabab ko'rsatilmagan"
    if context.args and len(context.args) > 1:
        potential = context.args[1]
        secs = parse_duration(potential)
        if secs:
            duration_str = potential
            reason = " ".join(context.args[2:]) if len(context.args) > 2 else reason
        else:
            reason = " ".join(context.args[1:])
    no_perms = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
    )
    until = None
    if duration_str:
        until = datetime.now() + timedelta(seconds=parse_duration(duration_str))
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    try:
        await context.bot.restrict_chat_member(chat_id, target.id, permissions=no_perms, until_date=until)
        data["mutes"][key] = {
            "user_id": target.id,
            "username": target.username or target.first_name,
            "reason": reason,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "temp" if until else "permanent",
            "until": until.strftime("%Y-%m-%d %H:%M:%S") if until else "doimiy",
        }
        save_data(data)
        log_action("MUTE", update.effective_user.full_name, target.username or str(target.id), reason, duration_str or "doimiy")
        msg = (
            f"🔇 *Mute:* @{target.username or target.first_name}\n"
            f"📝 *Sabab:* {reason}\n🕐 *Muddat:* {duration_str or 'Doimiy'}"
        )
        if until:
            msg += f"\n📅 *Tugaydi:* {until.strftime('%Y-%m-%d %H:%M')}"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchini ko'rsating.")
        return
    full_perms = ChatPermissions(
        can_send_messages=True, can_send_media_messages=True,
        can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True, can_invite_users=True,
    )
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    try:
        await context.bot.restrict_chat_member(chat_id, target.id, permissions=full_perms)
        data["mutes"].pop(key, None)
        save_data(data)
        log_action("UNMUTE", update.effective_user.full_name, target.username or str(target.id))
        await update.message.reply_text(
            f"🔊 *Unmute:* @{target.username or target.first_name} yana xabar yoza oladi.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchini ko'rsating.")
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Sabab ko'rsatilmagan"
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    if key not in data["warns"]:
        data["warns"][key] = {"user_id": target.id, "username": target.username or target.first_name, "warns": []}
    data["warns"][key]["warns"].append({
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin": update.effective_user.full_name,
    })
    warn_count = len(data["warns"][key]["warns"])
    save_data(data)
    log_action("WARN", update.effective_user.full_name, target.username or str(target.id), reason, f"warn #{warn_count}")
    msg = (
        f"⚠️ *Ogohlantirish:* @{target.username or target.first_name}\n"
        f"📝 *Sabab:* {reason}\n🔢 *Jami warnlar:* {warn_count}/3"
    )
    if warn_count >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            msg += "\n\n🔨 *3 warn — avtomatik ban qilindi!*"
            data["bans"][key] = {
                "user_id": target.id,
                "username": target.username or target.first_name,
                "reason": "3 warn to'plandi",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "auto_warn",
            }
            save_data(data)
            log_action("AUTO_BAN", "BOT", target.username or str(target.id), "3 warn to'plandi")
        except Exception as e:
            msg += f"\n\n❌ Avtomatik ban xato: {e}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchini ko'rsating.")
        return
    chat_id = update.effective_chat.id
    key = user_key(chat_id, target.id)
    if key in data["warns"] and data["warns"][key]["warns"]:
        data["warns"][key]["warns"].pop()
        if not data["warns"][key]["warns"]:
            data["warns"].pop(key)
        save_data(data)
        log_action("UNWARN", update.effective_user.full_name, target.username or str(target.id))
        await update.message.reply_text(
            f"✅ @{target.username or target.first_name} ning oxirgi warni o'chirildi.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text("ℹ️ Bu foydalanuvchida warn yo'q.")


async def cmd_warnlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    chat_id = update.effective_chat.id
    entries = [v for k, v in data["warns"].items() if k.startswith(f"{chat_id}:") and v["warns"]]
    if not entries:
        await update.message.reply_text("✅ Hech kimda warn yo'q.")
        return
    lines = ["⚠️ *Warnlar ro'yxati:*\n"]
    for e in entries:
        lines.append(f"👤 @{e['username']} — {len(e['warns'])}/3 warn")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    chat_id = update.effective_chat.id
    entries = [v for k, v in data["bans"].items() if k.startswith(f"{chat_id}:")]
    if not entries:
        await update.message.reply_text("✅ Hech kim banlangan emas.")
        return
    lines = ["🔨 *Banlangan foydalanuvchilar:*\n"]
    for e in entries:
        t = e.get("type", "?")
        lines.append(f"👤 @{e['username']} | {t} | {e['time'][:10]}" + (f" → {e.get('until','')[:10]}" if t == "temp" else ""))
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_mutelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    chat_id = update.effective_chat.id
    entries = [v for k, v in data["mutes"].items() if k.startswith(f"{chat_id}:")]
    if not entries:
        await update.message.reply_text("✅ Hech kim mute qilinmagan.")
        return
    lines = ["🔇 *Mute qilinganlar:*\n"]
    for e in entries:
        lines.append(f"👤 @{e['username']} | {e['reason'][:30]} | {e.get('until','?')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❗ Foydalanuvchini ko'rsating.")
        return
    chat_id = update.effective_chat.id
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Sabab ko'rsatilmagan"
    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        log_action("KICK", update.effective_user.full_name, target.username or str(target.id), reason)
        await update.message.reply_text(
            f"👢 *Kick:* @{target.username or target.first_name}\n📝 *Sabab:* {reason}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    recent = data["logs"][-15:]
    if not recent:
        await update.message.reply_text("📜 Hali hech qanday amal bajarilmagan.")
        return
    icons = {"BAN": "🔨", "TEMPBAN": "⏳", "UNBAN": "🔓", "MUTE": "🔇",
             "UNMUTE": "🔊", "WARN": "⚠️", "UNWARN": "✅", "AUTO_BAN": "🤖", "KICK": "👢"}
    lines = [f"📜 *Oxirgi {len(recent)} ta amal:*\n"]
    for log in reversed(recent):
        icon = icons.get(log["action"], "📌")
        lines.append(f"{icon} `{log['time'][5:16]}` *{log['action']}* — @{log['target']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ *Admin Bot — Buyruqlar*\n\n"
        "/menu — Admin panel\n"
        "/ban @user sabab — Doimiy ban\n"
        "/tempban @user 1h sabab — Vaqtli ban\n"
        "/unban @user — Banni olib tashlash\n"
        "/banlist — Banlangan ro'yxat\n"
        "/mute @user 1h sabab — Mute\n"
        "/unmute @user — Unmute\n"
        "/mutelist — Mute ro'yxat\n"
        "/warn @user sabab — Ogohlantirish\n"
        "/unwarn @user — Warnni o'chirish\n"
        "/warnlist — Warn ro'yxat\n"
        "/kick @user sabab — Chiqarish\n"
        "/logs — Amallar tarixi",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── CALLBACK HANDLER ─────────────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cb = query.data

    if cb == "menu_main":
        await query.edit_message_text(
            "🛡️ *Admin Panel* — Kerakli bo'limni tanlang:",
            reply_markup=main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN,
        )
    elif cb == "menu_ban":
        await query.edit_message_text(
            "🔨 *Ban menyusi:*", reply_markup=ban_menu_keyboard(), parse_mode=ParseMode.MARKDOWN,
        )
    elif cb == "menu_mute":
        await query.edit_message_text(
            "🔇 *Mute menyusi — muddat tanlang:*", reply_markup=mute_menu_keyboard(), parse_mode=ParseMode.MARKDOWN,
        )
    elif cb == "menu_warn":
        await query.edit_message_text(
            "⚠️ *Warn menyusi:*", reply_markup=warn_menu_keyboard(), parse_mode=ParseMode.MARKDOWN,
        )
    elif cb == "menu_list":
        chat_id = query.message.chat_id
        bc = sum(1 for k in data["bans"] if k.startswith(f"{chat_id}:"))
        mc = sum(1 for k in data["mutes"] if k.startswith(f"{chat_id}:"))
        wc = sum(1 for k in data["warns"] if k.startswith(f"{chat_id}:"))
        await query.edit_message_text(
            "📋 *Ro'yxatlar:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔨 Banlangan ({bc})", callback_data="list_bans")],
                [InlineKeyboardButton(f"🔇 Mute ({mc})", callback_data="list_mutes")],
                [InlineKeyboardButton(f"⚠️ Warnlar ({wc})", callback_data="list_warns")],
                [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")],
            ]),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif cb == "list_bans":
        chat_id = query.message.chat_id
        entries = [v for k, v in data["bans"].items() if k.startswith(f"{chat_id}:")]
        text = "🔨 *Banlangan:*\n\n" + "\n".join(f"• @{e['username']} — {e.get('type','?')} | {e['time'][:10]}" for e in entries[:20]) if entries else "✅ Hech kim banlangan emas."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="menu_list")]]), parse_mode=ParseMode.MARKDOWN)
    elif cb == "list_mutes":
        chat_id = query.message.chat_id
        entries = [v for k, v in data["mutes"].items() if k.startswith(f"{chat_id}:")]
        text = "🔇 *Mute:*\n\n" + "\n".join(f"• @{e['username']} | {e.get('until','?')}" for e in entries[:20]) if entries else "✅ Hech kim mute qilinmagan."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="menu_list")]]), parse_mode=ParseMode.MARKDOWN)
    elif cb == "list_warns":
        chat_id = query.message.chat_id
        entries = [v for k, v in data["warns"].items() if k.startswith(f"{chat_id}:") and v["warns"]]
        text = "⚠️ *Warnlar:*\n\n" + "\n".join(f"• @{e['username']} — {len(e['warns'])}/3" for e in entries[:20]) if entries else "✅ Hech kimda warn yo'q."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="menu_list")]]), parse_mode=ParseMode.MARKDOWN)
    elif cb == "menu_unban":
        await query.edit_message_text("🔓 `/unban @username` yuboring.", parse_mode=ParseMode.MARKDOWN)
    elif cb == "menu_unmute":
        await query.edit_message_text("🔊 `/unmute @username` yuboring.", parse_mode=ParseMode.MARKDOWN)
    elif cb == "menu_logs":
        recent = data["logs"][-10:]
        icons = {"BAN": "🔨", "UNBAN": "🔓", "MUTE": "🔇", "UNMUTE": "🔊", "WARN": "⚠️", "KICK": "👢", "AUTO_BAN": "🤖"}
        if not recent:
            text = "📜 Hali amal bajarilmagan."
        else:
            lines = ["📜 *Oxirgi amallar:*\n"]
            for log in reversed(recent):
                lines.append(f"{icons.get(log['action'],'📌')} {log['time'][5:16]} | *{log['action']}* @{log['target']}")
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]]), parse_mode=ParseMode.MARKDOWN)
    elif cb == "menu_close":
        await query.delete_message()
    elif cb.startswith("mute_"):
        dur_key = cb.split("_")[1]
        label = {"30m": "30 daqiqa", "1h": "1 soat", "1d": "1 kun", "7d": "7 kun", "perm": "Doimiy"}.get(dur_key, dur_key)
        cmd = f"/mute @username {dur_key}" if dur_key != "perm" else "/mute @username"
        await query.edit_message_text(
            f"🔇 *{label}* tanlandi.\n\nXabarga reply qilib:\n`{cmd} sabab`",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif cb in ("action_ban_reply", "action_mute_reply", "action_warn", "action_unwarn", "action_ban_temp"):
        tips = {
            "action_ban_reply": "🔨 Xabarga reply qilib `/ban sabab` yuboring.",
            "action_ban_temp":  "⏳ `/tempban @username 1h sabab` yuboring.\nVaqt: `30m` `1h` `1d` `7d`",
            "action_mute_reply":"🔇 Xabarga reply qilib `/mute 1h sabab` yuboring.",
            "action_warn":      "⚠️ Xabarga reply qilib `/warn sabab` yuboring.",
            "action_unwarn":    "✅ Xabarga reply qilib `/unwarn` yuboring.",
        }
        await query.edit_message_text(tips[cb], parse_mode=ParseMode.MARKDOWN)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    handlers = [
        ("menu", cmd_menu), ("help", cmd_help),
        ("ban", cmd_ban), ("tempban", cmd_tempban), ("unban", cmd_unban),
        ("mute", cmd_mute), ("unmute", cmd_unmute),
        ("warn", cmd_warn), ("unwarn", cmd_unwarn), ("warnlist", cmd_warnlist),
        ("banlist", cmd_banlist), ("mutelist", cmd_mutelist),
        ("kick", cmd_kick), ("logs", cmd_logs),
    ]
    for name, handler in handlers:
        app.add_handler(CommandHandler(name, handler))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("✅ Bot ishga tushdi — Pella.app")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
