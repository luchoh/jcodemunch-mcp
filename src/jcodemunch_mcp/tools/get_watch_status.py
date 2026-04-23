"""get_watch_status — surface watch-all state to agents.

Reports every locally-indexed repo the watch-all daemon would cover, each
repo's current reindex state (fresh / in-progress / stale / failing), and
the OS-level service status. Intended for agents to consult before relying
on a potentially stale index.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..reindex_state import get_reindex_status
from ..service_installer import service_status
from ..watch_all import discover_local_repos

logger = logging.getLogger(__name__)


def get_watch_status(storage_path: Optional[str] = None) -> dict:
    """Return a summary of watch-all coverage and health."""
    discovered = discover_local_repos(storage_path)
    repos_out = []
    any_stale = False
    any_in_progress = False
    any_failing = False
    for folder in discovered:
        # Repo-key used by reindex_state is the folder path itself (what
        # watcher._watch_single registers). Keep this aligned with watcher.py.
        status = get_reindex_status(folder)
        repos_out.append({
            "source_root": folder,
            "exists": Path(folder).is_dir(),
            **status,
        })
        if status.get("index_stale"):
            any_stale = True
        if status.get("reindex_in_progress"):
            any_in_progress = True
        if status.get("reindex_failures"):
            any_failing = True

    try:
        svc = service_status()
    except Exception as exc:
        logger.debug("service_status failed", exc_info=True)
        svc = {"active": False, "error": str(exc)}

    return {
        "service": svc,
        "repo_count": len(repos_out),
        "any_stale": any_stale,
        "any_in_progress": any_in_progress,
        "any_failing": any_failing,
        "repos": repos_out,
    }
