from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from youtube.statics.key import API_KEY
from youtube.statics.quarryes import queries
import pandas as pd
import json
import time

youtube = build("youtube", "v3", developerKey=API_KEY)


def transcrever_video(id_video):

    api = YouTubeTranscriptApi()

    try:
        transcrito = api.fetch(video_id=id_video, languages=['pt'])
    
    except:
        try:
            transcrito = api.fetch(video_id=id_video)
        except:
            print(f"Sem transcrição disponível para o vídeo {id_video}")
            return None

    return " ".join([trecho.text for trecho in transcrito.snippets])


def buscar_videos(queries, max_resultados=5):

    print("Iniciando busca de vídeos...")
    ids = set()

    for i, consulta in enumerate(queries):
        print(f"Buscando ({i+1}/{len(queries)}): {consulta}")

        requisicao = youtube.search().list(
            q=consulta,
            part="id",
            maxResults=max_resultados,
            type="video",
            order="relevance",
            regionCode="BR",
            relevanceLanguage="pt",
            publishedAfter="2026-02-01T00:00:00Z",
            videoDuration="medium"
        )
        
        resposta = requisicao.execute()

        ids_videos = [item["id"]["videoId"] for item in resposta["items"]]
        ids.update(ids_videos)

    print(f"Busca finalizada. Total de vídeos únicos encontrados: {len(ids)}\n")
    return ids


def obter_detalhes_videos(ids_videos):

    print("Coletando detalhes dos vídeos...")
    ids_videos = list(ids_videos)
    dados_videos = []

    for i in range(0, len(ids_videos), 50):
        print(f"Processando vídeos {i+1} até {min(i+50, len(ids_videos))}")

        bloco_ids = ids_videos[i:i+50]

        requisicao = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(bloco_ids)
        )

        resposta = requisicao.execute()

        for item in resposta["items"]:
            dados = {
                "fonte": "YouTube",
                "id_video": item["id"],
                "titulo": item["snippet"]["title"],
                "descricao": item["snippet"]["description"],
                "canal": item["snippet"]["channelTitle"],
                "data_publicacao": item["snippet"]["publishedAt"],
                "tags": item["snippet"].get("tags", []),
                "visualizacoes": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "total_comentarios": int(item["statistics"].get("commentCount", 0)),
                "comentarios": [],
                "transcricao": None
            }

            dados_videos.append(dados)

    print(f"Detalhes coletados para {len(dados_videos)} vídeos\n")
    return dados_videos


def adicionar_transcricoes(videos):

    print("Iniciando coleta de transcrições...")

    for i, video in enumerate(videos):
        print(f"Transcrevendo vídeo {i+1} de {len(videos)} ({video['id_video']})")

        try:
            video["transcricao"] = transcrever_video(video["id_video"])
            time.sleep(2)
        except:
            video["transcricao"] = None

    print("Transcrições finalizadas\n")
    return videos


def obter_comentarios(id_video, max_comentarios=50):

    print(f"Coletando comentários do vídeo {id_video}")

    comentarios = []

    try:
        requisicao = youtube.commentThreads().list(
            part="snippet",
            videoId=id_video,
            maxResults=100,
            textFormat="plainText"
        )

        while requisicao and len(comentarios) < max_comentarios:

            resposta = requisicao.execute()

            for item in resposta["items"]:
                snippet = item["snippet"]["topLevelComment"]["snippet"]

                comentarios.append({
                    "autor": snippet["authorDisplayName"],
                    "texto": snippet["textDisplay"],
                    "likes": snippet["likeCount"],
                    "data_publicacao": snippet["publishedAt"]
                })

                if len(comentarios) >= max_comentarios:
                    break

            requisicao = youtube.commentThreads().list_next(requisicao, resposta)

    except Exception:
        print(f"Comentários indisponíveis para o vídeo {id_video}")
        return []

    return comentarios


def coletar_dados_youtube(max_videos=20, max_comentarios=50):

    print("Iniciando coleta de dados do YouTube\n")

    ids_videos = buscar_videos(queries, max_videos)

    with open("ids.json", "w") as f:
        json.dump(list(ids_videos), f)

    videos = obter_detalhes_videos(ids_videos)

    # videos = adicionar_transcricoes(videos)

    print("Iniciando coleta de comentários...\n")

    for i, video in enumerate(videos):
        print(f"Vídeo {i+1} de {len(videos)}")
        video["comentarios"] = obter_comentarios(video["id_video"], max_comentarios)

    print("\nSalvando resultados em CSV...")

    df = pd.DataFrame(videos)
    df.to_csv("./databse/videos_coletados.csv", index=False)

    print("Processo finalizado com sucesso\n")
    return videos


coletar_dados_youtube()