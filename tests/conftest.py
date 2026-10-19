"""Fixtures compartilhadas: preserva/restaura a area de transferencia real."""

from __future__ import annotations

import pytest
from PIL import Image

from snapclip import clipboard


@pytest.fixture
def preserved_clipboard():
    """Salva o conteudo atual do clipboard e restaura ao final do teste.

    Guarda texto e imagem (se houver). Se ambos existirem, a imagem tem
    prioridade na restauracao (o clipboard suporta um "principal" por vez).
    """
    text = None
    image = None
    try:
        text = clipboard.get_text()
    except Exception:
        text = None
    try:
        image = clipboard.get_image()
        if image is not None:
            image = image.copy()
    except Exception:
        image = None

    yield

    try:
        if image is not None:
            clipboard.set_image(image)
        elif text is not None:
            clipboard.set_text(text)
        else:
            clipboard.set_text("")
    except Exception:
        # Restauracao best-effort: nunca falha o teste por causa disso.
        pass


_ = Image  # mantem o import explicito para clareza
