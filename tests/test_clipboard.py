"""Testes de ida-e-volta do clipboard (texto e imagem)."""

from __future__ import annotations

import io

from PIL import Image

from snapclip import clipboard


def test_text_roundtrip(preserved_clipboard):
    clipboard.set_text("snapclip teste 123 acentuacao: acao")
    assert clipboard.get_text() == "snapclip teste 123 acentuacao: acao"


def test_get_text_empty_returns_none(preserved_clipboard):
    clipboard.set_text("")
    # Texto vazio e devolvido como "" (o CLI trata como ausencia de texto).
    assert clipboard.get_text() == ""


def test_image_to_dib_strips_file_header():
    image = Image.new("RGB", (4, 3), (10, 20, 30))
    dib = clipboard.image_to_dib(image)
    # CF_DIB comeca no BITMAPINFOHEADER (biSize == 40 para BI_RGB).
    assert dib[0:4] == (40).to_bytes(4, "little")


def test_dib_to_bmp_reopens_in_pillow():
    image = Image.new("RGB", (5, 4), (200, 100, 50))
    dib = clipboard.image_to_dib(image)
    bmp = clipboard.dib_to_bmp(dib)
    assert bmp[:2] == b"BM"
    reopened = Image.open(io.BytesIO(bmp))
    assert reopened.size == (5, 4)


def test_image_roundtrip(preserved_clipboard):
    source = Image.new("RGB", (40, 30), (0, 0, 0))
    for x in range(0, 40, 2):
        for y in range(0, 30, 2):
            source.putpixel((x, y), (255, 255, 255))

    clipboard.set_image(source)
    result = clipboard.get_image()

    assert result is not None
    assert result.size == (40, 30)

    # Diferenca media de pixel toleravel (conversao/compactacao).
    original_bytes = source.convert("RGB").tobytes()
    result_bytes = result.convert("RGB").tobytes()
    diff = sum(
        abs(a - b) for a, b in zip(original_bytes, result_bytes)
    ) / len(original_bytes)
    assert diff < 8
