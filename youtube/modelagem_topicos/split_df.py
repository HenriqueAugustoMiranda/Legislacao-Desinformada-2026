import pandas as pd
import ast

# carregar CSV
df = pd.read_csv("../database/videos_coletados.csv")

# converter string → lista de dicts
def parse_comentarios(x):
    try:
        if pd.notnull(x) and x != "":
            return ast.literal_eval(x)
        return []
    except:
        return []  # evita quebrar se tiver string mal formatada

df['comentarios'] = df['comentarios'].apply(parse_comentarios)

# explode (1 comentário por linha)
df_explodido = df.explode('comentarios')

# remover valores inválidos (NaN ou não-dict)
df_explodido = df_explodido[
    df_explodido['comentarios'].apply(lambda x: isinstance(x, dict))
]

df_explodido = df_explodido.reset_index(drop=True)

comentarios_df = pd.json_normalize(df_explodido['comentarios'])

comentarios_df = comentarios_df.reset_index(drop=True)

df_final = df_explodido[['id_video']].join(comentarios_df)

df_final = df_final.dropna(subset=['texto'])

df_final.to_csv("comentarios_tratados.csv", index=False)