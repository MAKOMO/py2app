import argparse
import pathlib
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from . import _builder, _config


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        prog=f"{sys.executable} -mpy2app", description="Build macOS executable bundles"
    )
    parser.add_argument(
        "--pyproject-toml",
        dest="pyproject",
        default="pyproject.toml",
        metavar="FILE",
        type=pathlib.Path,
        help="pyproject.toml path",
    )
    parser.add_argument(
        "--semi-standalone",
        dest="build_type",
        default=None,
        action="store_const",
        const=_config.BuildType.SEMI_STANDALONE,
        help="build a semi-standalone bundle",
    )
    parser.add_argument(
        "--alias",
        dest="build_type",
        default=_config.BuildType.SEMI_STANDALONE,
        action="store_const",
        const=_config.BuildType.ALIAS,
        help="build an alias bundle",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.pyproject, "rb") as stream:
            contents = tomllib.load(stream)
    except OSError as exc:
        print(f"Cannot open {str(args.pyproject)!r}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        config = _config.parse_pyproject(contents, args.pyproject.parent)
    except _config.ConfigurationError as exc:
        print(f"{args.pyproject}: {exc}", file=sys.stderr)
        sys.exit(1)

    # XXX: I don't particularly like poking directly in '_locals'
    if args.build_type is not None:
        config._local["build-type"] = args.build_type
    return config


def main():
    config = parse_arguments(sys.argv[1:])

    for bundle in config.bundles:
        scanner = _builder.Scanner(config)
        scanner.process_bundle(bundle)
        # scanner.graph.report()
        # print(list(scanner.graph.roots()))


if __name__ == "__main__":
    main()
