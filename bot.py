import os
import json
import logging
from datetime import datetime, date, timezone, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "/home/clawadmin/clawbot/data.json"
PACIFIC = timezone(timedelta(hours=-7))
START_DATE = date(2026, 5, 21)
START_WEIGHT = 125.0
TARGET_WEIGHT = 95.0

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"days": {}, "current_day": 0, "start_date": None, "started": False}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_today():
    return str(datetime.now(PACIFIC).date())

def is_owner(update: Update):
    return update.effective_user.id == OWNER_CHAT_ID

def get_day_template():
    return {
        "workout1": False,
        "workout2": False,
        "outdoor": False,
        "diet": False,
        "water": False,
        "reading": False,
        "photo": False,
        "weight": None,
        "complete": False
    }

def ensure_today(data):
    today = get_today()
    if today not in data["days"]:
        data["days"][today] = get_day_template()
        save_data(data)
    return today

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text(
        "👊 ClawBot Online.\n\n"
        "Commands:\n"
        "/checkin — Daily 75 Hard check-in\n"
        "/weight [kg] — Log weight\n"
        "/status — Today's status\n"
        "/week — Weekly summary\n"
        "/streak — Current streak\n"
        "/startprogram — Start 75 Hard manually\n"
    )

async def startprogram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await _startprogram(context)

