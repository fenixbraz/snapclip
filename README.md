# snapclip

**Ponte de clipboard e screenshots do Windows para fluxos de trabalho com IA.**

O `snapclip` conecta o terminal (opencode, Claude Code, ChatGPT em CLI etc.) à
área de transferência e à tela do Windows. Com um comando você tira um print de
uma região e ele já vai para o clipboard no formato que a sessão de IA entende
(`CF_DIB`) — é só dar **Ctrl+V** no chat.

- **CLI** (`snapclip`): `print`, `copy`, `paste`.
- **Servidor MCP** (`snapclip-mcp`): 3 ferramentas para a IA controlar tela e
  clipboard por conta própria (transporte stdio).

## Por que existe

Tirar print, abrir o Paint, salvar, arrastar para o chat... trava o raciocínio.
O `snapclip` transforma "quero mostrar isso pra IA" em um comando. A captura
vira imagem **no clipboard** — exatamente o que o Ctrl+V do opencode lê via
`[System.Windows.Forms.Clipboard]::GetImage()`, sem arquivos temporários.

O tratamento de DPI (per-monitor v2) garante que a captura saia em **pixels
físicos**, evitando a classe de erro de escala (ex.: 1,31x) que desalinha
cliques e recortes.

## O que ele resolve no dia a dia

- **"Olha isso" vira um comando.** `snapclip print --region` → `Ctrl+V` no chat da IA. Sem Paint, sem salvar arquivo, sem arrastar — não quebra o raciocínio.
- **Bug visual se mostra, não se descreve.** A captura vai direto pro clipboard no formato certo pro `Ctrl+V` do opencode — a IA vê a tela que você vê.
- **Agentes ganham olhos.** Com o `snapclip-mcp`, a própria IA tira o print e lê/escreve o clipboard — o ciclo "errou → se olha → se corrige" fecha sozinho.
- **Roda de qualquer terminal — sem daemon.** CLI puro: sem app na bandeja, sem hotkey registrada, sem janela. Funciona de scripts e de agentes.
- **Pixel exato.** DPI per-monitor v2: nada de captura borrada ou desalinhada por escala.

## Requisitos

- Windows 10/11
- Python 3.11+ (testado com 3.13)
- Dependências: `Pillow`, `pywin32`, `mcp` (SDK oficial 2.x)

## Instalação

```powershell
# a partir da pasta do projeto
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Os dois comandos ficam disponíveis dentro do ambiente:

```powershell
.\.venv\Scripts\snapclip.exe --version   # snapclip 0.1.0
.\.venv\Scripts\snapclip-mcp.exe         # servidor MCP (stdio)
```

> Atalho: com `pipx install .` os scripts ficam no PATH sem ativar o venv.

## Comandos

| Comando | O que faz |
|---|---|
| `snapclip print` | Captura toda a área de trabalho (todos os monitores) e copia a imagem para o clipboard. |
| `snapclip print --window` | Captura a janela em foco. |
| `snapclip print --region` | Abre um seletor: arraste para recortar; **ESC** cancela. |
| `snapclip print --save PATH` | Além de copiar, salva o PNG em `PATH` (imprime o caminho absoluto na última linha). |
| `snapclip copy` | Lê o **texto** do clipboard e manda para o stdout (sem enfeites, seguro para pipe). |
| `snapclip copy --image PATH` | Salva a **imagem** do clipboard como PNG em `PATH` e imprime o caminho. |
| `snapclip paste` | Lê do stdin e copia o texto para o clipboard. |
| `snapclip paste FILE` | Copia o texto de `FILE` para o clipboard. |
| `snapclip paste --image FILE` | Copia uma imagem (PNG) para o clipboard. |
| `snapclip --version` | Mostra a versão. |

### Exemplos

```powershell
# print de região -> cola direto na sessão de IA com Ctrl+V
snapclip print --region

# print da tela inteira e salva o arquivo para anexar depois
snapclip print --save .\print.png

# joga o texto de um arquivo no clipboard
snapclip paste .\notas.txt

# pega o texto do clipboard e usa como entrada de outro comando
snapclip copy | findstr "erro"

# salva a imagem que está no clipboard
snapclip copy --image .\recorte.png
```

**Fluxo matador:** `snapclip print --region` → `Ctrl+V` na sessão de IA. A
imagem já está no clipboard no formato que o chat lê.

## Servidor MCP (opencode / Claude)

O `snapclip-mcp` expõe três ferramentas:

| Ferramenta | Descrição |
|---|---|
| `screenshot(mode="full"\|"region"\|"window", save_path=None)` | Captura e salva PNG (padrão: `%TEMP%\snapclip\shot_<timestamp>.png`). Copia também para o clipboard. |
| `clipboard_get(kind="text"\|"image")` | Devolve o texto, ou salva a imagem em `%TEMP%\snapclip\clip_<timestamp>.png` e devolve o caminho. |
| `clipboard_set(text=None, image_path=None)` | Escreve **texto** ou **imagem** (exatamente um dos dois) no clipboard. |

### Configurar no `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "snapclip": {
      "type": "local",
      "command": [
        "C:\\caminho\\para\\snapclip\\.venv\\Scripts\\snapclip-mcp.exe"
      ],
      "enabled": true,
      "environment": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Detalhes que importam:

- Troque `C:\\caminho\\para\\snapclip` pelo caminho onde você clonou o projeto.
- `"command"` é uma **lista de strings** (nunca uma string única).
- `"type": "local"` é obrigatório.
- No JSON, escape as barras invertidas do Windows (`\\`).
- `"environment"` com `PYTHONUTF8=1` garante acentuação correta.
- Reinicie o opencode após alterar a configuração (ela é lida na inicialização).

## Roadmap

- OCR de região (texto da imagem -> clipboard).
- Hotkey global **Ctrl+Shift+P** para captura instantânea.
- Saída em JSON (`--json`) para automação e agentes.

## Licença

MIT — veja [LICENSE](LICENSE). Autor: Ney.

---

## English (short)

**snapclip** is a Windows clipboard & screenshot bridge for AI terminal
workflows. It ships a CLI (`snapclip`) and a stdio MCP server
(`snapclip-mcp`).

- `snapclip print [--region|--window] [--save PATH]` — capture the screen and
  put the image on the clipboard as `CF_DIB` (what `Ctrl+V` in opencode/Claude
  reads). `--save` writes a PNG and prints its absolute path.
- `snapclip copy [--image PATH]` — dump clipboard text to stdout, or save the
  clipboard image to a PNG file.
- `snapclip paste [FILE] [--image FILE]` — set clipboard text (from a file or
  stdin) or an image.

Install: create a venv and `pip install -e .` (or `pipx install .`).
Requires Python 3.11+, Pillow, pywin32 and the official `mcp` SDK (2.x).
MIT licensed.
