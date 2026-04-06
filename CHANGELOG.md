# Changelog

## [1.2.0] - 2026-04-06

### Added

- `sync-notebooklm` subcommand: queries installed custom modules from an Odoo
  instance via `odoo_cloc` webhook, builds a combined bilingual document from
  all module READMEs (`.md` and `.rst`) across all cloned repos, and uploads it
  to a Google Doc for use as a NotebookLM source.
- `odoo_client.py`: public webhook client for `odoo_cloc` — returns installed
  module names; returns `[]` silently on any error.
- `docs_sync.py`: Google Docs API integration using a service account —
  `build_service`, `clear_and_update_doc`, `build_combined_document`.
- New env vars for `sync-notebooklm`: `ODOO_URL`, `GOOGLE_SA_CREDENTIALS`,
  `GOOGLE_DOCS_ID`, `CUSTOMER`, `REPOS_ROOT`.
- Falls back to local repo modules when `odoo_cloc` webhook is unavailable.
- New dependencies: `google-api-python-client>=2.100.0`, `google-auth>=2.23.0`,
  `requests>=2.28.0`.

## [1.1.5] - 2026-04-06

### Added

- `version` subcommand: prints the installed version and exits (`odoo-readme-bot version`).

## [1.1.4] - 2026-04-06

### Added

- **Preflight check**: before generating any README, `run` now verifies
  GitLab API credentials and branch existence. If invalid, exits with error
  immediately — no tokens wasted.
- **GitLab API commits**: READMEs are now pushed via the GitLab Commits API
  instead of `git push`, which works even when HTTP git access is disabled
  on the server (only SSH allowed). Falls back to `git push` when
  `CI_PROJECT_PATH` is not set (local runs).

### Fixed

- Removed unused imports in tests (ruff F401, F821, E741).

## [1.1.3] - 2026-04-06

### Fixed

- Remove unused `shutil` import in `hook_installer.py` (ruff F401).
- Remove extraneous `f` prefix on string literal in `cli.py` (ruff F541).

## [1.1.2] - 2026-04-06

### Fixed

- `git push` now uses `HEAD:{branch}` to work correctly in GitLab CI's detached
  HEAD checkout mode (`error: src refspec X does not match any`).
- Branch is now resolved from `CI_COMMIT_REF_NAME` (actual pipeline branch, e.g.
  `17.0`) before falling back to `CI_DEFAULT_BRANCH`, fixing pushes to non-default
  branches.

## [1.1.1] - 2026-04-04

### Fixed

- `configure-gitlab`: HTTP errors now show the GitLab API message body
  (e.g. "Token is expired...") instead of the generic `HTTP Error 401: Unauthorized`.

## [1.1.0] - 2026-04-03

### Added

- `install` subcommand: installs a post-commit git hook that detects changed
  Odoo modules and interactively asks if READMEs should be regenerated.
  Supports `--uninstall` and `--repo PATH`. Idempotent; preserves existing hooks.
- `configure-gitlab` subcommand: creates the Pipeline Schedule in a GitLab
  project via the REST API. Supports `--project`, `--branch`, `--host`,
  `--token`, `--cron`, `--timezone`, `--force`.
- `local_client.py`: `LocalClaudeClient` — uses the `claude` CLI when
  `ANTHROPIC_API_KEY` is not set, enabling local usage with Claude Code auth.

## [1.0.0] - 2025-04-02

### Added

- Initial release
- SHA-based diff tracking
- Haiku analyzer + Sonnet generator pipeline
- CLI with --dry-run, --force, --module flags
- GitLab CI auto-publish on tag
