"""Entry point for odoo-readme-bot."""

import argparse
import logging
import os
import sys
from importlib.resources import files

import anthropic

from . import (
    __version__,
    analyzer,
    detector,
    docs_sync,
    generator,
    git_utils,
    gitlab_configurator,
    hook_installer,
    odoo_client,
    readme_utils,
)
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

    # --- version ---
    sub.add_parser("version", help="Print the installed version and exit")

    # --- run ---
    run_p = sub.add_parser("run", help="Run the documentation pipeline")
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only — no file writes, no git operations",
    )
    run_p.add_argument(
        "--force",
        action="store_true",
        help="Skip SHA check and regenerate all module READMEs",
    )
    run_p.add_argument(
        "--module",
        metavar="PATH",
        help="Only process this specific module path",
    )

    # --- install ---
    install_p = sub.add_parser(
        "install",
        help="Install a post-commit git hook that offers to regenerate READMEs after each commit",
    )
    install_p.add_argument(
        "--repo",
        metavar="PATH",
        default=".",
        help="Path to the git repository (default: current directory)",
    )
    install_p.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the hook instead of installing it",
    )

    # --- configure-gitlab ---
    gl_p = sub.add_parser(
        "configure-gitlab",
        help="Create the Pipeline Schedule in a GitLab project via the API",
    )
    gl_p.add_argument(
        "--project",
        metavar="GROUP/REPO",
        required=True,
        help="GitLab project path, e.g. Jarsa/starka",
    )
    gl_p.add_argument(
        "--branch",
        metavar="BRANCH",
        default="main",
        help="Branch to schedule on (default: main)",
    )
    gl_p.add_argument(
        "--host",
        metavar="HOST",
        default=None,
        help="GitLab host (default: CI_SERVER_HOST env var or gitlab.com)",
    )
    gl_p.add_argument(
        "--token",
        metavar="TOKEN",
        default=None,
        help="GitLab personal access token (default: GITLAB_TOKEN env var)",
    )
    gl_p.add_argument(
        "--cron",
        metavar="CRON",
        default="0 12 * * 1-5",
        help="Cron expression in UTC (default: '0 12 * * 1-5' = Mon–Fri 6 am Torreón)",
    )
    gl_p.add_argument(
        "--timezone",
        metavar="TZ",
        default="America/Monterrey",
        help="Cron timezone (default: America/Monterrey)",
    )
    gl_p.add_argument(
        "--force",
        action="store_true",
        help="Delete and recreate the schedule if it already exists",
    )

    # --- sync-notebooklm ---
    sync_p = sub.add_parser(
        "sync-notebooklm",
        help="Sync installed module READMEs to a Google Doc (NotebookLM source)",
    )
    sync_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the combined document to stdout without writing to Google Docs",
    )

    return parser


