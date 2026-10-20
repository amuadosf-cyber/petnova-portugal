"""Publicação por APIs oficiais, com simulação e registo persistente por defeito."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .content import NOTICE, ROOT, fingerprint, media_path


class PublishError(RuntimeError):
    pass


class Transport:
    def __call__(self, method, url, *, headers=None, json_body=None, form=None, data=None):
        headers = dict(headers or {})
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
        elif form is not None:
            data = urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=45) as response:
                body = response.read()
                return (json.loads(body) if body else {}), dict(response.headers)
        except HTTPError as exc:
            # Não imprimir resposta, URL, token nem cabeçalhos do fornecedor.
            raise PublishError(f"A plataforma respondeu HTTP {exc.code}; verifica permissões e limites.") from None
        except (URLError, TimeoutError, OSError):
            raise PublishError("Falha de ligação à plataforma; confirma o estado antes de repetir.") from None
        except (ValueError, UnicodeError):
            raise PublishError("A plataforma devolveu uma resposta inesperada; confirma o estado antes de repetir.") from None


def required_environment(names, environ=None):
    env = os.environ if environ is None else environ
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise PublishError("Falta configurar: " + ", ".join(missing))
    return {name: env[name] for name in names}


def instagram_url(post, config):
    explicit = post["media"].get("public_video_url", "")
    base = config["publishing"].get("public_media_base", "").rstrip("/")
    url = explicit or (base + "/" + post["media"]["video"] if base else "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise PublishError("Instagram precisa de um URL HTTPS público do MP4, sem autenticação.")
    return url


def publish_youtube(post, manifest_path, config, transport, environ=None):
    env = required_environment(("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"), environ)
    token, _ = transport("POST", "https://oauth2.googleapis.com/token", form={
        "client_id": env["YOUTUBE_CLIENT_ID"], "client_secret": env["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": env["YOUTUBE_REFRESH_TOKEN"], "grant_type": "refresh_token",
    })
    if not token.get("access_token"):
        raise PublishError("Não foi possível obter autorização do YouTube.")
    video = media_path(manifest_path, post["media"]["video"])
    metadata = {
        "snippet": {"title": post["youtube_title"], "description": post["captions"]["youtube"],
                    "categoryId": "15", "defaultLanguage": "pt-PT"},
        "status": {"privacyStatus": config["publishing"]["youtube_privacy"],
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False},
    }
    _, headers = transport("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token['access_token']}", "X-Upload-Content-Length": str(video.stat().st_size),
                 "X-Upload-Content-Type": "video/mp4"}, json_body=metadata)
    location = next((value for key, value in headers.items() if key.lower() == "location"), "")
    parsed = urlsplit(location)
    if parsed.scheme != "https" or parsed.hostname != "www.googleapis.com":
        raise PublishError("Sessão de upload YouTube inválida.")
    # Os vídeos gráficos são pequenos. Não se repete automaticamente uma escrita incerta.
    result, _ = transport("PUT", location, headers={"Content-Type": "video/mp4",
        "Content-Length": str(video.stat().st_size)}, data=video.read_bytes())
    identifier = result.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise PublishError("Upload sem confirmação de vídeo; verifica o YouTube Studio.")
    return {"remote_id": identifier, "status": "uploaded", "privacy": metadata["status"]["privacyStatus"]}


def publish_instagram(post, manifest_path, config, transport, environ=None, sleep=time.sleep):
    env = required_environment(("IG_USER_ID", "IG_ACCESS_TOKEN"), environ)
    version = config["publishing"].get("instagram_api_version", "")
    if not re.fullmatch(r"v\d+\.\d+", version) or not env["IG_USER_ID"].isdigit():
        raise PublishError("Define a versão Graph API suportada e o IG_USER_ID numérico.")
    video_url = instagram_url(post, config)
    host = f"https://graph.instagram.com/{version}"
    headers = {"Authorization": f"Bearer {env['IG_ACCESS_TOKEN']}"}
    created, _ = transport("POST", f"{host}/{env['IG_USER_ID']}/media", headers=headers, form={
        "media_type": "REELS", "video_url": video_url, "caption": post["captions"]["instagram"], "share_to_feed": "true",
    })
    container = str(created.get("id", ""))
    if not container.isdigit():
        raise PublishError("Instagram não confirmou a criação do Reel.")
    for attempt in range(12):
        state, _ = transport("GET", f"{host}/{container}?fields=status_code", headers=headers)
        status = state.get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise PublishError("O processamento do Reel falhou; confirma o contentor antes de repetir.")
        if status != "IN_PROGRESS":
            raise PublishError("Estado de Reel inesperado; verifica a conta antes de repetir.")
        if attempt < 11:
            sleep(5)
    else:
        raise PublishError("Reel ainda em processamento; não foi reenviado para evitar duplicados.")
    result, _ = transport("POST", f"{host}/{env['IG_USER_ID']}/media_publish", headers=headers,
                          form={"creation_id": container})
    identifier = str(result.get("id", ""))
    if not identifier.isdigit():
        raise PublishError("Instagram não confirmou a publicação; verifica a conta.")
    return {"remote_id": identifier, "status": "published"}


class Ledger:
    """SQLite persistente: a chave é o post e a rede, mesmo se o texto mudar."""
    def __init__(self, path=None):
        self.path = Path(path or ROOT / "state/publications.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.execute("CREATE TABLE IF NOT EXISTS publications (post_id TEXT, platform TEXT, fingerprint TEXT, status TEXT, receipt TEXT, PRIMARY KEY (post_id, platform))")
        self.db.commit()

    def claim(self, post_id, platform, content_hash):
        try:
            with self.db:
                self.db.execute("INSERT INTO publications VALUES (?, ?, ?, 'pending', '{}')", (post_id, platform, content_hash))
            return True
        except sqlite3.IntegrityError:
            return False

    def finish(self, post_id, platform, status, receipt):
        with self.db:
            self.db.execute("UPDATE publications SET status=?, receipt=? WHERE post_id=? AND platform=?",
                            (status, json.dumps(receipt), post_id, platform))

    def close(self):
        self.db.close()


def readiness(post, manifest_path, config, platform, *, now=None, environ=None):
    reasons = []
    if config["publishing"]["enabled"] is not True:
        reasons.append("Publicação real desativada na configuração.")
    if post.get("mode") != "demonstracao" or any(NOTICE not in post["captions"].get(p, "") for p in ("tiktok", "instagram", "youtube")):
        reasons.append("Falta o aviso de loja em demonstração.")
    if not post["review"].get("approved"):
        reasons.append("Rascunho por rever.")
    else:
        try:
            if post["review"].get("fingerprint") != fingerprint(post, manifest_path):
                reasons.append("Conteúdo alterado desde a revisão.")
        except OSError:
            reasons.append("Ficheiros de media em falta.")
    for key in ("video", "ad"):
        if not media_path(manifest_path, post["media"][key]).is_file():
            reasons.append(f"Falta o ficheiro {key}.")
    scheduled = datetime.fromisoformat(post["scheduled_at"])
    if scheduled.tzinfo is None:
        reasons.append("Horário sem fuso definido.")
    elif scheduled > (now or datetime.now(timezone.utc)):
        reasons.append("Horário de publicação ainda não atingido.")
    env = os.environ if environ is None else environ
    if platform == "tiktok":
        reasons.append("TikTok: ficheiros prontos para publicação nativa; Direct Post não ativado neste projeto interno.")
    elif platform == "youtube":
        missing = [name for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN") if not env.get(name)]
        if missing:
            reasons.append("Falta configurar: " + ", ".join(missing))
    elif platform == "instagram":
        missing = [name for name in ("IG_USER_ID", "IG_ACCESS_TOKEN") if not env.get(name)]
        if missing:
            reasons.append("Falta configurar: " + ", ".join(missing))
        if not re.fullmatch(r"v\d+\.\d+", config["publishing"].get("instagram_api_version", "")):
            reasons.append("Falta a versão suportada da API do Instagram.")
        try:
            instagram_url(post, config)
        except PublishError as exc:
            reasons.append(str(exc))
    else:
        raise ValueError("Plataforma desconhecida.")
    return reasons


def process_post(post, manifest_path, config, platform, *, live=False, ledger=None,
                 transport=None, now=None, environ=None):
    reasons = readiness(post, manifest_path, config, platform, now=now, environ=environ)
    report = {"post_id": post["id"], "platform": platform, "dry_run": not live, "sent": False, "blockers": reasons}
    if not live:
        return dict(report, status="simulation")
    if reasons:
        return dict(report, status="blocked")
    if ledger is None:
        raise ValueError("Publicação real exige um registo persistente.")
    digest = fingerprint(post, manifest_path)
    if not ledger.claim(post["id"], platform, digest):
        return dict(report, status="already_recorded", blockers=["Publicação já registada ou incerta; não foi repetida."])
    try:
        if platform == "youtube":
            receipt = publish_youtube(post, manifest_path, config, transport or Transport(), environ)
        else:
            receipt = publish_instagram(post, manifest_path, config, transport or Transport(), environ)
        ledger.finish(post["id"], platform, "confirmed", receipt)
        return dict(report, status="confirmed", sent=True, receipt=receipt)
    except (PublishError, OSError, ValueError, KeyError, TypeError):
        # Pode existir uma escrita remota mesmo sem resposta. Nunca repetir às cegas.
        ledger.finish(post["id"], platform, "uncertain", {"message": "Verificar a conta antes de qualquer repetição."})
        return dict(report, status="uncertain", blockers=["Sem confirmação final da plataforma. Verifica a conta; repetição automática bloqueada."])
