# Agent Guide

## Working conventions

- Use agents primarily for codebase review and small corrective changes, not
  substantial technical implementations unless the task explicitly calls for one.
- Preserve unrelated changes in a dirty worktree. Inspect both `git diff` and
  `git diff --cached` before editing.
- Use `apply_patch` for source and documentation edits.
- Avoid live downloads in tests. Use ZIP fixtures or mocked `requests.get`.
- Treat the generic API and cache layout as a v0.5 public contract: make
  migration and compatibility decisions explicitly, and document them.

## Verification

Run these checks from the repository root:

```bash
uv run pytest
uv run pyright
uv run ruff check .
```

If uv cannot write its usual cache, use:

```bash
UV_CACHE_DIR=/private/tmp/ne_loader_uv_cache uv run pytest
UV_CACHE_DIR=/private/tmp/ne_loader_uv_cache uv run pyright
UV_CACHE_DIR=/private/tmp/ne_loader_uv_cache uv run ruff check .
```
