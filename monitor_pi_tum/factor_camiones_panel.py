"""Diagnóstico diario de camiones. Fase 1: exclusivamente lectura."""
import json
import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, Patch, callback, ctx, dcc, html
import dash_bootstrap_components as dbc

from . import db
from . import limites_camiones_panel as limites
from . import override_camiones_panel as override

log = logging.getLogger(__name__)
DERIVADAS = (
    "Chancado_TMH_Con_Ajuste", "Movimiento_Mina_TMH",
    "Carga_KOM_TMH_Viaje_Con_Ajuste", "Carga_CAT_TMH_Viaje_Con_Ajuste",
)


def figura_vacia():
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white", height=480, barmode="group",
        margin=dict(l=65, r=65, t=15, b=100),
        xaxis=dict(type="date", tickformat="%d-%m", hoverformat="%d-%m-%Y"),
        yaxis_title="TMH", yaxis2=dict(title="Factor", overlaying="y", side="right", range=[0, 1.05]),
        legend=dict(orientation="h", y=-0.2), clickmode="event", hovermode="x unified",
    )
    fig.add_shape(type="line", xref="paper", x0=0, x1=1,
                  yref="y2", y0=1, y1=1, line=dict(color="#777777", dash="dot"))
    fig.add_annotation(xref="paper", x=1, yref="y2", y=1,
                       text="Factor = 1,0000", showarrow=False, yshift=12)
    return fig


def layout():
    return dbc.Card(dbc.CardBody([
        html.H4([
            "Factor de ajuste camiones ",
            html.Span("ⓘ", id="pitum-factor-ayuda", tabIndex=0, role="button",
                      **{"aria-label": "Ayuda sobre los factores"},
                      style={"cursor": "help"}),
        ], style={"color": "#1F4E78"}),
        html.P("Diagnóstico diario del factor de ajuste de camiones KOM/CAT.",
               className="text-muted mb-2"),
        html.P("Compara el factor calculado con el factor aplicado y permite revisar el detalle de cada día.",
               className="small mb-2"),
        dbc.Tooltip([
            "Factor calculado: resultado automático del balance y control de cargas.", html.Br(),
            "Factor aplicado: valor efectivamente usado por los reportes; puede diferir por override o respaldo.", html.Br(),
            "Factor < 1: se aplica una reducción de tonelaje.", html.Br(),
            "Factor = 1: no se aplica reducción.",
        ], target="pitum-factor-ayuda", trigger="hover focus", placement="bottom"),
        dcc.Store(id="pitum-factor-datos"),
        dcc.Loading(html.Div([
            html.Div(id="pitum-factor-alerta"),
            dcc.Graph(id="pitum-factor-grafico", figure=figura_vacia(),
                      config={"displaylogo": False, "scrollZoom": True}),
        ])),
        html.P("Seleccione un día para revisar el detalle del cálculo y sus principales componentes.", className="text-muted small"),
        html.Div(id="pitum-factor-detalle"),
        override.layout(),
        limites.layout(),
    ]), className="my-3")


def preparar_datos(df):
    """Solo magnitudes de presentación; nunca calcula ni sustituye factores."""
    df = df.copy()
    df["Chancado_TMH_Con_Ajuste"] = df["KOM_TMH_Corregido"] + df["CAT_TMH_Corregido"]
    df["Movimiento_Mina_TMH"] = df["Produccion_KOM_TMH"] + df["Produccion_CAT_TMH"]
    for flota in ("KOM", "CAT"):
        vueltas = df[f"Vueltas_{flota}"]
        df[f"Carga_{flota}_TMH_Viaje_Con_Ajuste"] = (
            df[f"{flota}_TMH_Corregido"] / vueltas.where(vueltas > 0))
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.strftime("%Y-%m-%d")
    return json.loads(df.to_json(orient="records", date_format="iso", double_precision=15))


def es_respaldo(fila):
    return (fila.get("Factor_Ajuste_Calculado") is None
            or fila.get("Flag_Factor_Ajuste_Valido") == 0
            or "FALLBACK" in str(fila.get("Regla_Aplicacion_Automatica", fila.get("Regla_Aplicacion")) or "").upper())


