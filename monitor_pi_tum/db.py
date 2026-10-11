"""Lectura del contrato de tendencia; las fuentes se resuelven en SQL."""
from datetime import date, datetime, time, timedelta
import os
import logging

import pandas as pd
from sqlalchemy import text
from db_connection import get_engine

CORREAS = ("CV001", "CV002", "CV003", "CV006", "CV008", "CV025", "CV108", "CV201", "CV202")

GRUPOS_EQUIPOS = (
    ("CHANCADO", ("CHANCADOR_CV006",)),
    ("APILADO PRINCIPAL", ("PRINCIPAL_CV008", "PRINCIPAL_CV108")),
    ("SRR", ("SRR_CV001", "SRR_CV002", "SRR_CV003")),
    ("RIPIOS", ("RIPIOS_CV025",)),
)
EQUIPOS = tuple(equipo for _, equipos in GRUPOS_EQUIPOS for equipo in equipos)
CORTE = date(2026, 9, 1)
ACCIONES = ("ACTIVAR_CONTINGENCIA", "CERRAR_CONTINGENCIA")
MOTIVOS = ("CAIDA_PI", "MANTENCION", "COMUNICACIONES", "SERVIDOR", "OTRO")
RESOLVEDOR = "inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test"
BITACORA = "inventar_SpcHidr.contingencia_pi_accion_test"
DEV_SERVER_ENV = 'SIIR_DEV_SQLSERVER_HOST'
DEV_BLOCKED = 'Gestión PI/TUM bloqueada: la conexión no corresponde al ambiente DEV.'
log = logging.getLogger(__name__)


def _assert_dev_connection(conn):
    """Comprueba la identidad SQL efectiva en la conexión que hará la escritura."""
    esperado = os.getenv(DEV_SERVER_ENV, '').strip()
    if not esperado:
        log.error('Guard DEV sin %s; base esperada=%s', DEV_SERVER_ENV, 'inventar_SpcHidr')
        raise RuntimeError(DEV_BLOCKED)
    try:
        identidad = conn.execute(text('''SELECT DB_NAME() AS database_name,
            CAST(SERVERPROPERTY('ServerName') AS nvarchar(128)) AS server_name,
            CAST(SERVERPROPERTY('MachineName') AS nvarchar(128)) AS machine_name''')).mappings().one()
        base = identidad['database_name']
        servidor = identidad['server_name']
        maquina = identidad['machine_name']
    except Exception:
        log.exception('Guard DEV: no se pudo consultar identidad SQL; servidor esperado=%s, base esperada=%s',
                      esperado, 'inventar_SpcHidr')
        raise RuntimeError(DEV_BLOCKED) from None
    # Una instancia nombrada puede agregar "\\instancia" a ServerName.
    valido = (base == 'inventar_SpcHidr' and maquina == esperado
              and isinstance(servidor, str)
              and (servidor == esperado or servidor.startswith(esperado + '\\')))
    if not valido:
        log.error('Guard DEV rechazó conexión: servidor esperado=%s real=%s; máquina real=%s; base esperada=%s real=%s',
                  esperado, servidor, maquina, 'inventar_SpcHidr', base)
        raise RuntimeError(DEV_BLOCKED)


def _engine_dev():
    if os.getenv("SQLSERVER_DB") != "inventar_SpcHidr":
        raise RuntimeError("Gestión operacional habilitada exclusivamente en DEV.")
    engine = get_engine()
    if engine is None or engine.url.database != "inventar_SpcHidr":
        raise RuntimeError("La conexión debe apuntar a DEV.")
    return engine


def validar_periodo(fecha, turno):
    try:
        fecha = date.fromisoformat(str(fecha))
    except (ValueError, TypeError):
        raise ValueError("Seleccione una fecha operacional válida.") from None
    if turno not in ("A", "B"):
        raise ValueError("Seleccione turno A o B.")
    if fecha < CORTE:
        raise ValueError("La gestión de contingencias está disponible desde el 01-09-2026.")
    return fecha


def turno_siguiente(fecha, turno):
    fecha = validar_periodo(fecha, turno)
    try:
        return (fecha, 'B') if turno == 'A' else (fecha + timedelta(days=1), 'A')
    except OverflowError:
        raise ValueError('No se puede calcular el cierre posterior al período final.') from None


def validar_rango(inicio, turno_inicio, fin, turno_fin):
    inicio = validar_periodo(inicio, turno_inicio)
    fin = validar_periodo(fin, turno_fin)
    if (fin, turno_fin) < (inicio, turno_inicio):
        raise ValueError('El período final no puede ser anterior al período inicial.')
    turno_siguiente(fin, turno_fin)
    return inicio, fin


def expandir_turnos(inicio, turno_inicio, fin, turno_fin):
    inicio, fin = validar_rango(inicio, turno_inicio, fin, turno_fin)
    periodos, punto = [], (inicio, turno_inicio)
    while punto <= (fin, turno_fin):
        periodos.append(punto)
        punto = turno_siguiente(*punto)
    return periodos


