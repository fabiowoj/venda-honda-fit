#!/usr/bin/env python3
"""Marca o carro como vendido ou de volta à venda.

    python3 scripts/vendido.py sim      # vendido
    python3 scripts/vendido.py nao      # à venda de novo
    python3 scripts/vendido.py          # só mostra o estado atual

Também dá para fazer pelo GitHub, sem computador: aba Actions →
"Vendido / à venda" → Run workflow → escolher a opção.

Quando vendido:
  - a página mostra o carimbo VENDIDO, o preço riscado e uma faixa de aviso;
  - somem os botões de WhatsApp, e-mail e os links da OLX/Webmotors;
  - título, descrição e dados para o Google passam a dizer "vendido"
    (schema.org SoldOut / og "out of stock");
  - a página pede para sair da busca (robots "noindex"), para ninguém
    mais ligar procurando o carro.
Tudo volta ao normal com "nao".
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEX = RAIZ / "index.html"
LLMS = RAIZ / "llms.txt"

ROBOTS_A_VENDA = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
ROBOTS_VENDIDO = "noindex, follow"
PREFIXO = "VENDIDO · "
AVISO_LLMS = "> **Status: VENDIDO.** Este carro já foi vendido e não está mais disponível.\n\n"


def trocar(texto, padrao, novo, nome):
    texto, n = re.subn(padrao, novo, texto, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"Não achei {nome} no index.html")
    return texto


def prefixar(texto, padrao, vendido, nome):
    """Coloca ou tira o prefixo "VENDIDO · " do conteúdo capturado pelo grupo 2."""
    def f(m):
        conteudo = m.group(2).removeprefix(PREFIXO)
        return m.group(1) + (PREFIXO + conteudo if vendido else conteudo) + m.group(3)
    return trocar(texto, padrao, f, nome)


def aplicar(vendido):
    t = INDEX.read_text(encoding="utf-8")
    t = trocar(t, r'<body data-status="[^"]*">', f'<body data-status="{"vendido" if vendido else "a-venda"}">', "<body data-status>")
    t = prefixar(t, r"(<title>)(.*?)(</title>)", vendido, "<title>")
    # No título, "VENDIDO · ... à venda em Brasília" se contradiz: tira o "à venda" (e devolve depois).
    t = trocar(t, r"(<title>)(.*?)(</title>)",
               lambda m: m.group(1) + (m.group(2).replace(" à venda em ", " em ") if vendido
                                       else m.group(2).replace(" em ", " à venda em ", 1) if " à venda " not in m.group(2)
                                       else m.group(2)) + m.group(3), "<title>")
    t = prefixar(t, r'(<meta name="description" content=")([^"]*)(")', vendido, "meta description")
    t = prefixar(t, r'(<meta property="og:title" content=")([^"]*)(")', vendido, "og:title")
    t = prefixar(t, r'(<meta name="twitter:title" content=")([^"]*)(")', vendido, "twitter:title")
    t = trocar(t, r'(<meta name="robots" content=")[^"]*(")',
               lambda m: m.group(1) + (ROBOTS_VENDIDO if vendido else ROBOTS_A_VENDA) + m.group(2), "meta robots")
    t = trocar(t, r'(<meta property="product:availability" content=")[^"]*(")',
               lambda m: m.group(1) + ("out of stock" if vendido else "in stock") + m.group(2), "product:availability")
    t = trocar(t, r'("availability": "https://schema\.org/)\w+(")',
               lambda m: m.group(1) + ("SoldOut" if vendido else "InStock") + m.group(2), "availability no JSON-LD")
    INDEX.write_text(t, encoding="utf-8")

    llms = LLMS.read_text(encoding="utf-8").replace(AVISO_LLMS, "")
    if vendido:
        titulo, resto = llms.split("\n\n", 1)
        llms = f"{titulo}\n\n{AVISO_LLMS}{resto}"
    LLMS.write_text(llms, encoding="utf-8")


def estado_atual():
    m = re.search(r'<body data-status="([^"]*)">', INDEX.read_text(encoding="utf-8"))
    return m.group(1) if m else "?"


def main():
    if len(sys.argv) < 2:
        print("Estado atual:", estado_atual())
        return
    op = sys.argv[1].strip().lower()
    if op in ("sim", "vendido", "s", "yes"):
        aplicar(True)
    elif op in ("nao", "não", "a-venda", "n", "no"):
        aplicar(False)
    else:
        sys.exit('Use "sim" (vendido) ou "nao" (à venda).')
    print("Estado atual:", estado_atual())


if __name__ == "__main__":
    main()
