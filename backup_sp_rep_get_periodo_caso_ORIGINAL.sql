CREATE   PROCEDURE inventar_SpcHidr.sp_rep_get_periodo_caso
    @caso_id INT
AS
BEGIN
    SET NOCOUNT ON;

    -- EJEMPLO: reemplaza por tu tabla real
    SELECT
        c.caso_id,
        CAST(c.fecha_ini AS DATE) AS fecha_inicio,
        CAST(c.fecha AS DATE) AS fecha_fin
    FROM inventar_SpcHidr.casos_balance c
    WHERE c.caso_id = @caso_id;
END