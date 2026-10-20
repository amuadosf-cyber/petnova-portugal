"""Inspeciona a fila em simulação; --enviar ativa o envio apenas se estiver configurado."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import ROOT, fingerprint, load_config, read_json, write_json
from petnova.publish import Ledger, process_post


def run(manifest_path, config, platforms, live=False, state_path=None):
    manifest = read_json(manifest_path)
    ledger = Ledger(state_path) if live else None
    reports = []
    try:
        for post in manifest["posts"]:
            for platform in platforms:
                reports.append(process_post(post, manifest_path, config, platform, live=live, ledger=ledger))
    finally:
        if ledger:
            ledger.close()
    write_json(Path(manifest_path).parent / "relatorio-publicacoes.json", reports)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--plataforma", choices=["all", "tiktok", "instagram", "youtube"], default="all")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enviar", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--aprovar", metavar="ID", help="Marca um único rascunho como revisto; nunca publica.")
    parser.add_argument("--estado", type=Path, default=ROOT / "state/publications.sqlite3")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.aprovar:
        manifest = read_json(args.manifest)
        post = next((post for post in manifest["posts"] if post["id"] == args.aprovar), None)
        if post is None:
            parser.error("Não existe esse ID no manifesto.")
        post["review"] = {"approved": True, "fingerprint": fingerprint(post, args.manifest)}
        write_json(args.manifest, manifest)
        print("Revisão guardada. Nada foi enviado.")
        return
    platforms = ("tiktok", "instagram", "youtube") if args.plataforma == "all" else (args.plataforma,)
    reports = run(args.manifest, config, platforms, args.enviar, args.estado)
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    if args.enviar and any(report["status"] in ("blocked", "uncertain") for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
