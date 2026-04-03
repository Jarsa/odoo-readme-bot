"""Entry point for odoo-readme-bot."""

import argparse
import logging
import os
import sys
from importlib.resources import files

import anthropic

from . import analyzer, detector, generator, git_utils, readme_utils
from .local_client import LocalClaudeClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_base_prompt() -> str:
    """Load prompt.md bundled with the package."""
    return files("odoo_readme_bot").joinpath("prompt.md").read_text(encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odoo-readme-bot",
        description="Automatic README documentation bot for Odoo custom modules",
    )
    sub = parser.add_subparsers(dest="command")
    run_parser = sub.add_parser("run", help="Run the documentation pipeline")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only — no file writes, no git operations",
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip SHA check and regenerate all module READMEs",
    )
    run_parser.add_argument(
        "--module",
        metavar="PATH",
        help="Only process this specific module path",
    )
    return parser


def main() -> None:  # noqa: C901
    """Orchestrate the full documentation pipeline."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        sys.exit(0)

    # --- Environment variables ---
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    gitlab_token = os.environ.get("GITLAB_TOKEN")
    branch = os.environ.get("CI_DEFAULT_BRANCH", "main")
    ci_server_host = os.environ.get("CI_SERVER_HOST", "gitlab.com")
    ci_project_path = os.environ.get("CI_PROJECT_PATH", "")
    repo_root = os.environ.get("CI_PROJECT_DIR", ".")
    bot_name = os.environ.get("BOT_NAME", "Jarsa Docs Bot")
    bot_email = os.environ.get("BOT_EMAIL", "docs-bot@jarsa.com")

    # --- Git remote configuration for CI ---
    if gitlab_token and ci_project_path:
        git_utils.configure_git(bot_name, bot_email, cwd=repo_root)
        remote_url = (
            f"https://oauth2:{gitlab_token}@{ci_server_host}/{ci_project_path}.git"
        )
        try:
            git_utils.run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_root)
        except RuntimeError as exc:
            print(f"Error configurando el remoto git: {exc}", file=sys.stderr)
            sys.exit(1)

    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        print("Modo: API key (GitLab CI / producción)")
    else:
        client = LocalClaudeClient()
        print("Modo: claude CLI local (cuenta Claude Code)")

    base_prompt = _load_base_prompt()

    # --- Discover modules ---
    if args.module:
        if args.force or True:
            # When --module is specified, always attempt; detect handles SHA logic
            all_candidates = [{"path": args.module, "last_sha": None, "changed_files": []}]
        modules_to_process = all_candidates
    elif args.force:
        raw = git_utils.get_all_modules(repo_root)
        modules_to_process = [{"path": m, "last_sha": None, "changed_files": []} for m in raw]
    else:
        modules_to_process = detector.get_modules_needing_review(repo_root)

    if not modules_to_process:
        print("No hay módulos con cambios pendientes de documentar.")
        sys.exit(0)

    print(f"Módulos a revisar: {len(modules_to_process)}")

    current_sha = git_utils.get_current_sha(cwd=repo_root)
    sha_short = current_sha[:8]
    updated: list[str] = []

    for module in modules_to_process:
        module_path = module["path"]
        last_sha = module["last_sha"]
        print(f"\n→ {module_path} (último SHA documentado: {last_sha or 'nunca'})")

        # Read diff and README preview for Haiku
        diff = git_utils.get_diff_since(last_sha or current_sha, module_path) if last_sha else ""
        readme_path = os.path.join(module_path, "README.md")
        readme_preview = ""
        if os.path.isfile(readme_path):
            with open(readme_path, "r", encoding="utf-8") as fh:
                readme_preview = fh.read()

        # --- Haiku analysis (skip if --force or never documented) ---
        if not args.force and last_sha:
            analysis = analyzer.should_update(client, diff, readme_preview)
            print(f"  Análisis: {analysis['reason']}")
            if not analysis["needs_update"]:
                print("  → Sin cambios significativos, omitiendo.")
                continue
        else:
            print("  → Forzando actualización (--force o módulo sin SHA previo).")

        if args.dry_run:
            print("  [dry-run] Se generaría el README pero no se escribirá.")
            updated.append(module_path)
            continue

        # --- Sonnet generation ---
        print("  Generando README con Claude Sonnet…")
        try:
            content = generator.generate_readme(client, module_path, base_prompt)
        except Exception as exc:  # noqa: BLE001
            print(f"  Error generando README para {module_path}: {exc}", file=sys.stderr)
            continue

        readme_utils.write_sha_to_readme(module_path, current_sha, content)
        print(f"  ✓ README actualizado ({len(content)} caracteres)")
        updated.append(module_path)

    # --- Summary ---
    print(f"\nResumen: {len(updated)} README(s) actualizados.")
    for m in updated:
        print(f"  - {m}")

    if not updated:
        sys.exit(0)

    if args.dry_run:
        print("[dry-run] No se realizaron cambios en el repositorio.")
        sys.exit(42)

    # --- Commit and push ---
    if gitlab_token:
        try:
            git_utils.commit_and_push(branch, updated, sha_short, cwd=repo_root)
        except RuntimeError as exc:
            print(f"Error al hacer commit/push: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("GITLAB_TOKEN no configurado — omitiendo commit/push.")

    sys.exit(42)
