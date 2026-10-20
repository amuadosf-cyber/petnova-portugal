"""Publica a galeria demonstrativa no GitHub; não acede às contas das redes sociais."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import ROOT, read_json
from scripts.preparar_galeria import PUBLIC_BRANCH, REPOSITORY


def gh(*arguments, payload=None, allow_missing=False):
    result = subprocess.run(['gh', *arguments], input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, timeout=120)
    if result.returncode:
        if allow_missing and ('HTTP 404' in result.stderr or 'release not found' in result.stderr.lower()):
            return None
        raise RuntimeError('O GitHub recusou a atualização da galeria. Verifica as permissões contents: write e os limites da execução.')
    return result.stdout.strip()


def publish(output):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Esta publicação é executada apenas pelo workflow do repositório PetNova.')
    output = Path(output).resolve()
    data = read_json(output / 'latest.json')
    uploads = read_json(output / 'upload-list.json')
    tag = data['release_tag']
    files = []
    for name in uploads['assets']:
        path = (output / name).resolve()
        if not path.is_relative_to(output) or path.parent != output or not path.is_file():
            raise ValueError('Ficheiro fora da lista de exportação.')
        files.append(str(path))
    existing = gh('release', 'view', tag, '--repo', REPOSITORY, '--json', 'url', allow_missing=True)
    if existing is None:
        gh('release', 'create', tag, *files, '--repo', REPOSITORY, '--target', os.environ['GITHUB_SHA'],
           '--title', f"PetNova — {data['date']} — rascunhos de demonstração", '--prerelease', '--latest=false',
           '--notes', 'Anúncios, vídeos gráficos e legendas de demonstração, por rever. Sem vendas nem envios às redes sociais.')
    else:
        # Reexecutar um passo da mesma tentativa substitui só os seus ficheiros exportados.
        gh('release', 'upload', tag, *files, '--repo', REPOSITORY, '--clobber')
    # Só apontar a galeria para o lote depois de os ficheiros estarem carregados.
    reference = gh('api', f'repos/{REPOSITORY}/git/ref/heads/{PUBLIC_BRANCH}', allow_missing=True)
    if reference is None:
        gh('api', '--method', 'POST', f'repos/{REPOSITORY}/git/refs', '--input', '-', payload={
            'ref': f'refs/heads/{PUBLIC_BRANCH}', 'sha': os.environ['GITHUB_SHA']})
    previous = gh('api', f'repos/{REPOSITORY}/contents/latest.json?ref={PUBLIC_BRANCH}', allow_missing=True)
    payload = {'branch': PUBLIC_BRANCH, 'message': f"Atualizar rascunhos públicos de {data['date']}",
               'content': base64.b64encode((output / 'latest.json').read_bytes()).decode('ascii')}
    if previous:
        payload['sha'] = json.loads(previous)['sha']
    gh('api', '--method', 'PUT', f'repos/{REPOSITORY}/contents/latest.json', '--input', '-', payload=payload)
    print(f"Galeria atualizada: {len(data['posts'])} rascunhos de {data['date']}. Publicações nas redes continuam desativadas.")


if __name__ == '__main__':
    try:
        publish(ROOT / '_galeria')
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
