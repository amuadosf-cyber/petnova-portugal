"""Cria anúncios, guiões, legendas e vídeos; nunca publica. Python 3.11+."""
import argparse
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from petnova.content import ROOT, load_config, load_products, plan_day, read_json, write_json


def generate(config, day, output, videos=True):
    folder = Path(output) / str(day)
    manifest_path = folder / "manifest.json"
    # Repetir a rotina não substitui rascunhos revistos ou vídeos existentes.
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest.get("schema_version") != 1 or manifest.get("date") != str(day):
            raise ValueError("O manifesto existente não corresponde ao dia ou à versão esperada.")
        if videos:
            from petnova.render import render_post
            changed = False
            for post in manifest["posts"]:
                target = folder / post["id"]
                if not (target / "video.mp4").is_file() or not (target / "anuncio.png").is_file():
                    render_post(post, target, config["content"]["video_seconds"])
                    post["generation"].pop("media_status", None)
                    post["review"] = {"approved": False, "fingerprint": None}
                    changed = True
            if changed:
                write_json(manifest_path, manifest)
        return manifest_path, manifest
    manifest = plan_day(config, load_products(), day)
    folder.mkdir(parents=True, exist_ok=True)
    from petnova.render import render_post, write_subtitles
    for post in manifest["posts"]:
        target = folder / post["id"]
        target.mkdir(exist_ok=True)
        write_subtitles(post, target / "legendas.srt", config["content"]["video_seconds"])
        if videos:
            render_post(post, target, config["content"]["video_seconds"])
        else:
            post["generation"]["media_status"] = "apenas_texto"
        text = f"# {post['product_name']}\n\nEstado: rascunho. {post['scheduled_at']}\n\n"
        for platform, caption in post["captions"].items():
            text += f"## {platform.title()}\n\n{caption}\n\n"
            (target / f"legenda_{platform}.txt").write_text(caption + "\n", encoding="utf-8")
        text += "## Guião de vídeo\n\n" + "\n".join(f"{i}. {s['title']} — {s['body']}" for i, s in enumerate(post["scenes"], 1))
        text += "\n\nImagens: ilustrações originais de conceito, sem fotografias de produto.\n"
        (target / "rascunho.md").write_text(text, encoding="utf-8")
        (target / "prompt_video_ia.txt").write_text(
            f"Guião para criação opcional de filmagens por IA: {post['product_name']}. "
            "Formato vertical 9:16, luz natural, cenas calmas de convivência com animais. "
            "Não representar um produto real, marca de terceiros, resultados ou testes. "
            "Adicionar na edição: loja em demonstração e ilustração de conceito. "
            "Rever a segurança da interação e os direitos de uso antes de publicar.\n", encoding="utf-8")
    with (folder / "calendario.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "data_hora_lisboa", "produto", "plataformas", "estado"])
        for post in manifest["posts"]:
            writer.writerow([post["id"], post["scheduled_at"], post["product_name"], "TikTok;Instagram;YouTube", "rascunho"])
    write_json(manifest_path, manifest)
    return manifest_path, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dia", help="Data local YYYY-MM-DD; por defeito, hoje em Lisboa.")
    parser.add_argument("--saida", type=Path, default=ROOT / "conteudos")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--sem-video", action="store_true", help="Só textos e legendas SRT; não cria imagens nem MP4.")
    parser.add_argument("--ia", choices=["templates", "ollama"])
    parser.add_argument("--modelo", help="Modelo já instalado no Ollama, sem downloads automáticos.")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.ia:
        config["content"]["provider"] = args.ia
    if args.modelo:
        config["content"]["ollama_model"] = args.modelo
    day = args.dia or datetime.now(ZoneInfo(config["content"]["timezone"])).date().isoformat()
    path, manifest = generate(config, day, args.saida, videos=not args.sem_video)
    print(f"{len(manifest['posts'])} rascunhos preparados em {path}. Nenhuma publicação enviada.")
    used = sum(bool(post["generation"]["ai_used"]) for post in manifest["posts"])
    print(f"IA usada em {used} de {len(manifest['posts'])} rascunhos. Restantes: modelos de texto. Revisão pendente.")


if __name__ == "__main__":
    main()
