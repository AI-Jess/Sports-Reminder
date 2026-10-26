# Sports Reminder 🏀

Every morning, a free GitHub job checks ESPN for women's college basketball games. If any match, it posts one message to Discord, and a tiny iPhone Shortcut texts the same message to the group chat.

**What counts as a match**
- Any game with **UConn, USC or South Carolina**, all season.
- Every NCAA tournament game from the **Sweet 16 through the National Championship** (the Women's NIT and other tournaments are skipped).

**What the message looks like** (real output for April 3, 2026):

```
🏀 Women's hoops today

• 🏆 Final Four: UConn vs South Carolina — 6:00 PM CT · ESPN
• 🏆 Final Four: UCLA vs Texas — 8:40 PM CT · ESPN
```

No matches → nothing is sent anywhere.

**How it flows**
1. ~7:30 AM CT — GitHub job checks ESPN, posts to Discord, saves the message.
2. 9:00 AM — your iPhone Shortcut grabs that message and texts the group.

---

## Part 1 — Discord (3 min)

1. In Discord: your server → **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**.
2. Name it `Hoops Reminder` and pick the channel.
3. Tap **Copy Webhook URL**.
4. On github.com, open this repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   - Name: `DISCORD_WEBHOOK`
   - Secret: paste the webhook URL → **Add secret**.

## Part 2 — A key so your phone can read the message (3 min)

The repo is private, so the Shortcut needs a read-only key.

1. github.com → your profile picture → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Name: `Hoops Shortcut`. Expiration: the longest option offered (set a reminder to renew it).
3. Repository access: **Only select repositories** → **Sports-Reminder**.
4. Permissions → Repository permissions → **Contents: Read-only**. Nothing else.
5. **Generate token** and copy it (starts with `github_pat_`). It's only shown once.

## Part 3 — The Shortcut (5 actions)

Shortcuts app → **+** → name it **Hoops Reminder**. Add:

1. **Format Date** → Date: **Current Date**, Date Format: **Custom**, Format String: `yyyyMMdd`
2. **Get Contents of URL** → URL:
   `https://api.github.com/repos/AI-Jess/Sports-Reminder/contents/days/`**Formatted Date**`.txt?ref=messages`
   (type the first part, insert the **Formatted Date** variable, then type the rest)
   Tap **Show More** → Method **GET** → **Headers**, add two:
   - `Authorization` → `Bearer ` followed by your token (one space after Bearer)
   - `Accept` → `application/vnd.github.raw`
3. **If** → **Contents of URL** **contains** `🏀`
4. Inside the If: **Send Message** → Message: **Contents of URL**, Recipients: your group chat. Tap the arrow and turn **Show When Run** off.
5. **End If** (added for you).

The 🏀 check means it only texts when there's a real message — no games, a missed job, or an error all mean silence.

## Part 4 — Test it

1. **Discord:** On GitHub, open **Actions** → **Daily reminder** → **Run workflow**. Date: `20260403`, keep **Post to Discord** ticked → **Run workflow**. In about a minute the Final Four message should appear in your channel.
2. **Phone:** In the Shortcut, temporarily swap action 1 for a **Text** action containing `20260403` (and fix the URL to use it). Set the recipient to just yourself and run it. You should get the same message as a text. Tap **Always Allow** if iOS asks about contacting GitHub.
3. Put action 1 back to **Format Date**, and the recipient back to the group.

## Part 5 — Run it every morning

Shortcuts → **Automation** → **+** → **Time of Day** → 9:00 AM, **Daily** → **Run Immediately**, **Notify When Run** off → pick **Hoops Reminder**.

The GitHub side already runs daily on its own.

---

## Changing teams

Edit `MY_TEAMS` near the top of `check_games.py` (or ask Claude to). Keep the pipes around each name: `|UConn|USC|South Carolina|Iowa|`. Names are ESPN's short team names ("UConn", not "Connecticut"). Nothing on the phone changes.

## Checking any date

**Actions** → **Daily reminder** → **Run workflow**, enter a date, untick **Post to Discord**. The result shows on the run page.

## If it stops working

- **No texts but Discord works** → the phone key probably expired; make a new one (Part 2) and paste it into the Shortcut header.
- **Nothing anywhere** → check the **Actions** tab for a red ❌ run.
