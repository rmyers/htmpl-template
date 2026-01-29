import argparse
import copier

TEMPLATE_REPO = "gh:rmyers/htmpl-template.git"


def init(args):
    """Create a new htmpl project."""
    copier.run_copy(TEMPLATE_REPO, args.dest, vcs_ref=args.version)
    print(f"\n✓ Created htmpl project in {args.dest}")
    print(f"  Run 'cd {args.dest} && make dev' to start")
    print("  Admin UI available at /admin")


def main():
    parser = argparse.ArgumentParser(description="htmpl project generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init subcommand
    init_parser = subparsers.add_parser("init", help="Create a new htmpl project")
    init_parser.add_argument("dest", help="Destination directory")
    init_parser.add_argument("--version", "-v", help="Template version (git tag)")
    init_parser.set_defaults(func=init)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