def _validar_solapamiento(conn, inicio, turno_inicio, fin, turno_fin, bloquear=False):
    cierre, turno_cierre = turno_siguiente(fin, turno_fin)
    # Cada punto puede tener varias correcciones append-only: solo rige la última.
    # El bloqueo de rango también protege frente a escrituras ajenas a la aplicación.
    hint = 'WITH (UPDLOCK, HOLDLOCK)' if bloquear else ''
    conflicto = conn.execute(text(f'''
        WITH orden AS (
            SELECT fecha_operacional, turno, accion,
                ROW_NUMBER() OVER (PARTITION BY fecha_operacional,turno
                    ORDER BY fecha_registro DESC,id DESC) AS rn
            FROM {BITACORA} {hint} WHERE fecha_operacional>=:corte
        ), vigente AS (
            SELECT *, LEAD(fecha_operacional) OVER (ORDER BY fecha_operacional,turno) AS siguiente_fecha,
                LEAD(turno) OVER (ORDER BY fecha_operacional,turno) AS siguiente_turno
            FROM orden WHERE rn=1
        )
        SELECT COALESCE(MAX(CASE
            WHEN fecha_operacional=:cierre AND turno=:turno_cierre THEN 2
            ELSE 1 END),0)
        FROM vigente WHERE (accion='ACTIVAR_CONTINGENCIA'
          AND (fecha_operacional<:cierre OR (fecha_operacional=:cierre AND turno<=:turno_cierre))
          AND (siguiente_fecha IS NULL OR siguiente_fecha>:inicio
               OR (siguiente_fecha=:inicio AND siguiente_turno>:turno_inicio)))
          OR (accion='CERRAR_CONTINGENCIA'
              AND (fecha_operacional>:inicio OR (fecha_operacional=:inicio AND turno>:turno_inicio))
              AND (fecha_operacional<:cierre OR (fecha_operacional=:cierre AND turno<:turno_cierre)))
    '''), dict(corte=CORTE,inicio=inicio,turno_inicio=turno_inicio,
               cierre=cierre,turno_cierre=turno_cierre)).scalar()
    if conflicto == 1:
        raise ValueError('El rango seleccionado se superpone con una contingencia PI ya registrada.')
    if conflicto == 2:
        raise ValueError('El cierre calculado coincide con el inicio de otra contingencia PI. '
                         'Seleccione un fin anterior para conservar los eventos existentes.')


def _preview_rango(conn, inicio, turno_inicio, fin, turno_fin):
    return pd.read_sql(text(f'''SELECT fecha_operacional, turno, equipo_codigo,
        valor_turno_tum, tum_disponible_operacional, pi_disponible_operacional,
        fuente_resuelta, valor_final_resuelto
        FROM {RESOLVEDOR}
        WHERE fecha_operacional BETWEEN :inicio AND :fin
          AND (fecha_operacional>:inicio OR turno>=:turno_inicio)
          AND (fecha_operacional<:fin OR turno<=:turno_fin)
          AND equipo_codigo IN ('CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108',
                                'SRR_CV001','SRR_CV002','SRR_CV003','RIPIOS_CV025')
        ORDER BY fecha_operacional,turno,equipo_codigo'''), conn,
        params=dict(inicio=inicio,turno_inicio=turno_inicio,fin=fin,turno_fin=turno_fin))


def obtener_preview_rango(inicio, turno_inicio, fin, turno_fin):
    inicio, fin = validar_rango(inicio, turno_inicio, fin, turno_fin)
    with _engine_dev().connect() as conn:
        _validar_solapamiento(conn,inicio,turno_inicio,fin,turno_fin)
        return _preview_rango(conn,inicio,turno_inicio,fin,turno_fin)


def _adquirir_lock_contingencia(conn):
    """Serializa PI/TUM hasta el COMMIT/ROLLBACK de la transacción del caller."""
    lock = conn.execute(text('''DECLARE @resultado int;
        EXEC @resultado=sys.sp_getapplock @Resource='SIIR_CONTINGENCIA_PI_APILADO',
            @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000;
        SELECT @resultado;''')).scalar()
    if lock is None or lock < 0:
        raise ValueError('Hay otra acción en proceso. Actualice el estado antes de reintentar.')


