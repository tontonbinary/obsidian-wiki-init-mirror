#!/usr/bin/env python3
"""
lint_state.py — Read/write .lint-state.json and manage issue lifecycle.

State machine
-------------
  new → pending  : script first discovers issue → report + save
  pending → fixed : next scan confirms the issue no longer exists → auto-remove
  pending → ignored: agent decided no fix needed → keep in state, stop reporting
  pending → deferred: needs human confirm → keep + set remind_at → re-report after date
  (fixed / ignored / deferred stay as-is; fixed is cleaned up on next scan)

Issue id format: {type}_{relative_path_with_underscores}
  e.g. orphan_wiki__项目__ChatERP
       broken_link_wiki__参考与对比__A-vs-B
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# local import – vault_utils is in the same package
from vault_utils import relative_to_vault


LINT_STATE_FILENAME = ".lint-state.json"
VALID_STATES = frozenset({"new", "pending", "fixed", "ignored", "deferred"})


def load_lint_state(vault: Path) -> dict[str, Any]:
    """Return the current lint-state dict, or a fresh empty structure."""
    state_path = vault / LINT_STATE_FILENAME
    if not state_path.exists():
        return {"issues": [], "version": "1.0"}

    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"issues": [], "version": "1.0"}


def save_lint_state(vault: Path, state: dict[str, Any]) -> None:
    """Write lint-state back to disk (atomic via temp file)."""
    state_path = vault / LINT_STATE_FILENAME
    tmp = state_path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(state_path)
    except OSError:
        pass   # read-only vault, skip gracefully


# ---------------------------------------------------------------------------
# Issue helpers
# ---------------------------------------------------------------------------

def make_issue_id(issue_type: str, vault: Path, file_path: Path) -> str:
    """Generate a deterministic id for an issue."""
    rel = relative_to_vault(file_path, vault)
    # Replace path separators with double-underscore so the id is single-level
    safe = rel.replace("/", "__").replace(".", "_")
    return f"{issue_type}_{safe}"


def make_issue_id_custom(issue_type: str, rel_path: str) -> str:
    """Make a custom id from an arbitrary relative path string."""
    safe = rel_path.replace("/", "__").replace(".", "_")
    return f"{issue_type}_{safe}"


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def ensure_issue(
    vault: Path,
    state: dict[str, Any],
    issue_type: str,
    rel_path: str,
    *,
    status: str = "pending",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ensure an issue exists in state with the given status.

    If it already exists, leave it untouched (preserve deferral etc.).
    If it is new, insert it and mark `new → pending`.
    """
    issue_id = make_issue_id_custom(issue_type, rel_path)
    issues = state.setdefault("issues", [])

    existing = next((i for i in issues if i["id"] == issue_id), None)
    if existing:
        return existing

    issue: dict[str, Any] = {
        "id": issue_id,
        "type": issue_type,
        "path": rel_path,
        "first_found": today_str(),
        "status": status,
    }
    if extra:
        issue.update(extra)

    issues.append(issue)
    return issue


def prune_fixed_issues(
    vault: Path,
    state: dict[str, Any],
    current_issues: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Remove issues that no longer exist in the vault.

    Returns (removed_fixed, kept) where removed_fixed are auto-cleared issues.
    Issues in 'fixed' / 'ignored' / 'deferred' are kept; only 'pending' are
    auto-removed when they disappear from current_issues.
    """
    kept: list[dict[str, Any]] = []
    auto_cleared: list[dict[str, Any]] = []

    for issue in state.get("issues", []):
        if issue["id"] in current_issues:
            kept.append(issue)
        elif issue["status"] == "pending":
            # No longer present → mark fixed and drop next scan
            auto_cleared.append(issue)
            # don't keep it
        else:
            # ignored / deferred / already fixed – keep in state
            kept.append(issue)

    state["issues"] = kept
    return auto_cleared, kept


def get_active_issues(
    state: dict[str, Any],
    today: str | None = None,
) -> list[dict[str, Any]]:
    """Return issues that should be reported right now.

    - 'new' / 'pending' always reported
    - 'deferred' only reported when remind_at <= today
    - 'ignored' / 'fixed' never reported
    """
    if today is None:
        today = today_str()

    active: list[dict[str, Any]] = []
    for issue in state.get("issues", []):
        s = issue.get("status", "pending")
        if s in ("new", "pending"):
            active.append(issue)
        elif s == "deferred":
            remind = issue.get("remind_at", "")
            if remind and remind <= today:
                active.append(issue)
        # ignored / fixed → skip
    return active


def transition_issue(
    state: dict[str, Any],
    issue_id: str,
    new_status: str,
    extra: dict[str, Any] | None = None,
) -> bool:
    """Change the status of an existing issue. Returns True if found."""
    for issue in state.get("issues", []):
        if issue["id"] == issue_id:
            issue["status"] = new_status
            if extra:
                issue.update(extra)
            return True
    return False
