from youtube_transcript_api import YouTubeTranscriptApi, IpBlocked, RequestBlocked
import time
import pandas as pd
import random


api = YouTubeTranscriptApi()


def transcrever_video(id_video):
    try:
        transcrito = api.fetch(video_id=id_video, languages=['pt'])
    except Exception as e1:

        if isinstance(e1, (IpBlocked, RequestBlocked)):
            print(f"\nBAN DETECTADO no vídeo {id_video}")
            print(f"Tipo: {type(e1).__name__}\nMotivo: {e1}\n")
            return None, True

        try:
            transcrito = api.fetch(video_id=id_video)
        except Exception as e2:
            print(f"Sem transcrição para o vídeo {id_video}")
            print(f"Motivo: {e2}, {e1}\n")
            return None, False

    texto = " ".join([trecho.text for trecho in transcrito.snippets])
    return texto, False



def adicionar_transcricoes(videos, max_vds=15):

    print("\nIniciando coleta de transcrições...\n")

    total = len(videos)

    for i, video in enumerate(videos):

        print(f"[{i+1}/{total}] Vídeo: {video['id_video']}")

        if video["transcricao"] not in [None, "", "None"] and pd.notna(video["transcricao"]):
            print("Já possui transcrição, pulando\n")
            continue

        print("Tentando obter transcrição via API...")

        try:

            transcricao, ipBlock = transcrever_video(video["id_video"])

            if ipBlock:
                print("\n\nip Block!\n\n")
                return videos, 0
            
            elif transcricao is None:
                print("\n\nSEM TRANSCRICAO\n\n")
                return videos, 0

            if not transcricao:
                print("Falhou!\n")
                continue

            video["transcricao"] = transcricao
            print("Transcrição obtida com sucesso\n")

            time.sleep(1 + random.random())

        except Exception as e:
            print("\nParando execução por erro inesperado")
            print(f"Vídeo: {video['id_video']}")
            print(f"Erro: {e}\n")
            break

        max_vds -= 1
        if max_vds <= 0:
            break

    print("Execução finalizada\n")
    return videos, total - (i+1)


def init():
    
    df = pd.read_csv("./database/videos_coletados.csv")
    videos = df.to_dict(orient="records")

    videos, faltantes = adicionar_transcricoes(
        videos,
        max_vds= 20 # random.randint(10, 17)
    )

    df2 = pd.DataFrame(videos)
    df2.to_csv("./database/videos_coletados.csv", index=False)

    return faltantes


faltantes = 1000

while faltantes > 0:
    faltantes = init()
    time.sleep(3 + random.random())