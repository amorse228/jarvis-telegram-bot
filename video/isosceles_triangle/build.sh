#!/usr/bin/env bash
# Сборка видеоурока «Равнобедренный треугольник» (30 с, 3840x2160, 30 fps).
# Требуется: node + playwright (chromium), ffmpeg, python3 (numpy, scipy), piper-tts
# и русский голос Piper (ru-irinia-medium) в каталоге voice/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out vo

# 1. Озвучка: каждая реплика отдельным файлом (тайминги — в voice.txt и audio.py)
i=0
while IFS='|' read -r _ line; do
  i=$((i + 1))
  ls=0.9; [ "$i" -eq 11 ] && ls=0.8
  echo "$line" | piper -m voice/ru-irinia-medium.onnx -c voice/ru-irinia-medium.onnx.json \
    --length_scale "$ls" -f "vo/$i.wav" >/dev/null 2>&1
  ffmpeg -y -loglevel error -i "vo/$i.wav" -ar 48000 -ac 1 "vo/r$i.wav"
done < voice.txt

# 2. Музыка + звуковые эффекты + озвучка -> out/audio.wav
python3 audio.py

# 3. Кадры анимации (canvas в headless Chromium) -> out/seg_*.mp4
node render.mjs
printf "file 'seg_%d.mp4'\n" 0 1 2 > out/segs.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i out/segs.txt -c copy out/video.mp4

# 4. Финальный файл
ffmpeg -y -loglevel error -i out/video.mp4 -i out/audio.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -tag:v avc1 \
  -c:a aac -b:a 256k -movflags +faststart -shortest isosceles_triangle_4k.mp4
echo "Готово: isosceles_triangle_4k.mp4"
