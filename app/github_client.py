
import os
import time
from pathlib import Path

import httpx
import jwt


GITHUB_API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
}


def create_app_jwt():
    app_id = os.environ["GITHUB_APP_ID"]
    key_path = os.environ["GITHUB_PRIVATE_KEY_PATH"]

    private_key = Path(key_path).read_text(
        encoding="utf-8"
    )

    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )


def get_installation_token(owner: str, repo: str):
    app_jwt = create_app_jwt()

    jwt_headers = {
        **HEADERS,
        "Authorization": f"Bearer {app_jwt}",
    }

    with httpx.Client(timeout=20) as client:

        installation_response = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/installation",
            headers=jwt_headers,
        )
        installation_response.raise_for_status()

        installation_id = installation_response.json()["id"]

        token_response = client.post(
            f"{GITHUB_API}/app/installations/"
            f"{installation_id}/access_tokens",
            headers=jwt_headers,
        )
        token_response.raise_for_status()

        return token_response.json()["token"]


def post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    comment: str,
):
    token = get_installation_token(owner, repo)

    headers = {
        **HEADERS,
        "Authorization": f"Bearer {token}",
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}"
            f"/issues/{pr_number}/comments",
            headers=headers,
            json={"body": comment},
        )

        response.raise_for_status()

        return response.json()["id"]


def find_existing_comment(
    owner: str,
    repo: str,
    pr_number: int,
    marker: str,
):
    token = get_installation_token(owner, repo)

    headers = {
        **HEADERS,
        "Authorization": f"Bearer {token}",
    }

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/issues/{pr_number}/comments"
    )

    with httpx.Client(timeout=20) as client:
        for page in range(1, 11):
            response = client.get(
                url,
                headers=headers,
                params={"per_page": 100, "page": page},
            )
            response.raise_for_status()

            comments = response.json()

            for comment in comments:
                if marker in comment.get("body", ""):
                    return comment["id"]

            if len(comments) < 100:
                return None

    raise RuntimeError(
        "Too many comments to verify safely"
    )


def get_repository_id(owner: str, repo: str) -> int:
    token = get_installation_token(owner, repo)

    with httpx.Client(timeout=20) as client:
        response = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers={
                **HEADERS,
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        return response.json()["id"]
