# Changelog

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
