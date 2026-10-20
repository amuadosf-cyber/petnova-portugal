"""Verifica todos os anúncios e MP4 dos manifestos gerados."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from petnova.content import ROOT, media_path, read_json
from petnova.render import inspect_video

manifests = list((ROOT / 'conteudos').glob('*/manifest.json'))
if not manifests:
    raise SystemExit('Nenhum conteúdo foi gerado.')
count = 0
for manifest_path in manifests:
    for post in read_json(manifest_path)['posts']:
        info = inspect_video(media_path(manifest_path, post['media']['video']))
        assert (info['width'], info['height'], info['codec'], info['pixel_format']) == (1080, 1920, 'h264', 'yuv420p'), info
        assert info['audio'] and 12 <= info['duration'] <= 60, info
        with Image.open(media_path(manifest_path, post['media']['ad'])) as image:
            assert image.size == (1080, 1350), image.size
            image.verify()
        assert media_path(manifest_path, post['media']['subtitles']).read_text(encoding='utf-8').count('-->') == 4
        count += 1
print(f'{count} vídeos H.264 verticais, anúncios e legendas verificados.')