def registrar_contingencia_rango(inicio, turno_inicio, fin, turno_fin, motivo, comentario, usuario):
    inicio, fin = validar_rango(inicio, turno_inicio, fin, turno_fin)
    _validar_accion(inicio,turno_inicio,'ACTIVAR_CONTINGENCIA',motivo,comentario,usuario)
    if motivo == 'OTRO' and (not isinstance(comentario,str) or not comentario.strip()):
        raise ValueError('Especifique la causa para registrar el motivo Otro.')
    cierre, turno_cierre = turno_siguiente(fin,turno_fin)
    with _engine_dev().begin() as conn:
        _assert_dev_connection(conn)
        _validar_materializable(conn, inicio, turno_inicio)
        _validar_materializable(conn, fin, turno_fin)
        _adquirir_lock_contingencia(conn)
        _validar_solapamiento(conn,inicio,turno_inicio,fin,turno_fin,bloquear=True)
        ids = []
        for fecha, turno, accion, razon, nota in [
            (inicio,turno_inicio,'ACTIVAR_CONTINGENCIA',motivo,comentario),
            (cierre,turno_cierre,'CERRAR_CONTINGENCIA',None,
             f'Cierre del rango inclusivo {inicio:%d-%m-%Y} {turno_inicio} a {fin:%d-%m-%Y} {turno_fin}.')]:
            row = conn.execute(text('''EXEC inventar_SpcHidr.sp_registrar_contingencia_pi_test
                @FechaOperacional=:fecha, @Turno=:turno, @Accion=:accion,
                @Motivo=:motivo, @Comentario=:comentario, @Usuario=:usuario;'''),
                dict(fecha=fecha,turno=turno,accion=accion,motivo=razon,
                     comentario=nota or None,usuario=usuario)).mappings().one()
            ids.append(row['id'])
        reprocesar_apilado(conn,inicio,fin)
        frame = _preview_rango(conn,inicio,turno_inicio,fin,turno_fin)
        pendientes = frame.loc[frame.fuente_resuelta=='PENDIENTE_TUM','equipo_codigo'].unique().tolist()
        return dict(ids=ids,inicio=inicio,fin=fin,fecha_cierre=cierre,turno_cierre=turno_cierre,
                    pendientes_tum=pendientes)


def _estado(conn, fecha, turno):
    # La bitácora es autoridad también cuando aún no existe fila de señales.
    return dict(conn.execute(text(f'''
        SELECT CAST(CASE WHEN a.accion='ACTIVAR_CONTINGENCIA' THEN 1 ELSE 0 END AS bit)
                   AS contingencia_pi_activa,
               a.id AS accion_vigente_id, a.fecha_operacional AS fecha_accion_vigente,
               a.turno AS turno_accion_vigente, a.motivo AS motivo_contingencia,
               a.usuario AS usuario_estado_operacional,
               a.fecha_registro AS fecha_registro_estado_operacional
        FROM (VALUES (1)) AS punto(n)
        OUTER APPLY (
            SELECT TOP (1) * FROM {BITACORA}
            WHERE fecha_operacional >= :corte AND
                (CAST(:fecha AS date) IS NULL OR fecha_operacional < :fecha
                 OR (fecha_operacional=:fecha AND turno<=:turno))
            ORDER BY fecha_operacional DESC, turno DESC, fecha_registro DESC, id DESC
        ) AS a
    '''), {"fecha":fecha, "turno":turno, "corte":CORTE}).mappings().one())


def obtener_estado_contingencia(fecha, turno):
    fecha = validar_periodo(fecha, turno)
    with _engine_dev().connect() as conn:
        return _estado(conn, fecha, turno)


def obtener_estado_actual():
    """Acción vigente ahora, sin adelantar cierres programados del rango (Chile, 08/20 h)."""
    with _engine_dev().connect() as conn:
        punto = conn.execute(text('''WITH reloj AS (
            SELECT CONVERT(datetime2, SYSUTCDATETIME() AT TIME ZONE 'UTC'
                AT TIME ZONE 'Pacific SA Standard Time') AS local
        ) SELECT CONVERT(date,DATEADD(hour,-8,local)) AS fecha,
            CASE WHEN CONVERT(time,local)>='08:00' AND CONVERT(time,local)<'20:00'
                 THEN 'A' ELSE 'B' END AS turno FROM reloj''')).mappings().one()
        return _estado(conn, punto['fecha'], punto['turno'])


def _preview(conn, fecha, turno):
    return pd.read_sql(text(f'''SELECT fecha_operacional, turno, equipo_codigo,
        estado_tecnico_pi, estado_fronteras, contingencia_pi_activa, estado_operacional,
        motivo_contingencia, valor_pi_final, valor_turno_tum, pi_disponible_operacional,
        tum_disponible_operacional, fuente_resuelta, valor_final_resuelto, motivo_decision,
        usuario_estado_operacional, fecha_registro_estado_operacional,
        fecha_accion_vigente, turno_accion_vigente
        FROM {RESOLVEDOR}
        WHERE fecha_operacional=:fecha AND turno=:turno
          AND equipo_codigo IN ('CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108',
                                'SRR_CV001','SRR_CV002','SRR_CV003','RIPIOS_CV025')
        ORDER BY equipo_codigo'''), conn, params={"fecha":fecha,"turno":turno})


