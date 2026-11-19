# =============================================================================
# Turma: 1TSCOR  |  Projeto: ClimaLink  |  Grupo: Datalorian
# Integrantes (ordem alfabética):
#   Gustavo Varadi - RM575461
#   Petrick Mateus - RM575301
# -----------------------------------------------------------------------------
# Executar a partir da pasta raiz do repositório (a que contém "2026.2").
# Todos os arquivos gerados pelos scripts ficam em ./2026.2/gs/data
# =============================================================================
"""
ClimaLink — Bases SINTÉTICAS relacionadas aos avisos REAIS do INMET
====================================================================

Gera 3 bases (máx. 100 linhas cada), uma para cada fonte citada no ClimaLink:

  ibge_municipios_sintetico.csv       -> dimensão territorial (código IBGE real,
                                         mesorregião no MESMO nome usado pelo INMET)
  mapbiomas_fogo_sintetico.csv        -> queimadas diárias por município
  cemaden_pluviometria_sintetico.csv  -> chuva diária por estação pluviométrica

Os eventos foram FORÇADOS para conversar com avisos reais do feed do INMET
coletado em 18/11/2026 (ids citados abaixo). Cenários:

  A) "seca_pre_tempestade" (Cerrado/arco do desmatamento): queimadas fortes
     entre 01 e 08/11 em TO, oeste da BA, sul do MA, norte do MT e sudeste do PA
     -> tempestades de severidade "Perigo" nas mesmas mesorregiões em 16-18/11
     (avisos 56423, 56430, 56432). Defasagem de ~8 a 15 dias.
  B) "baixa_umidade_sertao": queimadas no sertão (CE, PI, PE) entre 11 e 14/11,
     com pico no dia do aviso de Baixa Umidade (56393, 13/11) -> chuva
     intensa logo depois (56414, 15/11). Defasagem de ~1 a 4 dias.
  C) "controle_sul": quase sem fogo no Sul, mas tempestade "Perigo" em 18/11
     (56441). Serve de grupo de controle: nem toda tempestade vem depois de fogo.

Chaves de ligação entre as bases e com o INMET:
  cod_ibge  (IBGE <-> MapBiomas <-> CEMADEN)
  mesorregiao + data  (qualquer base <-> inmet_avisos_areas)
  id_aviso_* (atalho direto para o aviso real que motivou o evento)

Todos os valores numéricos são fictícios. Códigos IBGE e nomes de municípios
são reais; populações são aproximadas (ordem de grandeza do Censo 2022).

Uso:  python synthetic_data.py [--saida pasta] [--formato csv|parquet]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

SEMENTE = 42
PATH = Path(__file__).parent.parent          # pasta única de dados do projetoo
PASTA_SAIDA_PADRAO = PATH / "data" / "sinteticos"

# ----------------------------------------------------------------------------
# Municípios (código IBGE real) — mesorregião escrita como no feed do INMET
# ----------------------------------------------------------------------------
# cod, município, UF, região, mesorregião, bioma, lat, lon, pop. aprox., perfil
MUNICIPIOS = [
    (1721000, "Palmas", "TO", "Norte", "Oriental do Tocantins", "Cerrado", -10.18, -48.33, 302000, "urbano"),
    (1718204, "Porto Nacional", "TO", "Norte", "Oriental do Tocantins", "Cerrado", -10.71, -48.42, 64000, "misto"),
    (1709500, "Gurupi", "TO", "Norte", "Ocidental do Tocantins", "Cerrado", -11.73, -49.07, 85000, "misto"),
    (1702109, "Araguaína", "TO", "Norte", "Ocidental do Tocantins", "Cerrado", -7.19, -48.21, 171000, "urbano"),
    (2903201, "Barreiras", "BA", "Nordeste", "Extremo Oeste Baiano", "Cerrado", -12.15, -45.00, 159000, "urbano"),
    (2919553, "Luís Eduardo Magalhães", "BA", "Nordeste", "Extremo Oeste Baiano", "Cerrado", -12.10, -45.80, 107000, "misto"),
    (2928901, "São Desidério", "BA", "Nordeste", "Extremo Oeste Baiano", "Cerrado", -12.36, -44.97, 33000, "rural"),
    (2911105, "Formosa do Rio Preto", "BA", "Nordeste", "Extremo Oeste Baiano", "Cerrado", -11.05, -45.19, 25000, "rural"),
    (2101400, "Balsas", "MA", "Nordeste", "Sul Maranhense", "Cerrado", -7.53, -46.04, 101000, "misto"),
    (2105302, "Imperatriz", "MA", "Nordeste", "Oeste Maranhense", "Amazônia", -5.53, -47.49, 273000, "urbano"),
    (5107909, "Sinop", "MT", "Centro-Oeste", "Norte Mato-grossense", "Amazônia", -11.86, -55.51, 196000, "urbano"),
    (5107925, "Sorriso", "MT", "Centro-Oeste", "Norte Mato-grossense", "Amazônia", -12.55, -55.71, 110000, "misto"),
    (5100250, "Alta Floresta", "MT", "Centro-Oeste", "Norte Mato-grossense", "Amazônia", -9.88, -56.09, 58000, "misto"),
    (5101803, "Barra do Garças", "MT", "Centro-Oeste", "Nordeste Mato-grossense", "Cerrado", -15.89, -52.26, 69000, "misto"),
    (1504208, "Marabá", "PA", "Norte", "Sudeste Paraense", "Amazônia", -5.37, -49.12, 266000, "urbano"),
    (1506138, "Redenção", "PA", "Norte", "Sudeste Paraense", "Amazônia", -8.03, -50.03, 85000, "misto"),
    (1500602, "Altamira", "PA", "Norte", "Sudoeste Paraense", "Amazônia", -3.20, -52.21, 126000, "misto"),
    (2304202, "Crato", "CE", "Nordeste", "Sul Cearense", "Caatinga", -7.23, -39.41, 131000, "misto"),
    (2307304, "Juazeiro do Norte", "CE", "Nordeste", "Sul Cearense", "Caatinga", -7.21, -39.32, 287000, "urbano"),
    (2305506, "Iguatu", "CE", "Nordeste", "Centro-Sul Cearense", "Caatinga", -6.36, -39.30, 98000, "misto"),
    (2304103, "Crateús", "CE", "Nordeste", "Sertões Cearenses", "Caatinga", -5.18, -40.67, 76000, "misto"),
    (2208007, "Picos", "PI", "Nordeste", "Sudeste Piauiense", "Caatinga", -7.08, -41.47, 83000, "misto"),
    (2203909, "Floriano", "PI", "Nordeste", "Sudoeste Piauiense", "Cerrado", -6.77, -43.02, 61000, "misto"),
    (2211001, "Teresina", "PI", "Nordeste", "Centro-Norte Piauiense", "Cerrado", -5.09, -42.80, 866000, "urbano"),
    (2611101, "Petrolina", "PE", "Nordeste", "São Francisco Pernambucano", "Caatinga", -9.39, -40.50, 386000, "urbano"),
    (2613909, "Serra Talhada", "PE", "Nordeste", "Sertão Pernambucano", "Caatinga", -7.99, -38.30, 92000, "misto"),
    (2612208, "Salgueiro", "PE", "Nordeste", "Sertão Pernambucano", "Caatinga", -8.07, -39.12, 61000, "misto"),
    (2913606, "Ilhéus", "BA", "Nordeste", "Sul Baiano", "Mata Atlântica", -14.79, -39.05, 178000, "urbano"),
    (2914802, "Itabuna", "BA", "Nordeste", "Sul Baiano", "Mata Atlântica", -14.79, -39.28, 186000, "urbano"),
    (3143302, "Montes Claros", "MG", "Sudeste", "Norte de Minas", "Cerrado", -16.73, -43.86, 414000, "urbano"),
    (3170404, "Unaí", "MG", "Sudeste", "Noroeste de Minas", "Cerrado", -16.36, -46.91, 86000, "misto"),
    (5218805, "Rio Verde", "GO", "Centro-Oeste", "Sul Goiano", "Cerrado", -17.79, -50.92, 225000, "misto"),
    (4314100, "Passo Fundo", "RS", "Sul", "Noroeste Rio-grandense", "Mata Atlântica", -28.26, -52.41, 206000, "urbano"),
    (4316907, "Santa Maria", "RS", "Sul", "Centro Ocidental Rio-grandense", "Pampa", -29.69, -53.81, 271000, "urbano"),
    (4314902, "Porto Alegre", "RS", "Sul", "Metropolitana de Porto Alegre", "Pampa", -30.03, -51.23, 1332000, "urbano"),
    (4204202, "Chapecó", "SC", "Sul", "Oeste Catarinense", "Mata Atlântica", -27.10, -52.62, 254000, "urbano"),
    (4209300, "Lages", "SC", "Sul", "Serrana", "Mata Atlântica", -27.82, -50.33, 164000, "urbano"),
    (4104808, "Cascavel", "PR", "Sul", "Oeste Paranaense", "Mata Atlântica", -24.96, -53.46, 348000, "urbano"),
    (4109401, "Guarapuava", "PR", "Sul", "Centro-Sul Paranaense", "Mata Atlântica", -25.39, -51.46, 182000, "misto"),
]
COLS_MUN = ["cod_ibge", "municipio", "uf", "regiao", "mesorregiao", "bioma",
            "latitude", "longitude", "populacao_aprox", "perfil_territorial"]

# ----------------------------------------------------------------------------
# Avisos REAIS (feed INMET de 18/11/2026) por mesorregião e dia — usados
# para forçar a chuva da base CEMADEN.  P = Perigo, PP = Perigo Potencial,
# BU = Baixa Umidade.  Dias sem entrada: nenhum aviso de chuva no feed.
# ----------------------------------------------------------------------------
PP_CERRADO = {9: ("PP", 56359), 10: ("PP", 56372), 11: ("PP", 56376), 12: ("PP", 56383),
              13: ("PP", 56392), 14: ("PP", 56404), 15: ("PP", 56414)}
AVISOS_POR_MESO = {
    "Sul Cearense": {13: ("BU", 56393), 15: ("PP", 56414), 16: ("PP", 56422)},
    "Sertão Pernambucano": {10: ("PP", 56364), 13: ("BU", 56393), 15: ("PP", 56414),
                            16: ("PP", 56422), 17: ("PP", 56436), 18: ("PP", 56445)},
    "Sudeste Piauiense": {9: ("PP", 56358), 10: ("PP", 56372), 13: ("BU", 56393), 15: ("PP", 56414),
                          16: ("PP", 56422), 17: ("PP", 56436), 18: ("PP", 56445)},
    "Oriental do Tocantins": {**PP_CERRADO, 16: ("P", 56423), 17: ("P", 56430), 18: ("P", 56432)},
    "Ocidental do Tocantins": {**PP_CERRADO, 16: ("P", 56423), 17: ("P", 56430), 18: ("P", 56432)},
    "Extremo Oeste Baiano": {**PP_CERRADO, 16: ("P", 56423), 17: ("P", 56430), 18: ("P", 56432)},
    "Sul Maranhense": {**PP_CERRADO, 16: ("P", 56423), 17: ("P", 56430), 18: ("PP", 56445)},
    "Noroeste Rio-grandense": {11: ("PP", 56377), 12: ("PP", 56380), 14: ("PP", 56401),
                               15: ("PP", 56411), 17: ("PP", 56437), 18: ("P", 56441)},
    "Oeste Catarinense": {11: ("PP", 56377), 12: ("PP", 56383), 14: ("PP", 56401),
                          15: ("PP", 56411), 17: ("PP", 56437), 18: ("P", 56441)},
    "Sul Baiano": {9: ("PP", 56359), 10: ("PP", 56386), 11: ("P", 56379), 12: ("PP", 56387),
                   13: ("PP", 56392), 14: ("PP", 56404), 15: ("PP", 56412),
                   16: ("P", 56423), 17: ("P", 56430), 18: ("P", 56432)},
}
NIVEL_TXT = {"P": "Perigo", "PP": "Perigo Potencial", "BU": "Baixa Umidade", None: "Sem aviso"}

# Uma estação CEMADEN por município (10 estações x 10 dias = 100 linhas)
ESTACOES = [2304202, 2613909, 2208007, 1721000, 1709500, 2903201, 2101400, 4314100, 4204202, 2913606]
# chuva média diária de novembro (mm/dia) — "climatologia" fictícia por região
CLIMATOLOGIA = {"Norte": 5.5, "Nordeste": 2.0, "Centro-Oeste": 6.0, "Sudeste": 5.0, "Sul": 5.5}

CENARIO_A = [1721000, 1718204, 1709500, 1702109, 2903201, 2919553, 2928901, 2911105,
             2101400, 5107909, 1504208, 1506138]
CENARIO_B = [2304202, 2307304, 2305506, 2304103, 2208007, 2203909, 2211001, 2611101, 2613909, 2612208]
CENARIO_C = [4314100, 4204202, 4209300, 4104808, 4314902, 4316907]


def d(dia: int) -> date:
    return date(2026, 11, dia)


def base_ibge() -> pd.DataFrame:
    rng = np.random.default_rng(SEMENTE)
    df = pd.DataFrame(MUNICIPIOS, columns=COLS_MUN)
    # n.º de estações pluviométricas: menos estações em áreas rurais (viés de cobertura)
    base = df["perfil_territorial"].map({"urbano": 6, "misto": 3, "rural": 1})
    df["estacoes_pluviometricas"] = (base + rng.integers(0, 3, len(df))).astype(int)
    df["densidade_estacoes_por_100mil_hab"] = (df["estacoes_pluviometricas"] / df["populacao_aprox"] * 1e5).round(2)
    df["fonte"] = "SINTÉTICO (estrutura inspirada em IBGE)"
    return df


def base_mapbiomas(mun: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEMENTE + 1)
    info = mun.set_index("cod_ibge")
    linhas = []

    def add(cod, dia, area, cenario, concomitante, posterior):
        m = info.loc[cod]
        classes = {"Cerrado": ["Formação Savânica", "Pastagem", "Formação Campestre", "Agricultura"],
                   "Amazônia": ["Pastagem", "Formação Florestal", "Mosaico de Usos"],
                   "Caatinga": ["Formação Savânica", "Pastagem", "Mosaico de Usos"]}.get(m.bioma, ["Mosaico de Usos"])
        focos = max(0, int(round(area / rng.uniform(18, 30))))
        linhas.append({
            "data": d(dia), "cod_ibge": cod, "municipio": m.municipio, "uf": m.uf,
            "mesorregiao": m.mesorregiao, "bioma": m.bioma,
            "classe_cobertura": rng.choice(classes),
            "area_queimada_ha": round(area, 1), "focos_calor": focos,
            "cenario": cenario,
            "id_aviso_concomitante": concomitante,
            "id_aviso_posterior": posterior[0] if posterior else None,
            "data_aviso_posterior": d(posterior[1]) if posterior else None,
            "defasagem_dias": (posterior[1] - dia) if posterior else None,
        })

    # A) queimadas fortes 01-08/11 -> tempestade "Perigo" 16/11 (56423) | Sinop -> 56430 (17/11)
    for cod in CENARIO_A:
        posterior = (56430, 17) if cod == 5107909 else (56423, 16)
        escala = rng.uniform(0.7, 1.4)
        for dia in sorted(rng.choice(range(1, 9), size=4, replace=False)):
            pico = 3200 * np.exp(-((dia - 3) ** 2) / 10)          # pico ~03/11, cai até 08/11
            add(cod, int(dia), max(80, pico * escala * rng.uniform(0.8, 1.2)), "seca_pre_tempestade", None, posterior)

    # B) sertão: 11-14/11 com pico no dia da Baixa Umidade (13/11) -> chuva intensa 15/11 (56414)
    for cod in CENARIO_B:
        escala = rng.uniform(0.6, 1.3)
        for dia, fator in [(11, 0.35), (12, 0.6), (13, 1.0), (14, 0.45)]:
            add(cod, dia, max(15, 650 * fator * escala * rng.uniform(0.85, 1.15)), "baixa_umidade_sertao",
                56393 if dia == 13 else None, (56414, 15))

    # C) controle Sul: fogo quase nulo; tempestade 56441 em 18/11 sem fogo antes
    for cod in CENARIO_C:
        add(cod, 10, rng.uniform(0, 12), "controle_sul", None, (56441, 18))

    df = pd.DataFrame(linhas).sort_values(["data", "uf", "municipio"]).reset_index(drop=True)
    df.insert(0, "id_registro", [f"MBF-{i:04d}" for i in range(1, len(df) + 1)])
    for c in ["id_aviso_concomitante", "id_aviso_posterior", "defasagem_dias"]:
        df[c] = df[c].astype("Int64")
    df["fonte"] = "SINTÉTICO (estrutura inspirada em MapBiomas Fogo)"
    return df


def base_cemaden(mun: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEMENTE + 2)
    info = mun.set_index("cod_ibge")
    linhas = []
    for cod in ESTACOES:
        m = info.loc[cod]
        clima = CLIMATOLOGIA[m.regiao]
        avisos = AVISOS_POR_MESO[m.mesorregiao]
        for dia in range(9, 19):
            nivel, id_aviso = avisos.get(dia, (None, None))
            if nivel == "P":                       # Perigo: 50-100 mm/dia
                chuva, max1h = rng.uniform(55, 95), rng.uniform(30, 55)
            elif nivel == "PP":                    # Perigo Potencial: até 50 mm/dia (15% não se confirma)
                chuva = rng.uniform(18, 46) if rng.random() > 0.15 else rng.uniform(2, 9)
                max1h = chuva * rng.uniform(0.4, 0.7)
            elif nivel == "BU":                    # Baixa umidade: dia seco
                chuva, max1h = 0.0, 0.0
            else:                                  # sem aviso
                chuva = rng.uniform(0, 6) if rng.random() > 0.4 else 0.0
                max1h = chuva * rng.uniform(0.3, 0.6)
            linhas.append({
                "id_estacao": f"CMD-{m.uf}-{cod}-01", "cod_ibge": cod, "municipio": m.municipio,
                "uf": m.uf, "mesorregiao": m.mesorregiao, "data": d(dia),
                "chuva_acum_24h_mm": round(chuva, 1), "chuva_max_1h_mm": round(max1h, 1),
                "climatologia_nov_mm_dia": clima,
                "anomalia_mm": round(chuva - clima, 1),
                "dia_seco": chuva < 1,
                "nivel_aviso_inmet": NIVEL_TXT[nivel], "id_aviso_inmet": id_aviso,
            })
    df = pd.DataFrame(linhas)
    df["id_aviso_inmet"] = df["id_aviso_inmet"].astype("Int64")
    # dias secos consecutivos até a data (indicador simples de estiagem)
    df["dias_secos_consecutivos"] = (df.groupby("id_estacao")["dia_seco"]
                                       .transform(lambda s: s.groupby((~s).cumsum()).cumsum())).astype(int)
    df["fonte"] = "SINTÉTICO (estrutura inspirada em CEMADEN)"
    return df


def salvar(df: pd.DataFrame, pasta: Path, nome: str, formato: str) -> Path:
    assert len(df) <= 100, f"{nome} passou de 100 linhas ({len(df)})"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.{formato}"
    if formato == "parquet":
        df.to_parquet(caminho, index=False)
    else:
        df.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")
    return caminho


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--saida", type=Path, default=PASTA_SAIDA_PADRAO)
    p.add_argument("--formato", choices=["csv", "parquet"], default="csv")
    a = p.parse_args()

    mun = base_ibge()
    bases = {"ibge_municipios_sintetico": mun,
             "mapbiomas_fogo_sintetico": base_mapbiomas(mun),
             "cemaden_pluviometria_sintetico": base_cemaden(mun)}
    for nome, df in bases.items():
        print(f"{len(df):>3} linhas -> {salvar(df, a.saida, nome, a.formato)}")


if __name__ == "__main__":
    main()
