# -*- coding: utf-8 -*-
"""Servidor MCP ``snapclip-mcp`` (transporte stdio).

Expoe tres ferramentas para uma sessao de IA controlar a tela e a area de
transferencia do Windows:

* ``screenshot``     captura tela inteira / janela / regiao
* ``clipboard_get``  le texto ou salva a imagem do clipboard
* ``clipboard_set``  escreve texto ou imagem no clipboard

Uso (registro MCP, stdio):  snapclip-mcp
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import anyio
from mcp.server.mcpserver import MCPServer

from . import __version__, capture, clipboard

TEMP_DIR = Path(__import__("tempfile").gettempdir()) / "snapclip"

mcp = MCPServer(
    "snapclip",
    instructions=(
        "Ponte de clipboard e screenshots do Windows. Use screenshot para "
        "capturar a tela (full/region/window) e clipboard_get/clipboard_set "
        "para ler e escrever texto ou imagem na area de transferencia."
    ),
)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def _ensure_temp_dir() -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR


def _do_screenshot(mode: str, save_path: Optional[str]) -> str:
    mode = (mode or "full").lower()
    if mode == "full":
        image = capture.grab_full()
    elif mode == "window":
        image = capture.grab_window()
    elif mode == "region":
        image = capture.grab_region()
        if image is None:
            return "Cancelado pelo usuario (nenhuma regiao selecionada)."
    else:
        return (
            f"Modo invalido: '{mode}'. Use 'full', 'region' ou 'window'."
        )

    if save_path:
        target = Path(save_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target = _ensure_temp_dir() / f"shot_{_timestamp()}.png"

    image.save(target, "PNG")
    try:
        clipboard.set_image(image)
        clip_note = " Imagem tambem copiada para a area de transferencia."
    except Exception:  # noqa: BLE001 - salvar ja e o suficiente
        clip_note = " (Nao foi possivel copiar para a area de transferencia.)"
    return (
        f"Captura '{mode}' salva: {target} "
        f"({image.width}x{image.height}).{clip_note}"
    )


def _do_clipboard_get(kind: str) -> str:
    kind = (kind or "text").lower()
    if kind == "text":
        text = clipboard.get_text()
        if text is None:
            return "A area de transferencia nao contem texto."
        if text == "":
            return "A area de transferencia contem texto vazio."
        return text
    if kind == "image":
        image = clipboard.get_image()
        if image is None:
            return "A area de transferencia nao contem imagem."
        target = _ensure_temp_dir() / f"clip_{_timestamp()}.png"
        image.save(target, "PNG")
        return (
            f"Imagem do clipboard salva: {target} "
            f"({image.width}x{image.height})."
        )
    return f"Tipo invalido: '{kind}'. Use 'text' ou 'image'."


def _do_clipboard_set(
    text: Optional[str], image_path: Optional[str]
) -> str:
    if (text is None) == (image_path is None):
        return "Informe exatamente um de: text OU image_path."

    if text is not None:
        clipboard.set_text(text)
        return f"Texto copiado para a area de transferencia (~{len(text)} caracteres)."

    assert image_path is not None
    source = Path(image_path).expanduser().resolve()
    if not source.is_file():
        return f"Arquivo de imagem nao encontrado: {source}"
    from PIL import Image

    with Image.open(source) as image:
        clipboard.set_image(image)
        width, height = image.width, image.height
    return (
        f"Imagem copiada para a area de transferencia ({width}x{height})."
    )


@mcp.tool(structured_output=False)
async def screenshot(mode: str = "full", save_path: str | None = None) -> str:
    """Captura a tela e salva como PNG.

    Args:
        mode: "full" (todos os monitores), "window" (janela em foco) ou
            "region" (selecao interativa; ESC cancela).
        save_path: caminho opcional do PNG. Se omitido, salva em
            %TEMP%/snapclip/shot_<timestamp>.png.
    """
    return await anyio.to_thread.run_sync(_do_screenshot, mode, save_path)


@mcp.tool(structured_output=False)
async def clipboard_get(kind: str = "text") -> str:
    """Le a area de transferencia.

    Args:
        kind: "text" devolve o texto; "image" salva a imagem em
            %TEMP%/snapclip/clip_<timestamp>.png e devolve o caminho.
    """
    return await anyio.to_thread.run_sync(_do_clipboard_get, kind)


@mcp.tool(structured_output=False)
async def clipboard_set(
    text: str | None = None, image_path: str | None = None
) -> str:
    """Escreve na area de transferencia (exatamente um dos parametros).

    Args:
        text: texto a copiar.
        image_path: caminho de uma imagem (PNG) a copiar.
    """
    return await anyio.to_thread.run_sync(_do_clipboard_set, text, image_path)


def main() -> None:
    """Ponto de entrada do console script ``snapclip-mcp``."""
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
