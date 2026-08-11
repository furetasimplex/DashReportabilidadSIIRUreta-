"""Reportes de representatividad de torres dibujados directo en Python.

Reemplaza el camino xlsx -> LibreOffice -> PDF. El motivo es reproducibilidad:
LibreOffice decide alto de fila, escala de impresion y ubicacion de los objetos
anclados segun su version, y eso desplazaba el grafico FY sobre la tabla en el
servidor pero no en Windows. Aca la geometria la fija este archivo.

No importa nada de la app: recibe los DataFrames ya calculados (los mismos que
alimentan el Excel) y devuelve bytes de PDF. Asi no hay ciclo de imports y se
puede probar suelto.

Tipografia: Helvetica, que viene incrustada en reportlab. No se instala ni se
sustituye nada, o sea que Ubuntu pelado y Windows miden igual.
"""
from __future__ import annotations

import io
import os

import pandas as pd

# Paleta tomada de la hoja Excel oficial.
TINTA = "#476475"
NARANJA = "#E65400"
AZUL_FILA = "#D7E1E7"
AMARILLO = "#FFF2CC"
GRIS = "#F2F2F2"
VERDE = "#70AD47"
ROJO = "#C55A11"
BORDE = "#595959"
TARGET = "#4F81BD"
BLANCO = "#FFFFFF"

TARGET_REPRESENTATIVIDAD = 0.85
RADIO_SEMAFORO = 2.6

_MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre",
    12: "Diciembre",
}

# Ancho util del lienzo alto donde se dibuja todo antes de normalizar a A3.
ANCHO = 841.89
MARGEN = 24.0
# ponytail: un unico lienzo altisimo en vez de paginar. Lo que sobre lo recorta
# normalize_single_page_to_a3. Si algun mes se pasara de aca, reportlab crea una
# segunda pagina y _stack_pages_vertically la vuelve a unir: no se rompe, solo
# deja de ser una sola pasada.
ALTO_LIENZO = 3200.0

LOGO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "logoBHP.png",
)


# ──────────────────────────────────────────────────────────────────────────
# Estilos
# ──────────────────────────────────────────────────────────────────────────

def _estilos():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    def p(nombre, size, **kw):
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("textColor", TINTA)
        kw.setdefault("leading", size * 1.15)
        return ParagraphStyle(nombre, fontSize=size, **kw)

    return {
        "titulo": p("titulo", 11, fontName="Helvetica-Bold", leading=14,
                    alignment=TA_CENTER),
        "institucional": p("institucional", 7.5, fontName="Helvetica-Bold",
                           alignment=TA_RIGHT, leading=9.5),
        "seccion": p("seccion", 7.5, fontName="Helvetica-Bold"),
        "th": p("th", 6.5, fontName="Helvetica-Bold", alignment=TA_CENTER),
        "th_suave": p("th_suave", 6.5, alignment=TA_CENTER),
        "td": p("td", 6.5, alignment=TA_CENTER, textColor="#000000"),
        "td_izq": p("td_izq", 6, alignment=TA_LEFT, textColor="#000000"),
        "td_mtd": p("td_mtd", 6.5, fontName="Helvetica-Bold",
                    alignment=TA_CENTER),
        "target": p("target", 7.5, fontName="Helvetica-Bold"),
    }


def _semaforo(valor):
    """Circulo verde (1) / naranja (0) / vacio (None), como en la hoja.

    Se dibuja como figura y no como glifo: el U+25CF del Excel no existe en la
    codificacion WinAnsi de Helvetica, y el circulo de ZapfDingbats salia
    cuadrado. Un Circle no depende de ninguna fuente.
    """
    from reportlab.graphics.shapes import Circle, Drawing
    from reportlab.lib.colors import HexColor

    numero = _entero(valor)
    if numero not in (0, 1):
        return ""
    lienzo = Drawing(RADIO_SEMAFORO * 2, RADIO_SEMAFORO * 2)
    lienzo.hAlign = "CENTER"
    lienzo.add(Circle(
        RADIO_SEMAFORO, RADIO_SEMAFORO, RADIO_SEMAFORO,
        fillColor=HexColor(VERDE if numero == 1 else ROJO),
        strokeColor=None,
    ))
    return lienzo


def _pct(valor, decimales=1):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return f"{valor * 100:.{decimales}f}%".replace(".", ",")


