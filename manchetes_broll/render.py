"""B-roll: 3 manchetes entrando suavemente com efeito marca-texto.

Uso: python3 render.py <img1> <img2> <img3> <pasta_saida>
Gera um vídeo separado por manchete (manchete1, manchete2, manchete3),
cada um recortado em volta da manchete, 30 fps e 15 s, em duas versões: fundo verde (chroma key)
e transparente (ProRes 4444 com alfa).
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H, FPS = 1920, 1080, 30
SEG = 15.0  # segundos por manchete
HL_COLOR = np.array([255, 222, 60], dtype=np.float32) / 255.0  # amarelo marca-texto

# Linhas a destacar em cada imagem: (x0, x1, baseline, altura_maiuscula)
# Medidas em pixels da imagem original.
LINES = [
    [(53, 625, 170, 66), (49, 984, 285, 66), (51, 1069, 400, 66)],
    [(52, 1233, 185, 66), (50, 1189, 300, 66), (50, 1018, 414, 66)],
    # Apenas "Flávio Dino ... contra delegado da PF" (termina antes do ";")
    [(52, 1258, 270, 50), (46, 1222, 367, 50), (47, 1236, 464, 50), (50, 1075, 561, 50)],
]


def ease_out_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def line_mask(size, line, progress, seed):
    """Máscara (float 0..1) de uma faixa de marca-texto, revelada até `progress`."""
    x0, x1, base, cap = line
    pad = 10
    x0 -= pad
    x1 += pad
    y0 = base - 0.78 * cap
    y1 = base + 0.18 * cap
    xe = x0 + (x1 - x0) * progress
    if xe <= x0 + 1:
        return None
    rng = np.random.default_rng(seed)
    # bordas levemente irregulares, como uma caneta real
    n = 24
    xs = np.linspace(x0, x1, n)
    top = y0 + rng.normal(0, 1.6, n) - np.linspace(0, 3, n)
    bot = y1 + rng.normal(0, 1.6, n) - np.linspace(0, 3, n)
    keep = xs <= xe
    xs_k = list(xs[keep]) + [xe]
    top_k = list(top[keep]) + [np.interp(xe, xs, top)]
    bot_k = list(bot[keep]) + [np.interp(xe, xs, bot)]
    poly = list(zip(xs_k, top_k)) + list(zip(xs_k[::-1], bot_k[::-1]))
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(poly, fill=235)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    return np.asarray(m, dtype=np.float32) / 255.0


def highlighted_card(card, lines, t_rel, seg_idx):
    """Aplica o marca-texto (blend multiply) conforme o tempo do segmento."""
    arr = np.asarray(card, dtype=np.float32) / 255.0
    start, per_line, gap = 0.85, 0.42, 0.06
    total = np.zeros(arr.shape[:2], dtype=np.float32)
    for i, ln in enumerate(lines):
        p = ease_in_out((t_rel - start - i * (per_line + gap)) / per_line)
        if p <= 0:
            break
        m = line_mask(card.size, ln, p, seed=seg_idx * 10 + i)
        if m is not None:
            total = np.maximum(total, m)
    mult = 1 - total[..., None] * (1 - HL_COLOR)
    return Image.fromarray(np.clip(arr * mult * 255, 0, 255).astype(np.uint8))


def make_shadow(w, h, radius=40, opacity=0.35):
    pad = radius * 3
    s = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(s).rounded_rectangle((pad, pad + 18, pad + w, pad + h + 18), 18, fill=int(255 * opacity))
    return s.filter(ImageFilter.GaussianBlur(radius)), pad


def rounded_alpha(w, h, r=18):
    a = Image.new("L", (w, h), 0)
    ImageDraw.Draw(a).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return a


GREEN = (0, 255, 0)


def main():
    imgs = [Image.open(p).convert("RGB") for p in sys.argv[1:4]]
    out_dir = sys.argv[4]
    for idx in range(3):
        render_clip(imgs[idx], idx, f"{out_dir}/manchete{idx + 1}")


def encoder(cmd_out):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + cmd_out,
        stdin=subprocess.PIPE,
    )


def render_clip(card0, idx, out_base):
    """Gera duas versões da manchete:
    - <out_base>_chroma.mp4: fundo verde (chroma key), sem sombra
    - <out_base>_transparente.mov: ProRes 4444 com canal alfa e sombra suave (pesado)
    - <out_base>_transparente.webm: VP9 com canal alfa, mesma imagem, arquivo leve
    """
    # recorta o quadro só em volta da manchete (com folga para movimento e sombra)
    base = min(1560 / card0.width, 880 / card0.height) * 1.035
    m = 100
    cw_max, ch_max = card0.width * base, card0.height * base
    crop_w = min(W, int(cw_max + 2 * m) // 2 * 2)
    crop_h = min(H, int(ch_max + 120 + 2 * m) // 2 * 2)
    crop_x = (W - crop_w) // 2 // 2 * 2
    crop_y = max(0, int((H - ch_max) / 2 - 50 - m)) // 2 * 2
    crop_y = min(crop_y, H - crop_h)
    crop = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"

    ff_green = encoder(["-vf", f"{crop},format=rgb24", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{out_base}_chroma.mp4"])
    ff_alpha = encoder(["-vf", crop, "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-qscale:v", "12", "-alpha_bits", "8", "-vendor", "apl0", f"{out_base}_transparente.mov"])
    ff_webm = encoder(["-vf", crop, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", "20",
                       "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "3",
                       "-auto-alt-ref", "0", f"{out_base}_transparente.webm"])
    green_bg = Image.new("RGBA", (W, H), GREEN + (255,))

    for f in range(int(SEG * FPS)):
        tr = f / FPS
        card = highlighted_card(card0, LINES[idx], tr, idx)

        # escala base para caber no quadro + zoom lento
        base = min(1560 / card.width, 880 / card.height)
        zoom = 1.0 + 0.035 * (tr / SEG)
        # entrada: sobe e aparece; saída: sobe e desaparece
        e_in = ease_out_cubic(tr / 0.7)
        e_out = ease_in_out((tr - (SEG - 0.45)) / 0.45)
        alpha = e_in * (1 - e_out)
        dy = (1 - e_in) * 70 - e_out * 50
        s = base * zoom * (0.96 + 0.04 * e_in)

        cw, ch = int(card.width * s), int(card.height * s)
        c = card.resize((cw, ch), Image.LANCZOS)
        x = (W - cw) // 2
        y = int((H - ch) / 2 + dy)
        ra = rounded_alpha(cw, ch).point(lambda v: int(v * alpha))

        # camada só da manchete (transparente em volta)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c_rgba = c.convert("RGBA")
        c_rgba.putalpha(ra)
        layer.alpha_composite(c_rgba, (x, y))

        # versão transparente: sombra suave + manchete
        shadow, pad = make_shadow(cw, ch, opacity=0.30)
        shadow = shadow.point(lambda v: int(v * alpha))
        sh_rgba = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
        sh_rgba.putalpha(shadow)
        sh_layer = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
        sh_layer.alpha_composite(sh_rgba, (x, y))
        sh_layer = sh_layer.crop((pad, pad, pad + W, pad + H))
        sh_layer.alpha_composite(layer)
        ff_alpha.stdin.write(sh_layer.tobytes())
        ff_webm.stdin.write(sh_layer.tobytes())

        # versão chroma key: manchete sobre verde puro, sem sombra
        g = green_bg.copy()
        g.alpha_composite(layer)
        ff_green.stdin.write(g.tobytes())

    for ff in (ff_green, ff_alpha, ff_webm):
        ff.stdin.close()
        ff.wait()


if __name__ == "__main__":
    main()
