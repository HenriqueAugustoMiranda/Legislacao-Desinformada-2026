import time
import random
import json
import string
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import email.utils
import requests
import traceback

from instagrapi import Client
from instagrapi.exceptions import ClientForbiddenError
from utils import get_sessionid, get_users

USERNAMES_ALVO = get_users()

SLEEP_BETWEEN_COMMENT_PAGES = (0.8, 1.6)
SLEEP_BETWEEN_POSTS = (0.8, 1.6)
SLEEP_BETWEEN_USERS = (5.0, 9.0)

MAX_CONSECUTIVE_403 = 2  # para o usuário atual após N erros 403 seguidos

OUT_DIR = Path("out_instagram")
OUT_DIR.mkdir(exist_ok=True)

TZ_BR = ZoneInfo("America/Sao_Paulo")

def sleep_range(a_b):
    """Pausa a execução por um intervalo aleatório.

    Args:
        a_b: Tupla com limite inferior e superior do tempo de espera em segundos.

    Returns:
        None.
    """
    time.sleep(random.uniform(a_b[0], a_b[1]))

def ensure_user_dirs(username: str):
    """Cria os diretórios de saída de comentários para um usuário.

    Args:
        username: Nome do perfil do Instagram.

    Returns:
        tuple[Path, Path]: Diretório do usuário e diretório raiz de comentários.
    """
    user_dir = OUT_DIR / username
    comments_root = user_dir / "comments"
    user_dir.mkdir(parents=True, exist_ok=True)
    comments_root.mkdir(parents=True, exist_ok=True)
    return user_dir, comments_root

def ts_to_br_str(ts: int | None):
    """Converte timestamp epoch para string no horário de Brasília.

    Args:
        ts: Timestamp epoch em segundos.

    Returns:
        str | None: Data/hora formatada ou `None` quando o timestamp é inválido.
    """
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=TZ_BR).strftime("%Y-%m-%d %H:%M:%S")

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

def post_url_from_shortcode(shortcode: str) -> str:
    """Monta a URL pública de um post do Instagram.

    Args:
        shortcode: Código curto do post.

    Returns:
        str: URL completa do post.
    """
    return f"https://www.instagram.com/p/{shortcode}/"

def fetch_all_comments_raw(cl: Client, media_pk: int):
    """Busca todos os comentários principais de um post com paginação.

    Args:
        cl: Cliente autenticado do Instagrapi.
        media_pk: ID numérico do post.

    Returns:
        list[dict]: Lista de comentários principais no formato bruto da API.
    """
    all_comments = []
    max_id = None
    min_id = None
    seen_cursors = set()

    while True:
        params = {
            "can_support_threading": "true",
            "permalink_enabled": "false",
            "sort_order": "recent",
        }
        if max_id:
            params["max_id"] = max_id
        if min_id:
            params["min_id"] = min_id

        resp = cl.private_request(f"media/{media_pk}/comments/", params=params)

        comments = resp.get("comments", []) or []
        if comments:
            all_comments.extend(comments)

        next_max_id = resp.get("next_max_id")
        next_min_id = resp.get("next_min_id")

        if isinstance(next_min_id, dict):
            next_min_id = json.dumps(next_min_id, separators=(",", ":"))

        has_more_comments = resp.get("has_more_comments")
        has_more_headload = resp.get("has_more_headload_comments")

        chosen = None
        if next_max_id:
            chosen = ("max", next_max_id)
        elif next_min_id and (has_more_comments or has_more_headload or has_more_comments is None):
            # fallback para endpoints que avançam por min_id
            chosen = ("min", next_min_id)

        if not chosen:
            break

        kind, cursor = chosen
        if (kind, cursor) in seen_cursors:
            break
        seen_cursors.add((kind, cursor))

        if kind == "max":
            max_id = cursor
            min_id = None
        else:
            min_id = cursor
            max_id = None

        sleep_range(SLEEP_BETWEEN_COMMENT_PAGES)

    return all_comments

def fetch_all_replies_raw(cl: Client, media_pk: int, comment_pk: int):
    """Busca todas as replies de um comentário pai com paginação.

    Args:
        cl: Cliente autenticado do Instagrapi.
        media_pk: ID numérico do post.
        comment_pk: ID numérico do comentário pai.

    Returns:
        list[dict]: Lista de replies no formato bruto da API.
    """
    all_replies = []
    max_id = None
    seen = set()

    while True:
        params = {"can_support_threading": "true"}
        if max_id:
            params["max_id"] = max_id

        resp = cl.private_request(
            f"media/{media_pk}/comments/{comment_pk}/child_comments/",
            params=params
        )

        replies = resp.get("child_comments", None)
        if replies is None:
            replies = resp.get("comments", []) or []
        else:
            replies = replies or []

        if replies:
            all_replies.extend(replies)

        next_max_id = resp.get("next_max_id")
        if not next_max_id:
            break

        if next_max_id in seen:
            break
        seen.add(next_max_id)

        max_id = next_max_id
        sleep_range(SLEEP_BETWEEN_COMMENT_PAGES)

    return all_replies

def normalize_comment_record(c: dict) -> dict:
    """Normaliza um comentário bruto para o formato salvo no JSON de saída.

    Args:
        c: Dicionário bruto de comentário retornado pela API privada.

    Returns:
        dict: Comentário com campos padronizados de identificação, texto e data.
    """
    u = c.get("user") or {}
    created_at_ts = c.get("created_at")
    created_at_br = ts_to_br_str(created_at_ts)

    return {
        "comment_id": c.get("pk"),
        "created_at": created_at_ts,
        "created_at_br": created_at_br,
        "comment_user": u.get("username"),
        "text": c.get("text"),
        "like_count": c.get("comment_like_count"),
    }

