"""Testes da CLI (roteamento argparse, erros e caminhos principais)."""

from __future__ import annotations

import argparse

import pytest
from PIL import Image

from snapclip import capture, cli, clipboard


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "0.1.0" in out


def test_no_command_prints_help_and_fails(capsys):
    code = cli.main([])
    assert code == cli.EXIT_ERROR
    assert "usage" in capsys.readouterr().out.lower()


def test_print_routing_default(monkeypatch, capsys, tmp_path):
    sent = {}

    def fake_grab_full():
        return Image.new("RGB", (12, 8), (5, 5, 5))

    monkeypatch.setattr(capture, "grab_full", fake_grab_full)
    monkeypatch.setattr(clipboard, "set_image", lambda img: sent.update(img=img))

    target = tmp_path / "shot.png"
    code = cli.main(["print", "--save", str(target)])

    assert code == cli.EXIT_OK
    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == "Capturado 12x8 -> area de transferencia"
    assert out[-1] == str(target.resolve())
    assert target.is_file()
    assert isinstance(sent["img"], Image.Image)


def test_print_region_cancel_returns_130(monkeypatch, capsys):
    monkeypatch.setattr(capture, "grab_region", lambda: None)
    code = cli.main(["print", "--region"])
    assert code == cli.EXIT_CANCEL
    assert "Cancelado." in capsys.readouterr().err


def test_copy_text_to_stdout(monkeypatch, capsys):
    monkeypatch.setattr(clipboard, "get_text", lambda: "conteudo do clipboard")
    code = cli.main(["copy"])
    assert code == cli.EXIT_OK
    assert capsys.readouterr().out == "conteudo do clipboard"


def test_copy_empty_clipboard_errors(monkeypatch, capsys):
    monkeypatch.setattr(clipboard, "get_text", lambda: None)
    code = cli.main(["copy"])
    assert code == cli.EXIT_ERROR
    assert "nao contem texto" in capsys.readouterr().err


def test_copy_image_to_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        clipboard, "get_image", lambda: Image.new("RGB", (7, 5), (9, 9, 9))
    )
    target = tmp_path / "clip.png"
    code = cli.main(["copy", "--image", str(target)])
    assert code == cli.EXIT_OK
    assert target.is_file()
    assert capsys.readouterr().out.strip() == str(target.resolve())


def test_paste_from_file(monkeypatch, tmp_path, capsys):
    recorded = {}
    monkeypatch.setattr(clipboard, "set_text", lambda t: recorded.update(text=t))

    source = tmp_path / "texto.txt"
    source.write_text("ola mundo", encoding="utf-8")

    code = cli.main(["paste", str(source)])
    assert code == cli.EXIT_OK
    assert recorded["text"] == "ola mundo"
    assert "Texto copiado" in capsys.readouterr().out


def test_paste_missing_file_errors(capsys):
    code = cli.main(["paste", "nao_existe_12345.txt"])
    assert code == cli.EXIT_ERROR
    assert "nao encontrado" in capsys.readouterr().err


def test_paste_image_and_file_conflict(capsys):
    code = cli.main(["paste", "arquivo.txt", "--image", "img.png"])
    assert code == cli.EXIT_ERROR
    assert "nao os dois" in capsys.readouterr().err


def test_print_and_window_are_mutually_exclusive():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["print", "--region", "--window"])
    assert argparse  # uso do modulo, evita import nao utilizado
