from googleapiclient.discovery import build
from statics.key import API_KEY
import pandas as pd


youtube = build("youtube", "v3", developerKey=API_KEY)
df_vds = pd.read_csv("modelagem_topicos/preprocess_transcript.csv")
df_comentarios = pd.read_csv("modelagem_topicos/comentarios_tratados.csv")
SEM_COMENTARIOS = "sem_comentarios.txt"


def coletar_comentarios():

    ids_sem_comentarios = []
    todos_comentarios = []

    for video_id in df_vds['id_video']:

        comentarios = obter_comentarios(video_id, 200)

        if not comentarios:
            ids_sem_comentarios.append(video_id)
            continue

        for c in comentarios:
            c['id_video'] = video_id

        todos_comentarios.extend(comentarios)

    df_novos = pd.DataFrame(todos_comentarios)

    df_final = pd.concat([df_comentarios, df_novos], ignore_index=True)

    return df_final, ids_sem_comentarios


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


df, ids_sem_comentarios = coletar_comentarios()

df = df.drop_duplicates()
df = df.sort_values(by=["id_video", "autor"])

df.to_csv("comentarios_tratados.csv", index=False)

with open("sem_comentarios.txt", "a", encoding="utf-8") as f:
    f.write(f"\n{ids_sem_comentarios}\n")