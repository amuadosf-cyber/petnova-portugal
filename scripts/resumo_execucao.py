import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import ROOT, read_json

manifests = sorted((ROOT / 'conteudos').glob('*/manifest.json'))
summary = '## PetNova Portugal — conteúdos de demonstração\n\n'
for path in manifests:
    data = read_json(path)
    summary += f"**{data['date']} · {data['timezone']}**\n\n"
    summary += '| Hora | Produto | Texto | Estado |\n| --- | --- | --- | --- |\n'
    for post in data['posts']:
        summary += f"| {post['scheduled_at'][11:16]} | {post['product_name']} | {post['generation']['provider']} | Rascunho |\n"
summary += '\nOs ficheiros estão em **Artifacts** nesta execução. Incluem MP4, PNG, legendas, guiões e relatório de simulação.\n\n'
summary += 'Nenhuma publicação foi enviada. A loja continua sem encomendas e pagamentos.\n'
if os.environ.get('GITHUB_STEP_SUMMARY'):
    Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(summary, encoding='utf-8')
else:
    print(summary)
