
## inventar_SpcHidr.sp_razon_lixiviacion
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
26:     v_flujos_oxido_unpivot   → fecha_registro, parcela_numero, caudal (m³/h)
27:     v_flujos_sulfuro_unpivot → fecha_registro, parcela_numero, caudal (m³/h)
28:     v_drena_oxido_unpivot    → fecha_registro, parcela_numero, cu_pp (g/L)
29:     v_drena_sulfuro_unpivot  → fecha_registro, parcela_numero, cu_pp (g/L)
30:     recuperaciones_pad       → Recuperacion_parcela acumulada (%)
31:     parcela_campana_cinetica → Rmax, k1, k2, A
134:         dia_ciclo       INT,
135:         caudal_m3_dia   FLOAT,
136:         cu_pp           FLOAT,
137:         rec_acum_pct    FLOAT
138:     );
140:     IF @pad_id = 1  /* PAD OXIDO: parcela_id 1..32 */
141:     BEGIN
142:         INSERT INTO #serie (fecha_registro, dia_ciclo, caudal_m3_dia, cu_pp)
143:         SELECT
144:             CAST(f.fecha_registro AS DATE)                  AS fecha_registro,
147:                      CAST(f.fecha_registro AS DATE)) + 1    AS dia_ciclo,
148:             ISNULL(f.caudal, 0) * @factor_caudal            AS caudal_m3_dia,
149:             d.cu_pp
150:         FROM inventar_SpcHidr.v_flujos_oxido_unpivot f
151:         LEFT JOIN inventar_SpcHidr.v_drena_oxido_unpivot d
159:     ELSE  /* PAD SULFURO: parcela_id 33..60, numero 1..28 */
160:     BEGIN
161:         INSERT INTO #serie (fecha_registro, dia_ciclo, caudal_m3_dia, cu_pp)
162:         SELECT
163:             CAST(f.fecha_registro AS DATE),
165:                      CAST(f.fecha_registro AS DATE)) + 1,
166:             ISNULL(f.caudal, 0) * @factor_caudal,
167:             d.cu_pp
168:         FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot f
169:         LEFT JOIN inventar_SpcHidr.v_drena_sulfuro_unpivot d
224:
225:         /* Concentración Cu drenaje (g/L) */
226:         ROUND(s.cu_pp, 4)                                  AS cu_drenaje_gl,
227:
228:         /* Cu extraído (ton/día) = caudal_m3 × cu_pp(g/L) / 1000 */
229:         ROUND(
230:             s.caudal_m3_dia * ISNULL(s.cu_pp, 0) / 1000.0,
231:         4)                                                  AS cu_diario_ton,
232:
233:         /* Cu acumulado (ton) — reinicia por campaña */
234:         ROUND(
235:             SUM(s.caudal_m3_dia * ISNULL(s.cu_pp, 0) / 1000.0)
236:                 OVER (ORDER BY s.dia_ciclo
237:                       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
```


## inventar_SpcHidr.sp_flujo_riego_drenaje
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
17:   v_flujos_oxido_unpivot   → id_flujo_real, fecha_registro, parcela_numero, caudal
18:   v_flujos_sulfuro_unpivot → id_flujo_real, fecha_registro, parcela_numero, caudal
19:   v_drena_oxido_unpivot    → id_registro,   fecha_registro, parcela_numero, cu_pp
20:   v_drena_sulfuro_unpivot  → id_registro,   fecha_registro, parcela_numero, cu_pp
21:
22:   LÓGICA DE VINCULACIÓN:
146:         parcela_numero  INT,
147:         campana_id      INT,
148:         cu_pp           FLOAT
149:     );
150:
157:         p.numero,
158:         cpc.campana_id,
159:         d.cu_pp
160:     FROM inventar_SpcHidr.v_drena_oxido_unpivot d
161:     INNER JOIN inventar_SpcHidr.parcela p
181:         p.numero,
182:         cpc.campana_id,
183:         d.cu_pp
184:     FROM inventar_SpcHidr.v_drena_sulfuro_unpivot d
185:     INNER JOIN inventar_SpcHidr.parcela p
229:
230:         /* Concentración drenaje Cu (g/L) */
231:         ROUND(AVG(d.cu_pp), 4)                              AS cu_drenaje_prom_gl,
232:         ROUND(MAX(d.cu_pp), 4)                              AS cu_drenaje_max_gl,
233:         ROUND(MIN(d.cu_pp), 4)                              AS cu_drenaje_min_gl,
234:
235:         /* Contexto campaña/parcela desde campana_parcela_control */
```


## inventar_SpcHidr.vw_riego_oxido_refino_base
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
5:     CAST(fecha_registro AS DATE) AS fecha,
6:     fecha_registro,
7:     refino_cu_pp AS cu_pp,
8:     refino_h_p   AS h_p,
9:     refino_ph    AS ph,
```


## inventar_SpcHidr.vw_riego_sulfuro_refino_base
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
5:     CAST(fecha_registro AS DATE) AS fecha,
6:     fecha_registro,
7:     refino_cu_pp AS cu_pp,
8:     refino_h_p   AS h_p,
9:     refino_ph    AS ph,
```


## inventar_SpcHidr.sp_calcular_balance_flujos_modelo6_v2
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
3798:     SELECT
3799:         CAST(c.fecha_registro AS date) AS fecha,
3800:         COALESCE(c.dump_dpls_cu, 0) AS cu_g_l
3801:     FROM inventar_SpcHidr.conc_cu c
3802:     WHERE CAST(c.fecha_registro AS date)
3806:     SELECT
3807:         f.flujo_m3_dia,
3808:         c.cu_g_l
3809:     FROM flujo_diario f
3810:     INNER JOIN cu_diario c
3821:     COALESCE(SUM(flujo_m3_dia), 0),
3822:     COALESCE(
3823:         SUM(flujo_m3_dia * cu_g_l)
3824:         / NULLIF(SUM(flujo_m3_dia), 0),
3825:         0
3853:     SELECT
3854:         CAST(c.fecha_registro AS date) AS fecha,
3855:         COALESCE(c.dump_feed_cu, 0) AS cu_g_l
3856:     FROM inventar_SpcHidr.conc_cu c
3857:     WHERE CAST(c.fecha_registro AS date)
3861:     SELECT
3862:         f.flujo_m3_dia,
3863:         c.cu_g_l
3864:     FROM flujo_diario f
3865:     INNER JOIN cu_diario c
3876:     COALESCE(SUM(flujo_m3_dia), 0),
3877:     COALESCE(
3878:         SUM(flujo_m3_dia * cu_g_l)
3879:         / NULLIF(SUM(flujo_m3_dia), 0),
3880:         0
4719:             ELSE NULL
4720:
4721:         END AS Cu_g_L
4722:
4723:     FROM Riego_Base AS r
4739:             CASE
4740:                 WHEN Volumen > 0
4741:                  AND Cu_g_L IS NULL
4742:                     THEN 1
4743:                 ELSE 0
4748:         (
4749:             CASE
4750:                 WHEN Cu_g_L IS NOT NULL
4751:                 THEN Volumen * Cu_g_L
4752:             END
4753:         ) AS Suma_Cu_Ponderada,
4756:         (
4757:             CASE
4758:                 WHEN Cu_g_L IS NOT NULL
4759:                 THEN Volumen
4760:             END
4951:        - Se elimina el antiguo factor * 0.95 de F44.
4952:        - Se mantiene sin cambios la fuente actual de Ley Cu:
4953:              riego_concentrados_oxido.ingreso_piscina_pls_cu_pp
4954:        - El flujo diario bruto sigue utilizandose solamente para
4955:          ponderar la concentracion.
5006:     SELECT
5007:         CAST(p.fecha_registro AS date) AS Fecha,
5008:         NULLIF(p.ingreso_piscina_pls_cu_pp, 0) AS Cu_g_L
5009:
5010:     FROM inventar_SpcHidr.riego_concentrados_oxido AS p
5022:             (
5023:                 CASE
5024:                     WHEN l.Cu_g_L IS NOT NULL
5025:                     THEN f.Flujo_Base_Dia * l.Cu_g_L
5026:                 END
5027:             )
5032:                 (
5033:                     CASE
5034:                         WHEN l.Cu_g_L IS NOT NULL
5035:                         THEN f.Flujo_Base_Dia
5036:                     END
5127:     SELECT
5128:         CAST(p.fecha_registro AS date) AS fecha,
5129:         NULLIF(p.bleed_cu_pp, 0) AS cu_g_l
5130:     FROM inventar_SpcHidr.riego_concentrados_sulfuro p
5131:     WHERE CAST(p.fecha_registro AS date)
5135:     SELECT
5136:         f.flujo_ton_dia,
5137:         l.cu_g_l
5138:     FROM flujo_f48 f
5139:     INNER JOIN ley_f48 l
5153:         SUM(
5154:             CASE
5155:                 WHEN cu_g_l IS NOT NULL
5156:                 THEN flujo_ton_dia * cu_g_l
5157:             END
5158:         )
5161:             SUM(
5162:                 CASE
5163:                     WHEN cu_g_l IS NOT NULL
5164:                     THEN flujo_ton_dia
5165:                 END
5293:     SELECT
5294:         CAST(c.fecha_registro AS date) AS fecha,
5295:         COALESCE(c.oxidos_refino_cu, 0) AS cu_g_l
5296:     FROM inventar_SpcHidr.conc_cu c
5297:     WHERE CAST(c.fecha_registro AS date)
5301:     SELECT
5302:         f.flujo_m3_dia,
5303:         c.cu_g_l
5304:     FROM flujo_diario f
5305:     INNER JOIN cu_diario c
5316:     COALESCE(SUM(flujo_m3_dia), 0),
5317:     COALESCE(
5318:         SUM(flujo_m3_dia * cu_g_l)
5319:         / NULLIF(SUM(flujo_m3_dia), 0),
5320:         0
5420: ),
5421:     ley_inicial AS (
5422:         SELECT TOP 1 COALESCE(c.sulfuros_refino_cu, 0) AS Ley_i_gL
5423:         FROM inventar_SpcHidr.conc_cu c
5424:         WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
5428: (
5429:     SELECT TOP 1
5430:         COALESCE(c.sulfuros_refino_cu, 0) AS Ley_f_gL
5431:
5432:     FROM inventar_SpcHidr.conc_cu c
5440:         'F76_SULF',
5441:         vi.TMS_Inicial,
5442:         li.Ley_i_gL / 10.0,
5443:         vf.TMS_Final,
5444:         lf.Ley_f_gL / 10.0,
5445:         (vf.TMS_Final - vi.TMS_Inicial),
5446:         COALESCE((((vf.TMS_Final * lf.Ley_f_gL) - (vi.TMS_Inicial * li.Ley_i_gL)) / NULLIF((vf.TMS_Final - vi.TMS_Inicial),0)) / 10.0, 0)
5447:     FROM volumen_inicial vi
5448:     CROSS JOIN volumen_final vf
5527: ley_inicial AS (
5528:     SELECT TOP 1
5529:         COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_i_gL
5530:     FROM inventar_SpcHidr.conc_cu c
5531:     WHERE CAST(c.fecha_registro AS date)
5536: (
5537:     SELECT TOP 1
5538:         COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_f_gL
5539:
5540:     FROM inventar_SpcHidr.conc_cu c
5558:
5559:     vi.TMS_Inicial,
5560:     li.Ley_i_gL / 10.0,
5561:
5562:     vf.TMS_Final,
5563:     lf.Ley_f_gL / 10.0,
5564:
5565:     vf.TMS_Final - vi.TMS_Inicial,
5567:     COALESCE(
5568:         (
5569:             (vf.TMS_Final * lf.Ley_f_gL)
5570:           - (vi.TMS_Inicial * li.Ley_i_gL)
5571:         )
5572:         /
5751:
5752:             ORDER BY c.fecha_registro DESC
5753:         ) AS Ley_i_gL,
5754:
5755:
5764:
5765:             ORDER BY c.fecha_registro DESC
5766:         ) AS Ley_f_gL
5767: )
5768:
5782:
5783:     TMS_Inicial,
5784:     Ley_i_gL / 10.0,
5785:
5786:     TMS_Final,
5787:     Ley_f_gL / 10.0,
5788:
5789:     CASE
5799:         WHEN TMS_Inicial IS NULL
5800:           OR TMS_Final IS NULL
5801:           OR Ley_i_gL IS NULL
5802:           OR Ley_f_gL IS NULL
5803:             THEN NULL
5804:
5808:         ELSE
5809:             (
5810:                 (TMS_Final   * Ley_f_gL)
5811:               - (TMS_Inicial * Ley_i_gL)
5812:             )
5813:             /
5913:
5914:             WHERE CAST(c.fecha_registro AS date) = @fecha_inicio
5915:         ) AS Ley_i_gL,
5916:
5917:
5926:
5927:             WHERE CAST(c.fecha_registro AS date) = @ff_mas_1
5928:         ) AS Ley_f_gL
5929: )
5930:
5944:
5945:     TMS_Inicial,
5946:     Ley_i_gL / 10.0,
5947:
5948:     TMS_Final,
5949:     Ley_f_gL / 10.0,
5950:
5951:     CASE
5961:         WHEN TMS_Inicial IS NULL
5962:           OR TMS_Final IS NULL
5963:           OR Ley_i_gL IS NULL
5964:           OR Ley_f_gL IS NULL
5965:             THEN NULL
5966:
5972:                 (
5973:                     TMS_Final
5974:                     * Ley_f_gL / 10.0
5975:                 )
5976:                 -
5977:                 (
5978:                     TMS_Inicial
5979:                     * Ley_i_gL / 10.0
5980:                 )
5981:             )
6318:
6319:             ORDER BY c.fecha_registro DESC
6320:         ) AS Ley_i_gL,
6321:
6322:
6330:
6331:             ORDER BY c.fecha_registro DESC
6332:         ) AS Ley_f_gL
6333: )
6334:
6348:
6349:     TMS_Inicial,
6350:     Ley_i_gL / 10.0,
6351:
6352:     TMS_Final,
6353:     Ley_f_gL / 10.0,
6354:
6355:     CASE
6365:         WHEN TMS_Inicial IS NULL
6366:           OR TMS_Final IS NULL
6367:           OR Ley_i_gL IS NULL
6368:           OR Ley_f_gL IS NULL
6369:             THEN NULL
6370:
6374:         ELSE
6375:             (
6376:                 Ley_i_gL + Ley_f_gL
6377:             )
6378:             / 2.0
6611:
6612:             ORDER BY c.fecha_registro DESC
6613:         ) AS Ley_i_gL,
6614:
6615:
6623:
6624:             ORDER BY c.fecha_registro DESC
6625:         ) AS Ley_f_gL
6626: )
6627:
6641:
6642:     TMS_Inicial,
6643:     Ley_i_gL / 10.0,
6644:
6645:     TMS_Final,
6646:     Ley_f_gL / 10.0,
6647:
6648:     CASE
6658:         WHEN TMS_Inicial IS NULL
6659:           OR TMS_Final IS NULL
6660:           OR Ley_i_gL IS NULL
6661:           OR Ley_f_gL IS NULL
6662:             THEN NULL
6663:
6667:         ELSE
6668:             (
6669:                 (TMS_Final   * Ley_f_gL)
6670:               - (TMS_Inicial * Ley_i_gL)
6671:             )
6672:             /
6834:
6835:             ORDER BY c.fecha_registro DESC
6836:         ) AS Ley_i_gL,
6837:
6838:
6846:
6847:             ORDER BY c.fecha_registro DESC
6848:         ) AS Ley_f_gL
6849: )
6850:
6864:
6865:     TMS_Inicial,
6866:     Ley_i_gL / 10.0,
6867:
6868:     TMS_Final,
6869:     Ley_f_gL / 10.0,
6870:
6871:     CASE
6881:         WHEN TMS_Inicial IS NULL
6882:           OR TMS_Final IS NULL
6883:           OR Ley_i_gL IS NULL
6884:           OR Ley_f_gL IS NULL
6885:             THEN NULL
6886:
6890:         ELSE
6891:             (
6892:                 (TMS_Final   * Ley_f_gL)
6893:               - (TMS_Inicial * Ley_i_gL)
6894:             )
6895:             /
7410:             AVG(
7411:                 (
7412:                     COALESCE(s.ep_ecc1_gl, 0) +
7413:                     COALESCE(s.ep_ecc2_gl, 0) +
7414:                     COALESCE(s.ep_ecc3_gl, 0)
7415:                 ) / 3.0
7416:             ),
7453:             AVG(
7454:                 (
7455:                     COALESCE(s.ep_ecc1_gl, 0) +
7456:                     COALESCE(s.ep_ecc2_gl, 0) +
7457:                     COALESCE(s.ep_ecc3_gl, 0)
7458:                 ) / 3.0
7459:             ),
7487:             AVG(
7488:                 (
7489:                     COALESCE(s.ep_ecc1_gl, 0) +
7490:                     COALESCE(s.ep_ecc2_gl, 0) +
7491:                     COALESCE(s.ep_ecc3_gl, 0)
7492:                 ) / 3.0
7493:             ),
7521:             AVG(
7522:                 (
7523:                     COALESCE(s.ep_ecc1_gl, 0) +
7524:                     COALESCE(s.ep_ecc2_gl, 0) +
7525:                     COALESCE(s.ep_ecc3_gl, 0)
7526:                 ) / 3.0
7527:             ),
7557: --
7558: -- Concentraciones:
7559: --   er_ecc1_gl
7560: --   er_ecc2_gl
7561: --   er_ecc3_gl
7562: --
7563: -- Granularidad:
7581:         COALESCE(s.er_ecc3_m3h, 0) AS q3,
7582:
7583:         NULLIF(s.er_ecc1_gl, 0) AS c1,
7584:         NULLIF(s.er_ecc2_gl, 0) AS c2,
7585:         NULLIF(s.er_ecc3_gl, 0) AS c3
7586:
7587:     FROM inventar_SpcHidr.sx_ep_flujos_niveles s
7974: --
7975: -- Concentraciones EP:
7976: --   ep_ecc1_gl
7977: --   ep_ecc2_gl
7978: --   ep_ecc3_gl
7979:
7980: ;WITH f100 AS (
7990:         COALESCE(s.er_ecc3_m3h, 0) AS q3,
7991:
7992:         NULLIF(s.ep_ecc1_gl, 0) AS c1,
7993:         NULLIF(s.ep_ecc2_gl, 0) AS c2,
7994:         NULLIF(s.ep_ecc3_gl, 0) AS c3
7995:
7996:     FROM inventar_SpcHidr.sx_ep_flujos_niveles s
8096:             AVG(
8097:                 (
8098:                     NULLIF(s.conc_er_ta_gl, 0) +
8099:                     NULLIF(s.conc_er_tb_gl, 0) +
8100:                     NULLIF(s.conc_er_tc_gl, 0) +
8101:                     NULLIF(s.conc_er_td_gl, 0)
8102:                 )
8103:                 /
8104:                 NULLIF(
8105:                     (CASE WHEN NULLIF(s.conc_er_ta_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
8106:                      CASE WHEN NULLIF(s.conc_er_tb_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
8107:                      CASE WHEN NULLIF(s.conc_er_tc_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
8108:                      CASE WHEN NULLIF(s.conc_er_td_gl,0) IS NOT NULL THEN 1 ELSE 0 END),
8109:                     0
8110:                 )
```


## siir_curated.vw_siir_drena_concentrado_parcela_long
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
5: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
6: UNION ALL
7: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
8: UNION ALL
9: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
19: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
20: UNION ALL
21: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
22: UNION ALL
23: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
33: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
34: UNION ALL
35: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
36: UNION ALL
37: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
47: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
48: UNION ALL
49: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
50: UNION ALL
51: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
61: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
62: UNION ALL
63: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
64: UNION ALL
65: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
75: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
76: UNION ALL
77: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
78: UNION ALL
79: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
89: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
90: UNION ALL
91: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
92: UNION ALL
93: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
103: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
104: UNION ALL
105: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
106: UNION ALL
107: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
117: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
118: UNION ALL
119: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
120: UNION ALL
121: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
131: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
132: UNION ALL
133: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
134: UNION ALL
135: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
145: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
146: UNION ALL
147: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
148: UNION ALL
149: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
159: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
160: UNION ALL
161: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
162: UNION ALL
163: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
173: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
174: UNION ALL
175: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
176: UNION ALL
177: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
187: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
188: UNION ALL
189: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
190: UNION ALL
191: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
201: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
202: UNION ALL
203: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
204: UNION ALL
205: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
215: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
216: UNION ALL
217: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
218: UNION ALL
219: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
229: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
230: UNION ALL
231: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
232: UNION ALL
233: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
243: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
244: UNION ALL
245: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
246: UNION ALL
247: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
257: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
258: UNION ALL
259: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
260: UNION ALL
261: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
271: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
272: UNION ALL
273: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
274: UNION ALL
275: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
285: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
286: UNION ALL
287: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
288: UNION ALL
289: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
299: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
300: UNION ALL
301: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
302: UNION ALL
303: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
313: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
314: UNION ALL
315: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
316: UNION ALL
317: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
327: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
328: UNION ALL
329: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
330: UNION ALL
331: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
341: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
342: UNION ALL
343: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
344: UNION ALL
345: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
355: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
356: UNION ALL
357: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
358: UNION ALL
359: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
369: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
370: UNION ALL
371: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
372: UNION ALL
373: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
383: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
384: UNION ALL
385: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
386: UNION ALL
387: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
397: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
398: UNION ALL
399: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
400: UNION ALL
401: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
411: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
412: UNION ALL
413: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
414: UNION ALL
415: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
425: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
426: UNION ALL
427: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
428: UNION ALL
429: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
439: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
440: UNION ALL
441: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
442: UNION ALL
443: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(1 AS tinyint) AS pad_id_legacy, CAST('OXIDOS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_oxido AS src
453: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
454: UNION ALL
455: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
456: UNION ALL
457: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(1 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p1_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
467: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
468: UNION ALL
469: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
470: UNION ALL
471: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(10 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p10_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
481: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
482: UNION ALL
483: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
484: UNION ALL
485: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(11 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p11_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
495: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
496: UNION ALL
497: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
498: UNION ALL
499: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(12 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p12_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
509: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
510: UNION ALL
511: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
512: UNION ALL
513: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(13 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p13_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
523: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
524: UNION ALL
525: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
526: UNION ALL
527: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(14 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p14_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
537: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
538: UNION ALL
539: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
540: UNION ALL
541: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(15 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p15_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
551: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
552: UNION ALL
553: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
554: UNION ALL
555: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(16 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p16_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
565: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
566: UNION ALL
567: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
568: UNION ALL
569: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(17 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p17_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
579: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
580: UNION ALL
581: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
582: UNION ALL
583: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(18 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p18_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
593: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
594: UNION ALL
595: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
596: UNION ALL
597: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(19 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p19_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
607: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
608: UNION ALL
609: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
610: UNION ALL
611: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(2 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p2_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
621: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
622: UNION ALL
623: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
624: UNION ALL
625: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(20 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p20_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
635: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
636: UNION ALL
637: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
638: UNION ALL
639: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(21 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p21_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
649: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
650: UNION ALL
651: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
652: UNION ALL
653: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(22 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p22_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
663: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
664: UNION ALL
665: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
666: UNION ALL
667: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(23 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p23_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
677: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
678: UNION ALL
679: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
680: UNION ALL
681: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(24 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p24_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
691: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
692: UNION ALL
693: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
694: UNION ALL
695: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(25 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p25_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
705: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
706: UNION ALL
707: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
708: UNION ALL
709: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(26 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p26_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
719: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
720: UNION ALL
721: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
722: UNION ALL
723: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(27 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p27_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
733: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
734: UNION ALL
735: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
736: UNION ALL
737: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(28 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p28_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
747: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
748: UNION ALL
749: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
750: UNION ALL
751: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(29 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p29_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
761: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
762: UNION ALL
763: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
764: UNION ALL
765: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(3 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p3_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
775: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
776: UNION ALL
777: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
778: UNION ALL
779: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(30 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p30_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
789: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
790: UNION ALL
791: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
792: UNION ALL
793: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(31 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p31_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
803: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
804: UNION ALL
805: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
806: UNION ALL
807: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(32 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p32_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
817: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
818: UNION ALL
819: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
820: UNION ALL
821: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(4 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p4_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
831: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
832: UNION ALL
833: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
834: UNION ALL
835: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(5 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p5_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
845: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
846: UNION ALL
847: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
848: UNION ALL
849: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(6 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p6_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
859: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
860: UNION ALL
861: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
862: UNION ALL
863: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(7 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p7_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
873: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
874: UNION ALL
875: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
876: UNION ALL
877: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(8 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p8_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
887: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cl' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cl]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
888: UNION ALL
889: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('cu_pp' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_cu_pp]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
890: UNION ALL
891: SELECT CAST(src.id_registro AS bigint) AS id_origen_registro, CAST(src.fecha_registro AS datetime2(0)) AS fecha_registro, CAST(src.fecha_registro AS date) AS fecha_dia, CAST(2 AS tinyint) AS pad_id_legacy, CAST('SULFUROS' AS varchar(20)) AS pad_nombre, CAST(9 AS int) AS nro_parcela_pad, CAST('eh' AS varchar(30)) AS analito_codigo, TRY_CONVERT(decimal(18,6), src.[p9_eh]) AS valor_raw FROM inventar_SpcHidr.drena_concentrados_sulfuro AS src
```


## inventar_SpcHidr.vw_tablero_lixiviacion_final
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
27:         fecha,
28:         nro_parcela_pad,
29:         cu_pp,
30:         h_p,
31:         ph,
42:         fecha,
43:         nro_parcela_pad,
44:         cu_pp,
45:         h_p,
46:         ph,
56:         1 AS pad_tipo,
57:         fecha,
58:         cu_pp,
59:         h_p,
60:         ph,
70:         2 AS pad_tipo,
71:         fecha,
72:         cu_pp,
73:         h_p,
74:         ph,
104:     f.flujo_m3_h,
105:     f.flujo_m3_d,
106:     d.cu_pp AS cu_drenaje_ppm,
107:     d.h_p AS h_drenaje,
108:     d.ph AS ph_drenaje,
111:     d.fe2 AS fe2_drenaje,
112:     d.eh AS eh_drenaje,
113:     r.cu_pp AS cu_refino_ppm,
114:     r.h_p AS h_refino,
115:     r.ph AS ph_refino,
118:     r.fe2 AS fe2_refino,
119:     r.eh AS eh_refino,
120:     CASE WHEN d.cu_pp IS NOT NULL AND r.cu_pp IS NOT NULL
121:          THEN d.cu_pp - r.cu_pp
122:          ELSE NULL END AS delta_cu_ppm,
123:     CASE WHEN d.h_p IS NOT NULL AND r.h_p IS NOT NULL
124:          THEN d.h_p - r.h_p
125:          ELSE NULL END AS delta_h,
126:     CASE WHEN f.flujo_m3_d IS NOT NULL
127:            AND d.cu_pp IS NOT NULL
128:            AND r.cu_pp IS NOT NULL
129:          THEN f.flujo_m3_d * (d.cu_pp - r.cu_pp) / 1000.0
130:          ELSE NULL END AS transferencia_cu_kg_d,
131:     DATEDIFF(DAY, c.fecha_ini_carguio, f.fecha) + 1 AS dia_relativo_campana,
132:     CASE
```


## inventar_SpcHidr.vw_drena_concentrados_oxido_long
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
6:     d.fecha_registro,
7:     v.nro_parcela_pad,
8:     CAST(v.cu_pp AS decimal(12,2)) AS cu_pp,
9:     CAST(v.h_p  AS decimal(12,2)) AS h_p,
10:     CAST(v.ph   AS decimal(12,2)) AS ph,
15: FROM inventar_SpcHidr.drena_concentrados_oxido d
16: CROSS APPLY (VALUES
17:     (1 , d.p1_cu_pp , d.p1_h_p , d.p1_ph , d.p1_cl , d.p1_fet , d.p1_fe2 , d.p1_eh),
18:     (2 , d.p2_cu_pp , d.p2_h_p , d.p2_ph , d.p2_cl , d.p2_fet , d.p2_fe2 , d.p2_eh),
19:     (3 , d.p3_cu_pp , d.p3_h_p , d.p3_ph , d.p3_cl , d.p3_fet , d.p3_fe2 , d.p3_eh),
20:     (4 , d.p4_cu_pp , d.p4_h_p , d.p4_ph , d.p4_cl , d.p4_fet , d.p4_fe2 , d.p4_eh),
21:     (5 , d.p5_cu_pp , d.p5_h_p , d.p5_ph , d.p5_cl , d.p5_fet , d.p5_fe2 , d.p5_eh),
22:     (6 , d.p6_cu_pp , d.p6_h_p , d.p6_ph , d.p6_cl , d.p6_fet , d.p6_fe2 , d.p6_eh),
23:     (7 , d.p7_cu_pp , d.p7_h_p , d.p7_ph , d.p7_cl , d.p7_fet , d.p7_fe2 , d.p7_eh),
24:     (8 , d.p8_cu_pp , d.p8_h_p , d.p8_ph , d.p8_cl , d.p8_fet , d.p8_fe2 , d.p8_eh),
25:     (9 , d.p9_cu_pp , d.p9_h_p , d.p9_ph , d.p9_cl , d.p9_fet , d.p9_fe2 , d.p9_eh),
26:     (10, d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),
27:     (11, d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),
28:     (12, d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),
29:     (13, d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),
30:     (14, d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),
31:     (15, d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),
32:     (16, d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),
33:     (17, d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),
34:     (18, d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),
35:     (19, d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),
36:     (20, d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),
37:     (21, d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),
38:     (22, d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),
39:     (23, d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),
40:     (24, d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),
41:     (25, d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),
42:     (26, d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),
43:     (27, d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),
44:     (28, d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh),
45:     (29, d.p29_cu_pp, d.p29_h_p, d.p29_ph, d.p29_cl, d.p29_fet, d.p29_fe2, d.p29_eh),
46:     (30, d.p30_cu_pp, d.p30_h_p, d.p30_ph, d.p30_cl, d.p30_fet, d.p30_fe2, d.p30_eh),
47:     (31, d.p31_cu_pp, d.p31_h_p, d.p31_ph, d.p31_cl, d.p31_fet, d.p31_fe2, d.p31_eh),
48:     (32, d.p32_cu_pp, d.p32_h_p, d.p32_ph, d.p32_cl, d.p32_fet, d.p32_fe2, d.p32_eh)
49: ) v(nro_parcela_pad, cu_pp, h_p, ph, cl, fet, fe2, eh);
```


## inventar_SpcHidr.vw_drena_concentrados_sulfuro_long
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
6:     d.fecha_registro,
7:     v.nro_parcela_pad,
8:     CAST(v.cu_pp AS decimal(12,2)) AS cu_pp,
9:     CAST(v.h_p  AS decimal(12,2)) AS h_p,
10:     CAST(v.ph   AS decimal(12,2)) AS ph,
15: FROM inventar_SpcHidr.drena_concentrados_sulfuro d
16: CROSS APPLY (VALUES
17:     (1 , d.p1_cu_pp , d.p1_h_p , d.p1_ph , d.p1_cl , d.p1_fet , d.p1_fe2 , d.p1_eh),
18:     (2 , d.p2_cu_pp , d.p2_h_p , d.p2_ph , d.p2_cl , d.p2_fet , d.p2_fe2 , d.p2_eh),
19:     (3 , d.p3_cu_pp , d.p3_h_p , d.p3_ph , d.p3_cl , d.p3_fet , d.p3_fe2 , d.p3_eh),
20:     (4 , d.p4_cu_pp , d.p4_h_p , d.p4_ph , d.p4_cl , d.p4_fet , d.p4_fe2 , d.p4_eh),
21:     (5 , d.p5_cu_pp , d.p5_h_p , d.p5_ph , d.p5_cl , d.p5_fet , d.p5_fe2 , d.p5_eh),
22:     (6 , d.p6_cu_pp , d.p6_h_p , d.p6_ph , d.p6_cl , d.p6_fet , d.p6_fe2 , d.p6_eh),
23:     (7 , d.p7_cu_pp , d.p7_h_p , d.p7_ph , d.p7_cl , d.p7_fet , d.p7_fe2 , d.p7_eh),
24:     (8 , d.p8_cu_pp , d.p8_h_p , d.p8_ph , d.p8_cl , d.p8_fet , d.p8_fe2 , d.p8_eh),
25:     (9 , d.p9_cu_pp , d.p9_h_p , d.p9_ph , d.p9_cl , d.p9_fet , d.p9_fe2 , d.p9_eh),
26:     (10, d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),
27:     (11, d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),
28:     (12, d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),
29:     (13, d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),
30:     (14, d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),
31:     (15, d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),
32:     (16, d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),
33:     (17, d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),
34:     (18, d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),
35:     (19, d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),
36:     (20, d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),
37:     (21, d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),
38:     (22, d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),
39:     (23, d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),
40:     (24, d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),
41:     (25, d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),
42:     (26, d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),
43:     (27, d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),
44:     (28, d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh),
45:     (29, d.p29_cu_pp, d.p29_h_p, d.p29_ph, d.p29_cl, d.p29_fet, d.p29_fe2, d.p29_eh),
46:     (30, d.p30_cu_pp, d.p30_h_p, d.p30_ph, d.p30_cl, d.p30_fet, d.p30_fe2, d.p30_eh),
47:     (31, d.p31_cu_pp, d.p31_h_p, d.p31_ph, d.p31_cl, d.p31_fet, d.p31_fe2, d.p31_eh),
48:     (32, d.p32_cu_pp, d.p32_h_p, d.p32_ph, d.p32_cl, d.p32_fet, d.p32_fe2, d.p32_eh)
49: ) v(nro_parcela_pad, cu_pp, h_p, ph, cl, fet, fe2, eh);
```


## inventar_SpcHidr.vw_drena_quimica_ingest
Fuente histórica: `report_export/exports/auditoria_ley_srr_202609/catalogo.json`; líneas de definition.

```sql
1: CREATE   VIEW [inventar_SpcHidr].[vw_drena_quimica_ingest]
2: AS         SELECT              p.id_parcela AS parcela_id, CAST(d.fecha_registro AS DATE) AS fecha,             NULLIF(CAST(v.cu_pp AS FLOAT), 0) AS cu_gl, NULLIF(CAST(v.h_p AS FLOAT), 0) AS h_p,             NULLIF(CAST(v.ph AS FLOAT), 0) AS ph, NULLIF(CAST(v.cl AS FLOAT), 0) AS cl,             NULLIF(CAST(v.fet AS FLOAT), 0) AS fet, NULLIF(CAST(v.fe2 AS FLOAT), 0) AS fe2,             NULLIF(CAST(v.eh AS FLOAT), 0) AS eh         FROM inventar_SpcHidr.inventar_SpcHidr.drena_concentrados_oxido d         CROSS APPLY (VALUES             ('P01', d.p1_cu_pp,  d.p1_h_p,  d.p1_ph,  d.p1_cl,  d.p1_fet,  d.p1_fe2,  d.p1_eh),             ('P02', d.p2_cu_pp,  d.p2_h_p,  d.p2_ph,  d.p2_cl,  d.p2_fet,  d.p2_fe2,  d.p2_eh),             ('P03', d.p3_cu_pp,  d.p3_h_p,  d.p3_ph,  d.p3_cl,  d.p3_fet,  d.p3_fe2,  d.p3_eh),             ('P04', d.p4_cu_pp,  d.p4_h_p,  d.p4_ph,  d.p4_cl,  d.p4_fet,  d.p4_fe2,  d.p4_eh),             ('P05', d.p5_cu_pp,  d.p5_h_p,  d.p5_ph,  d.p5_cl,  d.p5_fet,  d.p5_fe2,  d.p5_eh),             ('P06', d.p6_cu_pp,  d.p6_h_p,  d.p6_ph,  d.p6_cl,  d.p6_fet,  d.p6_fe2,  d.p6_eh),             ('P07', d.p7_cu_pp,  d.p7_h_p,  d.p7_ph,  d.p7_cl,  d.p7_fet,  d.p7_fe2,  d.p7_eh),             ('P08', d.p8_cu_pp,  d.p8_h_p,  d.p8_ph,  d.p8_cl,  d.p8_fet,  d.p8_fe2,  d.p8_eh),             ('P09', d.p9_cu_pp,  d.p9_h_p,  d.p9_ph,  d.p9_cl,  d.p9_fet,  d.p9_fe2,  d.p9_eh),             ('P10', d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),             ('P11', d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),             ('P12', d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),             ('P13', d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),             ('P14', d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),             ('P15', d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),             ('P16', d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),             ('P17', d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),             ('P18', d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),             ('P19', d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),             ('P20', d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),             ('P21', d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),             ('P22', d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),             ('P23', d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),             ('P24', d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),             ('P25', d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),             ('P26', d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),             ('P27', d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),             ('P28', d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh),             ('P29', d.p29_cu_pp, d.p29_h_p, d.p29_ph, d.p29_cl, d.p29_fet, d.p29_fe2, d.p29_eh),             ('P30', d.p30_cu_pp, d.p30_h_p, d.p30_ph, d.p30_cl, d.p30_fet, d.p30_fe2, d.p30_eh),             ('P31', d.p31_cu_pp, d.p31_h_p, d.p31_ph, d.p31_cl, d.p31_fet, d.p31_fe2, d.p31_eh),             ('P32', d.p32_cu_pp, d.p32_h_p, d.p32_ph, d.p32_cl, d.p32_fet, d.p32_fe2, d.p32_eh)         ) AS v(nombre_parcela, cu_pp, h_p, ph, cl, fet, fe2, eh)         JOIN inventar_SpcHidr.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 1         UNION ALL         SELECT              p.id_parcela AS parcela_id, CAST(d.fecha_registro AS DATE) AS fecha,             NULLIF(CAST(v.cu_pp AS FLOAT), 0) AS cu_gl, NULLIF(CAST(v.h_p AS FLOAT), 0) AS h_p,             NULLIF(CAST(v.ph AS FLOAT), 0) AS ph, NULLIF(CAST(v.cl AS FLOAT), 0) AS cl,             NULLIF(CAST(v.fet AS FLOAT), 0) AS fet, NULLIF(CAST(v.fe2 AS FLOAT), 0) AS fe2,             NULLIF(CAST(v.eh AS FLOAT), 0) AS eh         FROM inventar_SpcHidr.inventar_SpcHidr.drena_concentrados_sulfuro d         CROSS APPLY (VALUES             ('P01', d.p1_cu_pp,  d.p1_h_p,  d.p1_ph,  d.p1_cl,  d.p1_fet,  d.p1_fe2,  d.p1_eh),             ('P02', d.p2_cu_pp,  d.p2_h_p,  d.p2_ph,  d.p2_cl,  d.p2_fet,  d.p2_fe2,  d.p2_eh),             ('P03', d.p3_cu_pp,  d.p3_h_p,  d.p3_ph,  d.p3_cl,  d.p3_fet,  d.p3_fe2,  d.p3_eh),             ('P04', d.p4_cu_pp,  d.p4_h_p,  d.p4_ph,  d.p4_cl,  d.p4_fet,  d.p4_fe2,  d.p4_eh),             ('P05', d.p5_cu_pp,  d.p5_h_p,  d.p5_ph,  d.p5_cl,  d.p5_fet,  d.p5_fe2,  d.p5_eh),             ('P06', d.p6_cu_pp,  d.p6_h_p,  d.p6_ph,  d.p6_cl,  d.p6_fet,  d.p6_fe2,  d.p6_eh),             ('P07', d.p7_cu_pp,  d.p7_h_p,  d.p7_ph,  d.p7_cl,  d.p7_fet,  d.p7_fe2,  d.p7_eh),             ('P08', d.p8_cu_pp,  d.p8_h_p,  d.p8_ph,  d.p8_cl,  d.p8_fet,  d.p8_fe2,  d.p8_eh),             ('P09', d.p9_cu_pp,  d.p9_h_p,  d.p9_ph,  d.p9_cl,  d.p9_fet,  d.p9_fe2,  d.p9_eh),             ('P10', d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),             ('P11', d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),             ('P12', d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),             ('P13', d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),             ('P14', d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),             ('P15', d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),             ('P16', d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),             ('P17', d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),             ('P18', d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),             ('P19', d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),             ('P20', d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),             ('P21', d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),             ('P22', d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),             ('P23', d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),             ('P24', d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),             ('P25', d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),             ('P26', d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),             ('P27', d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),             ('P28', d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh)         ) AS v(nombre_parcela, cu_pp, h_p, ph, cl, fet, fe2, eh)         JOIN inventar_SpcHidr.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 2;
```

