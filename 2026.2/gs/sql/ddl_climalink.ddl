-- =============================================================================
-- Turma: 1TSCOR  |  Projeto: ClimaLink  |  Grupo: Datalorian
-- Integrantes (ordem alfabética):
--   Gustavo Varadi - RM575461
--   Petrick Mateus - RM575301
-- -----------------------------------------------------------------------------
-- Ordem de execução no Oracle: ddl_climalink.sql > dml_climalink.sql > sql_climalink.sql
-- =============================================================================
-- ddl_climalink.sql  |  DDL gerado pelo Oracle SQL Developer Data Modeler
-- Bloco de limpeza: remove as tabelas do ClimaLink, se existirem, para o script
-- poder ser executado mais de uma vez sem erro (Executar Script / F5).
BEGIN
    FOR t IN (SELECT table_name
                FROM user_tables
               WHERE table_name IN ('T_CLK_MEDICAO_AMBIENTAL', 'T_CLK_AVISO_MESORREGIAO',
                                    'T_CLK_AVISO_INMET', 'T_CLK_MUNICIPIO', 'T_CLK_MESORREGIAO'))
    LOOP
        EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS PURGE';
    END LOOP;
END;
/

-- Gerado por Oracle SQL Developer Data Modeler 24.3.1.351.0831
--   em:        2026-11-18 22:34:00 BRT
--   site:      Oracle Database 21c
--   tipo:      Oracle Database 21c



-- predefined type, no DDL - MDSYS.SDO_GEOMETRY

-- predefined type, no DDL - XMLTYPE

CREATE TABLE t_clk_aviso_inmet 
    ( 
     id_aviso            NUMBER (8)  NOT NULL , 
     ds_evento           VARCHAR2 (40)  NOT NULL , 
     ds_severidade       VARCHAR2 (20)  NOT NULL , 
     nr_nivel_severidade NUMBER (1)  NOT NULL , 
     dt_inicio           DATE  NOT NULL , 
     dt_fim              DATE  NOT NULL , 
     nr_chuva_max_mm_dia NUMBER (5,1) , 
     nr_vento_max_kmh    NUMBER (5,1) , 
     nr_umidade_min_pct  NUMBER (3) , 
     fl_granizo          CHAR (1) DEFAULT 'N'  NOT NULL , 
     ds_aviso            VARCHAR2 (400)  NOT NULL , 
     ds_link             VARCHAR2 (120) , 
     st_aviso            VARCHAR2 (10) DEFAULT 'ATIVO'  NOT NULL , 
     ds_fonte            VARCHAR2 (80) DEFAULT 'INMET - https://apiprevmet3.inmet.gov.br/avisos/rss'  NOT NULL , 
     dt_coleta           DATE DEFAULT SYSDATE  NOT NULL 
    ) 
    LOGGING 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_severidade 
    CHECK (ds_severidade IN ('Grande Perigo', 'Perigo', 'Perigo Potencial')) 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_nivel 
    CHECK (nr_nivel_severidade BETWEEN 1 AND 3) 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_umidade 
    CHECK (nr_umidade_min_pct BETWEEN 0 AND 100) 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_granizo 
    CHECK (fl_granizo IN ('N', 'S')) 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_status 
    CHECK (st_aviso IN ('ATIVO', 'CANCELADO', 'ENCERRADO')) 
;

COMMENT ON TABLE t_clk_aviso_inmet IS 'Avisos meteorológicos REAIS publicados pelo INMET (feed RSS).'
;

COMMENT ON COLUMN t_clk_aviso_inmet.id_aviso IS 'Identificador do aviso no INMET.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.ds_evento IS 'Tipo de evento (Tempestade, Chuvas Intensas, Baixa Umidade...).' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.ds_severidade IS 'Perigo Potencial, Perigo ou Grande Perigo.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.nr_nivel_severidade IS '1 = Perigo Potencial, 2 = Perigo, 3 = Grande Perigo.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.dt_inicio IS 'Início da vigência do aviso.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.dt_fim IS 'Fim da vigência do aviso.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.nr_chuva_max_mm_dia IS 'Chuva máxima prevista (mm/dia), extraída do texto.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.nr_vento_max_kmh IS 'Vento máximo previsto (km/h), extraído do texto.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.nr_umidade_min_pct IS 'Umidade relativa mínima prevista (%).' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.fl_granizo IS 'S = há previsão de granizo, N = não há.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.ds_aviso IS 'Texto do aviso, sem o prefixo padrão do INMET.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.st_aviso IS 'ATIVO, ENCERRADO ou CANCELADO.' 
;

