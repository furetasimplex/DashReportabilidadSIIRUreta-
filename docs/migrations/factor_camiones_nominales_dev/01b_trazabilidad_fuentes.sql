IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Estado_Fuente_MOV_CAM') IS NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test ADD Estado_Fuente_MOV_CAM varchar(24) NULL;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Estado_Fuente_POWERBI') IS NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test ADD Estado_Fuente_POWERBI varchar(24) NULL;
