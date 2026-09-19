"""End-to-end smoke test: every GET endpoint across all five roles.

Runs against a live uvicorn server on 127.0.0.1:8000. Usage:
    python tests/smoke_endpoints.py

Exit code 0 == no unexpected 5xx errors.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

ROLES = [
    ("admin@campusiq.edu", "Admin@123"),
    ("hod.cse@campusiq.edu", "Hod@12345"),
    ("faculty@campusiq.edu", "Faculty@123"),
    ("cr@campusiq.edu", "Cr@12345"),
    ("adnan@campusiq.edu", "Student@123"),
]

# Real values for {path_param} placeholders so dynamic routes resolve.
PARAM_FIXES = {
    "/api/v1/announcements/{announcement_id}": "/api/v1/announcements/1",
    "/api/v1/assignments/{assignment_id}": "/api/v1/assignments/1",
    "/api/v1/assignments/{assignment_id}/submissions": "/api/v1/assignments/1/submissions",
    "/api/v1/attendance/analytics/section/{section}": "/api/v1/attendance/analytics/section/A",
    "/api/v1/attendance/analytics/student/{student_id}": "/api/v1/attendance/analytics/student/1",
    "/api/v1/attendance/predict/student/{student_id}": "/api/v1/attendance/predict/student/1",
    "/api/v1/attendance/roster/{subject_id}/{section}": "/api/v1/attendance/roster/1/A",
    "/api/v1/departments/{department_id}": "/api/v1/departments/1",
    "/api/v1/projects/{project_id}": "/api/v1/projects/1",
    "/api/v1/projects/{project_id}/groups": "/api/v1/projects/1/groups",
    "/api/v1/projects/{project_id}/milestones": "/api/v1/projects/1/milestones",
    "/api/v1/students/{student_id}": "/api/v1/students/1",
    "/api/v1/timetable/section/{section}": "/api/v1/timetable/section/A",
}

# Endpoints that legitimately require a query parameter; hit them properly.
QUERY_PARAMS = {
    "/api/v1/search": "?q=a",
    "/api/v1/users/permissions": "?role=student",
    "/api/v1/reports/assignment-submissions": "?assignment_id=1",
}

SKIP = {"/", "/health", "/docs", "/redoc", "/openapi.json"}

ROLE_NAMES = ["student", "faculty", "hod", "cr", "admin"]


def _request(path: str, token: str | None = None, timeout: int = 30):
    req = urllib.request.Request(f"{BASE}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def login(email: str, password: str) -> tuple[str, str] | None:
    data = json.dumps({"identifier": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
            return payload["access_token"], payload["user"]["role"]
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    status, _ = _request("/health")
    if status != 200:
        print(f"Server not healthy (health -> {status}). Start it first.")
        return 1

    with urllib.request.urlopen(f"{BASE}/openapi.json", timeout=30) as r:
        schema = json.loads(r.read())

    paths = []
    for p, ops in schema["paths"].items():
        if "get" not in ops or p in SKIP:
            continue
        if "{" in p:
            p = PARAM_FIXES.get(p)
            if p is None:
                continue
        p = p + QUERY_PARAMS.get(p, "")
        paths.append(p)
    paths.sort()

    tokens: dict[str, str] = {}
    for email, pwd in ROLES:
        result = login(email, pwd)
        if result is None:
            print(f"LOGIN FAILED: {email}")
            continue
        tokens[result[1]] = result[0]

    print(f"\n{'endpoint':<50}" + "".join(f"{r:>9}" for r in ROLE_NAMES))
    print("-" * (50 + 9 * len(ROLE_NAMES)))

    unexpected: list[tuple[str, str, int, str]] = []
    for ep in paths:
        row = f"{ep:<50}"
        for role in ROLE_NAMES:
            tok = tokens.get(role)
            if tok is None:
                row += f"{'-':>9}"
                continue
            code, body = _request(ep, tok)
            row += f"{code:>9}"
            # 5xx is always a bug; 0 means a connection-level failure.
            if code == 0 or code >= 500:
                unexpected.append((ep, role, code, body[:200]))
        print(row)

    print(f"\nEndpoints tested: {len(paths)}")
    print(f"Unexpected 5xx / connection errors: {len(unexpected)}")
    for ep, role, code, body in unexpected:
        print(f"  [{role}] {ep} -> {code}\n      {body}")
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
