import pandas as pd
import unicodedata
import spacy

nlp = spacy.load("pt_core_news_sm")
df = pd.read_csv("preprocess_transcript.csv")
df_coment = pd.read_csv("comentarios_tratados.csv")


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


def preprocess_descricao(df):

    df['descricao'] = df['descricao'].fillna("")

    df['descricao'] = df['descricao'].str.lower()

    df['descricao'] = df['descricao'].apply(remover_acentos)

    df['descricao'] = df['descricao'].str.replace(r"\[.*?\]", "", regex=True)
    df['descricao'] = df['descricao'].str.replace(r"\d+", "", regex=True)
    df['descricao'] = df['descricao'].str.replace(r"[^a-z\s]", "", regex=True)
    df['descricao'] = df['descricao'].str.replace(r"http\S+|www\S+", "", regex=True)
    df['descricao'] = df['descricao'].str.replace(r"\s+", " ", regex=True).str.strip()

    df['descricao_tokens'] = df['descricao'].apply(lambda x: x.split())

    df['descricao_tokens'] = df['descricao_tokens'].apply(
        lambda x: [p for p in x if p not in stopwords and len(p) > 2]
    )

    df['descricao'] = df['descricao_tokens'].apply(lambda x: " ".join(x))

    df.to_csv("preprocess_transcript.csv", index=False)

    return df

def preprocess_comentarios(df):

    df['texto'] = df['texto'].fillna("")

    df['texto_clean'] = df['texto'].str.lower()
    df['texto_clean'] = df['texto_clean'].apply(remover_acentos)

    df['texto_clean'] = df['texto_clean'].str.replace(r"\[.*?\]", "", regex=True)
    df['texto_clean'] = df['texto_clean'].str.replace(r"http\S+|www\S+", "", regex=True)
    df['texto_clean'] = df['texto_clean'].str.replace(r"\d+", "", regex=True)
    df['texto_clean'] = df['texto_clean'].str.replace(r"[^a-z\s]", "", regex=True)
    df['texto_clean'] = df['texto_clean'].str.replace(r"\s+", " ", regex=True).str.strip()

    df['comentario_tokens'] = df['texto_clean'].apply(lambda x: x.split())
    df['comentario_tokens'] = df['comentario_tokens'].apply(
        lambda x: [p for p in x if p not in stopwords and len(p) > 2]
    )

    df['texto_clean'] = df['comentario_tokens'].apply(lambda x: " ".join(x))

    df.to_csv("comentarios_tratados.csv", index=False)

    return df

def ordenar_por_media(df):
    
    df['score'] = (
        df['visualizacoes'] +
        df['likes'] +
        df['total_comentarios']
    ) / 3

    df = df.sort_values(by='score', ascending=False)

    df.to_csv("preprocess_transcript.csv", index=False)
    return df
