# Motions em vídeo

Repositório para criar motions em vídeo (usado pelo celular). Use as skills do
HyperFrames em `.claude/skills` (comece por `/hyperframes`).

## Padrões obrigatórios

- **Formato:** vídeo vertical **1080x1920**, **30 fps**, **MP4 H.264** (yuv420p).
- **Motion para sobrepor no vídeo:** fundo **verde puro `#00FF00`** (chroma key).
  Não use transparência/fade sobre o verde; saia de cena com movimento ou escala,
  para não criar bordas esverdeadas.
- **Arquivos finais:** sempre na pasta `renders/`, cada um com **menos de 50 MB**
  (confira com `ls -lh renders/`; se passar, reduza a qualidade/bitrate e renderize de novo).
- **Sempre fazer commit e push no final** de cada tarefa.

## Estrutura

- `motions/<nome>/` — um projeto HyperFrames por motion (`index.html` + `assets/`).
- `renders/` — MP4 finais.

## Como renderizar

```bash
cd motions/<nome>
npx --yes hyperframes@0.9.26 check
npx --yes hyperframes@0.9.26 render --quality delivery --fps 30 -o ../../renders/<nome>.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration,size -of default=nw=1 ../../renders/<nome>.mp4
```

Carregue bibliotecas (ex.: GSAP) de `assets/` locais, não de CDN: a rede do
ambiente na nuvem pode bloquear CDNs durante o render.
