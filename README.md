# Sports Reminder 🏀

A daily iOS Shortcut that checks ESPN for women's college basketball games and, if any match, posts one message to a Discord channel and texts the group chat.

**What counts as a match**
- Any game with **UConn, USC or South Carolina**, all season.
- Every NCAA tournament game from the **Sweet 16 through the National Championship** (the Women's NIT and other tournaments are skipped).

**What the message looks like** (real output for April 3, 2026):

```
🏀 Women's hoops today

• 🏆 Final Four: UConn vs South Carolina — 6:00 PM CT · ESPN
• 🏆 Final Four: UCLA vs Texas — 8:40 PM CT · ESPN
```

No matches → nothing is sent.

---

## Part 1 — Make the Discord webhook (2 min)

1. In Discord, open your server → **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**.
2. Name it `Hoops Reminder`, set the channel to the one you want (e.g. the Wordle channel or a new #sports one).
3. Tap **Copy Webhook URL**. Paste it into Notes for a minute — you'll need it in step 26.

Keep that URL private; anyone with it can post to the channel.

---

## Part 2 — Build the Shortcut

In the **Shortcuts** app, tap **+**, name it **Hoops Reminder**. Add these actions in order (search each name in the action search bar). Variable names matter — use them exactly.

### Setup

1. **Text** → type `|UConn|USC|South Carolina|`
2. **Set Variable** → name `MyTeams`
3. **Date** → Current Date
4. **Format Date** → Date Format: **Custom**, Format String: `yyyyMMdd`
5. **Set Variable** → name `Day`
6. **URL** → `https://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard?dates=` then insert the **Day** variable, then `&groups=50&limit=300`
7. **Get Contents of URL** (leave as GET)
8. **Get Dictionary Value** → Get **Value** for `events` in **Contents of URL**
9. **Repeat with Each** → item in **Dictionary Value**

### Inside the Repeat (one pass per game)

10. **Get Dictionary Value** → Value for `competitions` in **Repeat Item**
11. **Get Item from List** → **First Item**
12. **Set Variable** → `Comp`
13. **Get Dictionary Value** → Value for `competitors` in **Comp** → **Get Item from List** → Item At Index `1` → **Get Dictionary Value** `team` → **Get Dictionary Value** `location` → **Set Variable** `Team1`
14. Same as 13 but Index `2` → **Set Variable** `Team2`
15. **Get Dictionary Value** `notes` in **Comp** → **Get Item from List** First Item → **Get Dictionary Value** `headline` → **Set Variable** `Note`
16. **Get Dictionary Value** `broadcasts` in **Comp** → **Get Item from List** First Item → **Get Dictionary Value** `names` → **Combine Text** with Custom separator `, ` → **Set Variable** `TV`
17. **Get Dictionary Value** `date` in **Repeat Item** → **Replace Text**: find `Z`, replace with `:00+00:00` → **Get Dates from Input** → **Format Date**: Date Format **None**, Time Format **Short** → **Set Variable** `Time`
18. **Match Text** → in **Note**, pattern:
    `Women's Basketball Championship.*(Sweet 16|Elite 8|Final Four|National Championship)`
19. **Get Group from Matched Text** → Group At Index `1` → **Set Variable** `Round`
20. **If** → tap the condition and switch to **Any** of the following are true:
    - **MyTeams** contains `|`**Team1**`|`
    - **MyTeams** contains `|`**Team2**`|`
    - **Round** has any value
21. Inside that If: **If** **Round** has any value → **Text** `🏆 ` + **Round** + `: ` → **Set Variable** `Prefix` · Otherwise → **Text** (leave empty) → **Set Variable** `Prefix` · End If
22. Still inside the outer If: **Text** →
    `• ` **Prefix** **Team1** ` vs ` **Team2** ` — ` **Time** ` CT · ` **TV**
23. **Add to Variable** → `Lines`
24. End If · End Repeat (Shortcuts adds these for you — just make sure 10–23 sit inside the Repeat).

### After the Repeat

25. **If** **Lines** has any value:
    - **Combine Text** → **Lines** with **New Lines**
    - **Text** → `🏀 Women's hoops today` (Return twice) then **Combined Text**
    - **Set Variable** → `Message`
26. Still inside: **Get Contents of URL** → paste your Discord webhook URL. Tap **Show More**: Method **POST**, Request Body **JSON**, add field: Key `content`, type Text, value **Message**.
27. Still inside: **Send Message** → Message: **Message**, Recipients: pick your group chat. Tap the arrow and turn **Show When Run** off.
28. End If.

---

## Part 3 — Test it on a past date

1. Temporarily change step 4–5: delete the **Format Date** and put a **Text** `20260403` before **Set Variable Day** (the 2026 Final Four day).
2. Change step 27's recipient to just yourself and run the Shortcut.
3. You should get the Final Four message above, in Discord and as a text. Tap **Allow** / **Always Allow** if iOS asks about contacting ESPN or Discord.
4. If it looks right, restore step 4 and set the recipient back to the group.

**If something's off:**
- Time shows blank or wrong → step 17's date parsing; send me a screenshot.
- A USC game is missed → ESPN may spell it differently; I can check its name for you.

---

## Part 4 — Run it every morning

Shortcuts → **Automation** → **+** → **Time of Day** → 9:00 AM, **Daily** → **Run Immediately** (not "Ask Before Running"), turn **Notify When Run** off → pick **Hoops Reminder**.

---

## Changing teams

Edit the text in step 1. Keep the pipes around each name: `|UConn|USC|South Carolina|Iowa|`. The names are ESPN's short team names (e.g. "UConn", not "Connecticut").

## Previewing any date without your phone

GitHub → this repo → **Actions** → **Preview reminder** → **Run workflow**, enter dates like `20260327 20260403`. The result shows on the run page. `check_games.py` uses the same rules as the Shortcut.