COMMENT ON COLUMN t_clk_aviso_inmet.ds_fonte IS 'Origem do dado (base pública real).' 
;

ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT ck_clk_aviso_periodo 
    CHECK (dt_fim >= dt_inicio)
;
ALTER TABLE t_clk_aviso_inmet 
    ADD CONSTRAINT pk_clk_aviso_inmet PRIMARY KEY ( id_aviso ) ;

CREATE TABLE t_clk_aviso_mesorregiao 
    ( 
     id_aviso       NUMBER (8)  NOT NULL , 
     id_mesorregiao NUMBER (4)  NOT NULL , 
     dt_registro    DATE DEFAULT SYSDATE  NOT NULL 
    ) 
    LOGGING 
;

COMMENT ON TABLE t_clk_aviso_mesorregiao IS 'Associativa: mesorregiões abrangidas por cada aviso do INMET.'
;

COMMENT ON COLUMN t_clk_aviso_mesorregiao.dt_registro IS 'Data em que a associação foi registrada no ClimaLink.' 
;
CREATE INDEX ix_clk_avme_mesorregiao ON t_clk_aviso_mesorregiao 
    ( 
     id_mesorregiao ASC 
    ) 
;

ALTER TABLE t_clk_aviso_mesorregiao 
    ADD CONSTRAINT pk_clk_aviso_mesorregiao PRIMARY KEY ( id_aviso, id_mesorregiao ) ;

CREATE TABLE t_clk_medicao_ambiental 
    ( 
     id_medicao       NUMBER (10)  NOT NULL , 
     cd_ibge          NUMBER (7)  NOT NULL , 
     id_aviso         NUMBER (8) , 
     dt_medicao       DATE  NOT NULL , 
     tp_indicador     VARCHAR2 (20)  NOT NULL , 
     vl_medicao       NUMBER (10,2)  NOT NULL , 
     nm_fonte         VARCHAR2 (10)  NOT NULL , 
     tp_relacao_aviso VARCHAR2 (12) , 
     fl_sintetico     CHAR (1) DEFAULT 'S'  NOT NULL 
    ) 
    LOGGING 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_indicador 
    CHECK (tp_indicador IN ('AREA_QUEIMADA_HA', 'CHUVA_24H_MM', 'CHUVA_MAX_1H_MM', 'FOCOS_CALOR')) 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_valor 
    CHECK (vl_medicao >= 0) 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_fonte 
    CHECK (nm_fonte IN ('CEMADEN', 'MAPBIOMAS')) 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_relacao 
    CHECK (tp_relacao_aviso IN ('CONCOMITANTE', 'POSTERIOR')) 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_sintetico 
    CHECK (fl_sintetico IN ('N', 'S')) 
;

COMMENT ON TABLE t_clk_medicao_ambiental IS 'Medições diárias por município: queimadas (MapBiomas) e chuva (CEMADEN).'
;

COMMENT ON COLUMN t_clk_medicao_ambiental.id_medicao IS 'Identificador da medição.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.cd_ibge IS 'Município onde a medição foi feita.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.id_aviso IS 'Aviso do INMET relacionado à medição (opcional).' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.dt_medicao IS 'Dia da medição.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.tp_indicador IS 'AREA_QUEIMADA_HA, FOCOS_CALOR, CHUVA_24H_MM ou CHUVA_MAX_1H_MM.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.vl_medicao IS 'Valor medido, na unidade do indicador.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.nm_fonte IS 'MAPBIOMAS ou CEMADEN.' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.tp_relacao_aviso IS 'CONCOMITANTE (mesmo dia do aviso) ou POSTERIOR (o aviso veio depois).' 
;

COMMENT ON COLUMN t_clk_medicao_ambiental.fl_sintetico IS 'S = dado sintético de demonstração, N = dado real.' 
;
CREATE INDEX ix_clk_med_aviso ON t_clk_medicao_ambiental 
    ( 
     id_aviso ASC 
    ) 
;
CREATE INDEX ix_clk_med_data_ind ON t_clk_medicao_ambiental 
    ( 
     dt_medicao ASC , 
     tp_indicador ASC 
    ) 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_aviso_relacao 
    CHECK (( id_aviso IS NULL AND tp_relacao_aviso IS NULL ) OR ( id_aviso IS NOT NULL AND tp_relacao_aviso IS NOT NULL ))
