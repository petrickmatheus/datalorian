"""
ClimaLink — Coleta e tratamento dos avisos meteorológicos do INMET (RSS)
=========================================================================

Fonte (dado REAL): https://apiprevmet3.inmet.gov.br/avisos/rss

Gera duas tabelas:
  1. inmet_avisos         -> 1 linha por aviso (evento, severidade, período,
                             métricas extraídas do texto, riscos, link)
  2. inmet_avisos_areas   -> 1 linha por aviso x mesorregião (formato "longo",
                             pronto para cruzar com outras bases por
                             mesorregião/UF e data)

O feed só mostra os avisos recentes. Por isso o script ACUMULA o histórico:
a cada execução, junta o que já foi salvo com o que chegou e remove duplicados.

Uso:
    python inmet_avisos.py                       # baixa o feed e salva CSV em ./dados/inmet
    python inmet_avisos.py --formato parquet     # salva em Parquet
    python inmet_avisos.py --saida C:/climalink/dados
    python inmet_avisos.py --arquivo avisos.xml  # lê um XML salvo (teste offline)
    python inmet_avisos.py --sem-ibge            # não consulta a API do IBGE

Dependências: pandas, requests (e pyarrow, se usar Parquet)
    pip install pandas requests pyarrow
"""

from __future__ import annotations

import argparse
import html
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# Configuração — troque aqui o destino quando migrar para nuvem/banco
# ----------------------------------------------------------------------------
URL_RSS = "https://apiprevmet3.inmet.gov.br/avisos/rss"
URL_IBGE_MESO = "https://servicodados.ibge.gov.br/api/v1/localidades/mesorregioes"
PASTA_SAIDA_PADRAO = Path("./2026.2/gs/data") / "inmet"
FORMATO_PADRAO = "csv"  # "csv" ou "parquet"

NIVEL_SEVERIDADE = {"Perigo Potencial": 1, "Perigo": 2, "Grande Perigo": 3}
COR_SEVERIDADE = {"Perigo Potencial": "amarelo", "Perigo": "laranja", "Grande Perigo": "vermelho"}
STATUS_PT = {"Alert": "Alerta", "Update": "Atualização", "Cancel": "Cancelado"}


