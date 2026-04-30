import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os
from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return "Men uyg'oqman!"


def run():
    # Render beradigan PORT-ni oladi yoki 8080-ni ishlatadi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = Thread(target=run)
    t.start()


# ... botingizning asosiy funksiyalari (start, message_handler va h.k.) ...

if __name__ == '__main__':
    # 2. Botni ishga tushirishdan oldin Flask-ni yoqamiz
    keep_alive()

    # 3. Sizning ApplicationBuild kodingiz
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlerlarni qo'shish...
    # application.add_handler(...)

    print("Bot ishga tushdi...")
    application.run_polling()



BOT_TOKEN = "8405205988:AAGe3oGECGW_ZXt4xJjyS54Jq1f5VP29Ju4"
DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)

# ─── Ma'lumotlar ─────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid):
    data = load_data()
    if uid not in data:
        data[uid] = {
            "naxt": 0.0,
            "karta": 0.0,
            "qarz_berganlarim": [],
            "mening_qarzim": [],
            "step": None,
            "temp": {},
            "last_msg_id": None,
            "hisobotlar": {},  # {"01.05.2025": {...}}
        }
        save_data(data)
    user = data[uid]
    if "hisobotlar" not in user:
        user["hisobotlar"] = {}
        save_data(data)
    return user

def update_user(uid, user):
    data = load_data()
    data[uid] = user
    save_data(data)

def fmt(n):
    return f"{n:,.0f}".replace(",", " ")

def parse_amount(text):
    try:
        amount = float(text.replace(",", "").replace(" ", "").replace("'", ""))
        return amount if amount >= 0 else None
    except:
        return None

def today():
    return datetime.now().strftime("%d.%m.%Y")

# Kunlik hisobotni saqlash
def save_daily_report(uid, user):
    sana = today()
    naxt = user["naxt"]
    karta = user["karta"]
    qb = sum(q["summa"] for q in user["qarz_berganlarim"])
    qm = sum(q["summa"] for q in user["mening_qarzim"])
    jami = naxt + karta + qb - qm

    user["hisobotlar"][sana] = {
        "naxt": naxt,
        "karta": karta,
        "qarz_bergan": qb,
        "mening_qarz": qm,
        "jami": jami,
        "vaqt": datetime.now().strftime("%H:%M"),
    }
    update_user(uid, user)

# ─── Klaviaturalar ────────────────────────────────────────────────────────────

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💵 Naqt pul", callback_data="set_naxt"),
            InlineKeyboardButton("💳 Karta", callback_data="set_karta"),
        ],
        [
            InlineKeyboardButton("📤 Qarz berganlarim", callback_data="menu_bergan"),
            InlineKeyboardButton("📥 Mening qarzim", callback_data="menu_mening"),
        ],
        [
            InlineKeyboardButton("🧮 Hisoblash", callback_data="hisoblash"),
            InlineKeyboardButton("📒 Qarz daftar", callback_data="daftar"),
        ],
        [
            InlineKeyboardButton("📈 Kunlik hisobot", callback_data="hisobot"),
        ],
    ])

def bergan_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yangi qarz qo'shish", callback_data="add_bergan")],
        [InlineKeyboardButton("📋 Ro'yxatni ko'rish", callback_data="list_bergan")],
        [InlineKeyboardButton("🗑 Qarz o'chirish", callback_data="delete_bergan")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu")],
    ])

def mening_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yangi qarz qo'shish", callback_data="add_mening")],
        [InlineKeyboardButton("📋 Ro'yxatni ko'rish", callback_data="list_mening")],
        [InlineKeyboardButton("🗑 Qarz o'chirish", callback_data="delete_mening")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu")],
    ])

def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Menyuga qaytish", callback_data="menu")]])

def hisobot_menu(hisobotlar: dict):
    # Sanalar bo'yicha tugmalar (eng yangi tepada)
    sanalar = sorted(hisobotlar.keys(), reverse=True)
    keyboard = []
    for sana in sanalar[:10]:  # Oxirgi 10 kun
        h = hisobotlar[sana]
        emoji = "✅" if h["jami"] >= 0 else "⚠️"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {sana} — {fmt(h['jami'])} so'm",
                callback_data=f"h_{sana}"
            )
        ])
    keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)

def status(user):
    naxt = user["naxt"]
    karta = user["karta"]
    qb = sum(q["summa"] for q in user["qarz_berganlarim"])
    qm = sum(q["summa"] for q in user["mening_qarzim"])
    return (
        f"📊 <b>Joriy holat:</b>\n\n"
        f"💵 Naqt pul:          <b>{fmt(naxt)}</b> so'm\n"
        f"💳 Karta:              <b>{fmt(karta)}</b> so'm\n"
        f"📤 Qarz berganlarim:  <b>{fmt(qb)}</b> so'm\n"
        f"📥 Mening qarzim:     <b>{fmt(qm)}</b> so'm\n"
    )