;


ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT ck_clk_med_fonte_indicador 
    CHECK (( nm_fonte = 'MAPBIOMAS' AND tp_indicador IN ( 'AREA_QUEIMADA_HA', 'FOCOS_CALOR' ) ) OR ( nm_fonte = 'CEMADEN' AND tp_indicador IN ( 'CHUVA_24H_MM', 'CHUVA_MAX_1H_MM' ) ))
;
ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT pk_clk_medicao_ambiental PRIMARY KEY ( id_medicao ) ;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT un_clk_med_mun_data_ind UNIQUE ( cd_ibge , dt_medicao , tp_indicador ) ;

CREATE TABLE t_clk_mesorregiao 
    ( 
     id_mesorregiao NUMBER (4)  NOT NULL , 
     nm_mesorregiao VARCHAR2 (60)  NOT NULL , 
     sg_uf          CHAR (2)  NOT NULL , 
     nm_regiao      VARCHAR2 (12)  NOT NULL 
    ) 
    LOGGING 
;

ALTER TABLE t_clk_mesorregiao 
    ADD CONSTRAINT ck_clk_meso_uf 
    CHECK (sg_uf IN ('AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO')) 
;

ALTER TABLE t_clk_mesorregiao 
    ADD CONSTRAINT ck_clk_meso_regiao 
    CHECK (nm_regiao IN ('CENTRO-OESTE', 'NORDESTE', 'NORTE', 'SUDESTE', 'SUL')) 
;

COMMENT ON TABLE t_clk_mesorregiao IS 'Mesorregiões geográficas (IBGE), unidade territorial usada pelo INMET nos avisos.'
;

COMMENT ON COLUMN t_clk_mesorregiao.id_mesorregiao IS 'Identificador da mesorregião (chave substituta).' 
;

COMMENT ON COLUMN t_clk_mesorregiao.nm_mesorregiao IS 'Nome da mesorregião, grafado como no feed do INMET.' 
;

COMMENT ON COLUMN t_clk_mesorregiao.sg_uf IS 'Sigla da Unidade da Federação.' 
;

COMMENT ON COLUMN t_clk_mesorregiao.nm_regiao IS 'Grande região do Brasil.' 
;

ALTER TABLE t_clk_mesorregiao 
    ADD CONSTRAINT pk_clk_mesorregiao PRIMARY KEY ( id_mesorregiao ) ;

ALTER TABLE t_clk_mesorregiao 
    ADD CONSTRAINT un_clk_meso_nome_uf UNIQUE ( nm_mesorregiao , sg_uf ) ;

CREATE TABLE t_clk_municipio 
    ( 
     cd_ibge                    NUMBER (7)  NOT NULL , 
     id_mesorregiao             NUMBER (4)  NOT NULL , 
     nm_municipio               VARCHAR2 (60)  NOT NULL , 
     ds_bioma                   VARCHAR2 (15)  NOT NULL , 
     nr_latitude                NUMBER (8,5)  NOT NULL , 
     nr_longitude               NUMBER (8,5)  NOT NULL , 
     nr_populacao               NUMBER (9)  NOT NULL , 
     ds_perfil_territorial      VARCHAR2 (10)  NOT NULL , 
     qt_estacoes_pluviometricas NUMBER (3) DEFAULT 0  NOT NULL 
    ) 
    LOGGING 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_cd_ibge 
    CHECK (cd_ibge BETWEEN 1100000 AND 5399999) 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_bioma 
    CHECK (ds_bioma IN ('AMAZONIA', 'CAATINGA', 'CERRADO', 'MATA ATLANTICA', 'PAMPA', 'PANTANAL')) 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_populacao 
    CHECK (nr_populacao > 0) 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_perfil 
    CHECK (ds_perfil_territorial IN ('MISTO', 'RURAL', 'URBANO')) 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_estacoes 
    CHECK (qt_estacoes_pluviometricas >= 0) 
;

COMMENT ON TABLE t_clk_municipio IS 'Municípios do piloto ClimaLink. Fonte: IBGE (código e nome oficiais).'
;

COMMENT ON COLUMN t_clk_municipio.cd_ibge IS 'Código oficial do município no IBGE (7 dígitos).' 
;

COMMENT ON COLUMN t_clk_municipio.id_mesorregiao IS 'Mesorregião à qual o município pertence.' 
;

COMMENT ON COLUMN t_clk_municipio.nm_municipio IS 'Nome oficial do município.' 
;

