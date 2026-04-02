import pandas as pd

df = pd.read_csv("videos_coletados.csv")
videos = df.to_dict(orient="records")

for row in videos:
    row['fonte'] = "YouTube"

df2 = pd.DataFrame(videos)
df2.to_csv("videos_coletados.csv", index=False)