# ─── Xabar yuborish ───────────────────────────────────────────────────────────

async def send_msg(context, chat_id, uid, user, text, markup=None):
    if user.get("last_msg_id"):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user["last_msg_id"])
        except:
            pass
    msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup)
    user["last_msg_id"] = msg.message_id
    update_user(uid, user)
    return msg

# ─── Handlerlar ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    user["step"] = None
    user["temp"] = {}
    try:
        await update.message.delete()
    except:
        pass
    await send_msg(context, update.effective_chat.id, uid, user,
        "👋 <b>Moliyaviy hisoblagichga xush kelibsiz!</b>\n\nKategoriyani tanlang:",
        main_menu()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    user = get_user(uid)
    d = q.data

    async def show(text, markup=None):
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        user["last_msg_id"] = q.message.message_id
        update_user(uid, user)

    if d == "menu":
        user["step"] = None
        user["temp"] = {}
        update_user(uid, user)
        await show(status(user) + "\nKategoriya tanlang:", main_menu())

    elif d == "set_naxt":
        user["step"] = "naxt"
        update_user(uid, user)
        await show("💵 <b>Naqt pul</b> summasini kiriting:\n\n<i>Masalan: 500000</i>")

    elif d == "set_karta":
        user["step"] = "karta"
        update_user(uid, user)
        await show("💳 <b>Karta</b> summasini kiriting:\n\n<i>Masalan: 1500000</i>")

    elif d == "menu_bergan":
        user["step"] = None
        update_user(uid, user)
        await show("📤 <b>Qarz berganlarim</b>\n\nNima qilmoqchisiz?", bergan_menu())

    elif d == "menu_mening":
        user["step"] = None
        update_user(uid, user)
        await show("📥 <b>Mening qarzim</b>\n\nNima qilmoqchisiz?", mening_menu())

    elif d == "add_bergan":
        user["step"] = "bergan_ism"
        user["temp"] = {}
        update_user(uid, user)
        await show("📤 <b>Yangi qarz</b>\n\n👤 Kimga qarz berdingiz? Ismini yozing:")

    elif d == "add_mening":
        user["step"] = "mening_ism"
        user["temp"] = {}
        update_user(uid, user)
        await show("📥 <b>Yangi qarz</b>\n\n👤 Kimdan qarz oldingiz? Ismini yozing:")

    elif d == "list_bergan":
        qarzlar = user["qarz_berganlarim"]
        if not qarzlar:
            await show("📭 Ro'yxat bo'sh.", back())
            return
        text = "📤 <b>Qarz berganlarim:</b>\n\n"
        for i, qarz in enumerate(qarzlar, 1):
            text += f"{i}. 👤 <b>{qarz['ism']}</b> — {fmt(qarz['summa'])} so'm\n📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}\n\n"
        text += f"💰 <b>Jami: {fmt(sum(q['summa'] for q in qarzlar))} so'm</b>"
        await show(text, back())

    elif d == "list_mening":
        qarzlar = user["mening_qarzim"]
        if not qarzlar:
            await show("📭 Ro'yxat bo'sh.", back())
            return
        text = "📥 <b>Mening qarzlarim:</b>\n\n"
        for i, qarz in enumerate(qarzlar, 1):
            text += f"{i}. 👤 <b>{qarz['ism']}</b> — {fmt(qarz['summa'])} so'm\n📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}\n\n"
        text += f"💰 <b>Jami: {fmt(sum(q['summa'] for q in qarzlar))} so'm</b>"
        await show(text, back())

    elif d == "delete_bergan":
        qarzlar = user["qarz_berganlarim"]
        if not qarzlar:
            await show("📭 O'chiriladigan qarz yo'q.", back())
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {qarz['ism']} — {fmt(qarz['summa'])} so'm", callback_data=f"del_b_{i}")] for i, qarz in enumerate(qarzlar)]
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="menu_bergan")])
        await show("🗑 <b>Qaysi qarzni o'chirmoqchisiz?</b>", InlineKeyboardMarkup(keyboard))

    elif d == "delete_mening":
        qarzlar = user["mening_qarzim"]
        if not qarzlar:
            await show("📭 O'chiriladigan qarz yo'q.", back())
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {qarz['ism']} — {fmt(qarz['summa'])} so'm", callback_data=f"del_m_{i}")] for i, qarz in enumerate(qarzlar)]
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="menu_mening")])
        await show("🗑 <b>Qaysi qarzni o'chirmoqchisiz?</b>", InlineKeyboardMarkup(keyboard))

    elif d.startswith("del_b_"):
        idx = int(d.split("_")[-1])
        if idx < len(user["qarz_berganlarim"]):
            o = user["qarz_berganlarim"].pop(idx)
            update_user(uid, user)
            await show(f"✅ <b>{o['ism']}</b> — {fmt(o['summa'])} so'm\nRo'yxatdan o'chirildi!", back())

    elif d.startswith("del_m_"):
        idx = int(d.split("_")[-1])
        if idx < len(user["mening_qarzim"]):
            o = user["mening_qarzim"].pop(idx)
            update_user(uid, user)
            await show(f"✅ <b>{o['ism']}</b> — {fmt(o['summa'])} so'm\nRo'yxatdan o'chirildi!", back())

    elif d == "daftar":
        berganlar = user["qarz_berganlarim"]
        mening = user["mening_qarzim"]
        text = "📒 <b>QARZ DAFTAR</b>\n" + "━" * 20 + "\n\n"
        text += "📤 <b>Men qarz berganlarim:</b>\n"
        if berganlar:
            for i, qarz in enumerate(berganlar, 1):
                text += f"  {i}. 👤 <b>{qarz['ism']}</b>\n     💰 {fmt(qarz['summa'])} so'm\n     📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}\n"
            text += f"  📌 Jami: <b>{fmt(sum(q['summa'] for q in berganlar))} so'm</b>\n"
        else:
            text += "  — bo'sh —\n"
        text += "\n" + "─" * 20 + "\n\n"
        text += "📥 <b>Mening qarzlarim:</b>\n"
        if mening:
            for i, qarz in enumerate(mening, 1):
                text += f"  {i}. 👤 <b>{qarz['ism']}</b>\n     💰 {fmt(qarz['summa'])} so'm\n     📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}\n"
            text += f"  📌 Jami: <b>{fmt(sum(q['summa'] for q in mening))} so'm</b>\n"
        else:
            text += "  — bo'sh —\n"
        naxt = user["naxt"]
        karta = user["karta"]
        jami = naxt + karta + sum(q["summa"] for q in berganlar) - sum(q["summa"] for q in mening)
        emoji = "✅" if jami >= 0 else "⚠️"
        text += "\n" + "━" * 20 + "\n"
        text += f"💵 Naqt: <b>{fmt(naxt)}</b> | 💳 Karta: <b>{fmt(karta)}</b>\n"
        text += f"{emoji} <b>UMUMIY BALANS: {fmt(jami)} so'm</b>"
        await show(text, back())

    elif d == "hisoblash":
        naxt = user["naxt"]
        karta = user["karta"]
        qb = sum(q["summa"] for q in user["qarz_berganlarim"])
        qm = sum(q["summa"] for q in user["mening_qarzim"])
        jami = naxt + karta + qb - qm
        emoji = "✅" if jami >= 0 else "⚠️"

        # Hisobotni saqlash
        save_daily_report(uid, user)

        text = (
            f"{status(user)}\n{'─'*28}\n"
            f"🧮 <b>Hisob-kitob:</b>\n"
            f"Naqt + Karta + Qarz berganlarim − Qarzim\n"
            f"{fmt(naxt)} + {fmt(karta)} + {fmt(qb)} − {fmt(qm)}\n\n"
            f"{emoji} <b>JAMI: {fmt(jami)} so'm</b>\n\n"
            f"💾 <i>Bugungi hisobot saqlandi ({today()})</i>"
        )
        await show(text, back())

    elif d == "hisobot":
        hisobotlar = user.get("hisobotlar", {})
        if not hisobotlar:
            await show(
                "📈 <b>Kunlik hisobot</b>\n\n"
                "Hali hisobot yo'q.\n"
                "<i>🧮 Hisoblash tugmasini bosganda har kuni saqlanib boradi.</i>",
                back()
            )
            return
        await show(
            "📈 <b>Kunlik hisobot tarixi</b>\n\nKunni tanlang:",
            hisobot_menu(hisobotlar)
        )

    elif d.startswith("h_"):
        sana = d[2:]
        hisobotlar = user.get("hisobotlar", {})
        if sana not in hisobotlar:
            await show("❌ Hisobot topilmadi.", back())
            return
        h = hisobotlar[sana]
        emoji = "✅" if h["jami"] >= 0 else "⚠️"
        text = (
            f"📈 <b>{sana} — Kunlik hisobot</b>\n"
            f"🕐 Vaqt: {h.get('vaqt', '--')}\n\n"
            f"{'━'*20}\n"
            f"💵 Naqt pul:          <b>{fmt(h['naxt'])}</b> so'm\n"
            f"💳 Karta:              <b>{fmt(h['karta'])}</b> so'm\n"
            f"📤 Qarz berganlarim:  <b>{fmt(h['qarz_bergan'])}</b> so'm\n"
            f"📥 Mening qarzim:     <b>{fmt(h['mening_qarz'])}</b> so'm\n"
            f"{'━'*20}\n"
            f"{emoji} <b>JAMI: {fmt(h['jami'])} so'm</b>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Hisobotlarga qaytish", callback_data="hisobot")],
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="menu")],
        ])
        await show(text, keyboard)

