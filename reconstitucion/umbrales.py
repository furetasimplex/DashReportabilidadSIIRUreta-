"""Umbrales, convenciones y selectores del motor de reparto de masa apilada.

Un solo lugar para todo numero que decide algo. Antes estaban repartidos entre
la cabecera de engine.py, el cuerpo de sus funciones y constantes sueltas a
mitad de archivo, y algunos ni siquiera tenian nombre (0.999 en mark_status,
0.5 en la cobertura de horas, 24.0 en cuatro sitios distintos).

Regla: si un numero decide si un dato entra, sale, o cambia de camino, vive
aqui y trae escrito de donde salio. Los numeros que solo describen la forma de
un grafico (anchos, colores, paginacion) NO son umbrales y se quedan donde se
usan.

Cada umbral empirico dice contra que ventana de datos se midio. Esos valores
envejecen: validacion.py los vuelve a medir y avisa cuando la data deja de
respaldarlos.
"""

# ─────────────────────────── 1. Ventana operacional ───────────────────────────
# El dia operacional es [fecha 08:00, fecha+1 08:00), verificado contra los
# totalizadores de balanza (Control_Apilado_TMH_v2_test): el turno A de balanza
# cubre 08:00-20:00 y el B 20:00-08:00 del dia siguiente.
SHIFT1_START = 8            # abre la ventana y abre el turno 1
SHIFT1_END = 20             # cruce de turno: cierra el turno 1, abre el turno 2
LARGO_T1 = SHIFT1_END - SHIFT1_START    # h de turno 1
HORAS_DIA = 24.0
LARGO_T2 = HORAS_DIA - LARGO_T1         # h de turno 2

# Frontera turno1/turno2 de respaldo, en fraccion de masa del dia. Solo se usa
# cuando el dia no trae frontera medida (sin pesaje por turno) ni proyectada
# (sin horometro). Es un 50% plano: no pretende ser una medicion.
SHIFT1_FRAC = 0.5


# ─────────────────────────── 2. Avance de modulo ───────────────────────────
# Dos umbrales distintos sobre la misma columna 'avance'. No son el mismo
# numero con ruido: responden preguntas distintas y por eso no se unifican.

# AVANCE_CIERRE — ¿esta fila es un modulo ya terminado que la planilla sigue
# arrastrando? Se aplica solo a filas con vol_diario = 0, donde no hubo
# apiladora. El avance se usa solo para marcar el estado de filas sin volumen.
# sino una etiqueta de estado: en la duda, SIN_INICIO (que tampoco recibe masa)
# es la respuesta segura. Ver engine.mark_status.
AVANCE_CIERRE = 0.999


# ─────────────────────────── 3. Horometro ───────────────────────────
# Horometros que miden apilado de verdad. 'chancador' esta aguas arriba y satura
# en 24 h; 'rotopala' es del circuito de reclamo, aguas abajo — el 2026-07-14 se
# apilaron 91.9 kt en 23.4 h de torre mientras la rotopala marcaba 1 h y el
# chancador 24 h.
HOROMETROS_OK = ("torre",)

# ─────────────────────────── 4. Semana de reconstitucion ───────────────────────
# El levantamiento topografico es DIARIO: el volumen de cada dia es una medicion,
# no un prorrateo. En 422 dias con volumen solo 3 caen en una racha de dias
# consecutivos con el mismo total (2026-08-10/11/12, un bloque repartido en
# partes iguales porque falto el levantamiento) — 0.7% del dato.
#
# La semana NO existe porque el dato sea semanal. Existe porque agrega: en banda
# fisica la densidad diaria da CV 6.60% (n=340) y la semanal 7.31% (n=55) — son
# la misma medicion. Lo que cambia es cuantas unidades salen de banda: 94.2% de
# los dias contra 98.2% de las semanas. Agregar absorbe el dia con volumen
# centinela o sin masa; no mejora la precision, mejora la robustez.
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")

# (dia_inicial, dia_final), indices 0=lunes..6=domingo. Es un SELECTOR, no una
# constante fisica: el ancla no se puede leer del dato — probadas las 7 fases, el
# CV de la densidad semanal queda entre 8.4% y 11.5% sin minimo marcado.
SEMANA_DEF = (0, 6)         # lunes -> domingo, la convencion de plan_semanal_*

# Dias con dato que necesita una semana para que su densidad valga. Las semanas
# cortadas por el borde de la ventana traen el volumen entero contra los pocos
# dias de masa que alcanzaron a entrar: la primera semana de la ventana da
# 0.245 t/m3 con 2 dias, que es basura, no una densidad baja.
DIAS_SEM_MIN = 5


# ─────────────────────────── 5. Validez fisica ───────────────────────────
# Banda de densidad plausible para mineral chancado apilado, t/m3. NO es un
# filtro estadistico: es el rango en que el numero puede ser cierto. La mediana
# semanal medida es 1.735 con CV 9.8%, asi que la banda deja fuera solo lo que
# es error de dato (semanas cortadas, volumen sin su masa, division por un
# levantamiento incompleto). Una densidad fuera de aqui no se corrige: se marca
# y se conserva señalada para revisión.
RHO_MIN = 1.20
RHO_MAX = 2.30

