import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


AT_API_BASE_LIVE    = "https://api.africastalking.com/version1"
AT_API_BASE_SANDBOX = "https://api.sandbox.africastalking.com/version1"


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


def at_request(path: str, username: str, api_key: str, payload: dict, base: str = AT_API_BASE_LIVE) -> dict:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    headers = {
        "apiKey": api_key,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    request = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Africa's Talking POST {path} failed with {exc.code}: {error_body}"
        ) from exc


def main() -> int:
    load_dotenv()

    username = os.getenv("AT_USERNAME")
    api_key = os.getenv("AT_API_KEY")
    shortcode = os.getenv("AT_SHORTCODE")
    to = os.getenv("AT_SMOKE_TEST_PHONE")

    missing = [k for k, v in {"AT_USERNAME": username, "AT_API_KEY": api_key, "AT_SHORTCODE": shortcode}.items() if not v]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}", file=sys.stderr)
        return 1

    # Determine environment: sandbox username is always "sandbox" in AT
    is_sandbox = (username.lower() == "sandbox")
    base = AT_API_BASE_SANDBOX if is_sandbox else AT_API_BASE_LIVE
    env_label = "SANDBOX" if is_sandbox else "LIVE"

    print(f"Africa's Talking environment: {env_label}  ({base})", file=sys.stderr)

    if not to:
        print(
            "AT_SMOKE_TEST_PHONE not set — checking credentials only (set it to send a real SMS).",
            file=sys.stderr,
        )
        url = f"{base}/user?username={urllib.parse.quote(username)}"
        req = urllib.request.Request(
            url,
            headers={"apiKey": api_key, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                user_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(
                f"\nCredential check failed ({exc.code}): {body}\n"
                f"  -> If this is a live account, ensure it is verified and the key is from\n"
                f"     https://account.africastalking.com/apps/sandbox/settings/key (sandbox)\n"
                f"     or https://account.africastalking.com/profile (live).\n"
                f"  -> For sandbox testing set AT_USERNAME=sandbox in .env and use the sandbox key.",
                file=sys.stderr,
            )
            return 1

        print(json.dumps({"status": "credentials_ok", "env": env_label, "user": user_data}, indent=2))
        return 0

    payload = {
        "username": username,
        "to": to,
        "message": "[CONV-ENGINE smoke test] Africa's Talking SMS channel is live.",
        "from": shortcode,
    }
    result = at_request("/messaging", username, api_key, payload, base=base)
    print(json.dumps(result, indent=2))

    sms_data = result.get("SMSMessageData", {})
    recipients = sms_data.get("Recipients", [])
    if not recipients:
        print("No recipients returned — check the phone number format (+country code).", file=sys.stderr)
        return 1

    status = recipients[0].get("status", "")
    if status != "Success":
        print(f"Send failed with status: {status}", file=sys.stderr)
        return 1

    print(f"\nSMS sent OK  messageId={recipients[0].get('messageId')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
