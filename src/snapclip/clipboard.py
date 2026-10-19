"""Acesso a area de transferencia do Windows (texto e imagem).

Usa ``pywin32`` (win32clipboard) com um lote de tentativas, porque a area de
transferencia pode estar travada por outro aplicativo no momento do acesso.

Formatos usados:

* Texto  -> ``CF_UNICODETEXT``
* Imagem -> ``CF_DIB`` (o formato "device independent bitmap" que o
  clipboard do .NET/WinForms - usado pelo opencode/CTRL+V - entende)
"""

from __future__ import annotations

import io
import struct
import time
from typing import Callable, Optional, TypeVar

import pywintypes
import win32clipboard
import win32con
from PIL import Image

# Quantidade de tentativas e espera entre elas ao abrir o clipboard.
CLIPBOARD_RETRIES = 10
CLIPBOARD_DELAY_S = 0.05

T = TypeVar("T")


class ClipboardError(RuntimeError):
    """Erro ao acessar a area de transferencia apos todas as tentativas."""


def _with_retry(action: Callable[[], T]) -> T:
    """Executa ``action`` tentando novamente enquanto o clipboard estiver ocupado."""
    last_error: Optional[Exception] = None
    for _ in range(CLIPBOARD_RETRIES):
        try:
            return action()
        except (pywintypes.error, OSError) as exc:  # clipboard ocupado por outro app
            last_error = exc
            time.sleep(CLIPBOARD_DELAY_S)
    raise ClipboardError(
        "Nao foi possivel acessar a area de transferencia "
        f"(outro aplicativo pode estar usando-a): {last_error}"
    )


# --------------------------------------------------------------------------- #
# Texto
# --------------------------------------------------------------------------- #
def set_text(text: str) -> None:
    """Coloca ``text`` na area de transferencia como texto Unicode."""

    def _do() -> None:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

    _with_retry(_do)


def get_text() -> Optional[str]:
    """Le texto da area de transferencia ou ``None`` se nao houver texto."""
    if not is_text_available():
        return None

    def _do() -> Optional[str]:
        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(
                win32con.CF_UNICODETEXT
            ):
                return None
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    return _with_retry(_do)


def is_text_available() -> bool:
    """Retorna ``True`` se a area de transferencia contem texto."""

    def _do() -> bool:
        win32clipboard.OpenClipboard()
        try:
            return bool(
                win32clipboard.IsClipboardFormatAvailable(
                    win32con.CF_UNICODETEXT
                )
            )
        finally:
            win32clipboard.CloseClipboard()

    return _with_retry(_do)


# --------------------------------------------------------------------------- #
# Imagem
# --------------------------------------------------------------------------- #
def image_to_dib(image: Image.Image) -> bytes:
    """Converte uma imagem Pillow em bytes CF_DIB (BMP sem o file header)."""
    rgb = image.convert("RGB")
    buffer = io.BytesIO()
    rgb.save(buffer, "BMP")
    bmp = buffer.getvalue()
    # Os 14 primeiros bytes sao o BITMAPFILEHEADER; CF_DIB comeca no
    # BITMAPINFOHEADER, ou seja, logo depois deles.
    return bmp[14:]


def dib_to_bmp(dib: bytes) -> bytes:
    """Reconstroi um arquivo BMP completo a partir de bytes CF_DIB."""
    if len(dib) < 16:
        raise ValueError("CF_DIB muito curto.")
    bi_size = struct.unpack_from("<I", dib, 0)[0]
    bit_count = struct.unpack_from("<H", dib, 14)[0]
    compression = struct.unpack_from("<I", dib, 16)[0]
    clr_used = struct.unpack_from("<I", dib, 32)[0] if len(dib) >= 36 else 0
    if clr_used == 0 and bit_count <= 8:
        clr_used = 1 << bit_count
    extra_masks = 12 if compression == 3 else 0  # BI_BITFIELDS
    off_bits = 14 + bi_size + extra_masks + clr_used * 4
    file_header = b"BM" + struct.pack("<IHHI", 14 + len(dib), 0, 0, off_bits)
    return file_header + dib


def set_image(image: Image.Image) -> None:
    """Coloca ``image`` na area de transferencia como CF_DIB."""
    dib = image_to_dib(image)

    def _do() -> None:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
            # Alguns aplicativos preferem PNG; oferecemos os dois formatos.
            try:
                win32clipboard.SetClipboardData(_cf_png(), _png_bytes(image))
            except pywintypes.error:
                pass
        finally:
            win32clipboard.CloseClipboard()

    _with_retry(_do)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGBA").save(buffer, "PNG")
    return buffer.getvalue()


def _cf_png() -> int:
    return win32clipboard.RegisterClipboardFormat("PNG")


def get_image() -> Optional[Image.Image]:
    """Le a imagem da area de transferencia ou ``None`` se nao houver imagem."""
    dib = _get_dib()
    if dib:
        try:
            return Image.open(io.BytesIO(dib_to_bmp(dib)))
        except Exception:
            pass
    return _grabclipboard_fallback()


def _get_dib() -> Optional[bytes]:
    def _do() -> Optional[bytes]:
        win32clipboard.OpenClipboard()
        try:
            for fmt in (win32con.CF_DIB, getattr(win32con, "CF_DIBV5", 17)):
                if win32clipboard.IsClipboardFormatAvailable(fmt):
                    data = win32clipboard.GetClipboardData(fmt)
                    if isinstance(data, str):
                        data = data.encode("latin-1")
                    return data
            return None
        finally:
            win32clipboard.CloseClipboard()

    return _with_retry(_do)


def _grabclipboard_fallback() -> Optional[Image.Image]:
    try:
        from PIL import ImageGrab

        result = ImageGrab.grabclipboard()
    except Exception:
        return None
    if isinstance(result, Image.Image):
        return result
    return None


def is_image_available() -> bool:
    """Retorna ``True`` se a area de transferencia contem uma imagem DIB."""

    def _do() -> bool:
        win32clipboard.OpenClipboard()
        try:
            return bool(
                win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB)
            )
        finally:
            win32clipboard.CloseClipboard()

    return _with_retry(_do)
