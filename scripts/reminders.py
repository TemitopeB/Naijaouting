"""
Daily event reminders for signed-in visitors.

Runs every morning (.github/workflows/reminders.yml). For each visitor who is signed in
(not a guest), has reminders on, and saved an event that starts tomorrow (Lagos time),
it sends one short email listing those events. Each reminder is sent once.

Needs these GitHub secrets:
  SUPABASE_URL, SUPABASE_SERVICE_KEY   to read accounts (service key stays in GitHub only)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_FROM   the email service (e.g. Brevo)
Optional: SITE_URL (default https://naijaouting-ng.vercel.app)

If the email secrets aren't set yet, it only reports how many reminders it would send.
Run with --dry-run to print the emails instead of sending them.
"""
import datetime as dt
import html
import json
import os
import smtplib
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SITE = os.environ.get("SITE_URL", "https://naijaouting-ng.vercel.app").rstrip("/")
DRY = "--dry-run" in sys.argv
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")


def say(msg):
    print(msg)
    if SUMMARY:
        with open(SUMMARY, "a") as f:
            f.write(msg + "\n\n")


def api(method, path, body=None, extra=None):
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
    h.update(extra or {})
    req = urllib.request.Request(URL + path, method=method, headers=h,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def docs(col):
    out, start = [], 0
    while True:
        page = api("GET", f"/rest/v1/docs?col=eq.{col}&select=id,data", extra={"Range": f"{start}-{start + 999}"})
        out += page or []
        if not page or len(page) < 1000:
            return out
        start += 1000


def user(uid):
    try:
        return api("GET", "/auth/v1/admin/users/" + urllib.parse.quote(uid))
    except Exception:
        return None


def nice_date(d):
    x = dt.date.fromisoformat(d)
    return x.strftime("%A %-d %B")


def build(name, items):
    lines, rows = [], []
    for it in items:
        when = nice_date(it["s"]) + (f", {it['t']}" if it.get("t") else "")
        where = ", ".join(x for x in (it.get("vn"), it.get("c")) if x)
        link = f"{SITE}/events/#e={urllib.parse.quote(it['sl'])}" if it.get("sl") else f"{SITE}/events/"
        lines.append(f"- {it['n']}\n  {when}" + (f"\n  {where}" if where else "") + f"\n  {link}")
        rows.append(
            f'<tr><td style="padding:14px 0;border-top:1px solid #e6e3da">'
            f'<a href="{html.escape(link)}" style="font:600 16px Arial,sans-serif;color:#0f6e46;text-decoration:none">{html.escape(it["n"])}</a>'
            f'<div style="font:14px Arial,sans-serif;color:#444;margin-top:4px">{html.escape(when)}</div>'
            + (f'<div style="font:14px Arial,sans-serif;color:#777;margin-top:2px">{html.escape(where)}</div>' if where else "")
            + "</td></tr>")
    hi = f"Hi {name}," if name else "Hi,"
    one = len(items) == 1
    subject = ("Tomorrow: " + items[0]["n"]) if one else f"Tomorrow: {len(items)} events you saved"
    intro = "An event you saved is tomorrow." if one else "Events you saved are tomorrow."
    account = f"{SITE}/events/#account"
    text = (f"{hi}\n\n{intro}\n\n" + "\n\n".join(lines) +
            "\n\nCheck the organiser's page for any last-minute changes before you go.\n\n"
            f"You get this because reminders are on in your NaijaOuting account. Turn them off: {account}\n")
    body = (f'<div style="max-width:520px;margin:0 auto;padding:24px 16px;font-family:Arial,sans-serif;color:#1a1a1a">'
            f'<p style="font-size:15px;margin:0 0 6px">{html.escape(hi)}</p>'
            f'<p style="font-size:15px;margin:0 0 12px">{intro}</p>'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{"".join(rows)}</table>'
            f'<p style="font-size:13px;color:#555;margin:16px 0 0">Check the organiser’s page for any last-minute changes before you go.</p>'
            f'<p style="font-size:12px;color:#888;margin:20px 0 0">You get this because reminders are on in your NaijaOuting account. '
            f'<a href="{account}" style="color:#888">Turn reminders off</a>.</p></div>')
    return subject, text, body


def main():
    if not (URL and KEY):
        say("Reminders: SUPABASE_URL or SUPABASE_SERVICE_KEY is not set, so nothing to do.")
        return
    smtp = {k: os.environ.get(k, "").strip() for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_FROM")}
    can_send = all(smtp[k] for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "MAIL_FROM"))
    lagos_today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).date()
    tomorrow = (lagos_today + dt.timedelta(days=1)).isoformat()

    accounts = docs("users")
    sent_log = {d["id"]: (d.get("data") or {}).get("sent", {}) for d in docs("remlog")}
    todo = []
    for d in accounts:
        data = d.get("data") or {}
        if data.get("remind") is False:
            continue
        evs = data.get("ev") or {}
        due = []
        for eid in data.get("fav") or []:
            it = evs.get(eid)
            if not it or it.get("s") != tomorrow or not it.get("n"):
                continue
            if f"{eid}:{tomorrow}" in sent_log.get(d["id"], {}):
                continue
            due.append(dict(it, id=eid))
        if due:
            todo.append((d["id"], due))

    say(f"Reminders for {tomorrow}: {len(todo)} people with saved events tomorrow (of {len(accounts)} accounts).")
    if not todo:
        return
    if not can_send and not DRY:
        say("Email isn't set up yet (SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_FROM secrets), so no emails were sent.")
        return

    server = None
    if not DRY:
        port = int(smtp["SMTP_PORT"] or 587)
        server = smtplib.SMTP_SSL(smtp["SMTP_HOST"], port, timeout=30) if port == 465 else smtplib.SMTP(smtp["SMTP_HOST"], port, timeout=30)
        if port != 465:
            server.starttls()
        server.login(smtp["SMTP_USER"], smtp["SMTP_PASS"])
    from_name, from_addr = parseaddr(smtp["MAIL_FROM"] or "NaijaOuting <noreply@example.com>")
    sent = failed = skipped = 0
    for uid, due in todo:
        u = user(uid)
        email = (u or {}).get("email")
        if not u or u.get("is_anonymous") or not email:
            skipped += 1
            continue
        meta = u.get("user_metadata") or {}
        name = (meta.get("full_name") or meta.get("name") or "").split(" ")[0]
        subject, text, body = build(name, due)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name or "NaijaOuting", from_addr))
        msg["To"] = email
        msg["List-Unsubscribe"] = f"<{SITE}/events/#account>"
        msg.set_content(text)
        msg.add_alternative(body, subtype="html")
        if DRY:
            print("----", email, "|", subject, "\n", text)
            sent += 1
            continue
        try:
            server.send_message(msg)
            sent += 1
        except Exception as ex:
            failed += 1
            print("send failed:", type(ex).__name__)
            continue
        log = {k: v for k, v in sent_log.get(uid, {}).items() if v >= (lagos_today - dt.timedelta(days=30)).isoformat()}
        for it in due:
            log[f"{it['id']}:{tomorrow}"] = lagos_today.isoformat()
        api("POST", "/rest/v1/docs?on_conflict=col,id", {"col": "remlog", "id": uid, "data": {"sent": log}},
            extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
    if server:
        server.quit()
    say(f"Sent {sent} reminder email{'s' if sent != 1 else ''}" + (f", {failed} failed" if failed else "") +
        (f", {skipped} skipped (no email on the account)" if skipped else "") + (" (dry run)" if DRY else "") + ".")


if __name__ == "__main__":
    main()
