import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def load_env_value(name: str) -> str | None:
    for env_path in (Path(".env"), Path(".env.example")):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == name:
                return value.strip().strip('"').strip("'") or None
    return os.getenv(name)


def call_vk(method: str, token: str, **params: object) -> dict:
    payload = {
        "access_token": token,
        "v": "5.199",
        **params,
    }
    data = urllib.parse.urlencode(payload).encode()
    request = urllib.request.Request(f"https://api.vk.com/method/{method}", data=data)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    token = load_env_value("VK_GROUP_TOKEN")
    if not token:
        print("VK_GROUP_TOKEN is empty or missing", file=sys.stderr)
        return 1

    payload = call_vk("messages.getConversations", token, count=50)
    if "error" in payload:
        error = payload["error"]
        print(f"VK error {error.get('error_code')}: {error.get('error_msg')}", file=sys.stderr)
        return 1

    found = False
    for item in payload["response"]["items"]:
        conversation = item["conversation"]
        peer = conversation["peer"]
        title = conversation.get("chat_settings", {}).get("title")
        peer_id = peer["id"]
        peer_type = peer["type"]

        if title == "General":
            found = True
            print("title:", title)
            print("type:", peer_type)
            print("peer_id:", peer_id)

    if not found:
        print("Chat with title 'General' was not found in the first 50 conversations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