async def _startprogram(context):
    data = load_data()
    data["start_date"] = get_today()
    data["current_day"] = 1
    data["started"] = True
    save_data(data)
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=(
            "🔥 75 HARD — DAY 1 BEGINS NOW\n\n"
            f"Start date: {get_today()}\n"
            f"Start weight: {START_WEIGHT}kg\n"
            f"Target weight: {TARGET_WEIGHT}kg\n\n"
            "Every single day you must complete:\n"
            "✅ Workout 1 — 45 mins minimum\n"
            "✅ Workout 2 — 45 mins minimum, MUST be outdoor\n"
            "✅ OMAD diet — no cheat meals, no alcohol\n"
            "✅ 1 gallon of water\n"
            "✅ 10 pages of non-fiction\n"
            "✅ Progress photo\n\n"
            "Miss one task = restart from Day 1.\n"
            "No exceptions. No negotiations.\n\n"
            "Use /checkin to log tasks daily.\n"
            "Let's go. 💪"
        )
    )

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    data = load_data()
    today = ensure_today(data)
    day = data["days"][today]

    keyboard = [
        ["✅ Workout 1", "✅ Workout 2"],
        ["✅ Outdoor workout", "✅ Diet"],
        ["✅ Water (1 gallon)", "✅ Reading (10 pages)"],
        ["✅ Photo taken", "📊 View Status"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"📋 Day {data.get('current_day', 0)}/75 — {today}\n\n"
        f"Workout 1: {'✅' if day['workout1'] else '❌'}\n"
        f"Workout 2: {'✅' if day['workout2'] else '❌'}\n"
        f"Outdoor: {'✅' if day['outdoor'] else '❌'}\n"
        f"Diet: {'✅' if day['diet'] else '❌'}\n"
        f"Water: {'✅' if day['water'] else '❌'}\n"
        f"Reading: {'✅' if day['reading'] else '❌'}\n"
        f"Photo: {'✅' if day['photo'] else '❌'}\n\n"
        "Tap to log completed tasks:",
        reply_markup=reply_markup
    )

async def handle_checkin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    data = load_data()
    today = ensure_today(data)
    text = update.message.text
    day = data["days"][today]

    mapping = {
        "✅ Workout 1": "workout1",
        "✅ Workout 2": "workout2",
        "✅ Outdoor workout": "outdoor",
        "✅ Diet": "diet",
        "✅ Water (1 gallon)": "water",
        "✅ Reading (10 pages)": "reading",
        "✅ Photo taken": "photo"
    }

    if text in mapping:
        key = mapping[text]
        day[key] = True

        completed = sum(1 for k, v in day.items()
                       if k not in ["weight", "complete"] and v is True)
        total = 7

        if completed == total:
            day["complete"] = True
            data["current_day"] = data.get("current_day", 0) + 1
            save_data(data)
            await update.message.reply_text(
                f"🔥 DAY {data['current_day'] - 1} COMPLETE!\n"
                f"All 7 tasks done.\n"
                f"{data['current_day'] - 1}/75 days in the books.\n\n"
                f"{'🏆 HALFWAY THERE!' if data['current_day'] - 1 == 37 else ''}"
                f"Don't stop now."
            )
        else:
            save_data(data)
            await update.message.reply_text(
                f"✅ Logged! {completed}/{total} tasks done today.\n"
                f"{total - completed} remaining."
            )

    elif text == "📊 View Status":
        await status(update, context)

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    try:
        kg = float(context.args[0])
        data = load_data()
        today = ensure_today(data)
        data["days"][today]["weight"] = kg
        save_data(data)

        lost = START_WEIGHT - kg
        remaining = kg - TARGET_WEIGHT
        progress_pct = (lost / (START_WEIGHT - TARGET_WEIGHT)) * 100

        await update.message.reply_text(
            f"⚖️ Weight logged: {kg}kg\n\n"
            f"📉 Lost so far: {lost:.1f}kg\n"
            f"🎯 Target: {TARGET_WEIGHT}kg\n"
            f"📊 Remaining: {remaining:.1f}kg\n"
            f"🏆 Progress: {progress_pct:.1f}%\n\n"
            f"{'💪 Keep going!' if lost > 0 else '🔥 Day 1 logged. Lets go.'}"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /weight 124.5")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    data = load_data()
    today = get_today()

    if today not in data["days"]:
        await update.message.reply_text("No check-in today yet. Use /checkin")
        return

    day = data["days"][today]
    completed = sum(1 for k, v in day.items()
                   if k not in ["weight", "complete"] and v is True)

    missing = []
    checks = {
        "workout1": "Workout 1",
        "workout2": "Workout 2",
        "outdoor": "Outdoor workout",
        "diet": "Diet",
        "water": "Water",
        "reading": "Reading",
        "photo": "Photo"
    }
    for key, label in checks.items():
        if not day.get(key):
            missing.append(label)

    msg = (
        f"📊 Day {data.get('current_day', 0)}/75 — {today}\n\n"
        f"Workout 1: {'✅' if day.get('workout1') else '❌'}\n"
        f"Workout 2: {'✅' if day.get('workout2') else '❌'}\n"
        f"Outdoor: {'✅' if day.get('outdoor') else '❌'}\n"
        f"Diet: {'✅' if day.get('diet') else '❌'}\n"
        f"Water: {'✅' if day.get('water') else '❌'}\n"
        f"Reading: {'✅' if day.get('reading') else '❌'}\n"
        f"Photo: {'✅' if day.get('photo') else '❌'}\n"
        f"Weight: {day.get('weight', 'not logged')}kg\n\n"
        f"Progress: {completed}/7 tasks\n"
    )

    if missing:
        msg += f"\n⚠️ Still needed:\n" + "\n".join(f"• {m}" for m in missing)
    else:
        msg += "\n✅ All tasks complete for today!"

    await update.message.reply_text(msg)

async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    data = load_data()
    completed_days = sum(1 for d in data["days"].values() if d.get("complete"))
    current_day = data.get("current_day", 0)

    weights = [d["weight"] for d in data["days"].values()
               if d.get("weight") is not None]
    weight_msg = ""
    if weights:
        lost = START_WEIGHT - weights[-1]
        weight_msg = f"Weight lost: {lost:.1f}kg\nCurrent: {weights[-1]}kg\n"

    await update.message.reply_text(
        f"🔥 75 Hard Progress\n\n"
        f"Current day: {current_day}/75\n"
        f"Completed days: {completed_days}\n"
        f"Start date: {data.get('start_date', 'Not started')}\n"
        f"{weight_msg}\n"
        f"{'💪 Keep going!' if current_day > 0 else 'Program starts May 21.'}"
    )

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    data = load_data()
    days = list(data["days"].items())[-7:]

    summary = "📅 Weekly Summary\n\n"
    total_complete = 0
    weights = []

    for day_date, day_data in days:
        complete = day_data.get("complete", False)
        total_complete += 1 if complete else 0
        w = day_data.get("weight")
        if w:
            weights.append(w)
        summary += f"{day_date}: {'✅' if complete else '❌'}"
        if w:
            summary += f" | {w}kg"
        summary += "\n"

    summary += f"\nDays complete: {total_complete}/7\n"

    if len(weights) >= 2:
        weight_change = weights[-1] - weights[0]
        summary += f"Weight change this week: {weight_change:+.1f}kg\n"

    if total_complete < 7:
        summary += "\n⚠️ Missed days this week. 75 Hard has no mercy — missed day = restart."
    else:
        summary += "\n🔥 Perfect week. You're built different."

    await update.message.reply_text(summary)

# --- SCHEDULED NOTIFICATIONS ---

async def auto_start_program(context):
    data = load_data()
    if not data.get("started"):
        await _startprogram(context)

async def morning_notification(context):
    data = load_data()
    if not data.get("started"):
        return
    today = get_today()
    day_num = data.get("current_day", 0)
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=(
            f"☀️ Day {day_num}/75 — {today}\n\n"
            "Time to attack the day.\n\n"
            "Your tasks:\n"
            "□ Workout 1 (45 min)\n"
            "□ Workout 2 (45 min outdoor)\n"
            "□ OMAD — clean eating\n"
            "□ 1 gallon water\n"
            "□ 10 pages reading\n"
            "□ Progress photo\n\n"
            "Use /checkin to log. No excuses."
        )
    )

async def evening_check(context):
    data = load_data()
    if not data.get("started"):
        return
    today = get_today()
    if today not in data["days"]:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text="🌙 Evening check.\n\nNo tasks logged today. Use /checkin now.\n\nYou still have time."
        )
        return

    day = data["days"][today]
    completed = sum(1 for k, v in day.items()
                   if k not in ["weight", "complete"] and v is True)
    missing = []
    checks = {
        "workout1": "Workout 1",
        "workout2": "Workout 2",
        "outdoor": "Outdoor workout",
        "diet": "Diet",
        "water": "Water (1 gallon)",
        "reading": "Reading (10 pages)",
        "photo": "Progress photo"
    }
    for key, label in checks.items():
        if not day.get(key):
            missing.append(label)

    if not missing:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=f"🌙 Evening check — Day {data.get('current_day', 0)}/75\n\n✅ All tasks complete! Solid day."
        )
    else:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(
                f"🌙 Evening check — {completed}/7 tasks done.\n\n"
                f"⚠️ Still missing:\n" +
                "\n".join(f"• {m}" for m in missing) +
                "\n\nYou have until midnight.\nUse /checkin to log. No excuses."
            )
        )

