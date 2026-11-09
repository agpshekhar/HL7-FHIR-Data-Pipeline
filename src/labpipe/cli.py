"""Command-line entry point for labpipe."""

import argparse
import sys

from labpipe import __version__


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"labpipe {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labpipe",
        description="Synthetic HL7 v2 lab results to FHIR R4 to OMOP CDM 5.4.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    version_parser = subparsers.add_parser("version", help="Print the labpipe version and exit.")
    version_parser.set_defaults(func=_cmd_version)

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
