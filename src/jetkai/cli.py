"""Command line entry point: `jetkai fetch|build|verify|preview`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config


def _split(value: str | None, valid: list[str], what: str) -> list[str]:
    if not value:
        return valid
    items = [v.strip() for v in value.split(",") if v.strip()]
    unknown = [v for v in items if v not in valid]
    if unknown:
        raise SystemExit(f"unknown {what}: {unknown}; valid: {valid}")
    return items


def _built_fonts(config, paths: list[Path]) -> list[Path]:
    if paths:
        return paths
    found = sorted((config.output_dir / "ttf").glob("*.ttf"))
    if not found:
        raise SystemExit("no fonts in output/ttf; run `jetkai build` first")
    return found


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jetkai", description="Build JetKai Mono")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="download pinned source fonts")
    p.add_argument("--force", action="store_true", help="re-download even if present")

    p = sub.add_parser("build", help="merge fonts into output/ttf")
    p.add_argument("--variants", help="comma-separated variant keys (default: all)")
    p.add_argument("--styles", help="comma-separated style keys (default: all)")
    p.add_argument("-j", "--jobs", type=int, help="parallel builds (default: from config)")
    p.add_argument("--no-verify", action="store_true", help="skip checks after building")

    p = sub.add_parser("verify", help="check built fonts")
    p.add_argument("fonts", nargs="*", type=Path)

    p = sub.add_parser("preview", help="render PNG specimens into output/preview (needs Pillow)")
    p.add_argument("fonts", nargs="*", type=Path)

    p = sub.add_parser("package", help="zip built fonts per family into output/dist")
    p.add_argument("--variants", help="comma-separated variant keys (default: all)")
    p.add_argument("--styles", help="comma-separated style keys (default: all)")

    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "fetch":
        from .fetch import fetch_all

        fetch_all(config, force=args.force)
    elif args.command == "build":
        from .build import build_all
        from .verify import verify_all

        variants = _split(args.variants, list(config.variants), "variants")
        styles = _split(args.styles, list(config.styles), "styles")
        outputs = build_all(config, variants, styles, args.jobs or config.jobs)
        if not args.no_verify and not verify_all(outputs, config):
            sys.exit(1)
    elif args.command == "verify":
        from .verify import verify_all

        if not verify_all(_built_fonts(config, args.fonts), config):
            sys.exit(1)
    elif args.command == "preview":
        from .preview import render

        for path in _built_fonts(config, args.fonts):
            print(render(path, config.output_dir / "preview" / f"{path.stem}.png"))
    elif args.command == "package":
        from .package import package

        variants = _split(args.variants, list(config.variants), "variants")
        styles = _split(args.styles, list(config.styles), "styles")
        package(config, variants, styles)


if __name__ == "__main__":
    main()