def hover_dia(fila):
    """Texto de presentación; distingue valores ausentes de ceros reales."""
    def numero(campo, decimales):
        valor = fila.get(campo)
        if valor is None:
            return "—"
        return f"{valor:,.{decimales}f}".translate(str.maketrans(",.", ".,"))
    basico = [
        pd.Timestamp(fila["Fecha"]).strftime("%d-%m-%Y"),
        *[numero(c, 2) for c in ("Chancado_TMH_Sin_Ajuste", "Movimiento_Mina_TMH", "Chancado_TMH_Con_Ajuste")],
        *[numero(c, 4) for c in ("Factor_Ajuste_Calculado", "Factor_Aplicacion_Reportes")],
        fila.get("Estado_Calculo") if fila.get("Estado_Calculo") is not None else "—",
        fila.get("Regla_Aplicacion") if fila.get("Regla_Aplicacion") is not None else "—",
        fila.get("Modo_Aplicacion") if fila.get("Modo_Aplicacion") is not None else "—",
    ]
    return basico + [
        *[fila.get(c) or "—" for c in ("Fuente_Camiones", "Estado_Fuente_MOV_CAM", "Estado_Fuente_POWERBI")],
        *[numero(c, 2) for c in (
            "Vueltas_KOM", "Vueltas_CAT", "Carga_Nominal_KOM_TMH_Viaje", "Carga_Nominal_CAT_TMH_Viaje",
            "Produccion_KOM_TMH", "Produccion_CAT_TMH", "Carga_KOM_TMH_Viaje_Sin_Ajuste",
            "Carga_CAT_TMH_Viaje_Sin_Ajuste", "Limite_KOM_TMH_Viaje", "Limite_CAT_TMH_Viaje",
            "Chancado_TMS_Reporte")],
    ]


def motivo_visible(fila):
    if fila.get("Factor_Ajuste_Calculado") == fila.get("Factor_Aplicacion_Reportes"):
        return ""
    if fila.get("Modo_Aplicacion") == "FORZADO_1":
        return "Factor 1 forzado por usuario"
    if es_respaldo(fila):
        return "Regla de respaldo; revise el detalle diario"
    if fila.get("Regla_Aplicacion") == "APLICA_AJUSTE_VALIDADO":
        return "Ajuste automático validado"
    return "Regla efectiva; revise el detalle diario"


def banda_seleccion(fecha):
    dia = pd.Timestamp(fecha)
    return dict(type="rect", name="fecha-seleccionada", xref="x", yref="paper",
                x0=(dia-pd.Timedelta(hours=12)).isoformat(),
                x1=(dia+pd.Timedelta(hours=12)).isoformat(), y0=0, y1=1,
                fillcolor="#1F4E78", opacity=0.08, line_width=0, layer="below")


HOVER_DIA = (
    "Fecha: %{customdata[0]}<br>Chancado TMH sin ajuste: %{customdata[1]}"
    "<br>Producción de referencia total [TMH]: %{customdata[2]}<br>Chancado TMH corregido automático: %{customdata[3]}"
    "<br>Factor calculado: %{customdata[4]}<br>Factor aplicado: %{customdata[5]}"
    "<br>Estado cálculo automático: %{customdata[6]}<br>Regla efectiva: %{customdata[7]}"
    "<br>Modo de aplicación: %{customdata[8]}"
    "<br>Fuente camiones: %{customdata[9]}<br>Estado MOV_CAM: %{customdata[10]}<br>Estado PowerBI: %{customdata[11]}"
    "<br>Vueltas KOM / CAT: %{customdata[12]} / %{customdata[13]}"
    "<br>Carga nominal KOM / CAT [TMH/viaje]: %{customdata[14]} / %{customdata[15]}"
    "<br>Producción de referencia KOM / CAT [TMH]: %{customdata[16]} / %{customdata[17]}"
    "<br>Carga calculada KOM / CAT [TMH/viaje]: %{customdata[18]} / %{customdata[19]}"
    "<br>Límite KOM / CAT [TMH/viaje]: %{customdata[20]} / %{customdata[21]}"
    "<br><b>Chancado TMS publicado [TMS]: %{customdata[22]}</b><extra></extra>"
)


