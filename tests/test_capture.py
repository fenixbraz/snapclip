"""Testes de captura de tela (smoke + utilidades)."""

from __future__ import annotations

from PIL import Image

from snapclip import capture


def test_virtual_screen_rect_is_plausible():
    x, y, width, height = capture.virtual_screen_rect()
    assert width >= 800
    assert height >= 600


def test_normalize_bbox_orders_coordinates():
    assert capture.normalize_bbox((300, 200, 100, 50)) == (100, 50, 300, 200)


def test_crop_uses_given_bbox():
    image = Image.new("RGB", (20, 20), (1, 2, 3))
    cropped = capture.crop(image, (5, 5, 15, 12))
    assert cropped.size == (10, 7)


def test_grab_full_smoke():
    image = capture.grab_full()
    assert isinstance(image, Image.Image)
    assert image.width >= 800
    assert image.height >= 600
    colors = image.convert("RGB").getcolors(maxcolors=1 << 20)
    assert colors is None or len(colors) > 1  # tela nao e uma cor solida
