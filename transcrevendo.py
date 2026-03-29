from youtube_transcript_api import YouTubeTranscriptApi
import time
import pandas as pd

api = YouTubeTranscriptApi()

def adicionar_transcricoes(videos):

    for i, video in enumerate(videos):
        print(f"[TRANSCRIÇÃO] {i+1}/{len(videos)}")

        try:
            video["transcricao"] = transcrever_video(video["id_video"])
            time.sleep(2)  # 🔥 evita ban
        except:
            video["transcricao"] = None

    return videos


def transcrever_video(id_video):

    api = YouTubeTranscriptApi()

    try:
        transcrito = api.fetch(video_id=id_video, languages=['pt'])
    
    except:
        try:
            transcrito = api.fetch(video_id=id_video)
        except:
            print(f"[SEM TRANSCRIÇÃO] {id_video}")
            return None

    return " ".join([trecho.text for trecho in transcrito.snippets])


df = pd.read_csv("videos_coletados1.csv")
videos = df.to_dict(orient="records")
videos = adicionar_transcricoes(videos)

df2 = pd.DataFrame(videos)
df2.to_csv("videos_coletados_t.csv", index=False)