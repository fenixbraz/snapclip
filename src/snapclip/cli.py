"""Interface de linha de comando ``snapclip``.

Comandos:

* ``print``  captura a tela e copia a imagem para a area de transferencia
* ``copy``   le a area de transferencia (texto -> stdout; imagem -> arquivo)
* ``paste``  escreve texto/arquivo na area de transferencia
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image

from . import __version__, capture, clipboard

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CANCEL = 130


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapclip",
        description="Ponte de clipboard e screenshots do Windows para fluxos com IA.",
    )
    parser.add_argument(
        "--version", action="version", version=f"snapclip {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="comando")

    # print -----------------------------------------------------------------
    p_print = sub.add_parser(
        "print",
        help="Captura a tela e copia a imagem para a area de transferencia.",
    )
    group = p_print.add_mutually_exclusive_group()
    group.add_argument(
        "--region",
        action="store_true",
        help="Seleciona uma regiao interativamente (ESC cancela).",
    )
    group.add_argument(
        "--window",
        action="store_true",
        help="Captura a janela em foco.",
    )
    p_print.add_argument(
        "--save", metavar="PATH", help="Tambem salva o PNG nesse caminho."
    )
    p_print.set_defaults(func=cmd_print)

    # copy ------------------------------------------------------------------
    p_copy = sub.add_parser(
        "copy",
        help="Le a area de transferencia (texto no stdout, imagem no arquivo).",
    )
    p_copy.add_argument(
        "--image",
        metavar="PATH",
        help="Salva a imagem da area de transferencia como PNG em PATH.",
    )
    p_copy.set_defaults(func=cmd_copy)

    # paste -----------------------------------------------------------------
    p_paste = sub.add_parser(
        "paste",
        help="Copia texto (arquivo/stdin) ou imagem (--image) para o clipboard.",
    )
    p_paste.add_argument(
        "file", nargs="?", help="Arquivo de texto a copiar (padrao: stdin)."
    )
    p_paste.add_argument(
        "--image",
        metavar="FILE",
        help="Copia a imagem do arquivo para a area de transferencia.",
    )
    p_paste.set_defaults(func=cmd_paste)

    return parser


def cmd_print(args: argparse.Namespace) -> int:
    try:
        if args.region:
            image = capture.grab_region()
            if image is None:
                _err("Cancelado.")
                return EXIT_CANCEL
        elif args.window:
            image = capture.grab_window()
        else:
            image = capture.grab_full()
    except Exception as exc:  # noqa: BLE001 - reportar qualquer falha de captura
        _err(f"Erro ao capturar a tela: {exc}")
        return EXIT_ERROR

    try:
        clipboard.set_image(image)
    except Exception as exc:  # noqa: BLE001
        _err(f"Erro ao copiar a imagem para a area de transferencia: {exc}")
        return EXIT_ERROR

    print(f"Capturado {image.width}x{image.height} -> area de transferencia")

    if args.save:
        try:
            target = _resolve(args.save)
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "PNG")
        except Exception as exc:  # noqa: BLE001
            _err(f"Erro ao salvar a imagem: {exc}")
            return EXIT_ERROR
        print(str(target))  # ultima linha stdout: caminho absoluto

    return EXIT_OK


def cmd_copy(args: argparse.Namespace) -> int:
    if args.image:
        try:
            image = clipboard.get_image()
        except clipboard.ClipboardError as exc:
            _err(str(exc))
            return EXIT_ERROR
        if image is None:
            _err("Nenhuma imagem na area de transferencia.")
            return EXIT_ERROR
        target = _resolve(args.image)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "PNG")
        print(str(target))
        return EXIT_OK

    try:
        text = clipboard.get_text()
    except clipboard.ClipboardError as exc:
        _err(str(exc))
        return EXIT_ERROR

    if not text:
        _err("A area de transferencia nao contem texto.")
        return EXIT_ERROR

    sys.stdout.write(text)
    if not text.endswith("\n") and sys.stdout.isatty():
        sys.stdout.write("\n")
    sys.stdout.flush()
    return EXIT_OK


def cmd_paste(args: argparse.Namespace) -> int:
    if args.image and args.file:
        _err("Use --image OU um arquivo de texto, nao os dois.")
        return EXIT_ERROR

    if args.image:
        source = _resolve(args.image)
        if not source.is_file():
            _err(f"Arquivo de imagem nao encontrado: {source}")
            return EXIT_ERROR
        try:
            with Image.open(source) as image:
                clipboard.set_image(image)
                width, height = image.width, image.height
        except Exception as exc:  # noqa: BLE001
            _err(f"Erro ao copiar a imagem: {exc}")
            return EXIT_ERROR
        print(
            f"Imagem copiada para a area de transferencia ({width}x{height})."
        )
        return EXIT_OK

    if args.file:
        source = _resolve(args.file)
        if not source.is_file():
            _err(f"Arquivo nao encontrado: {source}")
            return EXIT_ERROR
        text = source.read_text(encoding="utf-8", errors="replace")
    else:
        data = sys.stdin.buffer.read()
        text = data.decode("utf-8", errors="replace")

    try:
        clipboard.set_text(text)
    except clipboard.ClipboardError as exc:
        _err(str(exc))
        return EXIT_ERROR

    print(f"Texto copiado (~{len(text)} caracteres).")
    return EXIT_OK


def _resolve(path: str) -> Path:
    return Path(path).expanduser().resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_ERROR

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        _err("Cancelado.")
        return EXIT_CANCEL


if __name__ == "__main__":
    sys.exit(main())
