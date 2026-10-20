"""Exporta apenas rascunhos públicos de demonstração para a galeria móvel."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import NOTICE, ROOT, media_path, read_json, write_json

REPOSITORY = 'amuadosf-cyber/petnova-portugal'
PUBLIC_BRANCH = 'conteudos-publicos'
GALLERY_URL = f'https://raw.githubusercontent.com/{REPOSITORY}/{PUBLIC_BRANCH}/latest.json'


def export_gallery(content_root, output, run_id='local', attempt='1'):
    manifests = sorted(Path(content_root).glob('*/manifest.json'))
    if not manifests:
        raise ValueError('Não existem conteúdos para a galeria.')
    path = manifests[-1]
    manifest = read_json(path)
    day = date.fromisoformat(manifest['date']).isoformat()
    if manifest.get('store_mode') != 'demonstracao' or manifest.get('schema_version') != 1:
        raise ValueError('A galeria só aceita conteúdos de demonstração.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', str(run_id)) or not str(attempt).isdigit():
        raise ValueError('Identificador de execução inválido.')
    tag = f'rascunhos-{day}-r{run_id}-a{attempt}'
    base = f'https://github.com/{REPOSITORY}/releases/download/{tag}'
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    public_posts = []
    asset_names = []
    seen = set()
    for post in manifest['posts']:
        identifier = post['id']
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', identifier) or identifier in seen:
            raise ValueError('Identificador de rascunho inválido ou repetido.')
        seen.add(identifier)
        if post.get('mode') != 'demonstracao' or any(NOTICE not in post['captions'].get(p, '') for p in ('tiktok', 'instagram', 'youtube')):
            raise ValueError('Falta o aviso de demonstração num rascunho.')
        media = {}
        for kind, extension in [('video', 'mp4'), ('ad', 'png'), ('subtitles', 'srt')]:
            source = media_path(path, post['media'][kind])
            if not source.is_file():
                raise ValueError(f'Falta o ficheiro de {kind}.')
            name = f'{identifier}.{extension}'
            shutil.copyfile(source, output / name)
            asset_names.append(name)
            media[kind] = f'{base}/{name}'
        srt = (output / f'{identifier}.srt').read_text(encoding='utf-8')
        vtt = 'WEBVTT\n\n' + re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', srt)
        (output / f'{identifier}.vtt').write_text(vtt, encoding='utf-8')
        asset_names.append(f'{identifier}.vtt')
        media['vtt'] = f'{base}/{identifier}.vtt'
        captions = {p: str(post['captions'][p]) for p in ('tiktok', 'instagram', 'youtube')}
        for platform, caption in captions.items():
            name = f'{identifier}-{platform}.txt'
            (output / name).write_text(caption + '\n', encoding='utf-8')
            asset_names.append(name)
        # Lista explícita: não exportar manifesto bruto, revisões, configuração ou credenciais.
        public_posts.append({'id': identifier, 'product_name': post['product_name'], 'hook': post['hook'],
            'scheduled_at': post['scheduled_at'], 'status': 'rascunho', 'ai_used': post['generation'].get('ai_used') is True,
            'captions': captions, 'media': media})
    if not public_posts:
        raise ValueError('O lote está vazio.')
    bundle_name = f'petnova-{day}.zip'
    with zipfile.ZipFile(output / bundle_name, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in asset_names:
            bundle.write(output / name, name)
    asset_names.append(bundle_name)
    public = {'schema_version': 1, 'date': day, 'generated_at': datetime.now(timezone.utc).isoformat(),
        'timezone': manifest['timezone'], 'mode': 'demonstracao', 'social_publishing_enabled': False,
        'release_tag': tag, 'source_url': f'https://github.com/{REPOSITORY}/releases/tag/{tag}',
        'bundle_url': f'{base}/{bundle_name}', 'posts': public_posts}
    write_json(output / 'latest.json', public)
    write_json(output / 'upload-list.json', {'assets': asset_names, 'tag': tag})
    return public


def main():
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conteudos', type=Path, default=ROOT / 'conteudos')
    parser.add_argument('--saida', type=Path, default=ROOT / '_galeria')
    args = parser.parse_args()
    data = export_gallery(args.conteudos, args.saida, os.environ.get('GITHUB_RUN_ID', 'local'), os.environ.get('GITHUB_RUN_ATTEMPT', '1'))
    print(f"Galeria preparada: {len(data['posts'])} rascunhos de {data['date']}. Nenhum envio às redes.")


if __name__ == '__main__':
    main()
