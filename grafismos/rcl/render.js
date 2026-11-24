// Renderiza rcl.html quadro a quadro e gera o vídeo com fundo verde (chroma key).
// Uso: node render.js <saida.mp4> [duracao_s=5]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const out = process.argv[2] || 'rcl_chroma.mp4';
const DUR = parseFloat(process.argv[3] || '5');
const FPS = 30;
const SIZE = 1080;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'rcl.html'));
  await page.evaluate((d) => { window.DUR = d; }, DUR);
  await page.evaluate(() => document.fonts.ready);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });

  const frames = Math.round(DUR * FPS);
  for (let f = 0; f < frames; f++) {
    await page.evaluate((t) => window.setTime(t), f / FPS);
    const png = await page.screenshot({ clip: { x: 0, y: 0, width: SIZE, height: SIZE } });
    if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
})();
