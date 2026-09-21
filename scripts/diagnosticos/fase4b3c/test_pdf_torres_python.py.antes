"""El renderer en Python entrega una A3 con las 6 secciones y sin solapes.

El defecto que motivó reescribir esto era el gráfico FY montado sobre la tabla
del detalle, así que la comprobación que importa es que el gráfico empiece por
debajo de su propio título.
"""
import io
import unittest

import pandas as pd
import pdfplumber

from report_export.callbacks.reportabilidad_cb import (
    _calcular_resumen_mensual_torres,
    _calcular_tonelaje_por_material_torres,
    _merge_detalle_srr,
    _mineral_srr,
    _rep_turno_srr,
    _resumen_srr,
)
from report_export import pdf_torres as cb_pdf
from report_export.pdf_torres import render_srr, render_torres


def _detalle_muestra(dias=31):
    fechas = pd.date_range("2026-07-01", periods=dias, freq="D")
    registros = []
    for indice, fecha in enumerate(fechas):
        for orden, turno in enumerate(("TA", "TB")):
            n = indice * 2 + orden
            activo = n % 11 != 0
            registros.append({
                "Semana_Num": min(indice // 7 + 1, 6),
                "Semana": f"Semana {min(indice // 7 + 1, 6)}",
                "Fecha": fecha,
                "Pad": ["Óxido", "Sulfuro", "Sin clasificar"][n % 3],
                "Turno": turno,
                "TMH_CV08": 12345.6 + n if activo else None,
                "TM1_Activo": int(activo),
                "Rep_TM1": (1 if n % 4 else 0) if activo else None,
                "Comentario_TM1": "Falla CV-08" if n % 7 == 0 else None,
                "TMH_CV108": 9876.5 + n if activo else None,
                "TM2_Activo": int(activo),
                "Rep_TM2": (1 if n % 5 else 0) if activo else None,
                "Comentario_TM2": "Mantención torre 2" if n % 9 == 0 else None,
                "Rep_Turno": (1 if n % 4 or n % 5 else 0) if activo else None,
                "TMH_CV01": 5432.1 + n if activo else None,
                "TM3_Activo": 1 if activo else 0,
                "Rep_TM3": (1 if n % 4 else 0) if activo else None,
                "Comentario_TM3": "Falla SRR" if n % 8 == 0 else None,
            })
    return pd.DataFrame(registros)


def _gestion_fy():
    etiquetas = [f"M{n:02d}" for n in range(1, 13)] + ["YTD"]
    return pd.DataFrame({
        "Etiqueta": etiquetas,
        "Representatividad": [0.85] * len(etiquetas),
        "Objetivo": [0.85] * len(etiquetas),
    })


class PdfTorresPythonTests(unittest.TestCase):
    def _render(self, tipo, detalle=None):
        detalle = _detalle_muestra() if detalle is None else detalle
        return render_torres({
            "tipo": tipo,
            "fecha_base": pd.Timestamp("2026-07-01"),
            "detalle": detalle,
            "resumen": _calcular_resumen_mensual_torres(detalle),
            "tonelaje": _calcular_tonelaje_por_material_torres(detalle),
            "gestion_fy": _gestion_fy(),
            "anio_fiscal": 2027,
        })

    def test_una_pagina_a3_con_las_seis_secciones_sin_solape(self):
        for tipo in ("quimico", "fisico"):
            with self.subTest(tipo=tipo):
                with pdfplumber.open(io.BytesIO(self._render(tipo))) as doc:
                    self.assertEqual(len(doc.pages), 1)
                    pagina = doc.pages[0]
                    self.assertAlmostEqual(pagina.width, 841.8898, places=2)
                    self.assertAlmostEqual(pagina.height, 1190.5512, places=2)

                    titulos = {}
                    for palabra in pagina.extract_words():
                        for numero in "123456":
                            if palabra["text"].startswith(f"{numero}.-"):
                                titulos.setdefault(numero, palabra["top"])
                    self.assertEqual(sorted(titulos), list("123456"))

                    # Los títulos van en orden vertical y el gráfico FY (la
                    # imagen más baja) arranca debajo del título 6.
                    tapas = [titulos[n] for n in "123456"]
                    self.assertEqual(tapas, sorted(tapas))
                    grafico_fy = max(pagina.images, key=lambda im: im["top"])
                    self.assertGreater(grafico_fy["top"], titulos["6"])

    def test_srr_entrega_una_pagina_con_sus_cuatro_secciones(self):
        quimico = _detalle_muestra()
        fisico = _detalle_muestra()
        detalle = _merge_detalle_srr(quimico, fisico)
        pdf = render_srr({
            "fecha_base": pd.Timestamp("2026-07-01"),
            "detalle": detalle,
            "rep_turno": [
                _rep_turno_srr(f.get("Rep_TM3_Quimico"), f.get("Rep_TM3_Fisico"))
                for _, f in detalle.iterrows()
            ],
            "resumen_quimico": _resumen_srr(quimico),
            "resumen_fisico": _resumen_srr(fisico),
            "mineral": _mineral_srr(detalle),
        })
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            self.assertEqual(len(doc.pages), 1)
            palabras = doc.pages[0].extract_words()
            titulos = {
                numero
                for palabra in palabras
                for numero in "1234"
                if palabra["text"].startswith(f"{numero}.-")
            }
            self.assertEqual(sorted(titulos), list("1234"))
            # NaN es truthy: si una celda de comentario se formatea con
            # `valor or ""` termina imprimiendo "nan" en el reporte.
            self.assertNotIn("nan", [p["text"] for p in palabras])

    def test_el_semaforo_es_un_circulo_dibujado_y_no_un_glifo(self):
        from reportlab.graphics.shapes import Circle, Drawing

        for valor, color in ((1, cb_pdf.VERDE), (0, cb_pdf.ROJO)):
            marca = cb_pdf._semaforo(valor)
            self.assertIsInstance(marca, Drawing)
            circulo = marca.contents[0]
            self.assertIsInstance(circulo, Circle)
            self.assertEqual(circulo.fillColor.hexval()[2:], color[1:].lower())
        # Sin dato no se dibuja nada.
        self.assertEqual(cb_pdf._semaforo(None), "")

    def test_los_graficos_conservan_la_proporcion_de_la_figura(self):
        # bbox_inches="tight" recorta la figura, así que imponer ancho y alto
        # a la vez deformaba el gráfico (se veía estirado en la sección 6).
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figura, ejes = plt.subplots(figsize=(8, 2))
        ejes.bar([0, 1, 2], [1, 2, 3])
        imagen = cb_pdf._figura_a_imagen(figura, 400.0)

        self.assertEqual(imagen.drawWidth, 400.0)
        self.assertAlmostEqual(
            imagen.drawWidth / imagen.drawHeight,
            imagen.imageWidth / imagen.imageHeight,
            places=6,
        )

    def test_un_mes_mas_largo_sigue_cabiendo_en_una_pagina(self):
        # El detalle es lo que crece; si desbordara, el gráfico FY volvería a
        # pelear con la tabla como pasaba en LibreOffice.
        detalle = _detalle_muestra(dias=31)
        detalle = pd.concat([detalle, detalle.head(20)], ignore_index=True)
        with pdfplumber.open(io.BytesIO(self._render("quimico", detalle))) as doc:
            self.assertEqual(len(doc.pages), 1)


if __name__ == "__main__":
    unittest.main()
