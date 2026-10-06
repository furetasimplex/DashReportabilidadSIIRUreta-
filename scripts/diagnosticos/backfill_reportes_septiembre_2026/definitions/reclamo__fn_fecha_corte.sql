/* Funcion de acceso, para que las vistas puedan leer la fecha de corte sin
   repetir el literal. */
CREATE   FUNCTION [reclamo].[fn_fecha_corte]()
RETURNS date
AS
BEGIN
    RETURN
    (
        SELECT TRY_CONVERT(date, c.valor)
        FROM [reclamo].[configuracion] c
        WHERE c.clave = 'FECHA_CORTE_SISTEMA'
    );
END;