"""Sintetiza os efeitos sonoros que a biblioteca do HyperFrames não tem.
Uso: python3 synth_sfx.py <raiz_do_repo>"""
import math, random, struct, sys, wave, os

SR = 44100
ROOT = sys.argv[1]
rng = random.Random(7)


def buf(dur):
    return [0.0] * int(SR * dur)


def add(dst, src, at):
    o = int(at * SR)
    for i, v in enumerate(src):
        if 0 <= o + i < len(dst):
            dst[o + i] += v


def save(samples, path, peak=0.9):
    m = max(1e-9, max(abs(x) for x in samples))
    k = peak / m
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x * k)) * 32767)) for x in samples))


def lowpass(x, a):
    y, p = [], 0.0
    for v in x:
        p += a * (v - p); y.append(p)
    return y


def highpass(x, a):
    lp = lowpass(x, a)
    return [v - l for v, l in zip(x, lp)]


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


# --- sons unitários ---------------------------------------------------------
def thud(dur=0.35, f0=95, f1=45):
    n = int(SR * dur); out = []
    ph = 0.0
    nz = lowpass(noise(n), 0.08)
    for i in range(n):
        t = i / SR
        f = f1 + (f0 - f1) * math.exp(-t * 25)
        ph += 2 * math.pi * f / SR
        env = math.exp(-t * 14)
        out.append(env * (math.sin(ph) + 0.8 * nz[i] * math.exp(-t * 40)))
    return out


def clink(dur=0.7, base=2350):
    n = int(SR * dur); out = []
    partials = [(1.0, 1.0, 7), (2.76, 0.6, 9), (5.40, 0.4, 12), (8.93, 0.25, 16)]
    for i in range(n):
        t = i / SR
        out.append(sum(a * math.sin(2 * math.pi * base * r * t) * math.exp(-t * d) for r, a, d in partials))
    tr = highpass(noise(int(SR * 0.01)), 0.3)
    for i, v in enumerate(tr):
        out[i] += 0.6 * v * (1 - i / len(tr))
    return out


def tick(dur=0.04, bright=0.35):
    nz = highpass(noise(int(SR * dur)), bright)
    return [v * math.exp(-i / SR * 180) for i, v in enumerate(nz)]


def flip(dur=0.09):
    n = int(SR * dur)
    nz = highpass(lowpass(noise(n), 0.35), 0.05)
    return [v * math.sin(math.pi * i / n) ** 2 for i, v in enumerate(nz)]


def lubdub():
    out = buf(0.45)
    add(out, thud(0.18, 70, 40), 0.0)
    add(out, [0.7 * v for v in thud(0.15, 85, 50)], 0.17)
    return out


def beep(f=1000, dur=0.11):
    n = int(SR * dur)
    return [0.5 * math.sin(2 * math.pi * f * i / SR) * min(1, i / 200, (n - i) / 400) for i in range(n)]


def step():
    return [0.6 * v for v in thud(0.12, 120, 60)]


# --- trilhas por b-roll -----------------------------------------------------
def p(n, name):
    return os.path.join(ROOT, f"motions/broll_{n}/assets/sfx/{name}.wav")


# b-roll 1
save(thud(), p("01", "livro-thud"))
save(clink(), p("01", "moeda-clink"))

# b-roll 2: contador acelerando (mesma curva power2.in do número, 0,9 s -> 6,5 s)
tk = buf(5.7)
N = 70
for k in range(1, N + 1):
    add(tk, tick(0.035, 0.45), 5.6 * math.sqrt(k / N))
save(tk, p("02", "contador-ticks"))
# burburinho de multidão: ruído em banda de voz com modulação lenta, crescendo
n = int(SR * 9.2)
nz = highpass(lowpass(noise(n), 0.09), 0.012)
mur = []
for i, v in enumerate(nz):
    t = i / SR
    am = 0.6 + 0.25 * math.sin(2 * math.pi * 3.1 * t) * math.sin(2 * math.pi * 0.7 * t + 1) + 0.15 * math.sin(2 * math.pi * 5.3 * t)
    grow = min(1.0, t / 5.5) ** 1.5
    mur.append(v * am * (0.1 + 0.9 * grow))
save(mur, p("02", "multidao"), peak=0.7)
pas = buf(1.4)
for i, at in enumerate([0.0, 0.32, 0.64, 0.96]):
    add(pas, step(), at)
save(pas, p("02", "passos"))

# b-roll 3: batimentos e bipes de monitor (um a cada 0,8 s desde 0,1 s)
hb = buf(9.0); mon = buf(9.0)
t = 0.1
while t < 8.8:
    add(hb, lubdub(), t); add(mon, beep(), t)
    t += 0.8
save(hb, p("03", "coracao"))
save(mon, p("03", "monitor-bipe"), peak=0.6)
# zumbido do tomógrafo
n = int(SR * 9.0)
hum = [(0.5 * math.sin(2 * math.pi * 120 * i / SR) + 0.25 * math.sin(2 * math.pi * 240 * i / SR) + 0.12 * math.sin(2 * math.pi * 360 * i / SR)) * (0.85 + 0.15 * math.sin(2 * math.pi * 1.8 * i / SR)) for i in range(n)]
save(hum, p("03", "tomografo-hum"), peak=0.5)
# folhas do calendário: uma por mês, na curva power2.in (2,1 s -> 7,7 s, 31 meses)
fl = buf(5.8)
for k in range(1, 32):
    add(fl, flip(), 5.6 * math.sqrt(k / 31) - 0.03)
save(fl, p("03", "calendario-folhas"))
# tique-taque do relógio acelerando
ck = buf(5.8)
for k in range(1, 81):
    add(ck, tick(0.03, 0.25 if k % 2 else 0.4), 5.6 * math.sqrt(k / 80) - 0.01)
save(ck, p("03", "relogio-tique"))
print("ok")
