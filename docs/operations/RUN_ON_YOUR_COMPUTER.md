# Running AVEN GLOBAL on your own Windows computer

Decision (Director, 2026-11-13): host from the Director's computer for now.
Azure is dropped. Any future online hosting must be free.

## What this gives you, and what it does not

| | |
|---|---|
| Cost | Free |
| Works for | You, on this computer, at `http://localhost:3000` |
| Staff and phones | Not reachable yet. That needs an extra step (below). |
| When the computer is off or asleep | The system is off |
| Backups | Only if you run `Backup-AvenGlobal.bat` and copy the file elsewhere |
| Real business records | **Not recommended yet.** One disk failure or theft loses everything since the last backup you copied away. Use test data until backups are routine and an accountant has reviewed the finance setup. |

## One-time setup

1. Install **Docker Desktop** for Windows (free for small businesses) from
   <https://www.docker.com/products/docker-desktop/>. Accept the WSL 2 option.
   Restart if asked, then open Docker Desktop and wait for "Engine running".
2. Get the system files: on GitHub open the repository, choose
   **Code → Download ZIP**, and extract it, for example to
   `C:\Users\<you>\Projects\Avon-Global`.
3. Open the folder `scripts\windows` and double-click
   **Start-AvenGlobal.bat**. The first start takes 10 to 20 minutes.
4. Double-click **Create-Director.bat**, and enter your email, name and a
   password. Then sign in at `http://localhost:3000` and set up two-factor
   sign-in with an authenticator app.
5. In **Admin → Organisation**, enter the company details recorded in
   `docs/DIRECTOR_DECISIONS.md` and tick "Approved to print" for the address
   and telephone. Leave TPIN and VAT unticked.

## Every day

- Start: `Start-AvenGlobal.bat`. Stop: `Stop-AvenGlobal.bat`.
- Backup: `Backup-AvenGlobal.bat`, then copy the file from `backups\` to
  OneDrive or an external disk.

## Turning JARVIS on

Open the file `.env` in the main folder with Notepad and set these two lines,
then run `Stop-AvenGlobal.bat` and `Start-AvenGlobal.bat`:

```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your key>
```

The `.env` file stays on your computer and is never uploaded. Use a new key,
not one that has been pasted into a chat.

## Letting staff and phones in (later, needs your decision)

- **Same office Wi-Fi:** possible, but sign-in cookies and addresses need
  configuring for the computer's network address. Not set up yet.
- **From anywhere:** needs a secure tunnel service (some have free plans) and
  a domain name. Not set up yet. Without HTTPS the system must not be opened
  to the internet.

## Free online hosting

The only long-running free option found is Oracle Cloud "Always Free"
(`docs/research/HOSTING_FREE_OPTIONS.md`). It still needs a payment card to
open the account, and its free capacity is not guaranteed.
