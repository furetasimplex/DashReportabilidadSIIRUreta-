CREATE   PROCEDURE
    inventar_SpcHidr.sp_registrar_contingencia_pi_test
(
    @FechaOperacional date,
    @Turno            char(1),
    @Accion           varchar(30),
    @Motivo           varchar(30) = NULL,
    @Comentario       nvarchar(1000) = NULL,
    @Usuario          nvarchar(255)
)
AS
BEGIN

    SET NOCOUNT ON;
    SET XACT_ABORT ON;


    DECLARE @TurnoN char(1) =
        UPPER(LTRIM(RTRIM(@Turno)));

    DECLARE @AccionN varchar(30) =
        UPPER(LTRIM(RTRIM(@Accion)));

    DECLARE @MotivoN varchar(30) =
        NULLIF(
            UPPER(LTRIM(RTRIM(@Motivo))),
            ''
        );

    DECLARE @ComentarioN nvarchar(1000) =
        NULLIF(
            LTRIM(RTRIM(@Comentario)),
            ''
        );

    DECLARE @UsuarioN nvarchar(255) =
        LTRIM(RTRIM(@Usuario));


    /* ============================================================
       VALIDACIONES BÁSICAS
       ============================================================ */

    IF @FechaOperacional IS NULL
        THROW 51201,
              'Debe informar @FechaOperacional.',
              1;


    IF @TurnoN NOT IN ('A','B')
        THROW 51202,
              '@Turno debe ser A o B.',
              1;


    IF @AccionN NOT IN
    (
        'ACTIVAR_CONTINGENCIA',
        'CERRAR_CONTINGENCIA'
    )
        THROW 51203,
              '@Accion debe ser ACTIVAR_CONTINGENCIA o CERRAR_CONTINGENCIA.',
              1;


    IF @UsuarioN IS NULL
       OR LEN(@UsuarioN) = 0
        THROW 51204,
              'Debe informar @Usuario.',
              1;


    IF @AccionN = 'ACTIVAR_CONTINGENCIA'
       AND @MotivoN NOT IN
       (
           'CAIDA_PI',
           'MANTENCION',
           'COMUNICACIONES',
           'SERVIDOR',
           'OTRO'
       )
        THROW 51205,
              'Debe informar un motivo válido para activar la contingencia.',
              1;


    IF @AccionN = 'CERRAR_CONTINGENCIA'
        SET @MotivoN = NULL;


    /* ============================================================
       ESTADO VIGENTE EN EL PUNTO OPERACIONAL SOLICITADO
       ============================================================ */

    DECLARE @UltimaAccion varchar(30);


    SELECT TOP (1)
        @UltimaAccion = a.accion

    FROM inventar_SpcHidr.contingencia_pi_accion_test AS a

    WHERE
        a.fecha_operacional < @FechaOperacional

        OR
        (
            a.fecha_operacional = @FechaOperacional
            AND
            CASE
                WHEN a.turno = 'A' THEN 1
                ELSE 2
            END
            <=
            CASE
                WHEN @TurnoN = 'A' THEN 1
                ELSE 2
            END
        )

    ORDER BY
        a.fecha_operacional DESC,

        CASE
            WHEN a.turno = 'A' THEN 1
            ELSE 2
        END DESC,

        a.fecha_registro DESC,
        a.id DESC;


    /* ============================================================
       CONTROL DE TRANSICIONES
       ============================================================ */

    IF @AccionN = 'ACTIVAR_CONTINGENCIA'
       AND @UltimaAccion = 'ACTIVAR_CONTINGENCIA'
        THROW 51206,
              'La contingencia PI ya se encuentra activa para ese periodo.',
              1;


    IF @AccionN = 'CERRAR_CONTINGENCIA'
       AND ISNULL(@UltimaAccion, 'NORMAL')
           <> 'ACTIVAR_CONTINGENCIA'
        THROW 51207,
              'No existe una contingencia PI activa para cerrar en ese periodo.',
              1;


    /* ============================================================
       INSERT APPEND-ONLY
       ============================================================ */

    INSERT INTO inventar_SpcHidr.contingencia_pi_accion_test
    (
        fecha_operacional,
        turno,
        accion,
        motivo,
        comentario,
        usuario
    )

    OUTPUT
        inserted.id,
        inserted.fecha_operacional,
        inserted.turno,
        inserted.accion,
        inserted.motivo,
        inserted.comentario,
        inserted.usuario,
        inserted.fecha_registro

    VALUES
    (
        @FechaOperacional,
        @TurnoN,
        @AccionN,
        @MotivoN,
        @ComentarioN,
        @UsuarioN
    );

END;
