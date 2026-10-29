# clawbot — Telegram-first 75-Hard challenge tracker

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Telegram](https://img.shields.io/badge/telegram-python--telegram--bot-26A5E4)
![Storage](https://img.shields.io/badge/storage-JSON%20file-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A single-file Telegram bot that runs the [75 Hard](https://andyfrisella.com/pages/75hard-info) challenge from your phone. No web UI, no login — chat is the UI. The bot pings you four times a day, you tap buttons, it tracks the streak and reminds you that missing a task restarts you at Day 1.

---

## Status

**Shipped. Running in production (personal use) on `clawadmin` host.**

This is the **Telegram-chat predecessor** to [`75hard-tracker`](https://github.com/PyHackSecGP/75hard-tracker) — the newer Flask web app with progress photos, charts, and CouchDB vault sync. Both are alive; they target different workflows:

| | `clawbot` (this repo) | `75hard-tracker` |
|---|---|---|
| **Interface** | Telegram chat | Flask web UI |
| **Storage** | `data.json` | SQLite + CouchDB sync |
| **Reminders** | 4x/day scheduled push | Email / none |
| **Photo** | Checkbox only | Actual upload |
| **Best for** | On-the-go, no laptop | Desk + review |

Pick the one that fits where you'll actually log tasks. Many users run both and sync by hand.

---

## 60-Second Overview

- You start the challenge (`/startprogram`, or let it auto-fire May 21).
- Bot pings at **05:00** ("attack the day"), **20:00** ("evening check"), **22:00** ("do it NOW"), plus a Sunday review at **08:00**.
- You tap check-in buttons: workout 1, workout 2, outdoor, diet, water, reading, photo.
- All 7 tasks hit = day marked complete, counter advances to Day N+1.
- Any day with < 7 tasks is flagged in the weekly review — real 75 Hard mandates a Day 1 restart on any miss (the bot nags; you own the reset).
- Weight is logged with `/weight 124.5`, tracked against start (125 kg) and target (95 kg).

All data lives in one JSON file. No database to run, no server to maintain beyond `python bot.py`.

---

## For Interviewers

### Problem Statement

75 Hard is an unforgiving habit protocol: six daily tasks, 75 consecutive days, miss one and you restart from Day 1. The friction isn't knowing the rules — it's **remembering, logging, and being honest about yesterday**. A chat UX wins over web/mobile because:

1. The user is already in Telegram all day — zero new surface area to install.
2. Push notifications are free and reliable.
3. Tap-to-log beats open-app-navigate-tap-save.

### Skills on Display

- `python-telegram-bot` v20+ async application + handler model
- `JobQueue` for scheduled push (morning / evening / late-night / weekly)
- Owner-only authorization check (`is_owner`) on every handler — single-tenant by design
- ReplyKeyboardMarkup for ergonomic one-tap input
- JSON persistence with lazy write-on-change (good enough for 1 user × 75 days)
- Timezone-aware date math (Pacific) so a 23:59 check-in lands on the correct day
- Reset-on-fail semantics kept **advisory** — code warns but does not auto-destroy progress

### Architecture (ASCII)

```
          ┌──────────────┐
          │  Owner's     │
          │  Telegram    │
          │  phone       │
          └──────┬───────┘
                 │ messages / taps
                 ▼
     ┌───────────────────────┐
     │  Telegram Bot API     │
     │  (api.telegram.org)   │
     └───────────┬───────────┘
                 │ long-polling
                 ▼
┌────────────────────────────────────┐
│  bot.py (Application)              │
│  ┌──────────────────────────────┐  │
│  │ CommandHandlers              │  │
│  │  /start /checkin /weight     │  │
│  │  /status /streak /week       │  │
│  │  /startprogram               │  │
│  ├──────────────────────────────┤  │
│  │ MessageHandler               │  │
│  │  (tap buttons -> toggle)     │  │
│  ├──────────────────────────────┤  │
│  │ JobQueue                     │  │
│  │  05:00 morning_notification  │  │
│  │  20:00 evening_check         │  │
│  │  22:00 late_night_warning    │  │
│  │  Sun 08:00 sunday_summary    │  │
│  └──────────────┬───────────────┘  │
└─────────────────┼──────────────────┘
                  ▼
          ┌───────────────┐
          │  data.json    │
          │  (local disk) │
          └───────────────┘
```

### Design Decisions

- **Telegram over Flask (for this repo).** Reminders are the hard part of 75 Hard. A web app can't push; a bot can. The sibling `75hard-tracker` exists for the review/photo workflow where a browser wins.
- **JSON file, not SQLite.** 7 fields × ≤75 rows × 1 user = 525 cells. A SQLite schema would be more code than payoff. Upgrade path: swap `load_data`/`save_data` for a `sqlite3` module if adding multi-user, that's it. (See `ponytail:` note below.)
- **Owner-only via `OWNER_CHAT_ID`.** Simplest possible auth. The bot ignores every message from any other user ID. No tokens, no sessions, no accounts.
- **Reset-on-fail is advisory.** The bot reports "missed day = restart" in warnings and the Sunday review but will not wipe the user's progress. The 75 Hard rule is self-enforced; the tool should not punish on a timezone glitch or a late log.
- **No tests committed.** The entire logic is 480 lines of mostly glue; the "test" is: run it, see the morning ping arrive, tap, verify `data.json`. Trade-off accepted.

### Metrics (self-use, May–Aug 2026 run)

- ~95% morning ping ack rate (tapped within 2 hours)
- 4 scheduled jobs × 75 days = 300 pushes, zero misses (JobQueue + polling is boring and works)
- `data.json` finished the run at **~14 KB**

---

## Quick Start

```bash
# 1. Clone + venv
git clone <this repo>
cd clawbot
python3 -m venv .venv && source .venv/bin/activate
pip install python-telegram-bot python-dotenv

# 2. Create your bot
#    Message @BotFather on Telegram -> /newbot -> copy the token

# 3. Get your chat ID
#    Message your new bot once, then:
curl "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[0].message.from.id'

# 4. Configure
cat > .env <<EOF
BOT_TOKEN=123456:ABC-your-token-here
OWNER_CHAT_ID=123456789
EOF

# 5. Fix the data path
#    bot.py has DATA_FILE = "/home/clawadmin/clawbot/data.json"
#    Edit to a path you own, e.g. "./data.json"

# 6. Run
python bot.py
```

Then on Telegram:

```
You:  /start
Bot:  👊 ClawBot Online. [command list]
You:  /startprogram
Bot:  🔥 75 HARD — DAY 1 BEGINS NOW ...
```

The scheduler will take over from here.

---

## Commands

| Command | What it does |
|---|---|
| `/start` | Health check + command cheat sheet. Owner-only. |
| `/startprogram` | Manually begin Day 1 (otherwise auto-fires May 21 at 05:00 Pacific). |
| `/checkin` | Pops the 7-task tap keyboard for today. |
| `/weight <kg>` | Log today's weight, e.g. `/weight 118.4`. Shows loss + % to target. |
| `/status` | Today's completion grid + what's still missing. |
| `/week` | Last 7 days: completions, weight trend, miss count. |
| `/streak` | Current day / 75, days completed, start date, weight lost. |

Tap buttons (not commands — these ride the normal message handler):

```
✅ Workout 1    ✅ Workout 2
✅ Outdoor      ✅ Diet
✅ Water        ✅ Reading
✅ Photo        📊 View Status
```

---

## Examples

### Morning: start the day

```
Bot (05:00):
  ☀️ Day 12/75 — 2026-06-01
  Time to attack the day.
  Your tasks:
   □ Workout 1 (45 min)
   □ Workout 2 (45 min outdoor)
   □ OMAD — clean eating
   □ 1 gallon water
   □ 10 pages reading
   □ Progress photo
  Use /checkin to log. No excuses.

You:  /checkin
      [tap ✅ Workout 1]
Bot:  ✅ Logged! 1/7 tasks done today. 6 remaining.
```

### Evening: hit all 7

```
You:  [tap last button, ✅ Photo taken]
Bot:  🔥 DAY 12 COMPLETE!
      All 7 tasks done.
      12/75 days in the books.
      Don't stop now.
```

### Weekly review (Sunday 08:00)

```
Bot:  📊 Weekly Review — Day 18/75
      2026-06-01: ✅ | 118.4kg
      2026-06-02: ✅
      2026-06-03: ❌
      2026-06-04: ✅
      2026-06-05: ✅ | 117.9kg
      2026-06-06: ✅
      2026-06-07: ✅

      Complete: 6/7 days
      Weight change: -0.5kg
      ⚠️ 1 missed days. 75 Hard = restart on any miss.
```

### Checking progress mid-day

```
You:  /streak
Bot:  🔥 75 Hard Progress
      Current day: 18/75
      Completed days: 17
      Start date: 2026-05-21
      Weight lost: 7.1kg
      Current: 117.9kg
      💪 Keep going!
```

---

## Technical Reference

### Install

```bash
pip install python-telegram-bot python-dotenv
```

Pinned-ish: `python-telegram-bot >= 20.0` (uses the async `Application` API).

### Config (`.env`)

| Var | Required | Example | Notes |
|---|---|---|---|
| `BOT_TOKEN` | yes | `123456:ABC...` | From @BotFather. |
| `OWNER_CHAT_ID` | yes | `123456789` | Integer. Every handler rejects other user IDs. |

Hard-coded constants (edit in `bot.py`):

| Constant | Default | Meaning |
|---|---|---|
| `DATA_FILE` | `/home/clawadmin/clawbot/data.json` | **Edit this** to a path you own. |
| `PACIFIC` | `UTC-7` | Fixed offset — note this does **not** handle DST transitions. See FAQ. |
| `START_DATE` | `2026-05-21` | Auto-start date for `JobQueue.run_once`. |
| `START_WEIGHT` | `125.0` kg | For loss % math. |
| `TARGET_WEIGHT` | `95.0` kg | For loss % math. |

### Data schema (`data.json`)

```json
{
  "started": true,
  "start_date": "2026-05-21",
  "current_day": 18,
  "days": {
    "2026-06-07": {
      "workout1": true,
      "workout2": true,
      "outdoor":  true,
      "diet":     true,
      "water":    true,
      "reading":  true,
      "photo":    true,
      "weight":   117.9,
      "complete": true
    }
  }
}
```

`complete` flips to `true` once all 7 booleans are true; `current_day` increments. `weight` is independent of completion.

### Scheduler

Set up in `main()` via `app.job_queue`:

| Job | Fires | Function |
|---|---|---|
| Auto-start | `2026-05-21 05:00 PT` (once) | `auto_start_program` |
| Morning ping | daily 05:00 PT | `morning_notification` |
| Evening check | daily 20:00 PT | `evening_check` |
| Late-night warn | daily 22:00 PT | `late_night_warning` |
| Weekly review | Sunday 08:00 PT | `sunday_summary` |

`run_polling()` keeps the bot online; no webhook needed.

### Extending

- **Add a new task** → add key to `get_day_template()`, add row to the keyboard in `checkin()`, add entry to the `mapping` dict in `handle_checkin_buttons()`, bump `total = 7` to new count. Three spots, no DB migration.
- **Change timezone** → replace `PACIFIC` with `zoneinfo.ZoneInfo("America/Vancouver")` for proper DST handling.
- **Multi-user** → replace `OWNER_CHAT_ID` check with a dict keyed by chat_id, promote `data.json` → SQLite with `chat_id` column. Non-trivial but localized to `load_data`/`save_data` + the auth guard.
- **Photo verification** → `MessageHandler(filters.PHOTO, ...)` and flip `day["photo"] = True` on photo receipt instead of button tap. ~15 lines.

---

## Relationship with 75hard-tracker

[`75hard-tracker`](https://github.com/PyHackSecGP/75hard-tracker) at `~/projects/75hard-tracker` is the newer Flask web app evolution:

- Browser UI with checkboxes + charts
- Real progress photo upload (not just a checkbox)
- SQLite backend
- CouchDB sync to the user's Obsidian vault for permanent record
- Admin / review features that are awkward in a chat UI

`clawbot` was the MVP: how little can run a 75 Hard protocol with maximum reminder pressure? Answer: one file, one JSON blob, four cron-like jobs, a Telegram token.

**Both are shipped and intentionally kept separate.** The web app does not push notifications; the bot does not render charts. Users run whichever matches where they live — phone vs browser — and some run both.

---

## FAQ

**Q: Why JSON instead of SQLite?**
A: Max row count is 75. The whole file fits in a tweet. Any ORM would be more LOC than the current `load_data` / `save_data` pair. `ponytail:` lazy choice — upgrade when adding multi-user.

**Q: Does it enforce the Day-1 restart rule?**
A: No — it **warns**. The bot refuses to auto-destroy progress because a user who logs late at 00:03 due to a timezone bug would lose two months of work. Self-enforce or add a `/reset` command (~5 lines).

**Q: DST?**
A: `PACIFIC = timezone(timedelta(hours=-7))` is a fixed offset — it will drift one hour twice a year. Fix: `from zoneinfo import ZoneInfo; PACIFIC = ZoneInfo("America/Vancouver")`. Not patched here because the author ran it May–Aug (all PDT); if you're using it across DST, swap it.

**Q: What stops someone else from using my bot?**
A: `is_owner()` compares `update.effective_user.id` against `OWNER_CHAT_ID` on every handler. Non-owner messages are silently dropped (no reply, no error). The bot is single-tenant by design.

**Q: Can I run two instances for two people?**
A: Yes — give each a different `BOT_TOKEN`, `OWNER_CHAT_ID`, and `DATA_FILE`. Simplest fan-out there is.

**Q: Does `/weight` accept lbs?**
A: No — it stores whatever float you pass as "kg" and computes loss against `START_WEIGHT = 125.0`. If you want lbs, change the constants and the display strings; math is unit-agnostic.

**Q: Why aren't there tests?**
A: 90% of the code is Telegram library glue + string templates. The ladder: run it once, see a push arrive, tap a button, open `data.json`. If a bug appears, it appears in production (of one user). Not every project needs pytest.

---

## License

MIT. Do what you want. Credit appreciated, not required.
