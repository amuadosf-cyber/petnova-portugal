"""Espera no máximo 40 segundos pelo servidor local temporário do runner."""
import time
from urllib.request import urlopen

for attempt in range(20):
    try:
        with urlopen('http://127.0.0.1:11434/api/tags', timeout=1) as response:
            if response.status == 200:
                print('Servidor de IA local disponível. Nenhuma API externa usada.')
                break
    except OSError:
        if attempt == 19:
            raise SystemExit('IA local não ficou disponível; o workflow usará modelos de texto.')
        time.sleep(2)
