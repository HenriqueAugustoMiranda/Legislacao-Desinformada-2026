import time
import random
import json
import string
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import email.utils
import requests

from instagrapi import Client
from utils import get_sessionid, get_users

USERNAMES_ALVO = get_users()
BATCH_POSTS = 30

TZ_BR = ZoneInfo("America/Sao_Paulo")

DATA_LIMITE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ_BR).timestamp() # ano, mês, dia (Brasília)
USAR_DATA_LIMITE = True

SLEEP_BETWEEN_PAGES = (1.5, 3.0)
SLEEP_BETWEEN_USERS = (3.0, 6.0)

OUT_DIR = Path("out_instagram")  # pasta base de saída por perfil
OUT_DIR.mkdir(exist_ok=True)

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"

def pk_to_shortcode(pk: int) -> str:
    """Converte o `pk` numérico do Instagram para shortcode.

    Args:
        pk: Identificador numérico do post.

    Returns:
        str: Shortcode correspondente ao post.
    """
    code = ""
    while pk > 0:
        pk, rem = divmod(pk, 64)
        code = ALPHABET[rem] + code
    return code or "0"

def build_post_url(shortcode: str) -> str:
    """Monta a URL pública de um post do Instagram.

    Args:
        shortcode: Código curto do post.

    Returns:
        str: URL completa do post.
    """
    return f"https://www.instagram.com/p/{shortcode}/"

def sleep_range(a_b):
    """Pausa a execução por um intervalo aleatório.

    Args:
        a_b: Tupla com limite inferior e superior do tempo de espera em segundos.

    Returns:
        None.
    """
    time.sleep(random.uniform(a_b[0], a_b[1]))

def ensure_user_dirs(username: str) -> Path:
    """Cria os diretórios de saída de um usuário.

    Args:
        username: Nome do perfil do Instagram.

    Returns:
        Path: Caminho do diretório principal do usuário.
    """
    user_dir = OUT_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "comments").mkdir(parents=True, exist_ok=True)
    return user_dir

def get_server_time_br() -> tuple[int, str]:
    """Obtém o horário do servidor HTTP do Instagram e converte para horário de Brasília.

    Args:
        None.

    Returns:
        tuple[int, str]: Timestamp epoch e data/hora formatada em Brasília.
    """
    r = requests.head("https://www.instagram.com", timeout=10)
    date_header = r.headers.get("Date")
    if not date_header:
        raise RuntimeError("Servidor não retornou header Date")

    dt_utc = email.utils.parsedate_to_datetime(date_header)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    dt_br = dt_utc.astimezone(TZ_BR)
    return int(dt_br.timestamp()), dt_br.strftime("%Y-%m-%d %H:%M:%S")

def get_user_id_private(cl: Client, username: str) -> int:
    """Resolve o ID interno de um usuário do Instagram via endpoint privado.

    Args:
        cl: Cliente autenticado do Instagrapi.
        username: Nome do perfil alvo.

    Returns:
        int: ID numérico do usuário encontrado.
    """
    resp = cl.private_request("users/search/", params={"q": username, "count": 10})
    users = resp.get("users", [])
    if not users:
        raise RuntimeError(f"Não achei usuário via search: @{username}")

    for u in users:
        if u.get("username", "").lower() == username.lower():
            return int(u["pk"])
    return int(users[0]["pk"])

def iter_user_posts_raw(cl: Client, user_id: int, batch: int = 30):
    """Itera os posts brutos de um usuário com paginação.

    Args:
        cl: Cliente autenticado do Instagrapi.
        user_id: ID numérico do usuário.
        batch: Quantidade de posts por requisição.

    Returns:
        Generator[dict, None, None]: Itens brutos de posts retornados pela API privada.
    """
    max_id = None
    while True:
        params = {"count": batch}
        if max_id:
            params["max_id"] = max_id

        resp = cl.private_request(f"feed/user/{user_id}/", params=params)
        items = resp.get("items", [])
        if not items:
            break

        for it in items:
            yield it

        max_id = resp.get("next_max_id")
        if not max_id:
            break

        # pausa curta para reduzir bloqueio por excesso de requisições
        sleep_range(SLEEP_BETWEEN_PAGES)

