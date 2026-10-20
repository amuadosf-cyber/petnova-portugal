from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import ROOT, load_config
from scripts.publicar import run

count = 0
for manifest in (ROOT / 'conteudos').glob('*/manifest.json'):
    reports = run(manifest, load_config(), ('tiktok', 'instagram', 'youtube'))
    assert all(not report['sent'] and report['dry_run'] for report in reports)
    count += len(reports)
if not count:
    raise SystemExit('Não há publicações para simular.')
print(f'{count} publicações simuladas. Nenhuma chamada às plataformas.')
