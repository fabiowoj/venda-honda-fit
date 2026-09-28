#!/usr/bin/env python3
"""Prepara as fotos e o vídeo do site a partir de fotos-originais/.

Uso:
    pip install pillow imageio-ffmpeg     # uma vez só
    python3 scripts/fotos.py              # processa tudo e atualiza o site
    python3 scripts/fotos.py --conferir   # também gera prévias com a área da placa marcada

O que ele faz, para cada foto listada em fotos.json:
  1. lê fotos-originais/<id>.jpg (ou .jpeg/.png/.webp);
  2. endireita pela orientação da câmera e gira mais `girar` graus (sentido horário);
  3. borra de forma permanente cada área de `ocultar` (placa etc.);
  4. salva em assets/img/<id>-800.webp, <id>-1600.webp e <id>-1600.jpg,
     SEM metadados (remove GPS, modelo do celular, data...).

Depois atualiza a galeria do index.html, as imagens dos dados estruturados
(JSON-LD) e o sitemap.xml. Se existir fotos-originais/video-original.mp4, gera
também o vídeo da abertura, o pôster e a imagem de compartilhamento (og-image).

A pasta fotos-originais/ está no .gitignore: os originais têm GPS e a placa
visível e nunca devem ir para o repositório.
"""
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat
except ImportError:
    sys.exit("Falta a biblioteca Pillow. Rode: pip install pillow imageio-ffmpeg")

RAIZ = Path(__file__).resolve().parent.parent
ORIGINAIS = RAIZ / "fotos-originais"
SAIDA_IMG = RAIZ / "assets" / "img"
SAIDA_VIDEO = RAIZ / "assets" / "video"
INDEX = RAIZ / "index.html"
SITEMAP = RAIZ / "sitemap.xml"
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG")
TAMANHOS = (800, 1600)  # lado maior, em px


def achar_original(foto_id):
    for ext in EXTENSOES:
        p = ORIGINAIS / f"{foto_id}{ext}"
        if p.exists():
            return p
    return None