def media_type_to_label(media_type: int) -> str:
    """Mapeia o código de tipo de mídia para rótulo textual.

    Args:
        media_type: Código numérico do tipo de mídia.

    Returns:
        str: Rótulo do tipo (`photo`, `video`, `album` ou `unknown`).
    """
    return {1: "photo", 2: "video", 8: "album"}.get(media_type, "unknown")

def normalize_post_record(username: str, raw: dict) -> dict:
    """Normaliza um post bruto para o formato salvo no JSON de saída.

    Args:
        username: Nome do perfil de origem do post.
        raw: Dicionário bruto retornado pela API privada do Instagram.

    Returns:
        dict: Post com campos padronizados de identificação, data, conteúdo e métricas.
    """
    cap = raw.get("caption")
    caption_text = cap.get("text") if isinstance(cap, dict) else None

    media_pk = raw.get("pk")

    shortcode = raw.get("code")
    if not shortcode and media_pk:
        shortcode = pk_to_shortcode(int(media_pk))

    post_url = build_post_url(shortcode) if shortcode else None

    taken_at_ts = raw.get("taken_at")

    taken_at_br = None
    if taken_at_ts:
        taken_at_br = datetime.fromtimestamp(taken_at_ts, tz=TZ_BR).strftime("%Y-%m-%d %H:%M:%S")

    media_type = raw.get("media_type")

    return {
        "username": username,
        "media_pk": media_pk,
        "shortcode": shortcode,
        "url": post_url,
        "taken_at": taken_at_ts,
        "taken_at_br": taken_at_br,
        "media_type": media_type,
        "media_type_label": media_type_to_label(media_type),
        "caption": caption_text,
        "like_count": raw.get("like_count"),
        "comment_count": raw.get("comment_count"),
    }

cl = Client()
cl.login_by_sessionid(get_sessionid())
print("Login OK via sessionid")

COLLECTED_AT, COLLECTED_AT_BR = get_server_time_br()
print(f"Horario (servidor) da coleta BR: {COLLECTED_AT_BR}")

for username in USERNAMES_ALVO:
    print(f"\n=== Coletando POSTS: @{username} ===")

    user_dir = ensure_user_dirs(username)
    posts_file = user_dir / "posts.json"

    user_id = get_user_id_private(cl, username)
    print(f"user_id = {user_id}")

    posts = []  # posts válidos que entram no arquivo final

    for raw in iter_user_posts_raw(cl, user_id, batch=BATCH_POSTS):
        post = normalize_post_record(username, raw)
        media_pk = post["media_pk"]
        taken_at = post["taken_at"]

        if not media_pk:
            continue

        # interrompe quando cruza a data limite definida
        if USAR_DATA_LIMITE and taken_at is not None and taken_at < DATA_LIMITE:
            print("Cheguei em posts anteriores a data limite. Parando.")
            break

        posts.append(post)

    payload = {
        "username": username,
        "collected_at": COLLECTED_AT,
        "collected_at_br": COLLECTED_AT_BR,
        "timezone": "America/Sao_Paulo",
        "data_limite_epoch": int(DATA_LIMITE) if USAR_DATA_LIMITE else None,
        "data_limite_br": datetime.fromtimestamp(DATA_LIMITE, tz=TZ_BR).strftime("%Y-%m-%d %H:%M:%S")
                         if USAR_DATA_LIMITE else None,
        "batch_posts": BATCH_POSTS,
        "posts": posts,
    }

    posts_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Salvo: {posts_file} (total posts: {len(posts)})")
    sleep_range(SLEEP_BETWEEN_USERS)

print("\nFim do script de POSTS.")