@callback(
    Output("pitum-factor-grafico", "figure"), Output("pitum-factor-datos", "data"),
    Output("pitum-factor-alerta", "children"),
    Input("pitum-fechas", "start_date"), Input("pitum-fechas", "end_date"),
    Input("pitum-actualizar", "n_clicks"),
    Input("pitum-override-version", "data"),
)
def actualizar_factor(inicio, fin, _clicks, _override_version=None):
    fig = figura_vacia()
    try:
        df = db.obtener_factor_camiones(inicio, fin)
        dias = pd.date_range(inicio, fin, freq="D")
        # Media jornada de espacio mantiene completas las barras de los extremos.
        # Solo se etiquetan días pertenecientes al rango elegido, incluso sin datos.
        fig.update_xaxes(range=[(dias[0] - pd.Timedelta(hours=12)).isoformat(),
                                (dias[-1] + pd.Timedelta(hours=12)).isoformat()],
                         tickmode="array", tickvals=dias[::max(1, (len(dias) + 9) // 10)],
                         tickformat="%d-%m")
        if df.empty:
            return fig, [], dbc.Alert("Sin datos para el rango seleccionado.", color="info")
        filas = preparar_datos(df)
        fechas = [r["Fecha"] for r in filas]
        hover = [hover_dia(r) for r in filas]
        for indice, (campo, nombre, color) in enumerate((
            ("Chancado_TMH_Sin_Ajuste", "Chancado TMH sin ajuste", "#1F4E78"),
            ("Movimiento_Mina_TMH", "Producción de referencia", "#9DC3E6"),
            ("Chancado_TMH_Con_Ajuste", "Chancado TMH corregido automático", "#548235"),
        ), start=1):
            fig.add_trace(go.Bar(x=fechas, y=[r[campo] for r in filas], name=nombre,
                                 marker_color=color, customdata=hover,
                                 hovertemplate=nombre+": %{customdata["+str(indice)+"]}<extra></extra>"))
        for campo, nombre, color, dash in (
            ("Factor_Ajuste_Calculado", "Factor calculado", "#C55A11", "solid"),
            ("Factor_Aplicacion_Reportes", "Factor aplicado", "#7030A0", "dash"),
        ):
            templates = []
            for fila in filas:
                template = nombre + (": %{customdata[4]}" if campo == "Factor_Ajuste_Calculado" else ": %{customdata[5]}")
                if campo == "Factor_Aplicacion_Reportes":
                    if fila.get("Factor_Ajuste_Calculado") is None:
                        template = "Factor calculado: —<br>" + template
                    motivo = motivo_visible(fila)
                    if motivo:
                        template += "<br>Modo / regla efectiva: " + motivo
                templates.append(template + "<extra></extra>")
            # Señal sobre la línea existente, sin otra entrada de leyenda.
            diferencias = [
                campo == "Factor_Aplicacion_Reportes"
                and r.get("Factor_Ajuste_Calculado") is not None
                and r.get("Factor_Aplicacion_Reportes") is not None
                and r["Factor_Ajuste_Calculado"] != r["Factor_Aplicacion_Reportes"]
                for r in filas
            ]
            fig.add_trace(go.Scatter(x=fechas, y=[r[campo] for r in filas], name=nombre,
                                     yaxis="y2", mode="lines+markers", connectgaps=False,
                                     line=dict(color=color, dash=dash),
                                     marker=dict(symbol=["diamond-open" if d else "circle" for d in diferencias],
                                                 size=[10 if d else 6 for d in diferencias]),
                                     customdata=hover, hovertemplate=templates))
        respaldos = [r for r in filas if es_respaldo(r)]
        if respaldos:
            # Eje auxiliar fijo: señal de estado, independiente de toneladas/factores.
            fig.update_layout(yaxis3=dict(overlaying="y", range=[0, 1], visible=False,
                                          fixedrange=True, anchor="x"))
            fig.add_trace(go.Scatter(
                x=[r["Fecha"] for r in respaldos], y=[0.97] * len(respaldos), yaxis="y3",
                mode="markers", name="Revisar cálculo / regla de respaldo", showlegend=False, visible=False,
                marker=dict(symbol="triangle-up", size=9, color="#777777"),
                customdata=[hover_dia(r) for r in respaldos], hovertemplate=HOVER_DIA,
            ))
        eventos = (
            ("MOV_CAM_POWERBI", "Fuente_Camiones", "diamond", "#008B8B", 0.90),
            ("SIN_DATOS_CAMIONES", "Fuente_Camiones", "x", "#777777", 0.84),
            ("FORZADO_1", "Modo_Aplicacion", "square-open", "#7030A0", 0.78),
        )
        for nombre, campo, simbolo, color, altura in eventos:
            grupo = [r for r in filas if r.get(campo) == nombre]
            if not grupo:
                continue
            fig.update_layout(yaxis3=dict(overlaying="y", range=[0, 1], visible=False,
                                          fixedrange=True, anchor="x"))
            fig.add_trace(go.Scatter(x=[r["Fecha"] for r in grupo], y=[altura] * len(grupo),
                                    yaxis="y3", mode="markers", name=nombre, showlegend=False, visible=False,
                                    marker=dict(symbol=simbolo, size=9, color=color),
                                    customdata=[hover_dia(r) for r in grupo], hovertemplate=HOVER_DIA))
        fig.add_shape(banda_seleccion(fechas[0]))
        return fig, filas, ""
    except ValueError as exc:
        return fig, [], dbc.Alert(str(exc), color="warning")
    except Exception:
        log.exception("Error consultando diagnóstico de factor camiones")
        return fig, [], dbc.Alert("No fue posible consultar el factor de ajuste camiones.", color="danger")


def detalle_dia(filas, click=None):
    if not filas:
        return html.P("Sin datos", className="text-muted")
    puntos = (click or {}).get("points") or []
    fecha = str(puntos[0].get("x", ""))[:10] if puntos else None
    fila = next((r for r in filas if r["Fecha"] == fecha), filas[0])
    def n(key, decimals=2):
        return limites.numero(fila.get(key), decimals)
    def text(key):
        return fila.get(key) if fila.get(key) is not None else "—"
    def regla_visible(key):
        return {
            "APLICA_AJUSTE_VALIDADO": "Ajuste automático validado",
            "FORZADO_1_USUARIO": "Factor 1 forzado por usuario",
        }.get(fila.get(key), text(key))
    def estado(flota):
        carga=fila.get(f"Carga_{flota}_TMH_Viaje_Sin_Ajuste")
        limite=fila.get(f"Limite_{flota}_TMH_Viaje")
        if carga is None or limite is None:
            return "—"
        return "EXCEDE LÍMITE" if carga>limite else "DENTRO DE LÍMITE"
    balance=[
        ("Apilado bruto [TMH]","Apilado_TMH_Bruto_Original"),
        ("Humedad [%]","Humedad_Pct"),
        ("Apilado bruto [TMS]","Apilado_TMS_Bruto_Sin_Ajuste"),
        ("Sal del día","Sal_TMH_Dia"),
        ("Apilado neto [TMS]","Apilado_TMS_Neto_Sin_Ajuste"),
        ("Variación inventario chancado [TMS]","Delta_Inventario_Chancado_TMS"),
        ("SRR [TMS]","SRR_TMS_Dia"),
        ("Chancado sin ajuste [TMS]","Chancado_TMS_Sin_Ajuste"),
        ("Chancado sin ajuste [TMH]","Chancado_TMH_Sin_Ajuste"),
    ]
    camiones=[
        ["Producción de referencia [TMH]",n("Produccion_KOM_TMH"),n("Produccion_CAT_TMH")],
        ["Vueltas",n("Vueltas_KOM",0),n("Vueltas_CAT",0)],
        ["Carga nominal utilizada [TMH/viaje]",n("Carga_Nominal_KOM_TMH_Viaje"),n("Carga_Nominal_CAT_TMH_Viaje")],
        ["Carga calculada por viaje [TMH/viaje]",n("Carga_KOM_TMH_Viaje_Sin_Ajuste"),n("Carga_CAT_TMH_Viaje_Sin_Ajuste")],
        ["Límite utilizado [TMH/viaje]",n("Limite_KOM_TMH_Viaje"),n("Limite_CAT_TMH_Viaje")],
        ["Tonelaje corregido [TMH]",n("KOM_TMH_Corregido"),n("CAT_TMH_Corregido")],
        ["Carga corregida por viaje [TMH/viaje]",n("Carga_KOM_TMH_Viaje_Con_Ajuste"),n("Carga_CAT_TMH_Viaje_Con_Ajuste")],
        ["Estado respecto del límite",estado("KOM"),estado("CAT")],
    ]
    estados={"OK_AJUSTE_KOM":"Ajuste por límite KOM", "OK_AJUSTE_CAT":"Ajuste por límite CAT",
             "OK_AJUSTE_AMBAS_FLOTAS":"Ajuste por límite KOM y CAT", "OK_SIN_AJUSTE":"Sin ajuste requerido",
             "SIN_DATOS_CAMIONES":"Sin información suficiente de camiones"}
    flag=fila.get("Flag_Factor_Ajuste_Valido")
    return html.Div([
        html.H5("Detalle del día "+limites.fecha(fila["Fecha"])),
        html.H6("1. Balance de Chancado"),
        limites.tabla(["Componente","Valor"],[[label,n(key)] for label,key in balance]),
        html.H6("2. Validación Camiones"),
        limites.tabla(["Variable","KOM","CAT"],camiones),
        html.P("Producción de referencia total: "+n("Movimiento_Mina_TMH")+" TMH"),
        html.H6("3. Resultado Factor"),
        limites.tabla(["Resultado","Valor"],[
            ["Chancado sin ajuste [TMH]",n("Chancado_TMH_Sin_Ajuste")],
            ["Chancado corregido automático [TMH]",n("Chancado_TMH_Con_Ajuste")],
            ["Factor calculado",html.Strong(n("Factor_Ajuste_Calculado",4))],
            ["Factor automático",html.Strong(n("Factor_Aplicacion_Automatica",4))],
            ["Factor aplicado",html.Strong(n("Factor_Aplicacion_Reportes",4))],
            ["Modo de aplicación",text("Modo_Aplicacion")],
            ["Estado cálculo automático",estados.get(fila.get("Estado_Calculo"),text("Estado_Calculo"))],
            ["Chancado TMS publicado [TMS]",n("Chancado_TMS_Reporte")],
            ["Regla automática",regla_visible("Regla_Aplicacion_Automatica")],
            ["Regla efectiva",regla_visible("Regla_Aplicacion")],
            ["Validación del factor","—" if flag is None else "Válida" if flag else "No válida"],
        ]),
        html.Details([html.Summary("4. Trazabilidad Técnica"),
            limites.tabla(["Dato","Valor"],[
                ["Estado interno",text("Estado_Calculo")], ["Fuente",text("Fuente_Camiones")],
                ["Método",text("Metodo")], ["Fecha cálculo",limites.fecha(fila.get("Fecha_Calculo"),True)],
                ["Evaluación fuente MOV_CAM",text("Estado_Fuente_MOV_CAM")],
                ["Evaluación fuente PowerBI",text("Estado_Fuente_POWERBI")],
                ["Límite KOM utilizado [TMH/viaje]",n("Limite_KOM_TMH_Viaje")],
                ["Límite CAT utilizado [TMH/viaje]",n("Limite_CAT_TMH_Viaje")],
                ["ID control manual",text("Id_Control_Aplicacion")],
                ["Motivo control manual",text("Control_Aplicacion_Motivo")],
                ["Usuario control manual",text("Control_Aplicacion_Usuario")],
                ["Fecha control manual",limites.fecha(fila.get("Control_Aplicacion_Fecha_Registro"),True)],
            ])],className="text-muted small"),
    ])


@callback(Output("pitum-factor-detalle", "children"),
          Input("pitum-factor-datos", "data"), Input("pitum-factor-grafico", "clickData"),
          Input("pitum-limites-pendientes-datos", "data"))
def actualizar_detalle(filas, click, pendientes=None):
    # Un rango nuevo siempre selecciona su primer día, ignorando clicks del rango anterior.
    selection = click if ctx.triggered_id != "pitum-factor-datos" else None
    result = detalle_dia(filas, selection)
    if filas:
        points=(selection or {}).get("points") or []
        day=str(points[0].get("x", ""))[:10] if points else filas[0]["Fecha"]
        if day not in {r["Fecha"] for r in filas}:
            day=filas[0]["Fecha"]
        differences=[r for r in (pendientes or []) if str(r["Fecha"])[:10]==day]
        if differences:
            result.children.append(dbc.Alert([
                html.Strong("PENDIENTE DE REPROCESO"),
                html.P("La configuración difiere del resultado materializado. Se mantienen visibles los parámetros utilizados en su último cálculo."),
                html.P("Parámetro: "+db.PARAMETROS_FACTOR_CAMIONES.get(differences[0].get('parametro'),{}).get('nombre','Límite máximo')),
                limites.tabla(["Flota","Configurado","Utilizado"],[[r["flota"],limites.numero(r["limite_configurado"]),limites.numero(r["limite_utilizado"])] for r in differences]),
            ],color="warning"))
    return result


@callback(Output("pitum-factor-grafico", "figure", allow_duplicate=True),
          Input("pitum-factor-grafico", "clickData"), Input("pitum-factor-datos", "data"),
          prevent_initial_call=True)
def seleccionar_fecha(click, filas):
    selection = click if ctx.triggered_id != "pitum-factor-datos" else None
    puntos = (selection or {}).get("points") or []
    fecha = str(puntos[0].get("x", ""))[:10] if puntos else None
    fechas = [r["Fecha"] for r in (filas or [])]
    fecha = fecha if fecha in fechas else fechas[0] if fechas else None
    patch = Patch()
    # Conserva solo la referencia fija y la banda del día; sin selección por serie.
    shapes = [figura_vacia().layout.shapes[0].to_plotly_json()]
    if fecha:
        shapes.append(banda_seleccion(fecha))
    patch["layout"]["shapes"] = shapes
    return patch