cl = Client()
cl.login_by_sessionid(get_sessionid())
print("Login OK via sessionid")

COLLECTED_AT, COLLECTED_AT_BR = get_server_time_br()
print(f"Horario (servidor) da coleta BR: {COLLECTED_AT_BR}")

for username in USERNAMES_ALVO:
    print(f"\n=== Coletando COMENTARIOS (TUDO + REPLIES): @{username} ===")

    user_dir, comments_root = ensure_user_dirs(username)
    posts_file = user_dir / "posts.json"

    if not posts_file.exists():
        print(f"Nao achei {posts_file}. Rode o script de POSTS primeiro.")
        continue

    posts_payload = json.loads(posts_file.read_text(encoding="utf-8"))

    if isinstance(posts_payload, dict) and "posts" in posts_payload:
        posts = posts_payload["posts"]
    else:
        posts = posts_payload

    print(f"Posts carregados: {len(posts)}")

    saved = 0
    failed = 0
    skipped_existing = 0

    forbidden_403 = 0
    consecutive_403 = 0

    for idx, post in enumerate(posts, start=1):
        media_pk = post.get("media_pk")
        shortcode = post.get("shortcode") or post.get("code")
        url = post.get("url")
        taken_at_br = post.get("taken_at_br") or ts_to_br_str(post.get("taken_at"))

        if not media_pk:
            continue
        if not shortcode:
            shortcode = pk_to_shortcode(int(media_pk))
        if not url:
            url = post_url_from_shortcode(shortcode)
        if not taken_at_br:
            continue

        dt_post = datetime.strptime(taken_at_br, "%Y-%m-%d %H:%M:%S")

        year_folder = comments_root / f"{dt_post.year}"
        day_folder = year_folder / dt_post.strftime("%m-%d")
        day_folder.mkdir(parents=True, exist_ok=True)

        filename = f"{dt_post.strftime('%H-%M-%S')}_{shortcode}.json"
        comment_path = day_folder / filename

        # retomada segura: não reprocessa arquivo já coletado
        if comment_path.exists():
            skipped_existing += 1
            continue

        expected_count = post.get("comment_count")

        try:
            raw_comments = fetch_all_comments_raw(cl, int(media_pk))

            comments_norm = []
            total_replies = 0

            for c in raw_comments:
                c_norm = normalize_comment_record(c)

                child_count = int(c.get("child_comment_count", 0) or 0)
                c_norm["reply_count"] = child_count
                c_norm["replies"] = []

                # busca replies só quando o comentário pai indica filhos
                if child_count > 0 and c.get("pk"):
                    replies_raw = fetch_all_replies_raw(cl, int(media_pk), int(c["pk"]))
                    replies_norm = [normalize_comment_record(r) for r in replies_raw]
                    c_norm["replies"] = replies_norm
                    total_replies += len(replies_norm)

                comments_norm.append(c_norm)

            got_total = len(comments_norm) + total_replies

            payload = {
                "username": username,
                "media_pk": int(media_pk),
                "shortcode": shortcode,
                "url": url,
                "taken_at_br": taken_at_br,
                "collected_at": COLLECTED_AT,
                "collected_at_br": COLLECTED_AT_BR,
                "timezone": "America/Sao_Paulo",
                "n_parent_comments": len(comments_norm),
                "n_total_replies": total_replies,
                "check": {
                    "expected_comment_count_from_post": expected_count,
                    "got_total": got_total,
                    "diff": (expected_count - got_total) if isinstance(expected_count, int) else None,
                },
                "comments": comments_norm,
            }

            comment_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            saved += 1
            consecutive_403 = 0  # sucesso zera sequência de bloqueio

        except ClientForbiddenError as e:
            failed += 1
            forbidden_403 += 1
            consecutive_403 += 1

            print("\n403 FORBIDDEN (bloqueio/limite):")
            print(f"   user=@{username}")
            print(f"   idx={idx}/{len(posts)}")
            print(f"   media_pk={media_pk}")
            print(f"   shortcode={shortcode}")
            print(f"   url={url}")
            print(f"   taken_at_br={taken_at_br}")
            print(f"   exception={type(e).__name__}: {e}")
            traceback.print_exc()

            if consecutive_403 >= MAX_CONSECUTIVE_403:
                print(f"\nPeguei {consecutive_403} erros 403 seguidos. Parando @{username} agora pra nao piorar o bloqueio.")
                break

            time.sleep(random.uniform(30, 60))
            continue

        except Exception as e:
            failed += 1
            consecutive_403 = 0

            print("\nERRO ao coletar comentarios:")
            print(f"   user=@{username}")
            print(f"   idx={idx}/{len(posts)}")
            print(f"   media_pk={media_pk}")
            print(f"   shortcode={shortcode}")
            print(f"   url={url}")
            print(f"   taken_at_br={taken_at_br}")
            print(f"   exception={type(e).__name__}: {e}")
            traceback.print_exc()

        if idx % 5 == 0:
            print(
                f"... {idx}/{len(posts)} | salvos={saved} | falhas={failed} | 403={forbidden_403} | ja_existia={skipped_existing}"
            )

        sleep_range(SLEEP_BETWEEN_POSTS)

    print(
        f"@{username}: salvos={saved} | falhas(sem arquivo)={failed} | 403={forbidden_403} | ja_existia={skipped_existing}"
    )
    print(f"Comentarios em: {comments_root}")

    sleep_range(SLEEP_BETWEEN_USERS)

print("\nFim do script de COMENTARIOS.")
