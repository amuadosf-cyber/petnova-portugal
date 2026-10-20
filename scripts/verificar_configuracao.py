"""Diagnóstico local da PetNova. Apenas lê configuração; não revela credenciais."""
import argparse
import importlib.util
import json
from pathlib import Path
import os
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from petnova.content import load_config


def collect_report(config=None, environ=None):
    config = load_config() if config is None else config
    env = os.environ if environ is None else environ
    return {
        "store": {"mode": config["store"]["mode"],
                  "checkout_enabled": config["store"]["checkout_enabled"]},
        "generation": {
            "python_supported": sys.version_info >= (3, 11),
            "pillow_installed": importlib.util.find_spec("PIL") is not None,
            "ffmpeg_available": shutil.which("ffmpeg") is not None,
            "ffprobe_available": shutil.which("ffprobe") is not None,
        },
        "publishing": {
            "enabled": config["publishing"]["enabled"],
            "youtube_credentials_present": all(bool(env.get(name)) for name in
                ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")),
            "instagram_credentials_present": all(bool(env.get(name)) for name in
                ("IG_USER_ID", "IG_ACCESS_TOKEN")),
            "instagram_version_configured": bool(config["publishing"]["instagram_api_version"]),
            "instagram_media_host_configured": bool(config["publishing"]["public_media_base"]),
        },
        "note": "Este diagnóstico verifica apenas este computador. A existência das contas e a validade das autorizações não são verificadas.",
    }


def format_report(report):
    generation = report["generation"]
    publishing = report["publishing"]
    lines = ["PETNOVA PORTUGAL — VERIFICAÇÃO DESTE COMPUTADOR", "",
             f"Loja: {report['store']['mode']}. Compras: {'ativas' if report['store']['checkout_enabled'] else 'desativadas'}.", ""]
    labels = {"python_supported": "Python 3.11 ou superior", "pillow_installed": "Gerador de imagens",
              "ffmpeg_available": "Gerador de vídeos (FFmpeg)", "ffprobe_available": "Verificação de vídeos (ffprobe)"}
    lines.extend(f"{'OK' if generation[key] else 'POR PREPARAR'} — {label}" for key, label in labels.items())
    lines.extend(["", f"Publicações reais: {'ativadas na configuração' if publishing['enabled'] else 'desativadas'}.",
                  "Autorização YouTube neste processo: " + ("credenciais presentes; validade por testar" if publishing['youtube_credentials_present'] else "por configurar"),
                  "Autorização Instagram neste processo: " + ("credenciais presentes; validade por testar" if publishing['instagram_credentials_present'] else "por configurar"),
                  "", report["note"], "", "Próximo passo: seguir LIGAR_CONTAS.md usando as contas existentes da PetNova."])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Mostrar apenas indicadores, sem valores de credenciais.")
    args = parser.parse_args()
    try:
        report = collect_report()
    except (OSError, ValueError, KeyError):
        raise SystemExit("Não foi possível validar a configuração da PetNova. Consulta config/automacao.json.")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))


if __name__ == "__main__":
    main()
