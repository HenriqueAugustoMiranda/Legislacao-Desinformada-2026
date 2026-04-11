from youtube_transcript_api import YouTubeTranscriptApi, IpBlocked, RequestBlocked
import time
import pandas as pd
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

api = YouTubeTranscriptApi()



def criar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)



def transcrever2(id_video, driver):
    VIDEO_URL = "https://www.youtube.com/watch?v=" + id_video

    driver.get(VIDEO_URL)
    time.sleep(4)

    driver.execute_script("window.scrollTo(0, 800);")
    time.sleep(2)

    try:
        btn = driver.find_element(By.XPATH, '//button[contains(@aria-label, "trans")]')
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)
    except:
        print("Não achou botão de transcrição")
        return None

    segments = driver.find_elements(By.CSS_SELECTOR, "transcript-segment-view-model")

    texto = ""
    for seg in segments:
        try:
            texto += seg.find_element(By.CSS_SELECTOR, "span").text + " "
        except:
            pass

    return texto.strip() if texto else None



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
    driver = criar_driver()  

    for i, video in enumerate(videos):

        print(f"[{i+1}/{total}] Vídeo: {video['id_video']}")

        if video["transcricao"] not in [None, "", "None"] and pd.notna(video["transcricao"]):
            print("Já possui transcrição, pulando\n")
            continue

        print("Tentando obter transcrição via API...")

        try:
            transcricao, ipBlock = transcrever_video(video["id_video"])

            
            if ipBlock:
                break
                print("IP bloqueado → usando Selenium...\n")
                transcricao = transcrever2(video["id_video"], driver)

            
            elif transcricao is None:
                break
                print("Sem transcript via API → tentando Selenium...\n")
                transcricao = transcrever2(video["id_video"], driver)

            if not transcricao:
                print("Falhou geral (API + Selenium)\n")
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

    driver.quit()  

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