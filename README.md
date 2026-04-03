# odoo-readme-bot

Automatically detects outdated README files in Odoo custom module repositories and
regenerates them using the Claude API. Designed to run as a scheduled GitLab CI job
(once per day) on client repositories managed by Jarsa.

## Features

- **SHA-based tracking** — only processes modules that changed since the last documented commit
- **Two-model cost optimization** — Claude Haiku decides if update is needed, Claude Sonnet generates
- **Bilingual output** — technical English + functional Spanish per module
- **CI-friendly** — exit code 42 when READMEs were updated, enabling downstream steps
- **Dry-run mode** — analyze without writing files or pushing

## Installation

```bash
pip install odoo-readme-bot
```

## Usage

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# From any Odoo client repo root:
odoo-readme-bot run

# Dry run (no writes, no git ops):
odoo-readme-bot run --dry-run

# Force update all modules:
odoo-readme-bot run --force

# Single module only:
odoo-readme-bot run --module path/to/module_name
```

## GitLab CI Integration

```yaml
auto-update-readme:
  stage: auto-docs
  image: python:3.11-slim
  script:
    - pip install odoo-readme-bot -q
    - odoo-readme-bot run
  rules:
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
  allow_failure: true
```

**Required CI/CD variables:**

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (protected, masked) |
| `GITLAB_TOKEN` | Token with `write_repository` scope (protected, masked) |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success, no changes needed |
| 42 | Success, one or more READMEs updated and pushed |
| 1 | Unrecoverable error |

## License

MIT — Jarsa
