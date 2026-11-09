"""Command-line entry point for labpipe."""

import argparse
import sys

from labpipe import __version__


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"labpipe {__version__}")
    return 0


def _not_built_yet(phase: int):
    """Return a handler for a job that a later phase will build.

    The Compose stack runs these jobs in order, so each one must exist and exit 0
    before its real code lands.
    """

    def handler(args: argparse.Namespace) -> int:
        print(f"labpipe {args.command}: not built yet (Phase {phase}). Nothing to do.")
        return 0

    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labpipe",
        description="Synthetic HL7 v2 lab results to FHIR R4 to OMOP CDM 5.4.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    version_parser = subparsers.add_parser("version", help="Print the labpipe version and exit.")
    version_parser.set_defaults(func=_cmd_version)

    migrate_parser = subparsers.add_parser(
        "migrate", help="Apply database migrations (safe to rerun)."
    )
    migrate_parser.set_defaults(func=_not_built_yet(2))

    vocab_parser = subparsers.add_parser("vocab", help="Load OMOP vocabularies.")
    vocab_parser.add_argument("action", choices=["load"], help="What to do.")
    vocab_parser.set_defaults(func=_not_built_yet(3))

    run_parser = subparsers.add_parser("run", help="Run the pipeline end to end.")
    run_parser.add_argument("--all", action="store_true", help="Run every stage in order.")
    run_parser.set_defaults(func=_not_built_yet(4))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