COMMENT ON COLUMN t_clk_municipio.ds_bioma IS 'Bioma predominante.' 
;

COMMENT ON COLUMN t_clk_municipio.nr_latitude IS 'Latitude aproximada da sede (graus decimais).' 
;

COMMENT ON COLUMN t_clk_municipio.nr_longitude IS 'Longitude aproximada da sede (graus decimais).' 
;

COMMENT ON COLUMN t_clk_municipio.nr_populacao IS 'População aproximada (ordem de grandeza do Censo 2022).' 
;

COMMENT ON COLUMN t_clk_municipio.ds_perfil_territorial IS 'URBANO, MISTO ou RURAL.' 
;

COMMENT ON COLUMN t_clk_municipio.qt_estacoes_pluviometricas IS 'Quantidade de estações pluviométricas (indicador de viés de cobertura).' 
;
CREATE INDEX ix_clk_mun_mesorregiao ON t_clk_municipio 
    ( 
     id_mesorregiao ASC 
    ) 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT ck_clk_mun_coordenadas 
    CHECK (nr_latitude BETWEEN -34 AND 6 AND nr_longitude BETWEEN -74 AND -34)
;
ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT pk_clk_municipio PRIMARY KEY ( cd_ibge ) ;

ALTER TABLE t_clk_aviso_mesorregiao 
    ADD CONSTRAINT fk_clk_avme_aviso FOREIGN KEY 
    ( 
     id_aviso
    ) 
    REFERENCES t_clk_aviso_inmet 
    ( 
     id_aviso
    ) 
    NOT DEFERRABLE 
;

ALTER TABLE t_clk_aviso_mesorregiao 
    ADD CONSTRAINT fk_clk_avme_mesorregiao FOREIGN KEY 
    ( 
     id_mesorregiao
    ) 
    REFERENCES t_clk_mesorregiao 
    ( 
     id_mesorregiao
    ) 
    NOT DEFERRABLE 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT fk_clk_med_aviso FOREIGN KEY 
    ( 
     id_aviso
    ) 
    REFERENCES t_clk_aviso_inmet 
    ( 
     id_aviso
    ) 
    NOT DEFERRABLE 
;

ALTER TABLE t_clk_medicao_ambiental 
    ADD CONSTRAINT fk_clk_med_municipio FOREIGN KEY 
    ( 
     cd_ibge
    ) 
    REFERENCES t_clk_municipio 
    ( 
     cd_ibge
    ) 
    NOT DEFERRABLE 
;

ALTER TABLE t_clk_municipio 
    ADD CONSTRAINT fk_clk_mun_mesorregiao FOREIGN KEY 
    ( 
     id_mesorregiao
    ) 
    REFERENCES t_clk_mesorregiao 
    ( 
     id_mesorregiao
    ) 
    NOT DEFERRABLE 
;



-- Relatório do Resumo do Oracle SQL Developer Data Modeler: 
-- 
-- CREATE TABLE                             5
-- CREATE INDEX                             4
-- ALTER TABLE                             33
-- CREATE VIEW                              0
-- ALTER VIEW                               0
-- CREATE PACKAGE                           0
-- CREATE PACKAGE BODY                      0
-- CREATE PROCEDURE                         0
-- CREATE FUNCTION                          0
-- CREATE TRIGGER                           0
-- ALTER TRIGGER                            0
-- CREATE COLLECTION TYPE                   0
-- CREATE STRUCTURED TYPE                   0
-- CREATE STRUCTURED TYPE BODY              0
-- CREATE CLUSTER                           0
-- CREATE CONTEXT                           0
-- CREATE DATABASE                          0
-- CREATE DIMENSION                         0
-- CREATE DIRECTORY                         0
-- CREATE DISK GROUP                        0
-- CREATE ROLE                              0
-- CREATE ROLLBACK SEGMENT                  0
-- CREATE SEQUENCE                          0
-- CREATE MATERIALIZED VIEW                 0
-- CREATE MATERIALIZED VIEW LOG             0
-- CREATE SYNONYM                           0
-- CREATE TABLESPACE                        0
-- CREATE USER                              0
-- 
-- DROP TABLESPACE                          0
-- DROP DATABASE                            0
-- 
-- REDACTION POLICY                         0
-- 
-- ORDS DROP SCHEMA                         0
-- ORDS ENABLE SCHEMA                       0
-- ORDS ENABLE OBJECT                       0
-- 
-- ERRORS                                   0
-- WARNINGS                                 0
