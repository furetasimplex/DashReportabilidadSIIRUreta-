"""
Conversión de libros Excel (.xlsx) a PDF.

Único motor: LibreOffice headless (`soffice` / `libreoffice`).
Post-proceso: pypdf (+ pdfplumber) para normalizar a A3.

Requisito en servidor Linux (y en Windows de desarrollo): LibreOffice instalado
y `soffice` en PATH, o en las rutas estándar de instalación.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

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
    landscape: bool = False,
) -> bytes:
    """Ajusta el contenido de una única página al lienzo A3 solicitado."""
    import pdfplumber
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation
    from pypdf.generic import DecodedStreamObject, NameObject

    reader = PdfReader(BytesIO(pdf_bytes))
    if len(reader.pages) != 1:
        # LibreOffice no encoge tanto como fitToPage 1x1 ideal y puede
        # desbordar el contenido en varias paginas apiladas verticalmente
        # (fitToWidth=1 => 1 pagina de ancho). Se concatenan en una sola tira
        # vertical y luego el recorte+escalado A3 de abajo se encarga del resto.
        pdf_bytes = _stack_pages_vertically(pdf_bytes)
        reader = PdfReader(BytesIO(pdf_bytes))

    source = reader.pages[0]
    source_width = float(source.mediabox.width)
    source_height = float(source.mediabox.height)
    if source_width <= 0 or source_height <= 0:
        raise RuntimeError("La pagina PDF generada tiene dimensiones invalidas.")

    # Se detecta el rectangulo realmente ocupado y se lleva al A3
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
    page_width = A3_HEIGHT_PT if landscape else A3_WIDTH_PT
    page_height = A3_WIDTH_PT if landscape else A3_HEIGHT_PT
    target_width = page_width - 2 * margin_pt
    target_height = page_height - 2 * margin_pt
    # Escala uniforme (misma en X e Y) para no deformar tablas ni graficos.
    # Un escalado independiente por eje "aplana" el contenido cuando el
    # recuadro ocupado no comparte la proporcion del A3 (caso LibreOffice).
    scale = min(target_width / content_width, target_height / content_height)
    scaled_width = content_width * scale
    scaled_height = content_height * scale
    offset_x = margin_pt + (target_width - scaled_width) / 2.0
    offset_y = margin_pt + (target_height - scaled_height) / 2.0

    a3_page = PageObject.create_blank_page(
        width=page_width,
        height=page_height,
    )
    fondo = DecodedStreamObject()
    fondo.set_data(
        (
            "q 1 1 1 rg 0 0 "
            f"{page_width:.4f} {page_height:.4f} re f Q\n"
        ).encode("ascii")
    )
    a3_page[NameObject("/Contents")] = fondo
    transform = (
        Transformation()
        .translate(-content_x0, -content_y0)
        .scale(scale, scale)
        .translate(offset_x, offset_y)
    )
    a3_page.merge_transformed_page(source, transform)

    writer = PdfWriter()
    writer.add_page(a3_page)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def normalize_pages_to_a3_landscape(
    pdf_bytes: bytes,
    margin_pt: float = 18.0,
) -> bytes:
    """Normaliza cada página a A3 horizontal sin unir páginas verticalmente."""
    from pypdf import PdfReader, PdfWriter

    source_reader = PdfReader(BytesIO(pdf_bytes))
    output_writer = PdfWriter()
    for source_page in source_reader.pages:
        one_page_writer = PdfWriter()
        one_page_writer.add_page(source_page)
        one_page = BytesIO()
        one_page_writer.write(one_page)
        normalized = normalize_single_page_to_a3(
            one_page.getvalue(),
            margin_pt=margin_pt,
            landscape=True,
        )
        normalized_reader = PdfReader(BytesIO(normalized))
        output_writer.add_page(normalized_reader.pages[0])

    output = BytesIO()
    output_writer.write(output)
    return output.getvalue()


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
            "LibreOffice no está instalado o no se encontró 'soffice'/"
            "'libreoffice' en el PATH (ni en las rutas de instalación estándar)."
        )

    outdir = pdf_path.parent
    # Perfil de usuario propio por conversion: sin esto, dos workers de gunicorn
    # convirtiendo a la vez chocan en ~/.config/libreoffice y el segundo falla.
    # ponytail: perfil desechable por llamada; si el arranque en frio pesa,
    # cachear un perfil por worker (env var con el PID).
    perfil = (outdir / "lo_profile").resolve().as_uri()
    result = subprocess.run(
        [
            soffice,
            "--headless",
            f"-env:UserInstallation={perfil}",
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
    Convierte bytes de un libro .xlsx a PDF con LibreOffice headless.

    Requiere LibreOffice instalado en el entorno (Linux de producción o
    Windows de desarrollo).
    """
    if not xlsx_bytes:
        raise RuntimeError("El archivo Excel está vacío.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        nombre_temporal = f"reporte_{uuid.uuid4().hex}"
        xlsx_path = tmp / f"{nombre_temporal}.xlsx"
        pdf_path = tmp / f"{nombre_temporal}.pdf"
        xlsx_path.write_bytes(xlsx_bytes)

        try:
            _convert_with_libreoffice(xlsx_path, pdf_path, timeout_sec)
        except Exception as exc:
            raise RuntimeError(
                "No fue posible convertir el Excel a PDF con LibreOffice. "
                "Instale LibreOffice y asegúrese de que 'soffice' esté en el PATH. "
                f"Detalle: {exc}"
            ) from exc

        if not pdf_path.is_file():
            raise RuntimeError("La conversión a PDF no generó un archivo de salida.")

        logger.info(
            "[PDF] converter=libreoffice size=%s bytes",
            pdf_path.stat().st_size,
        )
        return pdf_path.read_bytes()
