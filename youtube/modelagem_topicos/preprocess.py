import pandas as pd
import unicodedata
import spacy

nlp = spacy.load("pt_core_news_sm")
df = pd.read_csv("../database/videos_coletados.csv")


def remover_acentos(texto):

    return ''.join(
        char for char in unicodedata.normalize('NFD', texto)
        if unicodedata.category(char) != 'Mn'
    )

stopwords = set(remover_acentos(w) for w in nlp.Defaults.stop_words)

def preprocess_transcript(df):

    df['transcricao'] = df['transcricao'].fillna("")

    df['transcricao_clean'] = df['transcricao'].str.lower()

    df['transcricao_clean'] = df['transcricao_clean'].apply(remover_acentos)

    df['transcricao_clean'] = df['transcricao_clean'].str.replace(r"\[.*?\]", "", regex=True)
    df['transcricao_clean'] = df['transcricao_clean'].str.replace(r"\d+", "", regex=True)
    df['transcricao_clean'] = df['transcricao_clean'].str.replace(r"[^a-z\s]", "", regex=True)
    df['transcricao_clean'] = df['transcricao_clean'].str.replace(r"\s+", " ", regex=True).str.strip()

    df['tokens'] = df['transcricao_clean'].apply(lambda x: x.split())

    df['tokens'] = df['tokens'].apply(
        lambda x: [p for p in x if p not in stopwords and len(p) > 2]
    )

    df['transcricao_clean'] = df['tokens'].apply(lambda x: " ".join(x))

    df.to_csv("preprocess_transcript.csv", index=False)

    return df

preprocess_transcript(df)


