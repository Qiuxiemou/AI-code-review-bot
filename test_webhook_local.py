import hashlib
import hmac
import json
import os
import urllib.request
from pathlib import Path
import urllib.error

def load_secret():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("WEBHOOK_SECRET="):
            return line.split("=", 1)[1]
    raise RuntimeError("WEBHOOK_SECRET not found")


secret = load_secret()


payload = {
    "action": "opened",
    "number": 1,
    "installation": {
        "id": 123456,
    },
    "repository": {
        "id": 987654,
    },
    "pull_request": {
        "number": 1,
        "head": {
            "sha": "a" * 40,
        },
    },
}


body = json.dumps(payload).encode("utf-8")

signature = "sha256=" + hmac.new(
    secret.encode("utf-8"),
    body,
    hashlib.sha256,
).hexdigest()

request = urllib.request.Request(
    "http://localhost:8000/webhook",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "local-test-001",
    },
    method="POST",
)




try:
    with urllib.request.urlopen(request) as response:
        print("HTTP Status:", response.status)
        print(response.read().decode("utf-8"))

except urllib.error.HTTPError as e:
    print("HTTP Status:", e.code)
    print("Error Response:", e.read().decode("utf-8"))