def _texto(valor):
    """Celda de texto. `valor or ""` no sirve: NaN es truthy y sale "nan"."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor)


def _entero(valor):
    """Normaliza a 0/1/None; el detalle trae NaN y numpy floats mezclados."""
    numero = pd.to_numeric(valor, errors="coerce")
    return None if pd.isna(numero) else int(numero)


def _miles(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    entero, _, dec = f"{float(valor):,.1f}".partition(".")
    return f"{entero.replace(',', '.')},{dec}"


# ──────────────────────────────────────────────────────────────────────────
# Graficos (matplotlib -> PNG)
# ──────────────────────────────────────────────────────────────────────────

def _figura_a_imagen(fig, ancho_pt):
    """Escala la figura al ancho pedido conservando su proporcion.

    El alto no se impone: bbox_inches="tight" recorta la figura a su contenido,
    asi que el PNG no mide lo que pidio figsize. Forzar ambos lados deformaba el
    grafico (se veia estirado, sobre todo el de la seccion 6).
    """
    from PIL import Image as PilImage
    from reportlab.platypus import Image

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight",
                facecolor="white")
    buffer.seek(0)
    import matplotlib.pyplot as plt
    plt.close(fig)

    ancho_px, alto_px = PilImage.open(buffer).size
    buffer.seek(0)
    return Image(buffer, width=ancho_pt, height=ancho_pt * alto_px / ancho_px)


def _enmarcar(imagen, ancho_pt):
    """Recuadro gris alrededor del grafico, como el borde del objeto en Excel."""
    from reportlab.platypus import Table, TableStyle

    marco = Table([[imagen]], colWidths=[ancho_pt])
    marco.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, "#7F8F9B"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return marco


def _grafico_barras_apiladas(filas, etiqueta_rep, etiqueta_perdidas, titulo,
                             ancho_pt, alto_pt):
    """Columnas 100% apiladas con linea de target, una por semana + MTD."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    periodos = [f["Periodo"] for f in filas]
    rep = [float(f["Pct_Representativos"] or 0.0) for f in filas]
    no_rep = [float(f["Pct_No_Representativos"] or 0.0) for f in filas]
    x = range(len(periodos))

    fig, ax = plt.subplots(figsize=(ancho_pt / 72.0, alto_pt / 72.0))
    ax.bar(x, rep, color=TINTA, width=0.55, label=etiqueta_rep)
    ax.bar(x, no_rep, bottom=rep, color=NARANJA, width=0.55,
           label=etiqueta_perdidas)
    ax.axhline(TARGET_REPRESENTATIVIDAD, color=TARGET, linestyle="--",
               linewidth=1.2, label="Target")

    for indice, (valor_rep, valor_no) in enumerate(zip(rep, no_rep)):
        if valor_rep > 0.06:
            ax.text(indice, valor_rep / 2, _pct(valor_rep), ha="center",
                    va="center", color="white", fontsize=6, fontweight="bold")
        if valor_no > 0.06:
            ax.text(indice, valor_rep + valor_no / 2, _pct(valor_no),
                    ha="center", va="center", color="white", fontsize=6,
                    fontweight="bold")

    ax.set_ylim(0, 1)
    ax.set_yticks([n / 10 for n in range(11)])
    ax.set_xticks(list(x))
    ax.set_xticklabels(periodos, fontsize=5.5, color="#595959")
    ax.set_ylabel("Muestras representativas", fontsize=5, color=TINTA)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.tick_params(axis="y", labelsize=5, colors="#595959", length=0)
    ax.tick_params(axis="x", length=0)
    # Título arriba y la leyenda debajo de él, ambos fuera del área de dibujo.
    # El pad tiene que superar el alto de la leyenda o se pisan.
    ax.set_title(titulo, fontsize=7, color="#595959", fontweight="bold",
                 pad=22)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
              fontsize=5, frameon=False, columnspacing=1.4, handlelength=1.8)
    ax.yaxis.grid(True, color=TINTA, linewidth=0.2)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(TINTA)
    ax.spines["bottom"].set_linewidth(0.8)

    return _enmarcar(_figura_a_imagen(fig, ancho_pt), ancho_pt)


