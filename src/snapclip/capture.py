"""Captura de tela: tela inteira, janela em foco e regiao interativa.

Todas as capturas sao feitas em pixels **fisicos** (consistente com o DPI
real do monitor). O setup de DPI awareness roda antes de qualquer captura para
evitar a classe de erro de escala (ex.: 1.31x) documentada em
``dev-stack/REGUA_CLIQUES.md``.
"""

from __future__ import annotations

import ctypes
from typing import Optional

import win32api
import win32gui
from PIL import Image, ImageGrab

# Metricas do "desktop virtual" (todos os monitores).
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

_dpi_ready = False


def setup_dpi_awareness() -> None:
    """Habilita per-monitor-v2 DPI awareness (com fallbacks), uma vez so."""
    global _dpi_ready
    if _dpi_ready:
        return
    # 1) Per-monitor v2 (Windows 10 1703+).
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        _dpi_ready = True
        return
    except Exception:
        pass
    # 2) Per-monitor (Windows 8.1+).
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _dpi_ready = True
        return
    except Exception:
        pass
    # 3) System DPI aware (Vista+).
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    _dpi_ready = True


def virtual_screen_rect() -> tuple[int, int, int, int]:
    """Retorna ``(x, y, largura, altura)`` do desktop virtual."""
    return (
        win32api.GetSystemMetrics(SM_XVIRTUALSCREEN),
        win32api.GetSystemMetrics(SM_YVIRTUALSCREEN),
        win32api.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        win32api.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def grab_full() -> Image.Image:
    """Captura todos os monitores em um unico bitmap."""
    setup_dpi_awareness()
    return ImageGrab.grab(all_screens=True)


def foreground_window_rect() -> tuple[int, int, int, int]:
    """Retorna ``(left, top, right, bottom)`` da janela em foco."""
    hwnd = win32gui.GetForegroundWindow()
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return int(left), int(top), int(right), int(bottom)


def normalize_bbox(
    bbox: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Garante largura/altura positivas e valores inteiros."""
    left, top, right, bottom = (int(v) for v in bbox)
    if right < left:
        left, right = right, left
    if bottom < top:
        top, bottom = bottom, top
    return left, top, right, bottom


def crop(image: Image.Image, bbox: tuple[int, int, int, int]) -> Image.Image:
    """Recorta ``image`` no retangulo dado (coordenadas da propria imagem)."""
    return image.crop(normalize_bbox(bbox))


def grab_window() -> Image.Image:
    """Captura a janela em foco."""
    setup_dpi_awareness()
    left, top, right, bottom = normalize_bbox(foreground_window_rect())
    if right - left <= 0 or bottom - top <= 0:
        raise RuntimeError("Nao foi possivel obter o retangulo da janela em foco.")
    return ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)


def grab_region() -> Optional[Image.Image]:
    """Abre um seletor interativo e retorna a regiao escolhida.

    Usa uma janela tkinter cobrindo o desktop virtual, com a captura atual como
    fundo. Arrastar seleciona; ``ESC`` cancela. Retorna ``None`` em cancelamento.
    """
    setup_dpi_awareness()
    import tkinter as tk

    screenshot = ImageGrab.grab(all_screens=True)
    x, y, width, height = virtual_screen_rect()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.geometry(_geometry(width, height, x, y))

    canvas = tk.Canvas(
        root, cursor="cross", highlightthickness=0, borderwidth=0
    )
    canvas.pack(fill="both", expand=True)

    # A captura tem origem no canto superior-esquerdo do desktop virtual,
    # que coincide com o (0,0) do canvas.
    photo = _to_photoimage(screenshot)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    canvas.image = photo  # evita coleta de lixo

    state: dict[str, object] = {"x0": 0, "y0": 0, "rect": None, "cancel": False}

    def on_press(event: "tk.Event") -> None:
        state["x0"], state["y0"] = event.x, event.y
        state["rect"] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="#e11d48", width=2
        )

    def on_drag(event: "tk.Event") -> None:
        if state["rect"] is not None:
            canvas.coords(state["rect"], state["x0"], state["y0"], event.x, event.y)

    def on_release(event: "tk.Event") -> None:
        state["rect"] = (state["x0"], state["y0"], event.x, event.y)
        root.quit()

    def on_cancel(_event: "tk.Event") -> None:
        state["cancel"] = True
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_cancel)

    root.mainloop()
    root.destroy()

    if state["cancel"] or not isinstance(state["rect"], tuple):
        return None
    return crop(screenshot, state["rect"])  # type: ignore[arg-type]


def _geometry(width: int, height: int, x: int, y: int) -> str:
    sx = f"+{x}" if x >= 0 else str(x)
    sy = f"+{y}" if y >= 0 else str(y)
    return f"{width}x{height}{sx}{sy}"


def _to_photoimage(image: Image.Image):
    from PIL import ImageTk

    return ImageTk.PhotoImage(image)