def obtener_preview_turno(fecha, turno):
    fecha = validar_periodo(fecha, turno)
    with _engine_dev().connect() as conn:
        return _preview(conn, fecha, turno)


def obtener_historial_contingencias():
    with _engine_dev().connect() as conn:
        return pd.read_sql(text(f'''SELECT id,fecha_operacional,turno,accion,motivo,comentario,
            usuario,fecha_registro FROM {BITACORA}
            WHERE fecha_operacional>=:corte ORDER BY fecha_registro DESC,id DESC'''),
            conn, params={"corte":CORTE})


def obtener_apilado(fecha, turno):
    fecha = validar_periodo(fecha, turno)
    with _engine_dev().connect() as conn:
        return pd.read_sql(text('''SELECT Fecha,
            CASE WHEN :turno='A' THEN TMH_CV008_A ELSE TMH_CV008_B END AS CV008,
            CASE WHEN :turno='A' THEN TMH_CV108_A ELSE TMH_CV108_B END AS CV108,
            CASE WHEN :turno='A' THEN TMH_Apilado_Total_A ELSE TMH_Apilado_Total_B END AS Total_turno,
            TMH_Apilado_Total_Dia, Fecha_Calculo
            FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test WHERE Fecha=:fecha'''),
            conn, params={"fecha":fecha,"turno":turno})


def _ultima_fecha_materializable(conn):
    # Incluye pendientes: su NULL también debe actualizar el apilado.
    # El límite se obtiene de SQL, nunca de fechas futuras inventadas ni conteos 12/24.
    return conn.execute(text(f'''SELECT MAX(fecha_operacional) FROM {RESOLVEDOR}
        WHERE equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108')
          AND fecha_operacional>=:corte
          AND fecha_operacional<=CONVERT(date,SYSDATETIME())'''), {"corte":CORTE}).scalar()


def _ultimo_periodo_materializable(conn):
    row = conn.execute(text(f'''SELECT TOP (1) fecha_operacional, turno FROM {RESOLVEDOR}
        WHERE equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108')
          AND fecha_operacional>=:corte
          AND fecha_operacional<=CONVERT(date,SYSDATETIME())
        ORDER BY fecha_operacional DESC, turno DESC'''), {'corte': CORTE}).mappings().first()
    if not row:
        raise ValueError('No existe un período operacional materializable.')
    return row['fecha_operacional'], row['turno']


def obtener_ultimo_periodo_materializable():
    with _engine_dev().connect() as conn:
        return _ultimo_periodo_materializable(conn)


def _validar_materializable(conn, fecha, turno):
    if (fecha, turno) > _ultimo_periodo_materializable(conn):
        raise ValueError('No es posible iniciar una contingencia en un período futuro o aún no materializable.')


def reprocesar_apilado(conn, inicio, fin):
    """
    Reprocesa PI/TUM y deja coherentes las capas downstream de
    Reportabilidad dentro de la misma transacción del llamador.

    Secuencia:
        Apilado -> Histórico -> Factor -> Clays -> Cache emisión

    inicio/fin son inclusivos.
    El cache recibe fecha_fin exclusiva.
    """
    _assert_dev_connection(conn)

    if inicio < CORTE or fin < inicio:
        raise ValueError("Rango de reproceso inválido.")

    # ---------------------------------------------------------
    # 1. Apilado TMH
    # Fuerza exactamente toda la ventana afectada.
    # ---------------------------------------------------------
    conn.execute(
        text("""
            DECLARE @dias int =
                DATEDIFF(day, :inicio, :fin) + 1;

            EXEC inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test
                @FechaInicio   = :inicio,
                @FechaFin      = :fin,
                @DiasReproceso = @dias;
        """),
        {
            "inicio": inicio,
            "fin": fin,
        },
    ).close()

    print(
        f"[PI/TUM] Apilado actualizado: "
        f"{inicio} -> {fin}"
    )

    # ---------------------------------------------------------
    # 2. Histórico de apilado
    # No ampliar el rango ya materializado.
    # ---------------------------------------------------------
    conn.execute(
        text("""
            EXEC inventar_SpcHidr.sp_refrescar_historico_apilado_test
                @FechaInicio   = :inicio,
                @FechaFin      = :fin,
                @DiasReproceso = 0;
        """),
        {
            "inicio": inicio,
            "fin": fin,
        },
    ).close()

    print(
        f"[PI/TUM] Histórico actualizado: "
        f"{inicio} -> {fin}"
    )

    # ---------------------------------------------------------
    # 3. Factor de ajuste camiones
    # Histórico ya está coherente.
    # ---------------------------------------------------------
    conn.execute(
        text("""
            EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test
                @FechaInicio   = :inicio,
                @FechaFin      = :fin,
                @DiasReproceso = 0;
        """),
        {
            "inicio": inicio,
            "fin": fin,
        },
    ).close()

    print(
        f"[PI/TUM] Factor actualizado: "
        f"{inicio} -> {fin}"
    )

    # ---------------------------------------------------------
    # 4. Clays / CuFe
    # Misma vigencia utilizada por Reporte por Turno.
    # ---------------------------------------------------------
    conn.execute(
        text("""
            DECLARE @inicio_clays date =
                CASE
                    WHEN CAST(:inicio AS date) < CAST('2026-08-01' AS date)
                        THEN CAST('2026-08-01' AS date)
                    ELSE CAST(:inicio AS date)
                END;

            DECLARE @fin_clays date = CAST(:fin AS date);

            IF @fin_clays >= CAST('2026-08-01' AS date)
            BEGIN
                EXEC inventar_SpcHidr.sp_refrescar_clays_cufe
                    @FechaInicio      = @inicio_clays,
                    @FechaFin         = @fin_clays,
                    @SoloVistaPrevia  = 0;
            END;
        """),
        {
            "inicio": inicio,
            "fin": fin,
        },
    ).close()

    print(
        f"[PI/TUM] Clays/CuFe procesado: "
        f"{inicio} -> {fin}"
    )

    # ---------------------------------------------------------
    # 5. Cache Reporte por Turno
    # El SP trabaja con fecha final exclusiva.
    # ---------------------------------------------------------
    conn.execute(
        text("""
            DECLARE @fin_exclusivo date =
                DATEADD(day, 1, CAST(:fin AS date));

            EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test
                @fecha_inicio = :inicio,
                @fecha_fin    = @fin_exclusivo;
        """),
        {
            "inicio": inicio,
            "fin": fin,
        },
    ).close()

    print(
        f"[PI/TUM] Cache emisión actualizado: "
        f"{inicio} -> {fin} inclusive"
    )


