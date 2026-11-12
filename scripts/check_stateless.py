from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost").rstrip("/")
APP_SERVICES = ("backend", "bot", "frontend")
HTTP = httpx.Client(timeout=10.0, trust_env=False)


def run(command: list[str], *, capture: bool = False) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout.strip() if capture else ""


def compose(*args: str, capture: bool = False) -> str:
    return run(["docker", "compose", *args], capture=capture)


def wait_for(path: str, *, timeout: float = 120.0) -> httpx.Response:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = HTTP.get(f"{BASE_URL}{path}")
            if response.is_success:
                return response
            last_error = RuntimeError(f"{path} returned {response.status_code}")
        except (httpx.HTTPError, RuntimeError) as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"{path} did not become ready: {last_error}")


def collect_instances(path: str, expected: int, *, attempts: int = 60) -> set[str]:
    instances: set[str] = set()
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            response = HTTP.get(f"{BASE_URL}{path}")
            response.raise_for_status()
            instance = response.headers.get("X-Instance")
            if not instance:
                raise RuntimeError(f"{path} has no X-Instance header")
            instances.add(instance)
            if len(instances) >= expected:
                return instances
        except (httpx.HTTPError, RuntimeError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"{path} reached {len(instances)} of {expected} instances; last error: {last_error}"
    )


def service_containers(service: str) -> list[str]:
    output = compose("ps", "-q", service, capture=True)
    containers = [line for line in output.splitlines() if line]
    if len(containers) < 2:
        raise RuntimeError(f"{service}: expected at least 2 containers, got {len(containers)}")
    return containers


def create_product(title: str, unique_id: str) -> dict[str, Any]:
    code = (
        "import json,os,httpx;"
        "r=httpx.post("
        "'http://backend:8000/internal/products',"
        "data={'title':os.environ['SMOKE_TITLE'],"
        "'photo_file_unique_id':os.environ['SMOKE_UNIQUE_ID']},"
        "files={'file':('smoke.jpg',b'\\xff\\xd8\\xffsmoke','image/jpeg')},"
        "headers={'X-Service-Token':os.environ['SERVICE_TOKEN']},timeout=30);"
        "print(json.dumps({'status':r.status_code,'body':r.json()}));"
        "r.raise_for_status()"
    )
    output = compose(
        "exec",
        "-T",
        "--index",
        "1",
        "-e",
        f"SMOKE_TITLE={title}",
        "-e",
        f"SMOKE_UNIQUE_ID={unique_id}",
        "bot",
        "uv",
        "run",
        "--no-dev",
        "--frozen",
        "python",
        "-c",
        code,
        capture=True,
    )
    return json.loads(output.splitlines()[-1])


def assert_product_once(title: str) -> None:
    products = HTTP.get(f"{BASE_URL}/api/products").raise_for_status().json()
    matches = [product for product in products if product["title"] == title]
    if len(matches) != 1:
        raise RuntimeError(f"expected one product titled {title!r}, got {len(matches)}")
    image_path = urlsplit(matches[0]["image_url"]).path
    image = HTTP.get(f"{BASE_URL}{image_path}")
    image.raise_for_status()


def main() -> None:
    stopped: list[str] = []
    marker = uuid4().hex
    title = f"stateless-smoke-{marker}"
    unique_id = f"stateless-smoke-{marker}"

    try:
        print("Starting two replicas of each application service...")
        compose(
            "up",
            "-d",
            "--build",
            "--wait",
            "--scale",
            "backend=2",
            "--scale",
            "bot=2",
            "--scale",
            "frontend=2",
        )
        # Application containers may be recreated with new addresses while nginx keeps running.
        # Restart it so the mounted config and current Docker DNS records are loaded.
        compose("restart", "nginx")
        for path in ("/health", "/bot/health", "/"):
            wait_for(path)

        exposed = HTTP.post(f"{BASE_URL}/internal/products")
        if exposed.status_code not in {404, 405}:
            raise RuntimeError(f"public /internal route is exposed: {exposed.status_code}")

        print("Checking load balancing across replicas...")
        paths = {"backend": "/health", "bot": "/bot/health", "frontend": "/"}
        before = {
            service: collect_instances(path, 2)
            for service, path in paths.items()
        }
        for service, instances in before.items():
            print(f"  {service}: {sorted(instances)}")

        first = create_product(title, unique_id)
        second = create_product(title, unique_id)
        if first["status"] != 201 or second["status"] != 200:
            raise RuntimeError(
                f"idempotency failed: statuses {first['status']} and {second['status']}"
            )
        assert_product_once(title)

        print("Stopping one replica of backend, bot and frontend...")
        for service in APP_SERVICES:
            container = service_containers(service)[0]
            run(["docker", "stop", container], capture=True)
            stopped.append(container)

        time.sleep(12)
        for service, path in paths.items():
            remaining = collect_instances(path, 1)
            if len(remaining) != 1:
                raise RuntimeError(f"{service}: expected one remaining instance")
        assert_product_once(title)

        print("Restarting services and checking persistence...")
        for container in stopped:
            run(["docker", "start", container], capture=True)
        stopped.clear()
        compose("restart", "postgres", "minio", "backend", "bot", "frontend", "nginx")
        for path in ("/health", "/bot/health", "/"):
            wait_for(path)
        assert_product_once(title)
        print("Stateless smoke check: OK")
    finally:
        for container in stopped:
            subprocess.run(
                ["docker", "start", container],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Stateless smoke check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
