"""Install and uninstall the odoo-readme-bot post-commit git hook."""

import logging
import os
import stat

logger = logging.getLogger(__name__)

_HOOK_MARKER = "# odoo-readme-bot managed hook"

# The hook script runs after every git commit.
# It detects changed Odoo modules and asks the user interactively
# whether to regenerate their READMEs.
_HOOK_SCRIPT = """\
#!/usr/bin/env bash
{marker}

# Find which Odoo modules (directories with __manifest__.py) had files changed
# in the last commit, excluding README.md itself.
changed_modules=()
while IFS= read -r file; do
    dir=$(dirname "$file")
    while [ "$dir" != "." ] && [ "$dir" != "/" ]; do
        if [ -f "$dir/__manifest__.py" ]; then
            changed_modules+=("$dir")
            break
        fi
        dir=$(dirname "$dir")
    done
done < <(git diff-tree --no-commit-id -r --name-only HEAD | grep -v 'README\\.md')

# Deduplicate
unique_modules=($(printf '%s\\n' "${{changed_modules[@]}}" | sort -u))

if [ ${{#unique_modules[@]}} -eq 0 ]; then
    exit 0
fi

echo ""
echo "odoo-readme-bot: módulos modificados en este commit:"
for mod in "${{unique_modules[@]}}"; do
    echo "  - $mod"
done
echo ""

# Prompt — works when hook has a terminal (git commit from shell)
exec < /dev/tty
read -r -p "¿Regenerar README(s)? [y/N] " answer
exec <&-

case "$answer" in
    [yYsS]*)
        for mod in "${{unique_modules[@]}}"; do
            echo "  → Generando README para $mod..."
            odoo-readme-bot run --module "$mod"
            exit_code=$?
            if [ $exit_code -eq 42 ]; then
                echo "  ✓ README actualizado: $mod"
                git add "$mod/README.md" 2>/dev/null || true
            elif [ $exit_code -ne 0 ]; then
                echo "  ✗ Error generando README para $mod (exit $exit_code)" >&2
            fi
        done
        # If READMEs were staged, amend the current commit silently
        if git diff --cached --quiet; then
            :
        else
            echo ""
            echo "  Agregando READMEs al commit actual..."
            git commit --amend --no-edit --no-verify -q
            echo "  ✓ Commit actualizado con los nuevos READMEs."
        fi
        ;;
    *)
        echo "  Omitido."
        ;;
esac

exit 0
"""


def _hook_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".git", "hooks", "post-commit")


def is_installed(repo_root: str) -> bool:
    """Return True if the odoo-readme-bot hook is already installed."""
    path = _hook_path(repo_root)
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        return _HOOK_MARKER in fh.read()


def install(repo_root: str) -> None:
    """Install the post-commit hook in the given git repository.

    If a post-commit hook already exists (not managed by us), it is preserved
    by appending our hook as a separate section.
    """
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        raise ValueError(f"{repo_root} no es un repositorio git válido.")

    if is_installed(repo_root):
        logger.info("El hook ya está instalado en %s", repo_root)
        return

    path = _hook_path(repo_root)
    hook_content = _HOOK_SCRIPT.format(marker=_HOOK_MARKER)

    if os.path.isfile(path):
        # Append to existing hook
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(existing.rstrip("\n") + "\n\n" + hook_content)
        logger.debug("Hook anexado al post-commit existente en %s", path)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(hook_content)
        logger.debug("Hook creado en %s", path)

    # Ensure executable
    current = os.stat(path).st_mode
    os.chmod(path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    logger.info("Hook post-commit instalado en %s", path)


def uninstall(repo_root: str) -> None:
    """Remove the odoo-readme-bot section from the post-commit hook.

    If the hook only contained our section, the file is removed entirely.
    """
    path = _hook_path(repo_root)
    if not os.path.isfile(path):
        logger.info("No hay hook post-commit en %s — nada que eliminar.", repo_root)
        return
    if not is_installed(repo_root):
        logger.info("El hook en %s no es gestionado por odoo-readme-bot.", repo_root)
        return

    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Find the block starting from our marker line to the end of the script
    marker_idx = content.find(_HOOK_MARKER)
    before = content[:marker_idx].rstrip("\n")

    if before.strip() in ("", "#!/usr/bin/env bash", "#!/bin/bash", "#!/bin/sh"):
        # Nothing meaningful before our section — remove the entire file
        os.remove(path)
        logger.info("Hook post-commit eliminado de %s", repo_root)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(before + "\n")
        logger.info("Sección de odoo-readme-bot eliminada del hook en %s", path)
