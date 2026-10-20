"""Gera o dia uma vez, percorre toda a fila e só envia se --enviar for explícito."""
import argparse
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automacao_conteudos import generate
from petnova.content import ROOT, load_config
from scripts.publicar import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enviar", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--saida", type=Path, default=ROOT / "conteudos")
    args = parser.parse_args()
    config = load_config(args.config)
    today = datetime.now(ZoneInfo(config["content"]["timezone"])).date().isoformat()
    generate(config, today, args.saida)
    totals = {}
    # Conteúdos revistos de dias anteriores não se perdem se o PC estiver desligado.
    for path in sorted(args.saida.glob("*/manifest.json")):
        for report in run(path, config, ("youtube", "instagram"), args.enviar):
            totals[report["status"]] = totals.get(report["status"], 0) + 1
    print(f"Rotina concluída. Resultados: {totals}. TikTok: exportação para publicação nativa.")
    if totals.get("uncertain"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