# ----------------------------------------------------------------------------
# 1. Coleta
# ----------------------------------------------------------------------------
def baixar_rss(url: str = URL_RSS, tentativas: int = 3, timeout: int = 30) -> bytes:
    """Baixa o XML do feed, com algumas tentativas em caso de falha de rede."""
    cabecalhos = {"User-Agent": "ClimaLink/1.0 (projeto academico FIAP)"}
    ultimo_erro = None
    for _ in range(tentativas):
        try:
            resp = requests.get(url, headers=cabecalhos, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as erro:
            ultimo_erro = erro
    raise RuntimeError(f"Não foi possível baixar o feed do INMET: {ultimo_erro}")


# ----------------------------------------------------------------------------
# 2. Leitura do XML
# ----------------------------------------------------------------------------
_RE_LINHA_TABELA = re.compile(r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", re.S | re.I)
_RE_TAGS = re.compile(r"<[^>]+>")


def _limpar_html(texto: str) -> str:
    texto = _RE_TAGS.sub("", texto or "")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def ler_itens(xml_bytes: bytes) -> list[dict]:
    """Transforma cada <item> do RSS em um dicionário com os campos da tabela HTML."""
    raiz = ET.fromstring(xml_bytes)
    itens = []
    for item in raiz.iter("item"):
        registro = {
            "titulo": (item.findtext("title") or "").strip(),
            "link_rss": (item.findtext("link") or "").strip(),
            "guid": (item.findtext("guid") or "").strip(),
            "pubdate_rss": (item.findtext("pubDate") or "").strip(),
        }
        descricao_html = item.findtext("description") or ""
        for campo, valor in _RE_LINHA_TABELA.findall(descricao_html):
            registro[_limpar_html(campo)] = _limpar_html(valor)
        itens.append(registro)
    return itens


# ----------------------------------------------------------------------------
# 3. Extração de métricas do texto da descrição
# ----------------------------------------------------------------------------
def _num(valor):
    return float(valor) if valor is not None else None


def extrair_metricas(descricao: str) -> dict:
    """Lê números do texto livre do INMET (chuva, vento, umidade, temperatura)."""
    d = descricao or ""
    m = {
        "chuva_mm_h_min": None, "chuva_mm_h_max": None,
        "chuva_mm_dia_min": None, "chuva_mm_dia_max": None,
        "vento_kmh_min": None, "vento_kmh_max": None,
        "umidade_pct_min": None, "umidade_pct_max": None,
        "declinio_temp_c_min": None, "declinio_temp_c_max": None,
        "granizo": bool(re.search(r"granizo", d, re.I)),
    }
    if r := re.search(r"Chuva entre (\d+) (?:e|a) (\d+) mm/h", d, re.I):
        m["chuva_mm_h_min"], m["chuva_mm_h_max"] = _num(r[1]), _num(r[2])
    if r := re.search(r"(\d+) (?:e|a) (\d+) mm/dia", d, re.I):
        m["chuva_mm_dia_min"], m["chuva_mm_dia_max"] = _num(r[1]), _num(r[2])
    elif r := re.search(r"até (\d+) mm/dia", d, re.I):
        m["chuva_mm_dia_min"], m["chuva_mm_dia_max"] = 0.0, _num(r[1])
    if r := re.search(r"\((\d+)\s*-\s*(\d+) km/h\)", d):
        m["vento_kmh_min"], m["vento_kmh_max"] = _num(r[1]), _num(r[2])
    elif r := re.search(r"entre (\d+) km/h e (\d+) km/h", d, re.I):
        m["vento_kmh_min"], m["vento_kmh_max"] = _num(r[1]), _num(r[2])
    if r := re.search(r"entre (\d+)% e (\d+)%", d):
        a, b = _num(r[1]), _num(r[2])
        m["umidade_pct_min"], m["umidade_pct_max"] = min(a, b), max(a, b)
    if r := re.search(r"entre (\d+)\s*º?\s*C e (\d+)\s*º?\s*C", d, re.I):
        m["declinio_temp_c_min"], m["declinio_temp_c_max"] = _num(r[1]), _num(r[2])
    return m


def extrair_riscos(descricao: str) -> str | None:
    """Mantém só as frases que descrevem riscos/impactos."""
    frases = [f.strip() for f in re.split(r"(?<=\.)\s+", descricao or "")]
    riscos = [f for f in frases if re.search(r"risco", f, re.I)]
    return " ".join(riscos) or None


def separar_areas(texto_area: str) -> list[str]:
    texto = re.sub(r"^Aviso para as Áreas:\s*", "", texto_area or "", flags=re.I)
    vistas, areas = set(), []
    for a in (p.strip() for p in texto.split(",")):
        if a and a not in vistas:
            vistas.add(a)
            areas.append(a)
    return areas


# ----------------------------------------------------------------------------
# 4. Tratamento
# ----------------------------------------------------------------------------
def tratar(itens: list[dict], coletado_em: datetime) -> pd.DataFrame:
    linhas = []
    for it in itens:
        descricao = it.get("Descrição", "")
        texto_limpo = re.sub(r"^INMET publica aviso iniciando em:\s*[\d/]+\s*[\d:]*\.\s*", "", descricao)
        id_txt = re.search(r"(\d+)\s*$", it.get("guid") or it.get("link_rss") or "")
        severidade = it.get("Severidade")
        try:
            publicado = parsedate_to_datetime(it["pubdate_rss"]).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError):
            publicado = None
        areas = separar_areas(it.get("Área", ""))
        linhas.append({
            "id_aviso": int(id_txt[1]) if id_txt else None,
            "evento": it.get("Evento"),
            "severidade": severidade,
            "severidade_nivel": NIVEL_SEVERIDADE.get(severidade),
            "severidade_cor": COR_SEVERIDADE.get(severidade),
            "status": STATUS_PT.get(it.get("Status"), it.get("Status")),
            "inicio": pd.to_datetime(it.get("Início"), errors="coerce"),
            "fim": pd.to_datetime(it.get("Fim"), errors="coerce"),
            "publicado_em": publicado,
            "descricao": texto_limpo or None,
            "riscos": extrair_riscos(texto_limpo),
            **extrair_metricas(texto_limpo),
            "qtd_areas": len(areas),
            "areas": " | ".join(areas),
            "link_grafico": re.sub(r"\s", "", it.get("Link Gráfico", "")) or None,
            "link_rss": it.get("link_rss"),
            "coletado_em": coletado_em,
        })
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    df["duracao_horas"] = ((df["fim"] - df["inicio"]).dt.total_seconds() / 3600).round(1)
    df["data_inicio"] = df["inicio"].dt.date
    df = (df.dropna(subset=["id_aviso"])
            .astype({"id_aviso": "int64"})
            .drop_duplicates("id_aviso", keep="last")
            .sort_values(["inicio", "id_aviso"])
            .reset_index(drop=True))
    ordem = ["id_aviso", "evento", "severidade", "severidade_nivel", "severidade_cor", "status",
             "inicio", "fim", "data_inicio", "duracao_horas", "publicado_em", "descricao", "riscos",
             "chuva_mm_h_min", "chuva_mm_h_max", "chuva_mm_dia_min", "chuva_mm_dia_max",
             "vento_kmh_min", "vento_kmh_max", "umidade_pct_min", "umidade_pct_max",
             "declinio_temp_c_min", "declinio_temp_c_max", "granizo",
             "qtd_areas", "areas", "link_grafico", "link_rss", "coletado_em"]
    return df[ordem]


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def tabela_mesorregioes_ibge() -> pd.DataFrame | None:
    """Busca na API do IBGE a UF e a região de cada mesorregião (para os cruzamentos)."""
    try:
        dados = requests.get(URL_IBGE_MESO, timeout=30).json()
    except Exception as erro:  # sem internet ou API fora do ar: segue sem enriquecer
        print(f"[aviso] IBGE indisponível ({erro}); UF ficará em branco.")
        return None
    meso = pd.DataFrame([{
        "chave": _normalizar(m["nome"]),
        "cod_mesorregiao_ibge": m["id"],
        "uf": m["UF"]["sigla"],
        "regiao": m["UF"]["regiao"]["nome"],
    } for m in dados])
    # nomes repetidos em UFs diferentes ficam juntos (ex.: "PR/SC")
    return (meso.groupby("chave", as_index=False)
                .agg({"cod_mesorregiao_ibge": lambda s: "/".join(map(str, s)),
                      "uf": lambda s: "/".join(s), "regiao": lambda s: "/".join(sorted(set(s)))}))


def explodir_areas(avisos: pd.DataFrame, meso_ibge: pd.DataFrame | None) -> pd.DataFrame:
    base = avisos[["id_aviso", "evento", "severidade", "severidade_nivel", "inicio", "fim",
                   "data_inicio", "areas"]].copy()
    base["mesorregiao"] = base["areas"].str.split(r" \| ")
    longo = base.explode("mesorregiao").drop(columns="areas")
    longo["mesorregiao"] = longo["mesorregiao"].str.strip()
    if meso_ibge is not None:
        longo["chave"] = longo["mesorregiao"].map(_normalizar)
        longo = longo.merge(meso_ibge, on="chave", how="left").drop(columns="chave")
        sem_uf = longo.loc[longo["uf"].isna(), "mesorregiao"].unique()
        if len(sem_uf):
            print(f"[aviso] {len(sem_uf)} área(s) sem correspondência no IBGE: {', '.join(sem_uf[:10])}")
    else:
        longo[["cod_mesorregiao_ibge", "uf", "regiao"]] = None
    return longo.sort_values(["inicio", "id_aviso", "mesorregiao"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# 5. Salvamento (com acúmulo de histórico)
# ----------------------------------------------------------------------------
def _ler(caminho: Path) -> pd.DataFrame | None:
    if not caminho.exists():
        return None
    if caminho.suffix == ".parquet":
        return pd.read_parquet(caminho)
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig",
                       parse_dates=["inicio", "fim"], dayfirst=False)


def salvar(df: pd.DataFrame, pasta: Path, nome: str, formato: str, chaves: list[str]) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.{formato}"
    anterior = _ler(caminho)
    if anterior is not None and not anterior.empty:
        df = (pd.concat([anterior, df], ignore_index=True)
                .drop_duplicates(subset=chaves, keep="last"))
    if formato == "parquet":
        df.to_parquet(caminho, index=False)
    else:
        # ";" + utf-8-sig abre direto e com acentos corretos no Excel em português
        df.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")
    return caminho


# ----------------------------------------------------------------------------
# 6. Execução
# ----------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Coleta e trata os avisos do INMET (RSS).")
    p.add_argument("--saida", type=Path, default=PASTA_SAIDA_PADRAO, help="pasta de destino")
    p.add_argument("--formato", choices=["csv", "parquet"], default=FORMATO_PADRAO)
    p.add_argument("--arquivo", type=Path, help="ler um XML salvo em vez de baixar")
    p.add_argument("--sem-ibge", action="store_true", help="não buscar UF/região no IBGE")
    args = p.parse_args()

    coletado_em = datetime.now().replace(microsecond=0)
    xml_bytes = args.arquivo.read_bytes() if args.arquivo else baixar_rss()
    itens = ler_itens(xml_bytes)
    avisos = tratar(itens, coletado_em)
    if avisos.empty:
        print("Nenhum aviso encontrado no feed.")
        return

    meso = None if args.sem_ibge else tabela_mesorregioes_ibge()
    areas = explodir_areas(avisos, meso)

    c1 = salvar(avisos, args.saida, "inmet_avisos", args.formato, ["id_aviso"])
    c2 = salvar(areas, args.saida, "inmet_avisos_areas", args.formato, ["id_aviso", "mesorregiao"])

    print(f"{len(avisos)} avisos lidos | {len(areas)} linhas aviso x mesorregião")
    print(avisos.groupby(["evento", "severidade"]).size().rename("avisos").to_string())
    print(f"\nSalvo em:\n  {c1.resolve()}\n  {c2.resolve()}")


if __name__ == "__main__":
    main()
