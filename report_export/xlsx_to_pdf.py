from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

__all__ = [
    'xlsx_to_pdf',
    'convert_xlsx_to_pdf',
    'convert_excel_to_pdf',
    'generar_pdf_desde_excel',
    'excel_to_pdf',
]


class LibreOfficeConversionError(RuntimeError):
    pass


def _soffice_path() -> str:
    soffice = shutil.which('soffice')
    if soffice:
        return soffice
    candidates = (
        '/usr/bin/soffice',
        '/usr/local/bin/soffice',
        '/snap/bin/libreoffice',
        '/opt/libreoffice/program/soffice',
        '/usr/lib/libreoffice/program/soffice',
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise LibreOfficeConversionError(
        "No fue posible convertir el Excel a PDF con LibreOffice. "
        "Instale LibreOffice y asegúrese de que 'soffice' esté en el PATH."
    )


def _normalize_input(xlsx_path: str | os.PathLike[str]) -> Path:
    p = Path(xlsx_path)
    if not p.exists():
        raise FileNotFoundError(f'No existe el archivo Excel: {p}')
    if not p.is_file():
        raise IsADirectoryError(f'La ruta no es un archivo: {p}')
    return p


def _run_soffice_convert(input_file: Path, outdir: Path, profile_dir: Path) -> subprocess.CompletedProcess[str]:
    soffice = _soffice_path()
    cmd = [
        soffice,
        '--headless',
        '--nologo',
        '--nofirststartwizard',
        '--norestore',
        '--nodefault',
        '--nolockcheck',
        f'-env:UserInstallation=file://{profile_dir.as_posix()}',
        '--convert-to',
        'pdf:calc_pdf_Export',
        '--outdir',
        str(outdir),
        str(input_file),
    ]
    env = os.environ.copy()
    env['HOME'] = str(profile_dir)
    env['XDG_CONFIG_HOME'] = str(profile_dir / '.config')
    env['XDG_CACHE_HOME'] = str(profile_dir / '.cache')
    env['SAL_USE_VCLPLUGIN'] = 'gen'
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)


def _find_output_pdf(outdir: Path, input_file: Path) -> Optional[Path]:
    expected = outdir / f'{input_file.stem}.pdf'
    if expected.exists() and expected.stat().st_size > 0:
        return expected

    same_stem = list(outdir.glob(f'{input_file.stem}*.pdf'))
    for candidate in same_stem:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    pdfs = [p for p in outdir.glob('*.pdf') if p.is_file() and p.stat().st_size > 0]
    if len(pdfs) == 1:
        return pdfs[0]
    if pdfs:
        pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return pdfs[0]
    return None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def convert_excel_to_pdf(
    xlsx_path: str | os.PathLike[str],
    pdf_path: str | os.PathLike[str] | None = None,
    *,
    overwrite: bool = True,
    retries: int = 2,
) -> str:
    input_file = _normalize_input(xlsx_path)
    if pdf_path is None:
        pdf_path = input_file.with_suffix('.pdf')
    output_file = Path(pdf_path)
    _ensure_parent(output_file)

    last_error = None
    for attempt in range(max(1, retries)):
        with tempfile.TemporaryDirectory(prefix='lo_profile_') as profile_tmp, tempfile.TemporaryDirectory(prefix='lo_out_') as out_tmp:
            profile_dir = Path(profile_tmp)
            outdir = Path(out_tmp)
            try:
                result = _run_soffice_convert(input_file, outdir, profile_dir)
            except subprocess.TimeoutExpired as exc:
                last_error = exc
                continue

            pdf_candidate = _find_output_pdf(outdir, input_file)
            if pdf_candidate is not None:
                if output_file.exists() and not overwrite:
                    raise FileExistsError(f'El archivo destino ya existe: {output_file}')
                shutil.copy2(pdf_candidate, output_file)
                if output_file.exists() and output_file.stat().st_size > 0:
                    return str(output_file)

            combined = (result.stdout or '') + '
' + (result.stderr or '')
            last_error = LibreOfficeConversionError(
                'LibreOffice finalizó sin generar el archivo PDF esperado. '
                f'Detalle: {combined.strip() or "sin salida"}'
            )
            time.sleep(0.5)

    raise LibreOfficeConversionError(
        'No fue posible convertir el Excel a PDF con LibreOffice. '
        "Instale LibreOffice y asegúrese de que 'soffice' esté en el PATH. "
        f'Detalle: {last_error}'
    )


def xlsx_to_pdf(*args, **kwargs) -> str:
    return convert_excel_to_pdf(*args, **kwargs)


def convert_xlsx_to_pdf(*args, **kwargs) -> str:
    return convert_excel_to_pdf(*args, **kwargs)


def generar_pdf_desde_excel(*args, **kwargs) -> str:
    return convert_excel_to_pdf(*args, **kwargs)


def excel_to_pdf(*args, **kwargs) -> str:
    return convert_excel_to_pdf(*args, **kwargs)
