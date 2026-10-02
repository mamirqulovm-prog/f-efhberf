# 🛡️ Telegram Admin Bot — Render + UptimeRobot Deploy

## 📁 Fayllar
```
bot.py           ← Asosiy bot
keep_alive.py    ← Render uxlamaslik uchun Flask server
requirements.txt ← Kutubxonalar
```

---

## 🚀 RENDER.COM DA DEPLOY (15 daqiqa)

### 1-qadam — GitHub ga yuklash
1. github.com → "New repository" → nom bering (masalan: `admin-bot`)
2. Uchala faylni yuklang: `bot.py`, `keep_alive.py`, `requirements.txt`

### 2-qadam — Render.com
1. render.com → GitHub bilan kirish
2. **"New +"** → **"Web Service"**
3. GitHub repo ni tanlang
4. Quyidagilarni to'ldiring:

| Maydon | Qiymat |
|--------|--------|
| Name | admin-bot |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python bot.py` |

5. **"Environment Variables"** bo'limiga o'ting:
   - Key: `BOT_TOKEN`
   - Value: `sizning_tokeningiz_bu_yerga`

6. **"Create Web Service"** tugmasini bosing
7. Deploy tugagandan so'ng URL ni nusxalang (masalan: `https://admin-bot-xxxx.onrender.com`)

---

## ⏰ UPTIMEROBOT.COM (Render uxlamaslik uchun)

1. uptimerobot.com → bepul ro'yxat
2. **"Add New Monitor"** tugmasi
3. To'ldiring:

| Maydon | Qiymat |
|--------|--------|
| Monitor Type | HTTP(s) |
| Friendly Name | Admin Bot |
| URL | `https://admin-bot-xxxx.onrender.com` (Render URL) |
| Monitoring Interval | Every 5 minutes |

4. **"Create Monitor"** — tayyor!

> UptimeRobot har 5 daqiqada `/health` endpoint ga ping qiladi.
> Bu Render ni uxlatmaydi. Bot 24/7 ishlaydi.

---

## 📋 BUYRUQLAR

| Buyruq | Vazifa |
|--------|--------|
| `/menu` | Interaktiv admin panel |
| `/ban @user sabab` | Doimiy ban |
| `/tempban @user 1h sabab` | Vaqtli ban (30m/1h/1d/7d) |
| `/unban @user` | Banni olib tashlash |
| `/banlist` | Banlangan ro'yxat |
| `/mute @user 1h sabab` | Mute |
| `/unmute @user` | Unmute |
| `/mutelist` | Mute ro'yxat |
| `/warn @user sabab` | Ogohlantirish (3 ta = auto ban) |
| `/unwarn @user` | Warnni o'chirish |
| `/warnlist` | Warn ro'yxat |
| `/kick @user sabab` | Guruhdan chiqarish |
| `/logs` | Oxirgi 15 ta amal |
| `/help` | Yordam |

---

## ⚙️ BOT SOZLAMALARI (@BotFather)

```
/setcommands

menu - Admin panel
ban - Doimiy ban
tempban - Vaqtli ban
unban - Banni olib tashlash
banlist - Banlangan ro'yxat
mute - Mute
unmute - Unmute
mutelist - Mute ro'yxat
warn - Ogohlantirish
unwarn - Warnni o'chirish
warnlist - Warn ro'yxat
kick - Guruhdan chiqarish
logs - Amallar tarixi
help - Yordam
```

## ⚠️ MUHIM
- Bot guruhda **admin** bo'lishi kerak
- Admin huquqlari: members cheklash, chiqarish, xabarlarni o'chirish
- `/setprivacy` → `DISABLE` qiling (@BotFather da) — bot barcha xabarlarni ko'rishi uchun
