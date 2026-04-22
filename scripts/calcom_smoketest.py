import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


CALCOM_API_BASE = "https://api.cal.com"
CALCOM_API_VERSION = "2026-02-25"


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


def public_request(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "conversion-engine-calcom-smoketest/0.1",
            "Accept": "text/html,application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Cal.com event URL check failed with {exc.code}: {body[:500]}"
        ) from exc


def api_request(token: str) -> dict:
    request = urllib.request.Request(
        f"{CALCOM_API_BASE}/v2/event-types",
        headers={
            "Authorization": f"Bearer {token}",
            "cal-api-version": CALCOM_API_VERSION,
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Cal.com API check failed with {exc.code}: {body[:500]}"
        ) from exc


def main() -> int:
    load_dotenv()

    event_url = os.getenv("CALCOM_EVENT_URL")
    if not event_url:
        print("Missing CALCOM_EVENT_URL in .env", file=sys.stderr)
        return 1

    parsed = urlparse(event_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or not parsed.netloc or len(path_parts) < 2:
        print(
            "CALCOM_EVENT_URL must look like https://cal.com/<username>/<event-slug>",
            file=sys.stderr,
        )
        return 1

    result = {
        "baseUrl": os.getenv("CALCOM_BASE_URL", "https://cal.com"),
        "eventUrl": event_url,
        "host": parsed.netloc,
        "username": path_parts[0],
        "eventSlug": path_parts[1],
    }

    result["publicCheck"] = public_request(event_url)

    api_key = os.getenv("CALCOM_API_KEY")
    if api_key:
        api_result = api_request(api_key)
        result["apiCheck"] = {
            "status": api_result.get("status"),
            "eventTypeCount": len(api_result.get("data", [])),
        }
    else:
        result["apiCheck"] = "skipped: CALCOM_API_KEY not set"

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