def _validar_accion(fecha, turno, accion, motivo, comentario, usuario):
    fecha = validar_periodo(fecha, turno)
    if accion not in ACCIONES:
        raise ValueError("Acción de contingencia inválida.")
    if accion == "ACTIVAR_CONTINGENCIA" and motivo not in MOTIVOS:
        raise ValueError("Seleccione el motivo de la contingencia.")
    if not isinstance(usuario, str) or not usuario.strip():
        raise ValueError("No fue posible identificar al usuario de la sesión. La acción no fue registrada.")
    if len(usuario.encode("utf-16-le")) > 510:
        raise ValueError("El usuario supera el largo permitido.")
    if comentario is not None and (not isinstance(comentario, str) or len(comentario.encode("utf-16-le")) > 2000):
        raise ValueError("El comentario supera 1000 caracteres.")
    return fecha


def _registrar_y_reprocesar(conn, fecha, turno, accion, motivo, comentario, usuario,
                           accion_vigente_esperada=None):
    """Usa la transacción del llamador; no hace COMMIT intermedio."""
    _assert_dev_connection(conn)
    fecha = _validar_accion(fecha, turno, accion, motivo, comentario, usuario)
    _validar_materializable(conn, fecha, turno)
    _adquirir_lock_contingencia(conn)
    estado = _estado(conn, fecha, turno)
    if accion_vigente_esperada is not None and (estado['accion_vigente_id'] or 0) != accion_vigente_esperada:
        raise ValueError("El estado cambió desde la confirmación. Actualice y revise la acción.")
    activa = bool(estado['contingencia_pi_activa'])
    if accion == 'ACTIVAR_CONTINGENCIA' and activa:
        raise ValueError("Ya existe una contingencia activa en el período seleccionado.")
    if accion == 'CERRAR_CONTINGENCIA' and not activa:
        raise ValueError("No existe una contingencia activa para cerrar en ese período.")
    inicio = fecha if accion == 'ACTIVAR_CONTINGENCIA' else estado['fecha_accion_vigente']
    fin = _ultima_fecha_materializable(conn)
    if fin is None or fecha > fin or inicio < CORTE:
        raise ValueError("El período está fuera del intervalo actualmente materializable.")
    row = conn.execute(text('''EXEC inventar_SpcHidr.sp_registrar_contingencia_pi_test
        @FechaOperacional=:fecha, @Turno=:turno, @Accion=:accion,
        @Motivo=:motivo, @Comentario=:comentario, @Usuario=:usuario;'''),
        {"fecha":fecha,"turno":turno,"accion":accion,
         "motivo":motivo if accion=='ACTIVAR_CONTINGENCIA' else None,
         "comentario":comentario or None,"usuario":usuario}).mappings().one()
    reprocesar_apilado(conn, inicio, fin)
    preview = _preview(conn, fecha, turno)
    pendientes = preview.loc[preview.fuente_resuelta=='PENDIENTE_TUM','equipo_codigo'].tolist()
    return {"id":row['id'], "inicio":inicio, "fin":fin, "pendientes_tum":pendientes}