# La frontera entre turnos es una fraccion: fuera de [0, 1] el dato de origen
# esta roto (masa de turno negativa, o de turno mayor que la del dia).
BOUNDARY_MIN = 0.0
BOUNDARY_MAX = 1.0

# Humedad en fraccion. La real medida en julio 2026 va de 2.95% a 5.37%; la
# banda es ancha a proposito, solo descarta lo imposible.
HUMEDAD_MIN = 0.0
HUMEDAD_MAX = 0.30

# CV por encima del cual una serie esta dominada por ruido y su promedio no
# significa nada. Referencia medida: la densidad diaria CRUDA da CV 1183%, pero
# eso no es ruido de medicion — son 7 filas centinela (3 dias con volumen de
# 1-2 m3 contra un dia entero de tonelaje, 4 dias con TMS 0) que por si solas
# mueven el CV tres ordenes de magnitud. Filtrada a la banda fisica, la misma
# serie da 6.60%. El umbral separa 'serie con artefactos dentro' de 'serie
# limpia'; no dice nada sobre la resolucion a la que se midio.
CV_MAX_CONFIABLE = 0.25

# Tolerancia relativa al cuadrar masa de turnos contra masa del dia. La formula
# del SP reproduce Apilado_TMS_Real desde los dos turnos con error 1e-11; 1e-6
# deja margen de sobra para redondeo de float sin dejar pasar un error real.
TOL_CUADRATURA = 1e-6


# Avance maximo creible. La planilla registra cierres de 0.995-1.004: ruido de
# levantamiento sobre un 100%. Mas alla de esto el avance no es ruido, es un dato
# equivocado — hay 141 filas sobre 1.0 y solo 2 sobre 1.05, asi que el corte
# separa el ruido del error y no parte una poblacion por la mitad.
AVANCE_MAX = 1.05

# Volumen diario bajo el cual una fila modulo-dia es borde del levantamiento y no
# apilado. DIAGNOSTICO: se reporta, no se aplica al motor. Descartarlo cambiaria
# numeros, y hay modulos cuya UNICA fila esta bajo este corte — filtrarla los
# borraria del itinerario. Ver reporte_anomalias.py.
VOL_DIA_MIN = 2000.0        # m3/dia


# ──────────────────── 6. Coherencia entre fuentes ────────────────────
# Los umbrales de arriba miran un valor a la vez y preguntan si puede ser cierto.
# Los de aqui miran DOS registros que tienen que contarse la misma historia y
# preguntan si se contradicen. Un dato corrido de dia, un metro cubico anotado en
# el modulo vecino y un horometro inventado pasan todos los rangos fisicos de uno
# en uno: solo se ven al cruzarlos contra su propio vecino.

# Tolerancia relativa al cerrar el acumulado de un modulo contra sus dias:
# vol_acum_final[t] tiene que ser vol_acum_final[t-1] + vol_diario[t]. Medido
# sobre 1789 filas: 44 se pasan de 1e-6 pero solo 37 de 1e-4, y esas mismas 37
# siguen fuera en 1e-3 — las 7 del medio son redondeo del prorrateo. El corte cae
# en el hueco, no parte una poblacion. Ver validacion.acum_descuadrado.
TOL_ACUM = 1e-4

# Desviacion relativa maxima de la densidad de una semana contra la mediana de
# todas antes de sospechar que un dia se anoto en la semana equivocada. Medido
# sobre 58 semanas completas (mediana 1.721 t/m3): la desviacion absoluta tiene
# mediana 1.5% y percentil 90 en 14%. 0.12 deja fuera la cola sin tocar el
# cuerpo. NO basta por si solo para declarar el error — es solo el filtro que
# selecciona los pares candidatos; la confirmacion es la prueba de reparacion.
DESVIO_SEM_MAX = 0.12

# ─────────────────────────── 7. Selectores ───────────────────────────
# Tecnica para cortar el dia en turno 1 / turno 2.
BOUNDARY_SRC = {
    # frontera medida: cuanta masa seca pesaron las balanzas en el turno 1
    "masa": "boundary",
    # frontera proyectada: el apilador corre a tonelaje constante, asi que el
    # volumen (y con el la masa) de cada turno es proporcional a las horas que
    # el horometro de torre marca entregando en ese turno. Contra la pesada:
    # corr 0.94, error medio 0.031, peor caso 0.12.
    "horas": "boundary_h",
}

def opcion(nombre, valor, validos):
    """Valida un selector y lo devuelve. Un selector mal escrito tiene que
    reventar, no caer a un camino por defecto: antes un boundary_src con typo
    dejaba al motor repartiendo todos los dias con el 50% fijo, sin error y con
    el nombre equivocado escrito en el resultado."""
    if valor not in validos:
        raise ValueError(
            f"{nombre} debe ser uno de {tuple(validos)}; se recibio {valor!r}")
    return valor
