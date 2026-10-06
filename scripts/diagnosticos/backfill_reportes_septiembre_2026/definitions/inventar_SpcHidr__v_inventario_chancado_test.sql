
CREATE   VIEW
    [inventar_SpcHidr].[v_inventario_chancado_test]
AS
SELECT
    Fecha,
    Fecha_Lectura_D1,

    Primera_Fila_Bloque,
    Ultima_Fila_Bloque,
    Cantidad_Filas_Bloque,
    Flag_Bloque_Archive_Valido,

    Nivel_Inventario_Silo,
    Nivel_Inventario_Harnero,
    Nivel_Inventario_Chancado,

    TMH_Silo,
    TMH_Harnero,
    TMH_Chancado,
    Tolva_Compensacion_TMH,

    Total_Inventario_Chancado_TMH,
    Humedad_Inventario,
    Total_Inventario_Chancado_TMS,

    Fecha_Inventario_Anterior,
    Inventario_Chancado_TMS_Anterior,
    Fuente_Inventario_Anterior,

    Delta_Inventario_Chancado_TMS,

    Flag_Continuidad_Diaria,
    Flag_Inventario_Valido

FROM
    [inventar_SpcHidr].[v_inventario_chancado_archive_test];
