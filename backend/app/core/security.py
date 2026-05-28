from pathlib import Path


def ensure_child_path(base_dir: Path, candidate: Path) -> Path:
    resolved_base = base_dir.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_base not in resolved_candidate.parents and resolved_candidate != resolved_base:
        raise ValueError("Path escapes the configured storage directory")
    return resolved_candidate

