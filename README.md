# Sports Reminder 🏀

Every morning, a free GitHub job checks ESPN for women's college basketball and WNBA games. If any match, it posts one message to Discord, and a tiny iPhone Shortcut texts the same message to the group chat.

**What counts as a match** (set in `settings.json`)
- College: any **UConn, USC, South Carolina, LSU or Notre Dame** game, plus every NCAA tournament game from the **Sweet 16 on** (the Women's NIT is skipped).
- WNBA: any **Fever, Wings or Lynx** game, plus **every playoff game**.

**What the message looks like** (real output for April 3, 2026):

```
🏀 Women's hoops today

• 🏆 Final Four: UConn vs South Carolina — 6:00 PM CT · ESPN
• 🏆 Final Four: UCLA vs Texas — 8:40 PM CT · ESPN
```

No matches → nothing is sent anywhere.

**How it flows**
1. ~7:30 AM CT — GitHub job checks ESPN, posts the lineup to Discord (matchups link to ESPN game pages), and saves a link-free version for the phone.
2. 9:00 AM — your iPhone Shortcut grabs that message and texts the group.
3. ~10 min before the first game — Discord gets "⏰ First game tips off in 10 min!" with the lineup and game links. (Checked every 15 min during game hours; sent once a day. Change the lead time with `pregame_minutes_before` in `settings.json`.)

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

Shortcuts → **Automation** → **+** → **Time of Day** → 8:00 AM, **Daily** → **Run Immediately**, **Notify When Run** off → pick **Hoops Reminder**.

## Part 6 — On-time triggers (cron-job.org)

GitHub's free scheduler often runs hours late, so cron-job.org (free) starts the jobs on time instead. GitHub's own morning schedule stays as a backup; nothing ever posts twice.

1. **Key:** github.com/settings/personal-access-tokens/new → name `cron-job trigger` → Only select repositories → **Sports-Reminder** → Repository permissions → **Actions: Read and write** → Generate, copy.
2. **cron-job.org** → sign up → **Create cronjob**, twice:

| | Morning | Pregame |
|---|---|---|
| URL | `https://api.github.com/repos/AI-Jess/Sports-Reminder/actions/workflows/daily.yml/dispatches` | same, ending `pregame.yml/dispatches` |
| Schedule | Every day at 6:30 | Custom: minutes `0,15,30,45`, hours `10–21` |

Both, under **Advanced**: Time zone `America/Chicago` · Request method `POST` · Headers `Authorization: Bearer <key>`, `Accept: application/vnd.github+json`, `Content-Type: application/json` · Request body `{"ref":"main","inputs":{"scheduled":"true"}}`

A successful call returns HTTP **204**.

---

## Changing teams

Edit `settings.json` on GitHub (pencil icon) or ask Claude. Each league has a `my_teams` list:

- College: `"my_teams": ["UConn", "USC", "South Carolina", "LSU"]`
- WNBA: `"my_teams": ["Indiana Fever", "Dallas Wings", "Minnesota Lynx"]`

Add a name inside the brackets, in quotes, separated by commas. Nothing on the phone changes. A new league (e.g. NBA) is one more block in the same file.

## Checking any date

**Actions** → **Daily reminder** → **Run workflow**, enter a date, untick **Post to Discord**. The result shows on the run page.

## If it stops working

- **No texts but Discord works** → the phone key probably expired; make a new one (Part 2) and paste it into the Shortcut header.
- **Nothing anywhere** → check the **Actions** tab for a red ❌ run.
