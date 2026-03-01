# Project Operating Model

This document complements AGENT.md (authoritative). Follow both.

## 1. Role Separation
- ChatGPT: produces prompts and plans only.
- Codex: executes code changes in the repo.
- AGENT.md rules override this file if conflict arises.

## 2. Snapshot Anchoring
- Anchor work to current HEAD SHA (record in PROJECT_SNAPSHOT.md).
- Do not rely on chat history; re-read required files each task.

## 3. Mandatory Reality Check
Before editing, Codex must confirm:
- Presence of AGENT.md (Operating Model section), docs/09_IMPLEMENTATION_STATUS.md, docs/CURRENT_STATE.md, workflows under .github/workflows/, and sentinelqa/ packages.
- Artifact directories are gitignored.
- CI state (green or assumed; declare assumption if not proven).
- Absence of PROJECT_SNAPSHOT.md / docs/PROJECT_OPERATING_MODEL.md if task requires creation.

## 4. One Committable Chunk Rule
- Deliver a single logical change set.
- No unrelated refactors or opportunistic edits.

## 5. Required Codex Output Format
Every task output must include:
- Files changed
+- Commands run + results (or state assumptions)
- Verification steps taken
- git diff --stat
- Proposed commit message
- STOP after reporting

## 6. Documentation Discipline
When behavior changes, update in the same chunk:
- docs/09_IMPLEMENTATION_STATUS.md
- docs/CURRENT_STATE.md
- PROJECT_SNAPSHOT.md

## 7. CI Integrity Rules
- Workflows contain orchestration only; business logic lives under sentinelqa/.
- Use pure-Python helpers (no curl) as in existing CI patterns.
- Keep gates runnable locally and in CI; respect baseline paths and artifact locations.

## 8. Determinism
- Use fixed fixtures and deterministic defaults.
- Avoid timestamps/run_ids in persisted artifacts unless required; gates must ignore unstable fields.
