import json
import os
import smtplib
import ssl
import sys
from email.mime.text import MIMEText
from pathlib import Path


# Resend REST API is Cloudflare-blocked from ET — SMTP relay works fine.
SMTP_HOST = "smtp.resend.com"
SMTP_PORT = 587
SMTP_USER = "resend"  # always "resend" for Resend SMTP


def parse_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        return cleaned[1:-1]
    return cleaned


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), parse_env_value(value))


def send_via_smtp(api_key: str, from_addr: str, to: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"CONV-ENGINE <{from_addr}>"
    msg["To"] = to
    msg["Subject"] = subject

    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.login(SMTP_USER, api_key)
        s.sendmail(from_addr, [to], msg.as_string())


def main() -> int:
    load_dotenv()

    api_key = os.getenv("RESEND_API_KEY")
    from_addr = os.getenv("RESEND_FROM", "onboarding@resend.dev")
    to = os.getenv("RESEND_SMOKE_TEST_EMAIL", "")
    if not to:
        print("Missing RESEND_SMOKE_TEST_EMAIL in .env", file=sys.stderr)
        return 1

    if not api_key:
        print("Missing RESEND_API_KEY in .env", file=sys.stderr)
        return 1

    print(f"Sending via SMTP relay {SMTP_HOST}:{SMTP_PORT}  from={from_addr}  to={to}", file=sys.stderr)

    try:
        send_via_smtp(
            api_key=api_key,
            from_addr=from_addr,
            to=to,
            subject="[CONV-ENGINE smoke test] Resend SMTP relay is live",
            body=(
                "This is an automated smoke test from the CONV-ENGINE preflight.\n"
                "Resend SMTP relay confirmed working (REST API is Cloudflare-blocked from ET).\n"
            ),
        )
    except Exception as exc:
        print(f"SMTP send failed: {exc}", file=sys.stderr)
        return 1

    result = {"status": "sent", "from": from_addr, "to": to, "relay": f"{SMTP_HOST}:{SMTP_PORT}"}
    print(json.dumps(result, indent=2))
    print("\nEmail sent OK via SMTP relay", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