async def late_night_warning(context):
    data = load_data()
    if not data.get("started"):
        return
    today = get_today()
    if today not in data["days"]:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text="⚠️ 10 PM. Nothing logged today.\n\nDo your tasks NOW or Day 1 restarts tomorrow.\n\nThis is the moment that separates you from everyone else."
        )
        return

    day = data["days"][today]
    if not day.get("complete"):
        missing = []
        checks = {
            "workout1": "Workout 1",
            "workout2": "Workout 2",
            "outdoor": "Outdoor workout",
            "diet": "Diet",
            "water": "Water",
            "reading": "Reading",
            "photo": "Photo"
        }
        for key, label in checks.items():
            if not day.get(key):
                missing.append(label)

        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(
                "⚠️ 10 PM WARNING\n\n"
                "Still incomplete:\n" +
                "\n".join(f"• {m}" for m in missing) +
                "\n\n2 hours left.\nGet it done."
            )
        )

async def sunday_summary(context):
    data = load_data()
    if not data.get("started"):
        return
    days = list(data["days"].items())[-7:]
    total_complete = sum(1 for _, d in days if d.get("complete"))
    weights = [d["weight"] for _, d in days if d.get("weight")]

    msg = f"📊 Weekly Review — Day {data.get('current_day', 0)}/75\n\n"
    for day_date, day_data in days:
        msg += f"{day_date}: {'✅' if day_data.get('complete') else '❌'}"
        if day_data.get("weight"):
            msg += f" | {day_data['weight']}kg"
        msg += "\n"

    msg += f"\nComplete: {total_complete}/7 days\n"
    if len(weights) >= 2:
        msg += f"Weight change: {weights[-1] - weights[0]:+.1f}kg\n"
    if total_complete == 7:
        msg += "\n🔥 Perfect week. Stay dangerous."
    else:
        msg += f"\n⚠️ {7 - total_complete} missed days. 75 Hard = restart on any miss."

    await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("startprogram", startprogram))
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("weight", weight))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("streak", streak))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_checkin_buttons))

    jq = app.job_queue

    # Auto-start on May 21 at 5:00 AM Pacific
    auto_start_time = datetime(2026, 5, 21, 5, 0, 0, tzinfo=PACIFIC)
    jq.run_once(auto_start_program, when=auto_start_time)

    # Daily notifications
    jq.run_daily(morning_notification, time=datetime.strptime("05:00", "%H:%M").time().replace(tzinfo=PACIFIC))
    jq.run_daily(evening_check, time=datetime.strptime("20:00", "%H:%M").time().replace(tzinfo=PACIFIC))
    jq.run_daily(late_night_warning, time=datetime.strptime("22:00", "%H:%M").time().replace(tzinfo=PACIFIC))
    jq.run_daily(sunday_summary, time=datetime.strptime("08:00", "%H:%M").time().replace(tzinfo=PACIFIC), days=(6,))

    print("ClawBot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
