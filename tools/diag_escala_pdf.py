"""Diagnostico: donde cae el grafico FY segun la configuracion de pagina.

Se corre EN EL SERVIDOR, con el LibreOffice de ese servidor, sobre el mismo
.xlsx que genero un PDF malo. No toca la app ni la base de datos.

    python3 tools/diag_escala_pdf.py "Reporte_Representatividad_Torres_....xlsx"

Mide sobre el PDF crudo de LibreOffice (sin normalizar): si el marco del
grafico FY empieza por encima del titulo "6.-", hay solape.

Temporal: borrar cuando este resuelto.
"""
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook


def _soffice():
    from shutil import which
    for c in ("soffice", "libreoffice"):
        if which(c):
            return which(c)
    raise SystemExit("No se encontro soffice/libreoffice en el PATH.")


def _hoja_mensual(wb):
    for nombre in wb.sheetnames:
        if nombre.endswith(" Quimico"):
            return nombre
    raise SystemExit(f"No hay hoja '* Quimico'. Hojas: {wb.sheetnames}")


def preparar(origen: Path, variante: str) -> bytes:
    wb = load_workbook(io.BytesIO(origen.read_bytes()))
    nombre = _hoja_mensual(wb)
    ws = wb[nombre]
    for otro in list(wb.sheetnames):
        if otro != nombre:
            wb.remove(wb[otro])
    wb.active = 0

    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.15
    ws.page_margins.top = ws.page_margins.bottom = 0.0
    ws.page_margins.header = ws.page_margins.footer = 0.0
    ws.sheet_view.showGridLines = False

    def escala_fija(valor):
        ws.sheet_properties.pageSetUpPr.fitToPage = False
        ws.page_setup.scale = valor
        ws.page_setup.fitToWidth = None
        ws.page_setup.fitToHeight = None

    if variante == "actual":                 # lo que hay desplegado hoy
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.scale = None
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
    elif variante.startswith("escala"):
        escala_fija(int(variante.removeprefix("escala")))
    elif variante == "filas_explicitas":
        # las filas del grafico no existen en el archivo (max_row < ancla):
        # se crean con alto conocido para que nadie tenga que inventarlas
        escala_fija(40)
        if ws._charts:
            ancla = max(c.anchor._from.row for c in ws._charts)
            for fila in range(ancla - 2, ancla + 18):
                ws.row_dimensions[fila].height = 15.0

    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def convertir(xlsx: bytes, tmp: Path, etq: str) -> bytes:
    p = tmp / f"{etq}.xlsx"
    p.write_bytes(xlsx)
    perfil = (tmp / "perfil").resolve().as_uri()
    r = subprocess.run(
        [_soffice(), "--headless", f"-env:UserInstallation={perfil}",
         "--convert-to", "pdf", "--outdir", str(tmp), str(p)],
        capture_output=True, text=True, timeout=300,
    )
    pdf = p.with_suffix(".pdf")
    if not pdf.is_file():
        raise SystemExit(f"LibreOffice fallo: {r.stderr or r.stdout}")
    return pdf.read_bytes()


def medir(pdf: bytes, etq: str) -> None:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        titulo = grafico = None
        for i, pagina in enumerate(doc.pages):
            for w in pagina.extract_words(extra_attrs=["size"]):
                if w["text"].startswith("6.-") and titulo is None:
                    titulo = (i, w["top"], w["size"] / 10)
            marcos = [c for c in pagina.curves if c["bottom"] - c["top"] > 50]
            if marcos:
                m = max(marcos, key=lambda c: c["top"])
                if grafico is None or (i, m["top"]) > grafico[:2]:
                    grafico = (i, m["top"], m["bottom"])
        n = len(doc.pages)
        if not titulo or not grafico:
            print(f"  {etq:18s} {n}pag  no se ubico titulo/grafico")
            return
        estado = "OK" if (grafico[0], grafico[1]) > (titulo[0], titulo[1]) else "SOLAPA"
        print(f"  {etq:18s} {n}pag escala={titulo[2]:.3f} | "
              f"titulo6 pag{titulo[0]} y={titulo[1]:7.1f} | "
              f"graficoFY pag{grafico[0]} y={grafico[1]:7.1f}..{grafico[2]:7.1f}"
              f"  {estado}")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    origen = Path(sys.argv[1])
    if not origen.is_file():
        raise SystemExit(f"No existe: {origen}")

    print(subprocess.run([_soffice(), "--version"], capture_output=True,
                         text=True).stdout.strip())
    wb = load_workbook(io.BytesIO(origen.read_bytes()))
    ws = wb[_hoja_mensual(wb)]
    anclas = [(c.anchor._from.row, c.anchor.to.row) for c in ws._charts]
    print(f"max_row={ws.max_row}  print_area={ws.print_area}  anclas={anclas}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for v in ("actual", "escala45", "escala40", "escala35", "escala30",
                  "filas_explicitas"):
            medir(convertir(preparar(origen, v), tmp, v), v)


if __name__ == "__main__":
    main()
