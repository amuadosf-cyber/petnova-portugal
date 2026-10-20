"""Mantém o catálogo público sincronizado com o CSV único."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import ROOT, load_config, load_products, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    load_config()
    expected = {'mode': 'demonstracao', 'checkout_enabled': False, 'products': load_products()}
    path = ROOT / 'catalogo.json'
    if args.check:
        if not path.exists() or read_json(path) != expected:
            raise SystemExit('Catálogo desatualizado. Executa python scripts/sincronizar_catalogo.py')
        print('Catálogo sincronizado; compras desativadas.')
    else:
        write_json(path, expected)
        print('Catálogo de demonstração atualizado.')


if __name__ == '__main__':
    main()