def _grafico_gestion_fy(df_fy, titulo, ancho_pt, alto_pt):
    """Barras de representatividad por mes fiscal + linea de objetivo.

    La ultima barra (YTD) va en naranja, igual que en la hoja.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    etiquetas = [str(v) for v in df_fy["Etiqueta"]]
    valores = [float(v) for v in df_fy["Representatividad"]]
    objetivos = [float(v) for v in df_fy["Objetivo"]]
    colores = [TINTA] * len(valores)
    if colores:
        colores[-1] = NARANJA
    x = range(len(etiquetas))

    fig, ax = plt.subplots(figsize=(ancho_pt / 72.0, alto_pt / 72.0))
    ax.bar(x, valores, color=colores, width=0.6, label="Representatividad")
    ax.plot(list(x), objetivos, color=TARGET, linestyle="--", linewidth=1.8,
            label="Target")

    for indice, valor in enumerate(valores):
        # Sobre la barra, igual que en el Excel: así los porcentajes bajos y
        # el 0,0% no desaparecen por falta de espacio dentro de la columna.
        posicion_y = min(valor + 0.015, 0.985)
        alineacion_y = "bottom" if valor < 0.97 else "top"
        ax.text(indice, posicion_y, _pct(valor), ha="center", va=alineacion_y,
                color="#595959", fontsize=6.5, fontweight="bold")

    ax.set_ylim(0, 1)
    ax.set_xticks(list(x))
    ax.set_xticklabels(etiquetas, fontsize=6.5, color="#595959")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.tick_params(axis="y", labelsize=6.5, colors="#595959", length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_title(titulo, fontsize=10, color="#595959", fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2,
              fontsize=6.5, frameon=False)
    ax.yaxis.grid(True, color="#D9D9D9", linewidth=0.5)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#D9D9D9")

    return _enmarcar(_figura_a_imagen(fig, ancho_pt), ancho_pt)


# ──────────────────────────────────────────────────────────────────────────
# Bloques del reporte
# ──────────────────────────────────────────────────────────────────────────

def _encabezado(tipo_titulo, fecha_base, estilos, ancho, titulo=None):
    """Institucional + logo arriba a la derecha, y el titulo centrado debajo."""
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

    mes = f"{_MESES[fecha_base.month]}, {fecha_base.year}"
    institucional = Paragraph(
        "Superintendencia de Medición y Reconciliación<br/>"
        "Gerencia Planificación Integrada",
        estilos["institucional"],
    )
    logo = Image(LOGO, width=76, height=31) if os.path.isfile(LOGO) else ""
    banda = Table([["", institucional, logo]],
                  colWidths=[ancho - 300, 210, 90])
    banda.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    texto = Paragraph(
        titulo or (
            "Muestras representativas de torres de muestreo - "
            f"Muestra {tipo_titulo} - {mes}"
        ),
        estilos["titulo"],
    )
    return [banda, Spacer(1, 8), texto, Spacer(1, 12)]


def _titulo_seccion(texto, estilos, ancho):
    """Titulo con la linea inferior que usa la hoja oficial."""
    from reportlab.platypus import Paragraph, Table, TableStyle

    tabla = Table([[Paragraph(texto, estilos["seccion"])]], colWidths=[ancho])
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabla


def _tabla_tonelaje(tonelaje, estilos, ancho):
    from reportlab.platypus import Paragraph, Table, TableStyle

    cabecera = [
        Paragraph("Pad", estilos["th"]),
        Paragraph("Mineral Apilado (ton)", estilos["th"]),
        "", "",
    ]
    filas = [cabecera]
    for fila in tonelaje:
        filas.append([
            Paragraph(str(fila["Pad"]), estilos["td"]),
            Paragraph(str(fila["Estado"]), estilos["td"]),
            Paragraph(_miles(fila["Tonelaje"]), estilos["td"]),
            Paragraph(_pct(fila["Distribucion"]), estilos["td"]),
        ])

    anchos = [a / 62.58 * ancho for a in (15.08, 15.5, 16.5, 15.5)]
    tabla = Table(filas, colWidths=anchos, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("SPAN", (1, 0), (3, 0)),
        # Oxido ocupa las dos primeras filas de datos y Sulfuro las dos
        # siguientes; el nombre del material va una sola vez, combinado.
        ("SPAN", (0, 1), (0, 2)),
        ("SPAN", (0, 3), (0, 4)),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDE),
        ("LINEBELOW", (0, 2), (-1, 2), 1.0, BORDE),
        ("LINEAFTER", (0, 0), (2, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tabla


def _tabla_resumen(filas, encabezados, estilos, ancho):
    from reportlab.platypus import Paragraph, Table, TableStyle

    datos = [[Paragraph(h, estilos["th_suave"]) for h in encabezados]]
    for fila in filas:
        estilo = estilos["td_mtd"] if fila["Periodo"] == "MTD" else estilos["td"]
        datos.append([
            Paragraph(str(fila["Periodo"]), estilo),
            Paragraph(_pct(fila["Pct_Representativos"]), estilo),
            Paragraph(_pct(fila["Pct_No_Representativos"]), estilo),
            Paragraph(_pct(fila["Total"], 0), estilo),
        ])

    anchos = [a / 62.58 * ancho for a in (15.08, 15.5, 16.5, 15.5)]
    tabla = Table(datos, colWidths=anchos, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDE),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, BORDE),
        ("LINEAFTER", (0, 0), (2, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return tabla


# Proporciones medidas sobre el PDF de referencia: la columna de tablas ocupa
# el 41% del ancho de contenido y la de gráficos el 49%, separadas por un canal.
FRACCION_TABLAS = 0.41
FRACCION_GRAFICOS = 0.49


def _columna_resumen(filas, encabezados, estilos, ancho):
    """Tabla de resumen más su línea de target, para la columna izquierda."""
    from reportlab.platypus import Paragraph, Table, TableStyle

    tabla = _tabla_resumen(filas, encabezados, estilos, ancho)
    objetivo = Paragraph(
        f"Target de muestras representativas: "
        f"{TARGET_REPRESENTATIVIDAD * 100:.0f}%",
        estilos["target"],
    )
    bloque = Table([[tabla], [objetivo]], colWidths=[ancho])
    bloque.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 1), (0, 1), 4),
    ]))
    return bloque


def _cuerpo_dos_columnas(izquierda, derecha, ancho):
    """Tablas 1..4 a la izquierda y los tres gráficos apilados a la derecha.

    En la hoja los gráficos están anclados a filas más altas que su tabla, así
    que forman una columna propia en vez de ir uno por sección.
    """
    from reportlab.platypus import Table, TableStyle

    ancho_izq = ancho * FRACCION_TABLAS
    ancho_der = ancho * FRACCION_GRAFICOS
    canal = ancho - ancho_izq - ancho_der

    cuerpo = Table([[izquierda, "", derecha]],
                   colWidths=[ancho_izq, canal, ancho_der])
    cuerpo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return cuerpo


def _tabla_detalle_generica(filas_datos, encabezados, grupo, marcas_pad,
                            estilos, ancho, anchos_columna):
    """Detalle turno a turno: dos filas de encabezado y N filas de datos.

    `filas_datos` ya viene con celdas listas (Paragraph o semáforo) para no
    repetir el armado entre la hoja de torres y la de SRR, que solo cambian en
    los rótulos y en qué columnas leen.
    """
    from reportlab.platypus import Paragraph, Table, TableStyle

    datos = [
        [Paragraph(t, estilos["th"]) if t else "" for t in grupo],
        [Paragraph(t.replace("\n", "<br/>"), estilos["th"])
         for t in encabezados],
    ]
    datos.extend(filas_datos)

    total = sum(anchos_columna)
    anchos = [a / total * ancho for a in anchos_columna]
    tabla = Table(datos, colWidths=anchos, repeatRows=2)

    estilo = [
        ("SPAN", (4, 0), (6, 0)),
        ("SPAN", (7, 0), (9, 0)),
        ("BACKGROUND", (4, 0), (9, 0), AZUL_FILA),
        ("BACKGROUND", (0, 1), (-1, 1), AZUL_FILA),
        ("BOX", (0, 0), (-1, -1), 1.0, BORDE),
        ("BOX", (4, 0), (6, 0), 1.0, BORDE),
        ("BOX", (7, 0), (9, 0), 1.0, BORDE),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Los semáforos son Drawing, no texto: sin esto la tabla los deja
        # pegados al borde izquierdo de su celda (hAlign no manda acá).
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
    ]
    # Bandas alternas y realce del Pad sin clasificar, igual que en la hoja.
    for indice, sin_clasificar in enumerate(marcas_pad):
        numero = indice + 2
        if indice % 2 == 1:
            estilo.append(("BACKGROUND", (0, numero), (-1, numero), AZUL_FILA))
        if sin_clasificar:
            estilo.append(("BACKGROUND", (2, numero), (2, numero), GRIS))

    tabla.setStyle(TableStyle(estilo))
    return tabla


def _tabla_detalle(detalle, estilos, ancho, anchos_columna):
    from reportlab.platypus import Paragraph

    encabezados = [
        "Semana", "Fecha", "Pad", "Turno", "TMH\nCV-08",
        "Muestra representativa CV-08", "Comentarios", "TMH\nCV-108",
        "Muestra representativa CV-108", "Comentarios",
        "Representatividad Turno\n(árbol de decisión)",
    ]
    grupo = ["", "", "", "", "Torre de muestreo #1", "", "",
             "Torre de muestreo #2", "", "", ""]

    filas = []
    for _, fila in detalle.iterrows():
        activo_1 = bool(fila["TM1_Activo"])
        activo_2 = bool(fila["TM2_Activo"])
        filas.append([
            Paragraph(_texto(fila["Semana"]), estilos["td"]),
            Paragraph(pd.Timestamp(fila["Fecha"]).strftime("%d-%m-%Y"),
                      estilos["td"]),
            Paragraph(_texto(fila["Pad"]), estilos["td"]),
            Paragraph(_texto(fila["Turno"]), estilos["td"]),
            Paragraph(_miles(fila["TMH_CV08"]) if activo_1 else "",
                      estilos["td"]),
            _semaforo(fila["Rep_TM1"] if activo_1 else None),
            Paragraph(_texto(fila["Comentario_TM1"]), estilos["td_izq"]),
            Paragraph(_miles(fila["TMH_CV108"]) if activo_2 else "",
                      estilos["td"]),
            _semaforo(fila["Rep_TM2"] if activo_2 else None),
            Paragraph(_texto(fila["Comentario_TM2"]), estilos["td_izq"]),
            _semaforo(fila["Rep_Turno"]),
        ])

    marcas = [fila["Pad"] == "Sin clasificar" for _, fila in detalle.iterrows()]
    return _tabla_detalle_generica(filas, encabezados, grupo, marcas,
                                   estilos, ancho, anchos_columna)


def _tabla_detalle_srr(detalle, rep_turno, estilos, ancho, anchos_columna):
    from reportlab.platypus import Paragraph

    encabezados = [
        "Semana", "Fecha", "Pad", "Turno", "TMH\nCV-01",
        "Muestra representativa CV-01", "Comentarios", "TMH\nCV-01",
        "Muestra representativa CV-01", "Comentarios",
        "Representatividad Turno\n(árbol de decisión)",
    ]
    grupo = ["", "", "", "", "Muestra química", "", "",
             "Muestra física", "", "", ""]

    filas = []
    for (_, fila), rep in zip(detalle.iterrows(), rep_turno):
        # Los turnos aún no ocurridos vienen sin Pad y salen en blanco.
        futura = pd.isna(fila.get("Pad"))
        if futura:
            filas.append([""] * 11)
            continue
        tmh = Paragraph(_miles(fila.get("TMH_CV01")), estilos["td"])
        filas.append([
            Paragraph(_texto(fila.get("Semana")), estilos["td"]),
            Paragraph(pd.Timestamp(fila["Fecha"]).strftime("%d-%m-%Y"),
                      estilos["td"]),
            Paragraph(_texto(fila.get("Pad")), estilos["td"]),
            Paragraph(_texto(fila.get("Turno")), estilos["td"]),
            tmh,
            _semaforo(_entero(fila.get("Rep_TM3_Quimico"))),
            Paragraph(_texto(fila.get("Comentario_TM3_Quimico")),
                      estilos["td_izq"]),
            Paragraph(_miles(fila.get("TMH_CV01")), estilos["td"]),
            _semaforo(_entero(fila.get("Rep_TM3_Fisico"))),
            Paragraph(_texto(fila.get("Comentario_TM3_Fisico")),
                      estilos["td_izq"]),
            _semaforo(_entero(rep)),
        ])

    marcas = [
        fila.get("Pad") == "Sin clasificar" for _, fila in detalle.iterrows()
    ]
    return _tabla_detalle_generica(filas, encabezados, grupo, marcas,
                                   estilos, ancho, anchos_columna)


# ──────────────────────────────────────────────────────────────────────────
# Entrada publica
# ──────────────────────────────────────────────────────────────────────────

ANCHOS_DETALLE = {
    "quimico": (15.08, 15.5, 16.5, 15.5, 10.08, 13.5, 42.91, 9.5, 13.5,
                44.0, 19.91),
    "fisico": (12.91, 15.5, 16.5, 15.5, 9.0, 13.5, 44.66, 9.5, 13.5,
               47.08, 19.91),
    "srr": (12.75, 15.5, 16.5, 15.5, 9.0, 13.5, 43.75, 9.5, 13.5,
            44.25, 19.75),
}


def render_torres(datos: dict) -> bytes:
    """Dibuja la hoja mensual Quimico/Fisico y la normaliza a una pagina A3.

    `datos` trae lo mismo que consume el constructor del Excel:
    tipo, fecha_base, detalle, resumen, tonelaje y gestion_fy.
    """
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Spacer

    from report_export.xlsx_to_pdf import normalize_single_page_to_a3

    tipo = str(datos["tipo"]).lower()
    tipo_titulo = "Química" if tipo == "quimico" else "Física"
    fecha_base = pd.Timestamp(datos["fecha_base"])
    detalle = datos["detalle"]
    resumen = datos["resumen"]
    estilos = _estilos()
    ancho = ANCHO - 2 * MARGEN
    mes_anio = f"{_MESES[fecha_base.month]} {fecha_base.year}"

    historia = _encabezado(tipo_titulo, fecha_base, estilos, ancho)

    ancho_izq = ancho * FRACCION_TABLAS
    ancho_der = ancho * FRACCION_GRAFICOS

    izquierda = [
        _titulo_seccion(
            "1.- Mineral apilado y caracterizado con información "
            f"{tipo_titulo.lower()} de torres de muestreo.",
            estilos, ancho_izq,
        ),
        Spacer(1, 5),
        _tabla_tonelaje(datos["tonelaje"], estilos, ancho_izq),
        Spacer(1, 16),
    ]

    secciones = [
        ("TM1",
         "2.- Torre de muestreo #1: Distribución porcentual de muestras "
         "obtenidas y perdidas.",
         "Torre #1",
         [mes_anio, "Muestras representativas TM1",
          "Muestras perdidas por Falla TM 1", "Total TM1"]),
        ("TM2",
         "3.- Torre de muestreo #2: Distribución porcentual de muestras "
         "obtenidas y perdidas.",
         "Torre #2",
         [mes_anio, "Muestras representativas TM2",
          "Muestras perdidas por Falla TM 2", "Total TM2"]),
        ("COMBINADO",
         "4.- Sistema TM1 y TM2: Distribución porcentual de muestras "
         "obtenidas y perdidas.",
         "Torre #1 y #2",
         [mes_anio, "Muestras representativas TM1+TM2",
          "Muestras perdidas por Falla TM1+TM2", "Total TM1+TM2"]),
    ]
    derecha = []
    for clave, titulo, titulo_grafico, encabezados in secciones:
        izquierda.extend([
            _titulo_seccion(titulo, estilos, ancho_izq),
            Spacer(1, 5),
            _columna_resumen(resumen[clave], encabezados, estilos, ancho_izq),
            Spacer(1, 16),
        ])
        derecha.extend([
            _grafico_barras_apiladas(
                resumen[clave], encabezados[1], encabezados[2],
                titulo_grafico, ancho_der, ancho_der * 0.45,
            ),
            Spacer(1, 14),
        ])

    historia.append(_cuerpo_dos_columnas(izquierda, derecha, ancho))
    historia.append(Spacer(1, 10))

    historia.append(_titulo_seccion(
        "5.- Detalle turno a turno de mineral apilado entre toma de muestras, "
        "muestras representativas y comentarios sobre muestras no "
        "representativas.",
        estilos, ancho,
    ))
    historia.append(Spacer(1, 5))
    historia.append(_tabla_detalle(
        detalle, estilos, ancho,
        ANCHOS_DETALLE["quimico" if tipo == "quimico" else "fisico"],
    ))
    historia.append(Spacer(1, 18))

    gestion_fy = datos.get("gestion_fy")
    if gestion_fy is not None and not gestion_fy.empty:
        anio = int(datos["anio_fiscal"]) % 100
        historia.append(_titulo_seccion(
            f"6.- Gestión sobre representatividad FY{anio:02d}.",
            estilos, ancho,
        ))
        historia.append(Spacer(1, 6))
        historia.append(_grafico_gestion_fy(
            gestion_fy, f"Gestión sobre representatividad FY{anio:02d}",
            ancho, ancho * 0.21,
        ))

    return _construir_documento(
        historia, f"Representatividad Muestra {tipo_titulo} Torre"
    )


def render_srr(datos: dict) -> bytes:
    """Dibuja la hoja mensual de TM3/SRR y la normaliza a una página A3.

    `datos` trae fecha_base, el detalle ya cruzado químico+físico, los dos
    resúmenes, el mineral y la representatividad de cada turno.
    """
    from reportlab.platypus import Spacer

    fecha_base = pd.Timestamp(datos["fecha_base"])
    estilos = _estilos()
    ancho = ANCHO - 2 * MARGEN
    mes_anio = f"{_MESES[fecha_base.month].lower()} {str(fecha_base.year)[-2:]}"

    historia = _encabezado(
        "Física y Química", fecha_base, estilos, ancho,
        titulo=(
            "Muestras representativas de Torre de Muestreo #3 / SRR - "
            f"Muestra Física y Química - {_MESES[fecha_base.month].lower()}, "
            f"{fecha_base.year}"
        ),
    )

    ancho_izq = ancho * FRACCION_TABLAS
    ancho_der = ancho * FRACCION_GRAFICOS

    izquierda = [
        _titulo_seccion(
            "1.- Mineral apilado y caracterizado con información física y "
            "química de Torre de Muestreo #3 / SRR.",
            estilos, ancho_izq,
        ),
        Spacer(1, 5),
        _tabla_tonelaje(datos["mineral"], estilos, ancho_izq),
        Spacer(1, 16),
    ]

    secciones = [
        ("resumen_quimico",
         "2.- Muestra Química Torre de muestreo #3: Distribución porcentual "
         "de muestras obtenidas y no representativas.",
         "Muestra Química TM3", "Muestras representativas TM SRR"),
        ("resumen_fisico",
         "3.- Muestra Física Torre de muestreo #3: Distribución porcentual "
         "de muestras obtenidas y no representativas.",
         "Muestra Física TM3", "Muestras representativas TM3"),
    ]
    derecha = []
    for clave, titulo, titulo_grafico, etiqueta_rep in secciones:
        encabezados = [mes_anio, etiqueta_rep,
                       "Muestras perdidas por Falla TM 3", "Total TM3"]
        izquierda.extend([
            _titulo_seccion(titulo, estilos, ancho_izq),
            Spacer(1, 5),
            _columna_resumen(datos[clave], encabezados, estilos, ancho_izq),
            Spacer(1, 16),
        ])
        derecha.extend([
            _grafico_barras_apiladas(
                datos[clave], encabezados[1], encabezados[2], titulo_grafico,
                ancho_der, ancho_der * 0.42,
            ),
            Spacer(1, 14),
        ])

    historia.append(_cuerpo_dos_columnas(izquierda, derecha, ancho))
    historia.append(Spacer(1, 10))

    historia.append(_titulo_seccion(
        "4.- Detalle turno a turno de mineral apilado entre toma de muestras, "
        "muestras representativas y comentarios sobre muestras no "
        "representativas.",
        estilos, ancho,
    ))
    historia.append(Spacer(1, 5))
    historia.append(_tabla_detalle_srr(
        datos["detalle"], datos["rep_turno"], estilos, ancho,
        ANCHOS_DETALLE["srr"],
    ))

    return _construir_documento(
        historia, "Representatividad Muestras SRR Torre"
    )


def _construir_documento(historia, titulo: str) -> bytes:
    """Vuelca la historia en el lienzo alto y lo normaliza a una A3."""
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

    from report_export.xlsx_to_pdf import normalize_single_page_to_a3

    salida = io.BytesIO()
    documento = BaseDocTemplate(
        salida, pagesize=(ANCHO, ALTO_LIENZO),
        leftMargin=MARGEN, rightMargin=MARGEN,
        topMargin=MARGEN, bottomMargin=MARGEN,
        title=titulo,
    )
    marco = Frame(
        MARGEN, MARGEN, ANCHO - 2 * MARGEN, ALTO_LIENZO - 2 * MARGEN,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    documento.addPageTemplates([PageTemplate(id="lienzo", frames=[marco])])
    documento.build(historia)

    return normalize_single_page_to_a3(salida.getvalue())
