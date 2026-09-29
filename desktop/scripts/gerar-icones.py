"""Gera ícone (logo com contorno branco) e imagens do instalador (logo sem fundo + captura do painel).

Uso (na pasta desktop/): python scripts/gerar-icones.py
Requer Pillow.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
LOGO = RAIZ.parent / "frontend" / "public" / "deskrudder-mark-alpha.png"
LOGO_CONTORNO = RAIZ.parent / "frontend" / "public" / "deskrudder-pwa-512-outline.png"
CAPTURA = RAIZ.parent / "frontend" / "public" / "marketing" / "shot-dashboard.png"
BUILD = RAIZ / "build"
FONTES = Path("C:/Windows/Fonts")


def logo_quadrada(tamanho: int, margem: float = 0.04, origem: Path = LOGO) -> Image.Image:
    logo = Image.open(origem).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    lado = int(max(logo.size) * (1 + 2 * margem))
    tela = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    tela.paste(logo, ((lado - logo.width) // 2, (lado - logo.height) // 2), logo)
    return tela.resize((tamanho, tamanho), Image.LANCZOS)


def fonte(nome: str, tamanho: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONTES / nome), tamanho)
    except OSError:
        return ImageFont.load_default()


def gradiente(largura: int, altura: int) -> Image.Image:
    topo, meio, base = (11, 45, 74), (19, 65, 102), (10, 77, 110)
    img = Image.new("RGB", (largura, altura))
    px = img.load()
    for y in range(altura):
        t = y / (altura - 1)
        a, b, f = (topo, meio, t / 0.45) if t < 0.45 else (meio, base, (t - 0.45) / 0.55)
        cor = tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))
        for x in range(largura):
            px[x, y] = cor
    return img


def captura_do_painel(largura: int) -> Image.Image:
    shot = Image.open(CAPTURA).convert("RGBA").crop((0, 0, 720, 900))
    altura = round(shot.height * largura / shot.width)
    shot = shot.resize((largura, altura), Image.LANCZOS)
    mascara = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura - 1, altura - 1), radius=8, fill=255)
    shot.putalpha(mascara)
    return shot


def sidebar() -> Image.Image:
    largura, altura = 164, 314
    img = gradiente(largura, altura).convert("RGBA")

    logo = logo_quadrada(52, margem=0.02)
    img.alpha_composite(logo, ((largura - logo.width) // 2, 14))

    draw = ImageDraw.Draw(img)
    f_desk, f_rudder = fonte("segoeui.ttf", 18), fonte("segoeuib.ttf", 18)
    w_desk = draw.textlength("Desk", font=f_desk)
    w_total = w_desk + draw.textlength("Rudder", font=f_rudder)
    x0 = (largura - w_total) / 2
    draw.text((x0, 68), "Desk", font=f_desk, fill=(248, 250, 252))
    draw.text((x0 + w_desk, 68), "Rudder", font=f_rudder, fill=(94, 234, 212))

    shot = captura_do_painel(190)
    x, y = 18, 104
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle(
        (x - 3, y - 3, x + shot.width + 3, y + shot.height + 3), radius=10, fill=(0, 0, 0, 70)
    )
    img = Image.alpha_composite(img, sombra.filter(ImageFilter.GaussianBlur(4)))
    img.alpha_composite(shot, (x, y))
    ImageDraw.Draw(img).rounded_rectangle(
        (x, y, x + shot.width - 1, y + shot.height - 1), radius=8, outline=(94, 234, 212, 90)
    )
    return img.convert("RGB")


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    logo_quadrada(512, margem=0.02, origem=LOGO_CONTORNO).save(BUILD / "icon.png")
    logo_quadrada(256, margem=0.02, origem=LOGO_CONTORNO).save(
        BUILD / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    lateral = sidebar()
    lateral.save(BUILD / "installerSidebar.bmp")
    lateral.save(BUILD / "uninstallerSidebar.bmp")


if __name__ == "__main__":
    main()
