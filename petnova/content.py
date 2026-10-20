"""Catálogo, planeamento e assistência opcional de IA local."""
import csv
import hashlib
import json
import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NOTICE = "Loja em demonstração. Não aceitamos encomendas nem pagamentos."
PLATFORMS = ("tiktok", "instagram", "youtube")
IDEAS = {
    "escovagem": ("Uma pausa para cuidar", "Escovagem com calma", "Conhece as preferências do teu gato antes de escolher um acessório."),
    "brincadeira": ("Tempo para brincar?", "Pequenos momentos juntos", "Uma ideia para a próxima sessão de brincadeira acompanhada."),
    "refeicoes": ("Um cantinho só deles", "A rotina das refeições", "Descobre uma ideia para organizar o espaço das refeições."),
    "passeio": ("O próximo passeio começa aqui", "Água também vai no passeio", "Uma ideia de acessório para a tua lista de passeio."),
    "casa": ("Casa com animais, casa com vida", "Uma ideia para o dia a dia", "Conhece um conceito de acessório para a rotina de casa."),
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_config(path=None):
    config = read_json(path or ROOT / "config/automacao.json")
    store = config["store"]
    if store.get("mode") != "demonstracao" or store.get("checkout_enabled") is not False:
        raise ValueError("Esta versão da PetNova exige modo demonstração e compras desativadas.")
    if not isinstance(config["publishing"].get("enabled"), bool):
        raise ValueError("A opção publishing.enabled tem de ser true ou false.")
    ZoneInfo(config["content"]["timezone"])
    slots = config["content"]["daily_slots"]
    if not 1 <= len(slots) <= 5 or len(set(slots)) != len(slots):
        raise ValueError("Define entre um e cinco horários diários distintos.")
    for slot in slots:
        time.fromisoformat(slot)
    if not 12 <= config["content"]["video_seconds"] <= 60:
        raise ValueError("A duração do vídeo deve ficar entre 12 e 60 segundos.")
    if config["publishing"]["youtube_privacy"] not in ("private", "unlisted", "public"):
        raise ValueError("Privacidade YouTube inválida.")
    url = urlsplit(config["site_url"])
    if url.scheme != "https" or not url.netloc or url.query or url.fragment:
        raise ValueError("O endereço da loja tem de ser HTTPS, sem parâmetros.")
    return config


def load_products(path=None):
    with Path(path or ROOT / "produtos.csv").open(encoding="utf-8-sig", newline="") as handle:
        products = list(csv.DictReader(handle))
    seen = set()
    for product in products:
        identifier = product["id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", identifier) or identifier in seen:
            raise ValueError("Identificador de produto inválido ou repetido.")
        seen.add(identifier)
        if product["estado"] != "demonstracao" or product["tema"] not in IDEAS:
            raise ValueError("Catálogo inválido ou fora do modo demonstração.")
        try:
            price = Decimal(product["preco_demo_eur"])
            if not price.is_finite() or price <= 0:
                raise ValueError("Preço demonstrativo inválido.")
        except InvalidOperation as exc:
            raise ValueError("Preço demonstrativo inválido.") from exc
        if not product["nome"].strip() or len(product["nome"]) > 120:
            raise ValueError("Nome de produto inválido.")
    if not products:
        raise ValueError("O catálogo está vazio.")
    return products


def tracking_url(config, platform, post_id):
    return config["site_url"] + "?" + urlencode({
        "utm_source": platform, "utm_medium": "organic_social", "utm_campaign": post_id,
    })


def assisted_hook(product, config, opener=None):
    """A IA só sugere um título. Preços, promessas e CTAs ficam em texto controlado."""
    settings = config["content"]
    endpoint = urlsplit(settings["ollama_url"])
    if endpoint.scheme != "http" or endpoint.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Ollama só é permitido no próprio computador (sem API paga).")
    if endpoint.username or endpoint.password or endpoint.path not in ("", "/") or endpoint.query:
        raise ValueError("Endereço Ollama inválido.")
    if not settings.get("ollama_model"):
        raise ValueError("Define um modelo já instalado no Ollama.")
    payload = {"model": settings["ollama_model"], "stream": False, "think": False,
               "options": {"num_ctx": 2048, "num_predict": 120, "temperature": 0.4},
               "format": "json", "messages": [
        {"role": "system", "content": "Escreve em português de Portugal. Responde apenas com JSON {\"hook\":\"...\"}. Cria um título afetivo curto, com 4 a 9 palavras e menos de 75 caracteres, relacionado com o contexto fornecido. Não inventes outro produto, divisão da casa, material ou característica. Exemplos de estilo: Um momento de cuidado e companhia; A tua casa, a companhia deles; Água para acompanhar o próximo passeio. Sem promessas, preços, descontos, descrições de design, superlativos, testemunhos ou pedidos de compra. O produto não foi testado e a loja é de demonstração."},
        {"role": "user", "content": json.dumps({"produto": product["nome"], "contexto": IDEAS[product["tema"]][2], "tema": product["tema"]}, ensure_ascii=False)},
    ]}
    request = Request(settings["ollama_url"].rstrip("/") + "/api/chat",
                      json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with (opener or urlopen)(request, timeout=45) as response:
        result = json.load(response)
    hook = json.loads(result["message"]["content"])["hook"]
    if not isinstance(hook, str):
        raise ValueError("Título de IA inválido.")
    hook = hook.strip()
    if not 8 <= len(hook) <= 85 or not 4 <= len(hook.split()) <= 9:
        raise ValueError("Título de IA fora dos limites.")
    forbidden = r"https?://|[<>{}\n\r€%\d]|grátis|garanti|cura|compr[ae]|desconto|stock|entrega|melhor|perfeit|segur[oa]|aprova|veterin|elimin|resultad|design|funcional|premium|cozinha|durável"
    if re.search(forbidden, hook, re.IGNORECASE):
        raise ValueError("Título de IA rejeitado pela verificação de alegações.")
    return hook


def make_post(product, config, day, slot_index):
    day = date.fromisoformat(str(day))
    slot = config["content"]["daily_slots"][slot_index]
    scheduled = datetime.combine(day, time.fromisoformat(slot), ZoneInfo(config["content"]["timezone"]))
    identifier = f"{day.isoformat()}-{slot.replace(':', '')}-p{product['id']}"
    hook, title, body = IDEAS[product["tema"]]
    generation = {"provider": "templates", "ai_used": False, "visuals": "ilustracao_original", "narration": "sem_voz"}
    if config["content"]["provider"] == "ollama":
        try:
            hook = assisted_hook(product, config)
            generation.update(provider="ollama", ai_used=True, model=config["content"]["ollama_model"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            generation["fallback"] = "IA local indisponível ou resposta rejeitada; usado modelo de texto."
    elif config["content"]["provider"] != "templates":
        raise ValueError("Gerador de texto desconhecido. Usa templates ou ollama.")
    scenes = [
        {"title": hook, "body": "Ideias para a vida com cães e gatos."},
        {"title": product["nome"], "body": body},
        {"title": "Estamos a preparar a PetNova", "body": "Produto e preço ilustrativos. Fornecedor ainda por confirmar."},
        {"title": "Conhece o projeto", "body": NOTICE},
    ]
    captions = {}
    for platform in PLATFORMS:
        captions[platform] = (f"{hook}\n\n{product['nome']} — um conceito do nosso catálogo.\n"
                              f"{NOTICE}\n\nConhece o projeto: {tracking_url(config, platform, identifier)}\n"
                              "#PetNovaPortugal #CaesEGatos #AnimaisDeEstimacao")
    return {"id": identifier, "product_id": product["id"], "product_name": product["nome"],
            "theme": product["tema"], "scheduled_at": scheduled.isoformat(), "mode": "demonstracao",
            "generation": generation, "hook": hook, "title": title, "scenes": scenes,
            "captions": captions, "youtube_title": f"{hook} | PetNova em demonstração"[:100],
            "media": {"video": f"{identifier}/video.mp4", "ad": f"{identifier}/anuncio.png",
                      "subtitles": f"{identifier}/legendas.srt", "public_video_url": ""},
            "review": {"approved": False, "fingerprint": None}}


def plan_day(config, products, day):
    day = date.fromisoformat(str(day))
    count = len(config["content"]["daily_slots"])
    offset = day.toordinal() * count
    return {"schema_version": 1, "date": day.isoformat(), "timezone": config["content"]["timezone"],
            "store_mode": "demonstracao", "posts": [
                make_post(products[(offset + index) % len(products)], config, day, index)
                for index in range(count)
            ]}


def media_path(manifest_path, relative):
    base = Path(manifest_path).resolve().parent
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError("O caminho de media sai da pasta de conteúdos.")
    return path


def fingerprint(post, manifest_path):
    payload = {key: value for key, value in post.items() if key != "review"}
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())
    for key in ("video", "ad"):
        path = media_path(manifest_path, post["media"][key])
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()
