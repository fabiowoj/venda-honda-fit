#!/usr/bin/env python3
"""Verificações de segurança e SEO antes de publicar. Roda no GitHub Actions a cada push.

    python3 scripts/verificar.py

Falha (código 1) se encontrar:
  - foto publicada com metadados EXIF (GPS, modelo do celular...);
  - arquivo da pasta fotos-originais/ versionado no git;
  - arquivo maior que 8 MB;
  - link local quebrado (src/href/srcset/poster) no index.html;
  - <img> sem alt, atributo style="" ou <script> inline (bloqueados pela CSP);
  - JSON-LD inválido, ou sitemap/robots/llms.txt faltando.
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
erros = []


def erro(msg):
    erros.append(msg)
    print("✗", msg)


def arquivos_versionados():
    try:
        saida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        return [RAIZ / l for l in saida.splitlines() if l]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts and "fotos-originais" not in p.parts]


def checar_metadados(arquivos):
    try:
        from PIL import Image
    except ImportError:
        erro("Pillow não instalado (pip install pillow): não foi possível checar metadados das fotos")
        return
    for p in arquivos:
        if p.suffix.lower() not in (".jpg", ".jpeg", ".webp", ".png"):
            continue
        with Image.open(p) as im:
            exif = im.getexif()
            if exif:
                gps = " (COM GPS!)" if exif.get_ifd(0x8825) else ""
                erro(f"{p.relative_to(RAIZ)} tem metadados EXIF{gps}. Reprocesse com scripts/fotos.py")
            if "xmp" in im.info or "XML:com.adobe.xmp" in im.info:
                erro(f"{p.relative_to(RAIZ)} tem metadados XMP")


class Coletor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.problemas, self.jsonld, self._ld = [], [], [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "style" in a:
            self.problemas.append(f"<{tag}> com style=\"\" (bloqueado pela CSP; use o CSS)")
        if tag == "img" and not a.get("alt") and a.get("alt") != "":
            self.problemas.append(f"<img src={a.get('src')}> sem alt")
        if tag == "script":
            if a.get("type") == "application/ld+json":
                self._ld = True
            elif "src" not in a:
                self.problemas.append("<script> inline (bloqueado pela CSP)")
        for k in ("src", "href", "poster", "data-foto"):
            if a.get(k):
                self.refs.append(a[k])
        if a.get("srcset"):
            self.refs += [s.strip().split(" ")[0] for s in a["srcset"].split(",")]

    def handle_data(self, data):
        if self._ld:
            self.jsonld.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self._ld = False


def checar_html(nome):
    caminho = RAIZ / nome
    c = Coletor()
    c.feed(caminho.read_text(encoding="utf-8"))
    for p in c.problemas:
        erro(f"{nome}: {p}")
    for ref in c.refs:
        if re.match(r"^(https?:|mailto:|tel:|#|data:)", ref) or ref == "":
            continue
        alvo = (RAIZ / ref.replace("/venda-honda-fit/", "", 1).split("#")[0].split("?")[0])
        if not alvo.exists():
            erro(f"{nome}: link quebrado → {ref}")
    for bloco in c.jsonld:
        try:
            dados = json.loads(bloco)
            if nome == "index.html" and not dados.get("image"):
                erro("index.html: JSON-LD sem imagens (rode scripts/fotos.py)")
        except json.JSONDecodeError as e:
            erro(f"{nome}: JSON-LD inválido: {e}")


def main():
    versionados = arquivos_versionados()
    for p in versionados:
        rel = p.relative_to(RAIZ)
        if rel.parts and rel.parts[0] == "fotos-originais":
            erro(f"{rel} está no git — originais têm GPS e placa! Remova com: git rm --cached -r fotos-originais")
        if p.exists() and p.stat().st_size > 8 * 1024 * 1024:
            erro(f"{rel} tem {p.stat().st_size / 1e6:.1f} MB (limite 8 MB)")
    checar_metadados([p for p in versionados if p.exists() and "assets" in p.relative_to(RAIZ).parts])
    for nome in ("index.html", "404.html"):
        checar_html(nome)
    for nome in ("robots.txt", "sitemap.xml", "llms.txt", "site.webmanifest", "assets/og-image.jpg"):
        if not (RAIZ / nome).exists():
            erro(f"falta {nome}")
    json.loads((RAIZ / "site.webmanifest").read_text(encoding="utf-8"))
    if erros:
        print(f"\n{len(erros)} problema(s).")
        sys.exit(1)
    print("✓ Tudo certo: sem metadados nas fotos, sem originais no git, links e dados estruturados ok.")


if __name__ == "__main__":
    main()