# ─── Matn handler ─────────────────────────────────────────────────────────────

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    step = user.get("step")
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    try:
        await update.message.delete()
    except:
        pass

    if not step:
        await send_msg(context, chat_id, uid, user, "Menyudan kategoriya tanlang:", main_menu())
        return

    if step == "naxt":
        amount = parse_amount(text)
        if amount is None:
            await send_msg(context, chat_id, uid, user, "❌ Faqat raqam kiriting. Masalan: 500000")
            return
        user["naxt"] = amount
        user["step"] = None
        await send_msg(context, chat_id, uid, user, f"✅ <b>Naqt pul</b> = <b>{fmt(amount)} so'm</b> saqlandi!\n\n" + status(user), main_menu())

    elif step == "karta":
        amount = parse_amount(text)
        if amount is None:
            await send_msg(context, chat_id, uid, user, "❌ Faqat raqam kiriting. Masalan: 1500000")
            return
        user["karta"] = amount
        user["step"] = None
        await send_msg(context, chat_id, uid, user, f"✅ <b>Karta</b> = <b>{fmt(amount)} so'm</b> saqlandi!\n\n" + status(user), main_menu())

    elif step == "bergan_ism":
        user["temp"]["ism"] = text
        user["step"] = "bergan_summa"
        await send_msg(context, chat_id, uid, user, f"👤 <b>{text}</b>\n\n💰 Qancha so'm qarz berdingiz?")

    elif step == "bergan_summa":
        amount = parse_amount(text)
        if amount is None:
            await send_msg(context, chat_id, uid, user, "❌ Faqat raqam kiriting:")
            return
        user["temp"]["summa"] = amount
        user["step"] = "bergan_qaytarish"
        await send_msg(context, chat_id, uid, user, f"💰 <b>{fmt(amount)} so'm</b>\n\n⏰ Qachon qaytarishi kerak?\n<i>Masalan: 15.05.2025</i>")

    elif step == "bergan_qaytarish":
        qarz = {"ism": user["temp"]["ism"], "summa": user["temp"]["summa"], "sana": datetime.now().strftime("%d.%m.%Y"), "qaytarish": text}
        user["qarz_berganlarim"].append(qarz)
        user["step"] = None
        user["temp"] = {}
        await send_msg(context, chat_id, uid, user,
            f"✅ <b>Saqlandi!</b>\n\n👤 <b>{qarz['ism']}</b>\n💰 {fmt(qarz['summa'])} so'm\n📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}",
            main_menu()
        )

    elif step == "mening_ism":
        user["temp"]["ism"] = text
        user["step"] = "mening_summa"
        await send_msg(context, chat_id, uid, user, f"👤 <b>{text}</b>\n\n💰 Qancha so'm qarz oldingiz?")

    elif step == "mening_summa":
        amount = parse_amount(text)
        if amount is None:
            await send_msg(context, chat_id, uid, user, "❌ Faqat raqam kiriting:")
            return
        user["temp"]["summa"] = amount
        user["step"] = "mening_qaytarish"
        await send_msg(context, chat_id, uid, user, f"💰 <b>{fmt(amount)} so'm</b>\n\n⏰ Qachon qaytarasiz?\n<i>Masalan: 20.06.2025</i>")

    elif step == "mening_qaytarish":
        qarz = {"ism": user["temp"]["ism"], "summa": user["temp"]["summa"], "sana": datetime.now().strftime("%d.%m.%Y"), "qaytarish": text}
        user["mening_qarzim"].append(qarz)
        user["step"] = None
        user["temp"] = {}
        await send_msg(context, chat_id, uid, user,
            f"✅ <b>Saqlandi!</b>\n\n👤 <b>{qarz['ism']}</b>\n💰 {fmt(qarz['summa'])} so'm\n📅 {qarz['sana']} | ⏰ {qarz['qaytarish']}",
            main_menu()
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()