def _cmd_run(args: argparse.Namespace) -> None:  # noqa: C901
    """Orchestrate the full documentation pipeline."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    gitlab_token = os.environ.get("GITLAB_TOKEN")
    # CI_COMMIT_REF_NAME is the actual branch being built (e.g. 17.0).
    # CI_DEFAULT_BRANCH is the repo's default branch — fallback for local runs.
    branch = (
        os.environ.get("CI_COMMIT_REF_NAME")
        or os.environ.get("CI_DEFAULT_BRANCH")
        or "main"
    )
    ci_server_host = os.environ.get("CI_SERVER_HOST", "gitlab.com")
    ci_project_path = os.environ.get("CI_PROJECT_PATH", "")
    repo_root = os.environ.get("CI_PROJECT_DIR", ".")
    bot_name = os.environ.get("BOT_NAME", "Jarsa Docs Bot")
    bot_email = os.environ.get("BOT_EMAIL", "docs-bot@jarsa.com")

    # GitLab API commit: preferred in CI (avoids git push / HTTP-not-allowed issues)
    use_gitlab_api = bool(gitlab_token and ci_project_path)

    # --- Preflight: verify GitLab credentials BEFORE calling Claude ---
    gitlab_project_id: int | None = None
    if use_gitlab_api and not args.dry_run:
        print(f"Preflight: verificando acceso a {ci_server_host} / {ci_project_path}…")
        try:
            gitlab_project_id = gitlab_configurator.preflight(
                host=ci_server_host,
                token=gitlab_token,
                project_path=ci_project_path,
                branch=branch,
            )
            print(f"✓ Acceso verificado — project_id={gitlab_project_id}, rama '{branch}' OK.")
        except RuntimeError as exc:
            print(f"Error de credenciales GitLab: {exc}", file=sys.stderr)
            print(
                "Revisa GITLAB_TOKEN (scope 'api') y que CI_PROJECT_PATH sea correcto.",
                file=sys.stderr,
            )
            sys.exit(1)

    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        print("Modo Claude: API key (GitLab CI / producción)")
    else:
        client = LocalClaudeClient()
        print("Modo Claude: claude CLI local (cuenta Claude Code)")

    base_prompt = _load_base_prompt()

    if args.module:
        modules_to_process = [{"path": args.module, "last_sha": None, "changed_files": []}]
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

        diff = git_utils.get_diff_since(last_sha or current_sha, module_path) if last_sha else ""
        readme_path = os.path.join(module_path, "README.md")
        readme_preview = ""
        if os.path.isfile(readme_path):
            with open(readme_path, "r", encoding="utf-8") as fh:
                readme_preview = fh.read()

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

        print("  Generando README con Claude Sonnet…")
        try:
            content = generator.generate_readme(client, module_path, base_prompt)
        except Exception as exc:  # noqa: BLE001
            print(f"  Error generando README para {module_path}: {exc}", file=sys.stderr)
            continue

        readme_utils.write_sha_to_readme(module_path, current_sha, content)
        print(f"  ✓ README actualizado ({len(content)} caracteres)")
        updated.append(module_path)

    print(f"\nResumen: {len(updated)} README(s) actualizados.")
    for m in updated:
        print(f"  - {m}")

    if not updated:
        sys.exit(0)

    if args.dry_run:
        print("[dry-run] No se realizaron cambios en el repositorio.")
        sys.exit(42)

    modules_str = ", ".join(updated)
    commit_message = (
        f"docs: auto-update README(s) [skip ci]\n\n"
        f"Modules: {modules_str}\n"
        f"Triggered by: {sha_short}"
    )
    readme_files = [os.path.join(m, "README.md") for m in updated]

    if use_gitlab_api and gitlab_project_id is not None:
        # GitLab API commit — works even when HTTP git push is disabled on the server
        print("\nSubiendo cambios via GitLab API…")
        try:
            result = gitlab_configurator.commit_files(
                host=ci_server_host,
                token=gitlab_token,
                project_id=gitlab_project_id,
                branch=branch,
                readme_paths=readme_files,
                commit_message=commit_message,
                repo_root=repo_root,
            )
            print(f"✓ Commit creado: {result.get('short_id', result.get('id'))}")
        except RuntimeError as exc:
            print(f"Error al hacer commit via API: {exc}", file=sys.stderr)
            sys.exit(1)
    elif gitlab_token:
        # Fallback: git push (requires HTTP git access on the server)
        git_utils.configure_git(bot_name, bot_email, cwd=repo_root)
        remote_url = (
            f"https://oauth2:{gitlab_token}@{ci_server_host}/{ci_project_path}.git"
        )
        try:
            git_utils.run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_root)
            git_utils.commit_and_push(branch, updated, sha_short, cwd=repo_root)
        except RuntimeError as exc:
            print(f"Error al hacer commit/push: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("GITLAB_TOKEN no configurado — omitiendo commit/push.")

    sys.exit(42)


def _cmd_install(args: argparse.Namespace) -> None:
    """Install or uninstall the post-commit git hook."""
    repo = os.path.abspath(args.repo)
    if args.uninstall:
        hook_installer.uninstall(repo)
        print(f"Hook desinstalado de {repo}")
    else:
        try:
            hook_installer.install(repo)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        if hook_installer.is_installed(repo):
            print(f"✓ Hook post-commit instalado en {repo}")
            print("  Después de cada commit se te preguntará si quieres regenerar los READMEs.")
        else:
            print("El hook ya estaba instalado.")


def _cmd_sync_notebooklm(args: argparse.Namespace) -> None:
    """Sync installed module READMEs to a Google Doc."""
    odoo_url = os.environ.get("ODOO_URL")
    if not odoo_url:
        print("Error: se requiere la variable de entorno ODOO_URL.", file=sys.stderr)
        sys.exit(1)

    google_sa_credentials = os.environ.get("GOOGLE_SA_CREDENTIALS")
    if not google_sa_credentials:
        print(
            "Error: se requiere la variable de entorno GOOGLE_SA_CREDENTIALS.",
            file=sys.stderr,
        )
        sys.exit(1)

    google_docs_id = os.environ.get("GOOGLE_DOCS_ID")
    if not google_docs_id:
        print("Error: se requiere la variable de entorno GOOGLE_DOCS_ID.", file=sys.stderr)
        sys.exit(1)

    client_name = os.environ.get("CUSTOMER")
    if not client_name:
        print("Error: se requiere la variable de entorno CUSTOMER.", file=sys.stderr)
        sys.exit(1)

    # REPOS_ROOT: directorio raíz con TODOS los repos clonados (starka-sh con submódulos).
    # En CI se setea al directorio clonado de GITHUB_REPO.
    # Si no está presente, cae en CI_PROJECT_DIR (sólo el repo actual).
    repos_root = os.environ.get("REPOS_ROOT") or os.environ.get("CI_PROJECT_DIR", ".")
    print(f"Buscando READMEs en: {os.path.abspath(repos_root)}")

    print(f"Consultando módulos instalados en {odoo_url}…")
    module_names = odoo_client.get_installed_custom_modules(odoo_url)
    if not module_names:
        print("Advertencia: webhook de Odoo no disponible — usando módulos del repositorio.")
        module_names = [
            os.path.basename(p) for p in git_utils.get_all_modules(repos_root)
        ]
    if not module_names:
        print("No se encontraron módulos. Sin cambios.")
        sys.exit(0)

    print(f"Módulos encontrados: {len(module_names)}")
    content = docs_sync.build_combined_document(module_names, repos_root, client_name)

    if args.dry_run:
        print(content)
        sys.exit(0)

    service = docs_sync.build_service(google_sa_credentials)
    docs_sync.clear_and_update_doc(service, google_docs_id, content)
    print(f"✅ Google Doc actualizado: {len(module_names)} módulos incluidos")
    sys.exit(0)


def _cmd_configure_gitlab(args: argparse.Namespace) -> None:
    """Create the Pipeline Schedule in GitLab via the API."""
    token = args.token or os.environ.get("GITLAB_TOKEN")
    if not token:
        print(
            "Error: se requiere --token o la variable de entorno GITLAB_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)

    host = args.host or os.environ.get("CI_SERVER_HOST", "gitlab.com")

    print(f"Configurando schedule en {host} / {args.project}…")
    try:
        schedule = gitlab_configurator.configure_schedule(
            host=host,
            token=token,
            project_path=args.project,
            branch=args.branch,
            cron=args.cron,
            timezone=args.timezone,
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error al configurar GitLab: {exc}", file=sys.stderr)
        sys.exit(1)

    print("✓ Pipeline Schedule configurado:")
    print(f"  ID:          {schedule['id']}")
    print(f"  Descripción: {schedule['description']}")
    print(f"  Rama:        {schedule['ref']}")
    print(f"  Cron:        {schedule['cron']} ({schedule['cron_timezone']})")
    print(f"  Activo:      {schedule['active']}")


def main() -> None:
    """Main entry point — dispatch to the appropriate subcommand."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "version":
        print(f"odoo-readme-bot {__version__}")
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "install":
        _cmd_install(args)
    elif args.command == "configure-gitlab":
        _cmd_configure_gitlab(args)
    elif args.command == "sync-notebooklm":
        _cmd_sync_notebooklm(args)
    else:
        parser.print_help()
        sys.exit(0)
