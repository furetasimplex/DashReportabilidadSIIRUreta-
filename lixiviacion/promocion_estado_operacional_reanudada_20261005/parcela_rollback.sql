IF DB_NAME() <> 'inventar_SpcHidr' THROW 51000, 'Solo DEV', 1;
DROP FUNCTION inventar_SpcHidr.fn_estado_operacional_parcela_diario;