def registrar_contingencia(fecha, turno, accion, motivo, comentario, usuario,
                          accion_vigente_esperada=None):
    fecha = _validar_accion(fecha, turno, accion, motivo, comentario, usuario)
    with _engine_dev().begin() as conn:
        return _registrar_y_reprocesar(conn, fecha, turno, accion, motivo, comentario, usuario,
                                      accion_vigente_esperada)


PARAMETROS_FACTOR_CAMIONES = {
    'LIMITE_CARGA_AJUSTE': {
        'nombre': 'Límite máximo',
        'columnas': ('Limite_KOM_TMH_Viaje', 'Limite_CAT_TMH_Viaje'),
    },
    'CARGA_NOMINAL_TMH_VIAJE': {
        'nombre': 'Carga nominal',
        'columnas': ('Carga_Nominal_KOM_TMH_Viaje', 'Carga_Nominal_CAT_TMH_Viaje'),
    },
}


def _categoria_parametro_factor(parametro):
    if not isinstance(parametro, str) or parametro not in PARAMETROS_FACTOR_CAMIONES:
        raise ValueError('Seleccione una categoría de parámetro válida.')
    return PARAMETROS_FACTOR_CAMIONES[parametro]


def validar_parametro_factor(parametro, flota, valor, vigencia_desde, motivo, usuario):
    _categoria_parametro_factor(parametro)
    from decimal import Decimal, InvalidOperation
    if flota not in ('KOM', 'CAT'):
        raise ValueError('Seleccione una flota KOM o CAT.')
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero <= 0 or numero >= Decimal('1000000000000'):
            raise ValueError
        if numero != numero.quantize(Decimal('0.000001')):
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValueError('El valor debe ser positivo, con hasta seis decimales y doce dígitos enteros.') from None
    try:
        fecha = date.fromisoformat(str(vigencia_desde))
    except (ValueError, TypeError):
        raise ValueError('Seleccione una fecha válida.') from None
    if not isinstance(motivo, str) or not motivo.strip() or len(motivo) > 1000:
        raise ValueError('Ingrese un motivo de hasta 1000 caracteres.')
    if not isinstance(usuario, str) or not usuario.strip() or len(usuario) > 128:
        raise ValueError('No fue posible identificar al usuario autenticado.')
    return dict(parametro=parametro, flota=flota, valor=numero, vigencia_desde=fecha,
                motivo=motivo.strip(), usuario=usuario.strip())


def validar_limite_factor(flota, valor, vigencia_desde, motivo, usuario):
    valores = validar_parametro_factor('LIMITE_CARGA_AJUSTE', flota, valor,
                                       vigencia_desde, motivo, usuario)
    valores.pop('parametro')
    return valores


def obtener_historial_limites_factor():
    return obtener_historial_parametros_factor('LIMITE_CARGA_AJUSTE')


def obtener_historial_parametros_factor(parametro):
    _categoria_parametro_factor(parametro)
    with _engine_dev().connect() as conn:
        return pd.read_sql(text('''SELECT id,parametro,flota,valor,vigencia_desde,vigencia_hasta,
            motivo,usuario_registro,fecha_registro,activo
            FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE parametro=:parametro
            ORDER BY vigencia_desde DESC,flota'''), conn, params={'parametro': parametro})


def obtener_limites_factor_vigentes(fecha):
    return obtener_parametros_factor_vigentes('LIMITE_CARGA_AJUSTE', fecha)


def obtener_parametros_factor_vigentes(parametro, fecha):
    _categoria_parametro_factor(parametro)
    fecha = date.fromisoformat(str(fecha))
    with _engine_dev().connect() as conn:
        df = pd.read_sql(text('''SELECT parametro,flota,valor,vigencia_desde,vigencia_hasta
            FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE parametro=:parametro AND activo=1
              AND vigencia_desde<=:fecha AND (vigencia_hasta IS NULL OR :fecha<vigencia_hasta)
            ORDER BY flota'''), conn, params={'fecha':fecha, 'parametro':parametro})
    if len(df) != 2 or set(df.flota) != {'KOM','CAT'}:
        raise ValueError('No existe una configuración única KOM/CAT para la fecha consultada.')
    return df


def obtener_pendientes_limites_factor():
    return obtener_pendientes_parametros_factor('LIMITE_CARGA_AJUSTE')


