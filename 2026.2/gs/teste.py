
import requests
import pandas as pd
import xml.etree.ElementTree as ET

url = "https://apiprevmet3.inmet.gov.br/avisos/rss"

response = requests.get(url, timeout=30)
response.raise_for_status()

root = ET.fromstring(response.content)

registros = []

for item in root.findall(".//item"):
    registros.append({
        "titulo": item.findtext("title"),
        "descricao": item.findtext("description"),
        "link": item.findtext("link"),
        "publicacao": item.findtext("pubDate")
    })

df = pd.DataFrame(registros)

if not df.empty:
    df["evento"] = df["titulo"].str.extract(
        r"Aviso de (.*?)\. Severidade",
        expand=False
    )

    df["severidade"] = df["titulo"].str.extract(
        r"Severidade Grau: (.*)",
        expand=False
    )

    print("TOTAL DE AVISOS:", len(df))

    print("\nEVENTOS:")
    print(df["evento"].value_counts(dropna=False))

    print("\nSEVERIDADES:")
    print(df["severidade"].value_counts(dropna=False))

    print("\nAVISOS:")
    print(df[["evento", "severidade", "publicacao", "link"]])
else:
    print("Nenhum aviso encontrado no RSS.")
