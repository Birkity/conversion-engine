import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HUBSPOT_API_BASE = "https://api.hubapi.com"


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


def hubspot_request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{HUBSPOT_API_BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HubSpot {method} {path} failed with {exc.code}: {error_body}"
        ) from exc


def main() -> int:
    load_dotenv()

    token = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        print("Missing HUBSPOT_PRIVATE_APP_TOKEN in .env", file=sys.stderr)
        return 1

    account = hubspot_request("GET", "/integrations/v1/me", token)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    test_email = os.getenv(
        "HUBSPOT_SMOKE_TEST_EMAIL",
        f"hubspot-smoke-{timestamp}@example.com",
    )

    contact_payload = {
        "properties": {
            "email": test_email,
            "firstname": "Codex",
            "lastname": "SmokeTest",
            "company": "Tenacious Challenge",
        }
    }
    contact = hubspot_request(
        "POST",
        "/crm/v3/objects/contacts",
        token,
        payload=contact_payload,
    )

    result = {
        "portalId": account.get("portalId"),
        "hubId": account.get("hubId"),
        "appId": account.get("appId"),
        "user": account.get("user"),
        "createdContactId": contact.get("id"),
        "createdContactEmail": test_email,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
