import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


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


def build_basic_auth_header(public_key: str, secret_key: str) -> str:
    token = f"{public_key}:{secret_key}".encode("utf-8")
    encoded = base64.b64encode(token).decode("ascii")
    return f"Basic {encoded}"


def langfuse_request(base_url: str, public_key: str, secret_key: str) -> dict | list:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/public/projects",
        headers={
            "Authorization": build_basic_auth_header(public_key, secret_key),
            "Accept": "application/json",
            "User-Agent": "conversion-engine-langfuse-smoketest/0.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Langfuse API check failed with {exc.code}: {body[:500]}"
        ) from exc


def main() -> int:
    load_dotenv()

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    environment = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "default")

    if not public_key or not secret_key:
        print(
            "Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY in .env",
            file=sys.stderr,
        )
        return 1

    payload = langfuse_request(base_url, public_key, secret_key)

    project_count = len(payload) if isinstance(payload, list) else len(payload.get("data", []))
    result = {
        "baseUrl": base_url,
        "environment": environment,
        "publicKeyPrefix": public_key[:10],
        "projectCount": project_count,
        "responseType": type(payload).__name__,
    }

    if isinstance(payload, list):
        result["projectIds"] = [project.get("id") for project in payload[:5] if isinstance(project, dict)]
    else:
        result["projectIds"] = [
            project.get("id") for project in payload.get("data", [])[:5] if isinstance(project, dict)
        ]

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
