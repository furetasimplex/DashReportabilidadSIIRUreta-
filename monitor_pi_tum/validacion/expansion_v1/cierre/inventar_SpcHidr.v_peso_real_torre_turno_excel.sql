CREATE VIEW inventar_SpcHidr.v_peso_real_torre_turno_excel
AS
SELECT
    Fecha,
    Turno,
    Torre,
    PesoReal_Quimico,
    PesoReal_Fisico,
    nombre_archivo,
    fecha_carga
FROM inventar_SpcHidr.peso_real_torre_turno
WHERE Torre IN ('T1', 'T2', 'SRR');
