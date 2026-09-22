"""`scitex-stats skills` — list / get / install agent-facing skills bundled with this package.

Self-contained. No scitex-dev runtime dep — walks the package's own
`_skills/scitex-stats/` directory directly.
"""

from __future__ import annotations

import os as _os
from pathlib import Path

import click

PKG = "scitex-stats"


def _skills_root() -> Path:
    """Resolve the bundled `_skills/scitex-stats/` directory."""
    import scitex_stats

    pkg_dir = Path(scitex_stats.__file__).parent
    return pkg_dir / "_skills" / PKG


def _list_skill_files(root: Path) -> list[Path]:
    """All `.md` files under `_skills/scitex-stats/` (recursive)."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


@click.group(name="skills")
def skills_group() -> None:
    """Agent-facing skills bundled with scitex-stats.

    \b
    Examples:
      $ scitex-stats skills list
      $ scitex-stats skills get 01_installation
      $ scitex-stats skills install                      # → ~/.scitex/dev/skills/scitex-stats/
      $ scitex-stats skills install --claude-symlink     # also expose to ~/.claude/skills/scitex/
    """


@skills_group.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def skills_list(as_json: bool) -> None:
    """List skill files bundled with this package.

    \b
    Example:
      $ scitex-stats skills list
      $ scitex-stats skills list --json
    """
    root = _skills_root()
    files = _list_skill_files(root)
    if as_json:
        import json as _json

        click.echo(
            _json.dumps(
                [{"name": p.stem, "path": str(p)} for p in files],
                indent=2,
            )
        )
        return
    if not files:
        click.echo(f"no skills found at {root}", err=True)
        raise SystemExit(1)
    for p in files:
        rel = p.relative_to(root)
        click.echo(f"{p.stem:36s}  {rel}")


@skills_group.command(name="get")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def skills_get(name: str, as_json: bool) -> None:
    """Print the contents of a skill file by NAME (e.g. `01_installation`).

    \b
    Example:
      $ scitex-stats skills get 01_installation
      $ scitex-stats skills get 02_quick-start --json
    """
    root = _skills_root()
    target_stem = name[:-3] if name.endswith(".md") else name
    match = next((p for p in _list_skill_files(root) if p.stem == target_stem), None)
    if match is None:
        click.echo(f"skill not found: {name}", err=True)
        available = ", ".join(p.stem for p in _list_skill_files(root)[:8])
        click.echo(f"available: {available}…", err=True)
        raise SystemExit(1)
    if as_json:
        import json as _json

        click.echo(
            _json.dumps(
                {
                    "name": match.stem,
                    "path": str(match),
                    "content": match.read_text(encoding="utf-8"),
                },
                indent=2,
            )
        )
        return
    click.echo(match.read_text(encoding="utf-8"))


def _default_skills_base() -> Path:
    """Default base dir for ``skills install`` (PS-145 plugin-port).

    Caller-owned ``SCITEX_STATS_SKILLS_DIR`` wins when set; otherwise the
    shared ecosystem skills tree. The consumer populates the variable from
    their own startup — this package never hardcodes another package's
    user-state tree as its only destination.
    """
    override = _os.environ.get("SCITEX_STATS_SKILLS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".scitex" / "dev" / "skills"


@skills_group.command(name="install")
@click.option(
    "--dest",
    type=click.Path(),
    default=None,
    help="Destination dir (default: $SCITEX_STATS_SKILLS_DIR or the shared skills tree).",
)
@click.option(
    "--no-link",
    "no_link",
    is_flag=True,
    help="Copy files instead of symlinking. Default is symlink.",
)
@click.option(
    "--claude-symlink",
    is_flag=True,
    help="Also expose at ~/.claude/skills/scitex/ for Claude Code consumers.",
)
@click.option("--dry-run", is_flag=True, help="Preview without copying/linking.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def skills_install(
    dest: str | None,
    no_link: bool,
    claude_symlink: bool,
    dry_run: bool,
    yes: bool,
) -> None:
    """Install this package's skills into a target directory.

    \b
    Default: symlink the entire `_skills/scitex-stats/` dir to
    `$SCITEX_STATS_SKILLS_DIR/scitex-stats/` when set, else the shared
    skills tree, so add/rename/delete in source propagates immediately.

    Use --claude-symlink to also expose at ~/.claude/skills/scitex/ for
    Claude Code's skill loader.

    \b
    Example:
      $ scitex-stats skills install
      $ scitex-stats skills install --claude-symlink
      $ scitex-stats skills install --no-link --dest /tmp/scitex-stats-skills
    """
    del yes  # accepted for §2 compliance; install is non-interactive
    src = _skills_root().resolve()
    if not src.is_dir():
        click.echo(f"no skills directory at {src}", err=True)
        raise SystemExit(1)

    base = Path(dest).expanduser() if dest else _default_skills_base()
    target = base / PKG

    if dry_run:
        action = "copy" if no_link else "symlink"
        click.echo(f"would {action} {src} → {target}")
        if claude_symlink:
            link = Path.home() / ".claude" / "skills" / "scitex"
            click.echo(f"would symlink {link} → {base}")
        return

    base.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        import shutil as _shutil

        _shutil.rmtree(target)

    if no_link:
        import shutil as _shutil

        _shutil.copytree(src, target)
        click.echo(f"copied {src} → {target}")
    else:
        _os.symlink(src, target, target_is_directory=True)
        click.echo(f"linked {target} → {src}")

    if claude_symlink:
        link = Path.home() / ".claude" / "skills" / "scitex"
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        if not link.exists():
            _os.symlink(base.resolve(), link, target_is_directory=True)
            click.echo(f"linked {link} → {base}")
        else:
            click.echo(
                f"warning: {link} exists and is not a symlink — skipping",
                err=True,
            )
