-- =============================================================================
-- Turma: 1TSCOR  |  Projeto: ClimaLink  |  Grupo: Datalorian
-- Integrantes (ordem alfabética):
--   Gustavo Varadi - RM575461
--   Petrick Mateus - RM575301
-- -----------------------------------------------------------------------------
-- Ordem de execução no Oracle: ddl_climalink.sql > dml_climalink.sql > sql_climalink.sql
-- =============================================================================
-- =============================================================================
-- ClimaLink - Global Solutions 2026 - 1TSCOR
-- sql_climalink.sql  |  consultas (executar depois do DDL e do DML)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Pergunta 1 (hipótese H1): Quais municípios queimaram mais de 1.000 ha entre
-- 01/11 e 08/11/2026 e, depois disso, entraram em aviso de TEMPESTADE de nível
-- Perigo ou superior? Quantos dias se passaram entre a última queimada e o aviso?
-- -----------------------------------------------------------------------------
SELECT q.nm_municipio,
       q.sg_uf,
       q.nm_mesorregiao,
       q.area_queimada_ha,
       q.dt_ultima_queimada,
       MIN(av.dt_inicio)                              AS dt_primeiro_aviso_perigo,
       TRUNC(MIN(av.dt_inicio)) - q.dt_ultima_queimada AS defasagem_dias
  FROM (SELECT mu.cd_ibge,
               mu.nm_municipio,
               me.sg_uf,
               me.id_mesorregiao,
               me.nm_mesorregiao,
               SUM(md.vl_medicao) AS area_queimada_ha,
               MAX(md.dt_medicao) AS dt_ultima_queimada
          FROM t_clk_medicao_ambiental md
          JOIN t_clk_municipio mu   ON mu.cd_ibge = md.cd_ibge
          JOIN t_clk_mesorregiao me ON me.id_mesorregiao = mu.id_mesorregiao
         WHERE md.tp_indicador = 'AREA_QUEIMADA_HA'
           AND md.dt_medicao BETWEEN DATE '2026-11-01' AND DATE '2026-11-08'
         GROUP BY mu.cd_ibge, mu.nm_municipio, me.sg_uf, me.id_mesorregiao, me.nm_mesorregiao
        HAVING SUM(md.vl_medicao) > 1000) q
  JOIN t_clk_aviso_mesorregiao am ON am.id_mesorregiao = q.id_mesorregiao
  JOIN t_clk_aviso_inmet av       ON av.id_aviso = am.id_aviso
 WHERE av.ds_evento LIKE 'Tempestade%'
   AND av.nr_nivel_severidade >= 2
   AND av.dt_inicio > q.dt_ultima_queimada
 GROUP BY q.nm_municipio, q.sg_uf, q.nm_mesorregiao, q.area_queimada_ha, q.dt_ultima_queimada
 ORDER BY q.area_queimada_ha DESC;


-- -----------------------------------------------------------------------------
-- Pergunta 2: Quais estações do CEMADEN no Cerrado (TO, BA ou MA) ou na região
-- Sul registraram mais de 50 mm de chuva em 24 horas em dias com aviso de nível
-- Perigo ou Grande Perigo do INMET? A chuva ficou dentro do máximo previsto?
-- -----------------------------------------------------------------------------
SELECT mu.nm_municipio,
       me.sg_uf,
       md.dt_medicao,
       md.vl_medicao              AS chuva_24h_mm,
       av.id_aviso,
       av.ds_evento,
       av.ds_severidade,
       av.nr_chuva_max_mm_dia     AS chuva_max_prevista_mm,
       CASE
           WHEN md.vl_medicao <= av.nr_chuva_max_mm_dia THEN 'DENTRO DO PREVISTO'
           ELSE 'ACIMA DO PREVISTO'
       END                        AS avaliacao
  FROM t_clk_medicao_ambiental md
  JOIN t_clk_municipio mu   ON mu.cd_ibge = md.cd_ibge
  JOIN t_clk_mesorregiao me ON me.id_mesorregiao = mu.id_mesorregiao
  JOIN t_clk_aviso_inmet av ON av.id_aviso = md.id_aviso
 WHERE md.nm_fonte = 'CEMADEN'
   AND md.tp_indicador = 'CHUVA_24H_MM'
   AND md.vl_medicao > 50
   AND av.ds_severidade IN ( 'Perigo', 'Grande Perigo' )
   AND ( me.sg_uf IN ( 'TO', 'BA', 'MA' ) OR me.nm_regiao = 'SUL' )
 ORDER BY md.vl_medicao DESC, md.dt_medicao;


-- -----------------------------------------------------------------------------
-- Pergunta 3 (prioridade de monitoramento e viés de cobertura): Quais municípios
-- RURAIS ou MISTOS, com no máximo 3 estações pluviométricas, estão em áreas com
-- aviso ainda ATIVO ou com aviso de BAIXA UMIDADE, e quanto já queimaram?
-- -----------------------------------------------------------------------------
SELECT mu.nm_municipio,
       me.sg_uf,
       mu.ds_perfil_territorial,
       mu.qt_estacoes_pluviometricas,
       mu.nr_populacao,
       av.id_aviso,
       av.ds_evento,
       av.ds_severidade,
       av.st_aviso,
       COALESCE(SUM(md.vl_medicao), 0) AS area_queimada_ha
  FROM t_clk_municipio mu
  JOIN t_clk_mesorregiao me       ON me.id_mesorregiao = mu.id_mesorregiao
  JOIN t_clk_aviso_mesorregiao am ON am.id_mesorregiao = me.id_mesorregiao
  JOIN t_clk_aviso_inmet av       ON av.id_aviso = am.id_aviso
  LEFT JOIN t_clk_medicao_ambiental md
         ON md.cd_ibge = mu.cd_ibge
        AND md.tp_indicador = 'AREA_QUEIMADA_HA'
 WHERE mu.ds_perfil_territorial IN ( 'RURAL', 'MISTO' )
   AND mu.qt_estacoes_pluviometricas <= 3
   AND ( av.st_aviso = 'ATIVO' OR av.ds_evento LIKE '%Umidade%' )
 GROUP BY mu.nm_municipio, me.sg_uf, mu.ds_perfil_territorial, mu.qt_estacoes_pluviometricas,
          mu.nr_populacao, av.id_aviso, av.ds_evento, av.ds_severidade, av.st_aviso,
          av.nr_nivel_severidade
 ORDER BY av.nr_nivel_severidade DESC, area_queimada_ha DESC, mu.nr_populacao DESC;
