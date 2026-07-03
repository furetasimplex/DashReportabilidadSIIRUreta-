"""
Conversión de libros Excel (.xlsx) a PDF.

Windows: Microsoft Excel vía COM (win32com).
Linux/Docker: LibreOffice headless (soffice).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

XL_TYPE_PDF = 0
A3_WIDTH_PT = 841.8898
A3_HEIGHT_PT = 1190.5512


def _stack_pages_vertically(pdf_bytes: bytes) -> bytes:
    """Une varias paginas en una sola tira vertical (pagina 0 arriba)."""
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation

    reader = PdfReader(BytesIO(pdf_bytes))
    pages = reader.pages
    total_height = sum(float(p.mediabox.height) for p in pages)
    max_width = max(float(p.mediabox.width) for p in pages)

    combined = PageObject.create_blank_page(width=max_width, height=total_height)
    cursor_y = total_height
    for page in pages:
        cursor_y -= float(page.mediabox.height)
        combined.merge_transformed_page(
            page, Transformation().translate(0, cursor_y)
        )

    writer = PdfWriter()
    writer.add_page(combined)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def normalize_single_page_to_a3(
    pdf_bytes: bytes,
    margin_pt: float = 24.0,
) -> bytes:
    """Ajusta el contenido de una unica pagina al lienzo A3 vertical."""
    import pdfplumber
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation
    from pypdf.generic import DecodedStreamObject, NameObject

    reader = PdfReader(BytesIO(pdf_bytes))
    if len(reader.pages) != 1:
        # LibreOffice (Linux) no encoge tanto como Excel para fitToPage 1x1
        # y desborda el contenido en varias paginas apiladas verticalmente
        # (fitToWidth=1 => 1 pagina de ancho). Se concatenan en una sola tira
        # vertical y luego el recorte+escalado A3 de abajo se encarga del resto.
        pdf_bytes = _stack_pages_vertically(pdf_bytes)
        reader = PdfReader(BytesIO(pdf_bytes))

    source = reader.pages[0]
    source_width = float(source.mediabox.width)
    source_height = float(source.mediabox.height)
    if source_width <= 0 or source_height <= 0:
        raise RuntimeError("La pagina PDF generada tiene dimensiones invalidas.")

    # Excel puede ignorar A3 si el controlador de impresora activo no lo
    # soporta. Se detecta el rectangulo realmente ocupado y se lleva al A3
    # con margenes controlados, evitando una pagina diminuta en el centro.
    with pdfplumber.open(BytesIO(pdf_bytes)) as plumber_pdf:
        plumber_page = plumber_pdf.pages[0]
        objetos = []
        for coleccion in plumber_page.objects.values():
            objetos.extend(coleccion)

    limites = []
    for obj in objetos:
        x0 = obj.get("x0")
        x1 = obj.get("x1")
        y0 = obj.get("y0")
        y1 = obj.get("y1")
        if None in (x0, x1, y0, y1):
            continue
        ancho = float(x1) - float(x0)
        alto = float(y1) - float(y0)
        if ancho >= source_width * 0.98 and alto >= source_height * 0.98:
            continue
        limites.append((float(x0), float(y0), float(x1), float(y1)))

    if limites:
        padding = 6.0
        content_x0 = max(0.0, min(v[0] for v in limites) - padding)
        content_y0 = max(0.0, min(v[1] for v in limites) - padding)
        content_x1 = min(source_width, max(v[2] for v in limites) + padding)
        content_y1 = min(source_height, max(v[3] for v in limites) + padding)
    else:
        content_x0, content_y0 = 0.0, 0.0
        content_x1, content_y1 = source_width, source_height

    content_width = max(content_x1 - content_x0, 1.0)
    content_height = max(content_y1 - content_y0, 1.0)
    target_width = A3_WIDTH_PT - 2 * margin_pt
    target_height = A3_HEIGHT_PT - 2 * margin_pt
    scale_x = target_width / content_width
    scale_y = target_height / content_height

    a3_page = PageObject.create_blank_page(
        width=A3_WIDTH_PT,
        height=A3_HEIGHT_PT,
    )
    fondo = DecodedStreamObject()
    fondo.set_data(
        (
            "q 1 1 1 rg 0 0 "
            f"{A3_WIDTH_PT:.4f} {A3_HEIGHT_PT:.4f} re f Q\n"
        ).encode("ascii")
    )
    a3_page[NameObject("/Contents")] = fondo
    transform = (
        Transformation()
        .translate(-content_x0, -content_y0)
        .scale(scale_x, scale_y)
        .translate(margin_pt, margin_pt)
    )
    a3_page.merge_transformed_page(source, transform)

    writer = PdfWriter()
    writer.add_page(a3_page)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _convert_with_excel_com(xlsx_path: Path, pdf_path: Path) -> None:
    import win32com.client  # type: ignore[import-untyped]

    excel = None
    workbook = None
    try:
        # DispatchEx fuerza una instancia aislada y evita interferir con un
        # Excel que el usuario ya tenga abierto.
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(xlsx_path.resolve()))
        workbook.ExportAsFixedFormat(
            Type=XL_TYPE_PDF,
            Filename=str(pdf_path.resolve()),
            Quality=0,
            IncludeDocProperties=True,
            IgnorePrintAreas=False,
            OpenAfterPublish=False,
        )
    finally:
        if workbook is not None:
            workbook.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()


def _find_soffice() -> str | None:
    candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
    ]
    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidates.extend([
            os.path.join(program_files, "LibreOffice", "program", "soffice.exe"),
            os.path.join(
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                "LibreOffice",
                "program",
                "soffice.exe",
            ),
        ])
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def _convert_with_libreoffice(
    xlsx_path: Path,
    pdf_path: Path,
    timeout_sec: int,
) -> None:
    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice no está instalado o no se encontró 'soffice' en el PATH."
        )

    outdir = pdf_path.parent
    result = subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(xlsx_path.resolve()),
        ],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"LibreOffice no pudo convertir el Excel a PDF. {stderr}"
        )

    generated = outdir / f"{xlsx_path.stem}.pdf"
    if not generated.is_file():
        raise RuntimeError(
            "LibreOffice finalizó sin generar el archivo PDF esperado."
        )
    if generated.resolve() != pdf_path.resolve():
        generated.replace(pdf_path)


def convert_xlsx_bytes_to_pdf(
    xlsx_bytes: bytes,
    timeout_sec: int = 120,
) -> bytes:
    """
    Convierte bytes de un libro .xlsx a PDF.

    En Windows intenta Excel COM primero; si falla o no está disponible,
    usa LibreOffice headless.
    """
    if not xlsx_bytes:
        raise RuntimeError("El archivo Excel está vacío.")

    converter_used = None
    last_error: Exception | None = None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        xlsx_path = tmp / "reporte.xlsx"
        pdf_path = tmp / "reporte.pdf"
        xlsx_path.write_bytes(xlsx_bytes)

        if sys.platform == "win32":
            try:
                _convert_with_excel_com(xlsx_path, pdf_path)
                converter_used = "excel_com"
            except ImportError:
                last_error = RuntimeError(
                    "pywin32 no está instalado; no se puede usar Excel COM."
                )
            except Exception as exc:
                last_error = exc
                logger.warning("[PDF] Excel COM falló: %s", exc)

        if converter_used is None:
            try:
                _convert_with_libreoffice(xlsx_path, pdf_path, timeout_sec)
                converter_used = "libreoffice"
            except Exception as exc:
                last_error = exc

        if converter_used is None:
            detail = str(last_error) if last_error else "convertidor desconocido"
            raise RuntimeError(
                "No fue posible convertir el Excel a PDF. "
                "Instale Microsoft Excel (Windows) o LibreOffice. "
                f"Detalle: {detail}"
            ) from last_error

        if not pdf_path.is_file():
            raise RuntimeError("La conversión a PDF no generó un archivo de salida.")

        logger.info("[PDF] converter=%s size=%s bytes", converter_used, pdf_path.stat().st_size)
        return pdf_path.read_bytes()
