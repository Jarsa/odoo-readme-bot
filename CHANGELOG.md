# Changelog

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
