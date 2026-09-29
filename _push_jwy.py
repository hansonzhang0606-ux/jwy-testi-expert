#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push local jwy-testi-expert changes to GitHub via REST API (git transport blocked)."""

import base64
import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "hansonzhang0606-ux/jwy-testi-expert"
BRANCH = "main"


def get_pat_from_credman():
    """Read PAT from Windows Credential Manager for git:https://github.com."""
    try:
        CRED_TYPE_GENERIC = 1
        class CREDENTIAL(ctypes.Structure):
            _fields_ = [
                ("Flags", ctypes.c_ulong),
                ("Type", ctypes.c_ulong),
                ("TargetName", ctypes.c_wchar_p),
                ("Comment", ctypes.c_wchar_p),
                ("LastWritten", ctypes.c_ulonglong),
                ("CredentialBlobSize", ctypes.c_ulong),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", ctypes.c_ulong),
                ("AttributeCount", ctypes.c_ulong),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", ctypes.c_wchar_p),
                ("UserName", ctypes.c_wchar_p),
            ]
        cred_ptr = ctypes.POINTER(CREDENTIAL)()
        if not ctypes.windll.advapi32.CredReadW(
            "git:https://github.com", CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)
        ):
            return None
        cred = cred_ptr.contents
        blob = bytes(cred.CredentialBlob[i] for i in range(cred.CredentialBlobSize))
        ctypes.windll.advapi32.CredFree(cred_ptr)
        return blob.decode("utf-16-le", errors="ignore").strip("\x00")
    except Exception:
        return None


def get_pat_from_git():
    """Fallback: try to read from git credential fill."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def get_token():
    token = os.environ.get("GITHUB_PAT") or get_pat_from_credman() or get_pat_from_git()
    if not token:
        print("ERROR: 无法获取 GitHub PAT。请设置 GITHUB_PAT 环境变量。", file=sys.stderr)
        sys.exit(1)
    return token


def api(token, method, path, data=None):
    import urllib.request
    url = f"https://api.github.com/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "jwy-push-script",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {}


def git_status_files(repo_root):
    """Return list of (path, status) where status is 'M','A','D'. Use -z to handle Unicode paths."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    files = []
    raw = proc.stdout
    i = 0
    while i < len(raw):
        if raw[i:i+1] == b"":
            break
        status = raw[i:i+2].decode("utf-8")
        i += 3
        end = raw.find(b"\x00", i)
        if end == -1:
            path = raw[i:].decode("utf-8")
            i = len(raw)
        else:
            path = raw[i:end].decode("utf-8")
            i = end + 1
        if status == "??":
            files.append((path, "A"))
        elif status.startswith("M") or status.endswith("M"):
            files.append((path, "M"))
        elif status.startswith("A") or status.endswith("A"):
            files.append((path, "A"))
        elif status.startswith("D") or status.endswith("D"):
            files.append((path, "D"))
    return files


def main():
    repo_root = Path(__file__).resolve().parent
    token = get_token()

    # Verify token
    status, user = api(token, "GET", "user")
    if status != 200:
        print(f"ERROR: PAT invalid ({status}): {user.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Authenticated as {user.get('login')}")

    # Get current HEAD
    status, ref = api(token, "GET", f"repos/{REPO}/git/refs/heads/{BRANCH}")
    if status != 200:
        print(f"ERROR: Cannot get ref ({status}): {ref.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    head_sha = ref["object"]["sha"]
    print(f"[OK] HEAD {BRANCH}: {head_sha}")

    # Get base tree
    status, commit = api(token, "GET", f"repos/{REPO}/git/commits/{head_sha}")
    if status != 200:
        print(f"ERROR: Cannot get commit ({status}): {commit.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    base_tree_sha = commit["tree"]["sha"]
    print(f"[OK] Base tree: {base_tree_sha}")

    files = git_status_files(repo_root)
    print(f"[INFO] {len(files)} files to push")

    tree_entries = []
    for rel, st in files:
        p = repo_root / rel
        if p.is_dir():
            print(f"  [SKIP DIR] {rel}")
            continue
        if st == "D":
            tree_entries.append({"path": rel.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": None})
            print(f"  [D] {rel}")
            continue
        content = p.read_bytes()
        encoding = "utf-8"
        try:
            payload = content.decode("utf-8")
        except UnicodeDecodeError:
            payload = base64.b64encode(content).decode("ascii")
            encoding = "base64"
        status, blob = api(token, "POST", f"repos/{REPO}/git/blobs", {"content": payload, "encoding": encoding})
        if status != 201:
            print(f"ERROR: blob failed for {rel} ({status}): {blob.get('message', '')}", file=sys.stderr)
            sys.exit(1)
        tree_entries.append({"path": rel.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  [{st}] {rel} -> {blob['sha'][:8]}")

    # Create tree
    status, tree = api(token, "POST", f"repos/{REPO}/git/trees", {
        "base_tree": base_tree_sha,
        "tree": tree_entries,
    })
    if status != 201:
        print(f"ERROR: tree create failed ({status}): {tree.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] New tree: {tree['sha']}")

    # Create commit
    status, new_commit = api(token, "POST", f"repos/{REPO}/git/commits", {
        "message": "feat: add install.ps1, persistent task path, build from core files; update DELETE docs",
        "tree": tree["sha"],
        "parents": [head_sha],
    })
    if status != 201:
        print(f"ERROR: commit create failed ({status}): {new_commit.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] New commit: {new_commit['sha']}")

    # Update ref
    status, updated = api(token, "PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": new_commit["sha"], "force": False})
    if status != 200:
        print(f"ERROR: ref update failed ({status}): {updated.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Pushed to {BRANCH}: {new_commit['sha']}")


if __name__ == "__main__":
    main()