def ocultar_area(im, caixa):
    """Borra de forma irreversível a área [x, y, largura, altura] (em % da foto)."""
    W, H = im.size
    x, y, w, h = caixa
    pad_x, pad_y = w * 0.06, h * 0.12
    l = max(0, int((x - pad_x) / 100 * W))
    t = max(0, int((y - pad_y) / 100 * H))
    r = min(W, int((x + w + pad_x) / 100 * W))
    b = min(H, int((y + h + pad_y) / 100 * H))
    area = im.crop((l, t, r, b))
    # Reduzir para poucos pixels destrói a informação (não dá para "desborrar").
    mini = area.resize((max(1, (r - l) // 48), max(1, (b - t) // 48)), Image.BILINEAR)
    borrada = mini.resize(area.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(4, (b - t) // 5)))
    cor_media = tuple(int(c) for c in ImageStat.Stat(borrada).mean[:3])
    borrada = Image.blend(borrada, Image.new("RGB", area.size, cor_media), 0.35)
    mascara = Image.new("L", area.size, 0)
    raio = max(4, (b - t) // 6)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, r - l - 1, b - t - 1), radius=raio, fill=255)
    mascara = mascara.filter(ImageFilter.GaussianBlur(max(1, (b - t) // 40)))
    im.paste(borrada, (l, t), mascara)


def processar_foto(foto, conferir):
    original = achar_original(foto["id"])
    if not original:
        return False
    im = Image.open(original)
    im = ImageOps.exif_transpose(im).convert("RGB")
    girar = int(foto.get("girar", 0)) % 360
    if girar:
        im = im.rotate(-girar, expand=True)  # PIL gira anti-horário; aqui é horário
    for caixa in foto.get("ocultar", []):
        ocultar_area(im, caixa)

    for lado in TAMANHOS:
        copia = im.copy()
        copia.thumbnail((lado, lado), Image.LANCZOS)
        # Salvar sem `exif=` descarta todos os metadados da câmera.
        copia.save(SAIDA_IMG / f"{foto['id']}-{lado}.webp", "WEBP", quality=78, method=6)
        if lado == max(TAMANHOS):
            copia.save(SAIDA_IMG / f"{foto['id']}-{lado}.jpg", "JPEG", quality=80, optimize=True, progressive=True)

    if conferir and foto.get("ocultar"):
        pasta = ORIGINAIS / "_conferir"
        pasta.mkdir(exist_ok=True)
        prev = ImageOps.exif_transpose(Image.open(original)).convert("RGB")
        if girar:
            prev = prev.rotate(-girar, expand=True)
        d = ImageDraw.Draw(prev)
        W, H = prev.size
        for x, y, w, h in foto["ocultar"]:
            d.rectangle((x / 100 * W, y / 100 * H, (x + w) / 100 * W, (y + h) / 100 * H), outline="red", width=max(3, W // 300))
        prev.thumbnail((1200, 1200))
        prev.save(pasta / f"{foto['id']}.jpg", quality=85)
    return True


def dimensoes(foto_id):
    with Image.open(SAIDA_IMG / f"{foto_id}-1600.jpg") as im:
        return im.size


def url_do_site():
    m = re.search(r'<link rel="canonical" href="([^"]+)"', INDEX.read_text(encoding="utf-8"))
    if not m:
        sys.exit('index.html precisa ter <link rel="canonical" href="...">')
    return m.group(1).rstrip("/") + "/"


def html_galeria(fotos):
    linhas = []
    for f in fotos:
        if not f.get("galeria", True):
            continue
        w, h = dimensoes(f["id"])
        alt = html.escape(f["alt"], quote=True)
        legenda = html.escape(f.get("legenda", ""))
        base = f"assets/img/{f['id']}"
        linhas.append(
            f'        <figure class="galeria-item">\n'
            f'          <button type="button" class="galeria-abrir" data-foto="{base}-1600.webp" aria-label="Ampliar: {legenda or alt}">\n'
            f'            <picture><source type="image/webp" srcset="{base}-800.webp 800w, {base}-1600.webp 1600w" sizes="(orientation: portrait) 72vw, 48vh">'
            f'<img src="{base}-1600.jpg" width="{w}" height="{h}" alt="{alt}" loading="lazy" decoding="async"></picture>\n'
            f"          </button>\n"
            f"          <figcaption>{legenda}</figcaption>\n"
            f"        </figure>"
        )
    return "\n".join(linhas)


def atualizar_index(fotos, site):
    texto = INDEX.read_text(encoding="utf-8")
    texto, n = re.subn(
        r"<!-- galeria:inicio -->.*?<!-- galeria:fim -->",
        lambda m: "<!-- galeria:inicio -->\n" + html_galeria(fotos) + "\n      <!-- galeria:fim -->",
        texto,
        flags=re.S,
    )
    if n != 1:
        sys.exit("Não achei os marcadores <!-- galeria:inicio --> / <!-- galeria:fim --> no index.html")

    def trocar_jsonld(m):
        dados = json.loads(m.group(2))
        dados["image"] = [f"{site}assets/img/{f['id']}-1600.jpg" for f in fotos]
        return m.group(1) + json.dumps(dados, ensure_ascii=False, indent=2) + m.group(3)

    texto, n = re.subn(
        r'(<script type="application/ld\+json" id="dados-carro">\n)(.*?)(\n</script>)', trocar_jsonld, texto, flags=re.S
    )
    if n != 1:
        sys.exit('Não achei <script type="application/ld+json" id="dados-carro"> no index.html')
    INDEX.write_text(texto, encoding="utf-8")


def atualizar_sitemap(fotos, site):
    hoje = datetime.date.today().isoformat()
    imagens = "\n".join(
        f"    <image:image><image:loc>{site}assets/img/{f['id']}-1600.jpg</image:loc></image:image>" for f in fotos
    )
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        "  <url>\n"
        f"    <loc>{site}</loc>\n"
        f"    <lastmod>{hoje}</lastmod>\n"
        f"{imagens}\n"
        "  </url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def processar_video():
    original = ORIGINAIS / "video-original.mp4"
    if not original.exists():
        return
    exe = ffmpeg()
    if not exe:
        print("! Vídeo não processado: instale o ffmpeg ou rode `pip install imageio-ffmpeg`.")
        return
    SAIDA_VIDEO.mkdir(parents=True, exist_ok=True)
    rodar = lambda *a: subprocess.run([exe, "-loglevel", "error", "-y", *a], check=True)
    # Quadro-chave a cada 4 quadros: o vídeo acompanha o scroll sem engasgar.
    for largura, crf in ((1280, 27), (720, 28)):
        rodar("-i", str(original), "-an", "-vf", f"scale={largura}:-2", "-c:v", "libx264", "-preset", "slow",
              "-crf", str(crf), "-g", "4", "-keyint_min", "4", "-sc_threshold", "0", "-pix_fmt", "yuv420p",
              "-movflags", "+faststart", "-map_metadata", "-1", str(SAIDA_VIDEO / f"abertura-{largura}.mp4"))
    quadro = ORIGINAIS / "_quadro.png"
    rodar("-i", str(original), "-frames:v", "1", str(quadro))
    with Image.open(quadro) as im:
        im = im.convert("RGB")
        im.save(SAIDA_VIDEO / "poster.webp", "WEBP", quality=72, method=6)
        im.save(SAIDA_VIDEO / "poster.jpg", "JPEG", quality=78, optimize=True, progressive=True)
        ImageOps.fit(im, (1200, 630), Image.LANCZOS, centering=(0.4, 0.55)).save(
            RAIZ / "assets" / "og-image.jpg", "JPEG", quality=84, optimize=True, progressive=True
        )
    quadro.unlink()
    print("✓ vídeo, pôster e og-image.jpg")


def main():
    conferir = "--conferir" in sys.argv
    SAIDA_IMG.mkdir(parents=True, exist_ok=True)
    dados = json.loads((RAIZ / "fotos.json").read_text(encoding="utf-8"))
    fotos = dados["fotos"]
    for f in fotos:
        if processar_foto(f, conferir):
            print(f"✓ {f['id']}")
        elif (SAIDA_IMG / f"{f['id']}-1600.jpg").exists():
            print(f"· {f['id']} (sem original; mantendo a versão já publicada)")
        else:
            sys.exit(f"✗ {f['id']}: coloque a foto em fotos-originais/{f['id']}.jpg")
    processar_video()
    site = url_do_site()
    atualizar_index(fotos, site)
    atualizar_sitemap(fotos, site)
    print("✓ index.html (galeria + JSON-LD) e sitemap.xml atualizados")
    if conferir:
        print(f"  Prévias com a área ocultada marcada em vermelho: {ORIGINAIS / '_conferir'}")


if __name__ == "__main__":
    main()
