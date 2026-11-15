"""SC9: sidecar down does NOT break pass-through.

If the sidecar is unreachable, the NGINX main request must still
succeed (the mirror subrequest failure is silent). We stop the
sidecar container, fire a request through nginx, and assert it
returns 200.
"""

from __future__ import annotations

import subprocess

import requests


def test_passthrough_survives_sidecar_outage(compose_stack: dict) -> None:
    nginx = compose_stack["nginx"]
    REPO = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Stop the sidecar
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            f"{REPO}/docker-compose.yml",
            "-f",
            f"{REPO}/tests/mock_upstream/docker-compose.override.yml",
            "stop",
            "sidecar",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )

    try:
        # Pass-through must still work
        r = requests.get(f"{nginx}/api/tags", timeout=10)
        assert r.status_code == 200, f"pass-through broke when sidecar was down: {r.status_code}"
        data = r.json()
        assert "models" in data
    finally:
        # Restart the sidecar
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                f"{REPO}/docker-compose.yml",
                "-f",
                f"{REPO}/tests/mock_upstream/docker-compose.override.yml",
                "start",
                "sidecar",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
        )
