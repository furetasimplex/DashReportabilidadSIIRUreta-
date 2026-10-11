CREATE   PROCEDURE
    inventar_SpcHidr.sp_guardar_contingencia_estado_operacional_test
(
    @FechaOperacional   date,
    @Turno              char(1),
    @EstadoOperacional  varchar(20),
    @Comentario         nvarchar(1000) = NULL,
    @Usuario            nvarchar(255)
)
AS
BEGIN

    SET NOCOUNT ON;
    SET XACT_ABORT ON;


    /* ============================================================
       NORMALIZACIÓN
       ============================================================ */

    DECLARE @TurnoNormalizado char(1);

    DECLARE @EstadoNormalizado varchar(20);

    DECLARE @UsuarioNormalizado nvarchar(255);

    DECLARE @ComentarioNormalizado nvarchar(1000);


    SET @TurnoNormalizado =
        UPPER(
            LTRIM(
                RTRIM(@Turno)
            )
        );


    SET @EstadoNormalizado =
        UPPER(
            LTRIM(
                RTRIM(@EstadoOperacional)
            )
        );


    SET @UsuarioNormalizado =
        LTRIM(
            RTRIM(@Usuario)
        );


    SET @ComentarioNormalizado =
        NULLIF(
            LTRIM(
                RTRIM(@Comentario)
            ),
            ''
        );


    /* ============================================================
       VALIDACIONES
       ============================================================ */

    IF @FechaOperacional IS NULL
        THROW 51101,
              'Debe informar @FechaOperacional.',
              1;


    IF @TurnoNormalizado NOT IN ('A', 'B')
        THROW 51102,
              '@Turno debe ser A o B.',
              1;


    IF @EstadoNormalizado NOT IN
    (
        'OPERATIVO',
        'MANTENCION',
        'CAIDA_PI'
    )
        THROW 51103,
              '@EstadoOperacional debe ser OPERATIVO, MANTENCION o CAIDA_PI.',
              1;


    IF @UsuarioNormalizado IS NULL
       OR LEN(@UsuarioNormalizado) = 0
        THROW 51104,
              'Debe informar @Usuario.',
              1;


    /* ============================================================
       INSERT APPEND-ONLY
       ============================================================ */

    INSERT INTO
        inventar_SpcHidr.contingencia_estado_operacional_test
    (
        fecha_operacional,
        turno,
        estado_operacional,
        comentario,
        usuario
    )

    OUTPUT
        inserted.id,
        inserted.fecha_operacional,
        inserted.turno,
        inserted.estado_operacional,
        inserted.comentario,
        inserted.usuario,
        inserted.fecha_registro

    VALUES
    (
        @FechaOperacional,
        @TurnoNormalizado,
        @EstadoNormalizado,
        @ComentarioNormalizado,
        @UsuarioNormalizado
    );

END;