def obtener_pendientes_parametros_factor(parametro):
    """Compara configuración y fotografía materializada; nunca reprocesa.

    Los nombres SQL proceden exclusivamente de la whitelist interna.
    Conserva aliases limite_* para compatibilidad de los consumidores actuales.
    """
    kom, cat = _categoria_parametro_factor(parametro)['columnas']
    with _engine_dev().connect() as conn:
        return pd.read_sql(text(f'''SELECT v.Fecha,p.parametro,p.flota,p.valor AS limite_configurado,
            CASE p.flota WHEN 'KOM' THEN v.{kom} ELSE v.{cat} END AS limite_utilizado
            FROM inventar_SpcHidr.v_ajuste_camiones_emision_test v
            JOIN inventar_SpcHidr.factor_camiones_parametro_vigencia_test p
              ON p.vigencia_desde<=v.Fecha AND (p.vigencia_hasta IS NULL OR v.Fecha<p.vigencia_hasta)
            WHERE p.activo=1 AND p.parametro=:parametro
              AND (CASE p.flota WHEN 'KOM' THEN v.{kom} ELSE v.{cat} END IS NULL
                   OR CAST(CASE p.flota WHEN 'KOM' THEN v.{kom} ELSE v.{cat} END AS decimal(18,6))
                      <> CAST(p.valor AS decimal(18,6)))
            ORDER BY v.Fecha,p.flota'''),conn,params={'parametro':parametro})


def registrar_parametro_factor(parametro, flota, valor, vigencia_desde, motivo, usuario):
    valores = validar_parametro_factor(parametro, flota, valor, vigencia_desde, motivo, usuario)
    with _engine_dev().begin() as conn:
        _assert_dev_connection(conn)
        return dict(conn.execute(text('''EXEC inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test
            @Parametro=:parametro, @Flota=:flota, @Valor=:valor, @VigenciaDesde=:vigencia_desde,
            @Motivo=:motivo, @Usuario=:usuario'''), valores).mappings().one())


def registrar_limite_factor(flota, valor, vigencia_desde, motivo, usuario):
    valores = validar_limite_factor(flota, valor, vigencia_desde, motivo, usuario)
    with _engine_dev().begin() as conn:
        _assert_dev_connection(conn)
        return dict(conn.execute(text('''EXEC inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
            @Flota=:flota, @Valor=:valor, @VigenciaDesde=:vigencia_desde,
            @Motivo=:motivo, @Usuario=:usuario'''), valores).mappings().one())


def validar_override_factor(fecha_desde, fecha_hasta, modo, motivo, usuario):
    try:
        inicio = date.fromisoformat(str(fecha_desde))
        fin = date.fromisoformat(str(fecha_hasta))
    except (ValueError, TypeError):
        raise ValueError('Seleccione fechas válidas.') from None
    if fin < inicio:
        raise ValueError('Hasta no puede ser anterior a Desde.')
    if modo not in ('FORZADO_1', 'AUTOMATICO'):
        raise ValueError('Modo de aplicación inválido.')
    if not isinstance(motivo, str) or not motivo.strip() or len(motivo) > 1000:
        raise ValueError('Ingrese un motivo de hasta 1000 caracteres.')
    if not isinstance(usuario, str) or not usuario.strip() or len(usuario) > 128:
        raise ValueError('Se requiere un usuario autenticado de hasta 128 caracteres.')
    return dict(fecha_desde=inicio, fecha_hasta=fin, modo=modo, motivo=motivo.strip(), usuario=usuario.strip())


def obtener_historial_override_factor():
    with _engine_dev().connect() as conn:
        return pd.read_sql(text('''SELECT id_override,fecha_desde,fecha_hasta,modo,motivo,usuario,fecha_registro
            FROM inventar_SpcHidr.factor_camiones_override_aplicacion_test
            ORDER BY fecha_registro DESC,id_override DESC'''), conn)


def _version_override_rango(conn, fecha_desde, fecha_hasta, bloquear=False):
    # HOLDLOCK protege también frente a altas que invoquen el SP sin applock.
    hint = 'WITH (UPDLOCK,HOLDLOCK)' if bloquear else ''
    return conn.execute(text(f'''SELECT MAX(id_override)
        FROM inventar_SpcHidr.factor_camiones_override_aplicacion_test {hint}
        WHERE fecha_desde<=:hasta AND fecha_hasta>=:desde'''),
        {'desde':fecha_desde,'hasta':fecha_hasta}).scalar()


def obtener_version_override_rango(fecha_desde, fecha_hasta):
    inicio, fin = date.fromisoformat(str(fecha_desde)), date.fromisoformat(str(fecha_hasta))
    if fin < inicio:
        raise ValueError('Hasta no puede ser anterior a Desde.')
    with _engine_dev().connect() as conn:
        return _version_override_rango(conn, inicio, fin)


def registrar_override_factor(fecha_desde, fecha_hasta, modo, motivo, usuario, version_esperada):
    payload = validar_override_factor(fecha_desde, fecha_hasta, modo, motivo, usuario)
    with _engine_dev().begin() as conn:
        _assert_dev_connection(conn)
        lock = conn.execute(text('''DECLARE @resultado int;
            EXEC @resultado=sys.sp_getapplock @Resource='SIIR_FACTOR_CAMIONES_OVERRIDE_2B',
                @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=15000;
            SELECT @resultado;''')).scalar()
        if lock is None or lock < 0:
            raise ValueError('Otro registro está en proceso. Revise nuevamente la solicitud.')
        actual = _version_override_rango(conn, payload['fecha_desde'], payload['fecha_hasta'], bloquear=True)
        if actual != version_esperada:
            raise ValueError('El historial cambió desde la confirmación. Revise nuevamente la solicitud.')
        return dict(conn.execute(text('''EXEC inventar_SpcHidr.sp_registrar_override_factor_camiones_test
            @FechaDesde=:fecha_desde, @FechaHasta=:fecha_hasta, @Modo=:modo,
            @Motivo=:motivo, @Usuario=:usuario'''), payload).mappings().one())


