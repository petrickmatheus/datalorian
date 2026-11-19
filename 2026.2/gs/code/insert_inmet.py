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
Base pública: avisos meteorológicos do INMET
              https://apiprevmet3.inmet.gov.br/avisos/rss  (baixada em 18/11/2026)
Entrada:      ./2026.2/gs/data/inmet/inmet_avisos.csv   (gerado por ingestion_inmet.py)
Saída:        ./2026.2/gs/data/sql/insert_t_clk_aviso_inmet.sql

Uso:  python insert_sql_inmet.py

Só usa a biblioteca padrão do Python (csv, pathlib, datetime).
"""

import csv
from datetime import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# Etapa 1 — Configuração: caminhos RELATIVOS e regras do recorte do projeto
# -----------------------------------------------------------------------------
PATH = Path(__file__).parent.parent          # pasta única de dados do projeto
ARQUIVO_CSV = PATH / "data" / "inmet" / "inmet_avisos.csv"
ARQUIVO_SQL = PATH / "sql" / "insert_t_clk_aviso_inmet.sql"

FONTE = "INMET - https://apiprevmet3.inmet.gov.br/avisos/rss"
TAMANHO_MAX_DS_AVISO = 400                       # tamanho da coluna ds_aviso (VARCHAR2(400))

# Recorte temporal do piloto: avisos que começam entre 09/11 e 18/11/2026
PERIODO_INICIO = datetime(2026, 11, 9, 0, 0)
PERIODO_FIM = datetime(2026, 11, 18, 23, 59)

# Recorte territorial do piloto: mesorregiões (como escritas pelo INMET) por UF.
# Dicionário UF -> lista de mesorregiões; é a mesma lista carregada em T_CLK_MESORREGIAO.
RECORTE_PILOTO = {
    "BA": ["Extremo Oeste Baiano", "Sul Baiano"],
    "CE": ["Centro-Sul Cearense", "Sertões Cearenses", "Sul Cearense"],
    "GO": ["Sul Goiano"],
    "MA": ["Oeste Maranhense", "Sul Maranhense"],
    "MG": ["Noroeste de Minas", "Norte de Minas"],
    "MT": ["Nordeste Mato-grossense", "Norte Mato-grossense"],
    "PA": ["Sudeste Paraense", "Sudoeste Paraense"],
    "PE": ["São Francisco Pernambucano", "Sertão Pernambucano"],
    "PI": ["Centro-Norte Piauiense", "Sudeste Piauiense", "Sudoeste Piauiense"],
    "PR": ["Centro-Sul Paranaense", "Oeste Paranaense"],
    "RS": ["Centro Ocidental Rio-grandense", "Metropolitana de Porto Alegre", "Noroeste Rio-grandense"],
    "SC": ["Oeste Catarinense", "Serrana"],
    "TO": ["Ocidental do Tocantins", "Oriental do Tocantins"],
}
# conjunto com todas as mesorregiões do piloto (busca rápida)
MESORREGIOES_PILOTO = {meso for lista in RECORTE_PILOTO.values() for meso in lista}

# Severidades aceitas pela restrição CHECK da tabela e o nível correspondente
NIVEL_POR_SEVERIDADE = {"Perigo Potencial": 1, "Perigo": 2, "Grande Perigo": 3}

# Campos que não podem estar vazios (colunas NOT NULL da tabela)
CAMPOS_OBRIGATORIOS = ["id_aviso", "evento", "severidade", "inicio", "fim", "descricao"]


# -----------------------------------------------------------------------------
# Etapa 2 — Funções auxiliares de conversão para SQL Oracle
# -----------------------------------------------------------------------------
def texto_sql(valor):
    """Texto entre aspas simples. Aspas internas são dobradas para o Oracle
    (ex.: Olho d'Água das Flores -> 'Olho d''Água das Flores')."""
    if valor is None or valor.strip() == "":
        return "NULL"
    return "'" + valor.strip().replace("'", "''") + "'"


def numero_sql(valor, inteiro=False):
    """Número no formato do Oracle (ponto decimal) ou NULL se vazio."""
    if valor is None or valor.strip() == "":
        return "NULL"
    numero = float(valor)
    if inteiro or numero.is_integer():
        return str(int(numero))
    return str(numero)


def data_sql(valor):
    """Converte '2026-11-16 09:05:00' em TO_DATE('2026-11-16 09:05', 'YYYY-MM-DD HH24:MI')."""
    data = datetime.strptime(valor.strip()[:16], "%Y-%m-%d %H:%M")
    return f"TO_DATE('{data:%Y-%m-%d %H:%M}', 'YYYY-MM-DD HH24:MI')"


def flag_sql(valor):
    """Converte True/False do CSV em 'S'/'N' (restrição CHECK fl_granizo)."""
    if valor.strip().lower() in ("true", "1", "s", "sim"):
        return "'S'"
    return "'N'"


# -----------------------------------------------------------------------------
# Etapa 3 — Leitura do CSV e tratamento de cada linha
# -----------------------------------------------------------------------------
def ler_e_tratar(caminho_csv):
    """Percorre o CSV, valida cada linha e separa registros aceitos e ignorados."""
    aceitos = []              # lista de dicionários prontos para virar INSERT
    ignorados = {}            # motivo -> lista de ids ignorados
    ids_vistos = set()        # para não gerar o mesmo aviso duas vezes

    with open(caminho_csv, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for numero_linha, linha in enumerate(leitor, start=2):     # linha 1 = cabeçalho
            id_aviso = (linha.get("id_aviso") or "").strip() or f"linha {numero_linha}"

            # 3.1 Campos obrigatórios vazios -> ignora
            vazios = [c for c in CAMPOS_OBRIGATORIOS if not (linha.get(c) or "").strip()]
            if vazios:
                motivo = "campo obrigatório vazio"
            # 3.2 Aviso repetido no CSV -> ignora
            elif id_aviso in ids_vistos:
                motivo = "aviso duplicado no CSV"
            # 3.3 Severidade que a tabela não aceita -> ignora
            elif linha["severidade"].strip() not in NIVEL_POR_SEVERIDADE:
                motivo = "severidade desconhecida"
            # 3.4 Fora do período do piloto -> ignora
            elif not (PERIODO_INICIO <= datetime.strptime(linha["inicio"][:16], "%Y-%m-%d %H:%M") <= PERIODO_FIM):
                motivo = "fora do período do piloto (09 a 18/11/2026)"
            # 3.5 Nenhuma mesorregião do aviso pertence ao piloto -> ignora
            elif not any(area.strip() in MESORREGIOES_PILOTO for area in (linha.get("areas") or "").split("|")):
                motivo = "fora do recorte territorial do piloto"
            else:
                motivo = None

            if motivo:
                ignorados.setdefault(motivo, []).append(id_aviso)
                continue

            # 3.6 Linha válida: ajusta o texto ao tamanho da coluna e guarda
            descricao = linha["descricao"].strip()
            if len(descricao) > TAMANHO_MAX_DS_AVISO:
                descricao = descricao[:TAMANHO_MAX_DS_AVISO - 3] + "..."

            ids_vistos.add(id_aviso)
            aceitos.append({
                "id_aviso": numero_sql(linha["id_aviso"], inteiro=True),
                "ds_evento": texto_sql(linha["evento"]),
                "ds_severidade": texto_sql(linha["severidade"]),
                "nr_nivel_severidade": str(NIVEL_POR_SEVERIDADE[linha["severidade"].strip()]),
                "dt_inicio": data_sql(linha["inicio"]),
                "dt_fim": data_sql(linha["fim"]),
                "nr_chuva_max_mm_dia": numero_sql(linha.get("chuva_mm_dia_max")),
                "nr_vento_max_kmh": numero_sql(linha.get("vento_kmh_max")),
                "nr_umidade_min_pct": numero_sql(linha.get("umidade_pct_min"), inteiro=True),
                "fl_granizo": flag_sql(linha.get("granizo") or ""),
                "ds_aviso": texto_sql(descricao),
                "ds_link": texto_sql(linha.get("link_grafico")),
                "st_aviso": "'ATIVO'",
                "ds_fonte": texto_sql(FONTE),
                "dt_coleta": data_sql(linha["coletado_em"]) if (linha.get("coletado_em") or "").strip() else "SYSDATE",
            })
    return aceitos, ignorados


# -----------------------------------------------------------------------------
# Etapa 4 — Montagem dos comandos INSERT
# -----------------------------------------------------------------------------
def montar_inserts(registros):
    comandos = []
    for registro in registros:
        colunas = ", ".join(registro.keys())
        valores = ", ".join(registro.values())
        comandos.append(f"INSERT INTO t_clk_aviso_inmet ({colunas}) VALUES ({valores});")
    return comandos


# -----------------------------------------------------------------------------
# Etapa 5 — Gravação do arquivo .sql
# -----------------------------------------------------------------------------
def gravar_sql(comandos, caminho_sql):
    caminho_sql.parent.mkdir(parents=True, exist_ok=True)
    cabecalho = [
        "-- =============================================================================",
        "-- Turma: 1TSCOR  |  Projeto: ClimaLink  |  Grupo: Datalorian",
        "-- Integrantes (ordem alfabética):",
        "--   Gustavo Varadi - RM575461",
        "--   Petrick Mateus - RM575301",
        "-- -----------------------------------------------------------------------------",
        "-- insert_t_clk_aviso_inmet.sql  |  GERADO AUTOMATICAMENTE por csv_to_sql_inmet.py",
        f"-- Gerado em: {datetime.now():%d/%m/%Y %H:%M}",
        f"-- Base pública: {FONTE} (baixada em 18/11/2026)",
        f"-- Origem: {ARQUIVO_CSV.as_posix()}",
        "-- Executar depois do DDL. O mesmo bloco está na seção 3 do dml_climalink.sql.",
        "-- =============================================================================",
        "SET DEFINE OFF;",
        "",
    ]
    with open(caminho_sql, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(cabecalho + comandos + ["", "COMMIT;", ""]))


# -----------------------------------------------------------------------------
# Etapa 6 — Execução e resumo
# -----------------------------------------------------------------------------
def main():
    if not ARQUIVO_CSV.exists():
        print(f"CSV não encontrado: {ARQUIVO_CSV}")
        print(f"Pasta atual: {Path.cwd()}")
        print("Execute a partir da raiz do repositório ou rode antes o ingestion_inmet.py.")
        return

    registros, ignorados = ler_e_tratar(ARQUIVO_CSV)
    comandos = montar_inserts(registros)
    gravar_sql(comandos, ARQUIVO_SQL)

    total_ignorados = sum(len(ids) for ids in ignorados.values())
    print(f"Arquivo gerado: {ARQUIVO_SQL}")
    print(f"Registros gerados (INSERT): {len(comandos)}")
    print(f"Registros ignorados:        {total_ignorados}")
    for motivo, ids in ignorados.items():
        print(f"  - {motivo}: {len(ids)} ({', '.join(ids)})")


if __name__ == "__main__":
    main()
