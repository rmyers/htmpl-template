#!/usr/bin/env python
"""Build release artifacts from the rendered/ symlink structure.

This script generates static files (like components.ttl) from the
symlinked rendered/ directory and places them in the template for
distribution.
"""

import argparse
import tomllib
from pathlib import Path

from rendered.services.htmpl_admin.graph import build_component_ttl


def find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


def build_ttl(rendered_dir: Path, output_path: Path) -> None:
    """Generate TTL from rendered/ and write to output."""
    ttl_content = build_component_ttl(rendered_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ttl_content)
    print(f"Generated {output_path}")


def validate_symlinks(rendered_dir: Path) -> list[str]:
    """Check that all symlinks in rendered/ are valid."""
    errors = []
    for path in rendered_dir.rglob("*"):
        if path.is_symlink():
            target = path.resolve()
            if not target.exists():
                errors.append(f"Broken symlink: {path} -> {path.readlink()}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Build release artifacts")
    parser.add_argument(
        "--rendered-dir",
        type=Path,
        default=None,
        help="Path to rendered/ directory (default: auto-detect)",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=None,
        help="Path to template/ directory (default: auto-detect)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate symlinks, don't generate files",
    )
    parser.add_argument(
        "--ttl-output",
        type=Path,
        default=None,
        help="Custom output path for TTL file",
    )
    args = parser.parse_args()

    root = find_project_root()
    rendered_dir = args.rendered_dir or root / "rendered"
    template_dir = args.template_dir or root / "template"

    if not rendered_dir.exists():
        raise SystemExit(f"rendered/ directory not found: {rendered_dir}")

    # Validate symlinks
    errors = validate_symlinks(rendered_dir)
    if errors:
        print("Symlink validation errors:")
        for err in errors:
            print(f"  - {err}")
        raise SystemExit(1)
    print("✓ All symlinks valid")

    if args.validate_only:
        return

    # Generate TTL file
    # Place it in a location that gets copied to rendered projects
    ttl_output = (
        args.ttl_output
        or template_dir
        / "{{name}}"
        / "app"
        / "services"
        / "htmpl_admin"
        / "components.ttl"
    )
    build_ttl(template_dir, ttl_output)

    print("\nBuild complete!")
    print(f"  TTL: {ttl_output}")


if __name__ == "__main__":
    main()