FACTOR_CAMIONES_SQL = """
SELECT Fecha, Humedad_Pct, Sal_TMH_Dia, Delta_Inventario_Chancado_TMS,
       Limite_KOM_TMH_Viaje, Limite_CAT_TMH_Viaje,
       Carga_Nominal_KOM_TMH_Viaje, Carga_Nominal_CAT_TMH_Viaje,
       Estado_Fuente_MOV_CAM, Estado_Fuente_POWERBI,
       Apilado_TMH_Bruto_Original, Apilado_TMS_Bruto_Sin_Ajuste,
       Apilado_TMS_Neto_Sin_Ajuste, Chancado_TMH_Sin_Ajuste, Chancado_TMS_Sin_Ajuste,
       Chancado_TMS_Reporte,
       Produccion_KOM_TMH, Produccion_CAT_TMH, KOM_TMH_Corregido, CAT_TMH_Corregido,
       Vueltas_KOM, Vueltas_CAT,
       Carga_KOM_TMH_Viaje_Sin_Ajuste, Carga_CAT_TMH_Viaje_Sin_Ajuste,
       Factor_Ajuste_Calculado, Factor_Aplicacion_Reportes, Flag_Factor_Ajuste_Valido,
       Estado_Calculo, Regla_Aplicacion, SRR_TMS_Dia, Metodo, Fuente_Camiones, Fecha_Calculo,
       Factor_Aplicacion_Automatica, Flag_Usa_Ajuste_Automatico, Flag_Usa_Ajuste,
       Regla_Aplicacion_Automatica, Modo_Aplicacion, Flag_Override_1,
       Id_Control_Aplicacion, Control_Aplicacion_Motivo, Control_Aplicacion_Usuario,
       Control_Aplicacion_Fecha_Registro
FROM inventar_SpcHidr.v_ajuste_camiones_emision_test
WHERE Fecha >= :fecha_inicio AND Fecha <= :fecha_fin
ORDER BY Fecha
"""


def obtener_factor_camiones(fecha_inicio, fecha_fin):
    """Diagnóstico de solo lectura; los factores son autoridad de la vista."""
    try:
        inicio = date.fromisoformat(str(fecha_inicio))
        fin = date.fromisoformat(str(fecha_fin))
    except (ValueError, TypeError):
        raise ValueError("Seleccione fechas válidas.") from None
    if inicio > fin:
        raise ValueError("La fecha inicial no puede ser posterior a la final.")
    # Conserva el ámbito DEV del monitor y valida una conexión efectiva al leer.
    with _engine_dev().connect() as conn:
        df = pd.read_sql(text(FACTOR_CAMIONES_SQL), conn,
                         params={"fecha_inicio": inicio, "fecha_fin": fin})
    fechas = pd.to_datetime(df["Fecha"], errors="raise").dt.normalize()
    if fechas.isna().any() or fechas.duplicated().any():
        raise ValueError("La vista de factor contiene fechas nulas o duplicadas.")
    return df.assign(Fecha=fechas).sort_values("Fecha", kind="stable").reset_index(drop=True)


def obtener_tendencia_totalizador(fecha_inicio, fecha_fin, correa):
    """Recibe fechas calendario inclusivas y consulta exclusivamente DEV."""
    inicio = date.fromisoformat(str(fecha_inicio))
    fin = date.fromisoformat(str(fecha_fin))
    if inicio > fin or correa not in CORREAS:
        raise ValueError("Seleccione un rango válido y una correa disponible.")
    fin_exclusivo = datetime.combine(fin + timedelta(days=1), time.min)
    if os.getenv("SQLSERVER_DB") != "inventar_SpcHidr":
        raise RuntimeError("Monitoreo PI/TUM habilitado exclusivamente en DEV.")
    engine = get_engine()
    if engine is None or engine.url.database != "inventar_SpcHidr":
        raise RuntimeError("La conexión PI/TUM debe apuntar a DEV.")
    with engine.connect() as conn:
        return pd.read_sql(text("""
            EXEC inventar_SpcHidr.sp_monitor_totalizador_tendencia_test
                @fecha_inicio = :fecha_inicio,
                @fecha_fin = :fecha_fin,
                @correa = :correa;
        """), conn, params={
            "fecha_inicio": datetime.combine(inicio, time.min),
            "fecha_fin": fin_exclusivo,
            "correa": correa,
        })
