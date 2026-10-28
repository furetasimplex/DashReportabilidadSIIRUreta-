"""Excel operacional M6 publicado. Solo SELECT; conserva el paquete de la plantilla."""
from pathlib import Path
from datetime import datetime
import io
import json
import math
import uuid
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

import pandas as pd
from sqlalchemy import text
from openpyxl import load_workbook
from openpyxl.utils.datetime import to_excel

from ajuste_reporte.rep_prod_adjuster import _m6_payload_digest
from report_export.export_to_excel import calcular_resumen_mtd, FILAS_RESUMEN_MTD, MESES_ES

TEMPLATE = Path(__file__).resolve().parents[1] / 'reporte/Template_DatosConciliados_Reconciliados.xlsx'
# Mapeo revisado contra los encabezados combinados C18:AX20 de la referencia.
COLUMN_MAP = (
 ('D','Chancado_TMS_Real'),
 ('E','Humedad_Turno_A'),('F','Humedad_Turno_B'),('G','Humedad_promedio_dia'),
 ('H','Sal_turno_A'),('I','Sal_Turno_B'),('J','Sal_promedio_dia'),
 ('K','SRR_TMS_Turno_A'),('L','SRR_TMS_Turno_B'),('M','SRR_TMS_promedio_dia'),('N','SRR_TMS_Plan'),
 ('O','Ley_CuT_Real_srr'),('P','Ley_CuT_Plan_srr'),
 ('Q','Apilado_TMH_turno_A'),('R','Apilado_TMH_turno_B'),('S','Apilado_TMH_promedio_dia'),
 ('T','Apilado_TMS_Real'),('U','Apilado_TMS_Plan'),('V','Campana_apilado'),('W','Modulo_apilado'),('X','Avance_apilado'),
 ('Y','Ley_CuT_Real'),('Z','Ley_CuT_Plan'),('AA','Cobre_fino_Apilado_Real'),('AB','Cobre_fino_Apilado_Plan'),
 ('AC','TMS_Rotopala_1_Real'),('AD','TMS_Rotopala_1_Plan'),('AE','Campana_reclamo_oxidos'),('AF','Modulo_reclamo_oxidos'),('AG','Avance_reclamo_oxidos'),
 ('AH','TMS_Rotopala_2_Real'),('AI','TMS_Rotopala_2_Plan'),('AJ','Campana_reclamo_sulfuros'),('AK','modulo_reclamo_sulfuros'),('AL','Avance_reclamo_sulfuros'),
 ('AM','Camiones_TMS_Reclamo_Oxidos'),('AN','Camiones_TMS_Reclamo_Sulfuros'),('AO','Movido'),('AP','Extraido'),('AQ','Camiones_TMS_total'),('AR','Camiones_TMS_plan'),('AS','Campana_reclamo_camiones'),('AT','Modulo_reclamo_camiones'),
 ('AU','Total_Ripios_Incluye_Camiones_Real'),('AV','Total_Ripios_Incluye_Camiones_Plan'),('AW','Produccion_Catodos_Real'),('AX','Produccion_Catodos_Plan'),
)
FIELDS = [field for _, field in COLUMN_MAP]
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('', NS)
ET.register_namespace('r', REL)


def validate_published(data, metadata, official, candidates):
    """No admite mezclas, huecos, payload alterado ni versiones desplazadas."""
    if data.empty or len(set(str(x).lower() for x in data['run_id'])) != 1:
        raise ValueError('El caso debe tener un unico UUID publicado; no se mezclan corridas.')
    run = str(data.iloc[0]['run_id']).lower()
    trace = json.loads(metadata['totales_json'])
    if (trace.get('namespace') != 'DEV_SIIR.hidro.recon_caso'
            or trace.get('modelo_codigo') != 'hidrometalurgia_125_v2'
            or int(trace.get('caso_id', -1)) != int(metadata['caso_id'])
            or int(trace.get('modelo_id', -1)) != int(metadata['modelo_id'])
            or int(trace.get('solver_run_id', -1)) != int(metadata['solver_run_id'])
            or metadata['modelo_codigo'] != 'hidrometalurgia_125_v2'
            or metadata['estado_solver'] != 'success'):
        raise ValueError('Procedencia de caso/modelo/solver no verificable.')
    start, end = pd.to_datetime(trace['periodo']).normalize()
    if (start != pd.Timestamp(metadata['fecha_inicio']).normalize()
            or end != pd.Timestamp(metadata['fecha_fin']).normalize()
            or start.to_period('M') != end.to_period('M')):
        raise ValueError('Periodo incoherente o superior a un mes de plantilla.')
    dates = pd.to_datetime(data['Fecha']).dt.normalize()
    if dates.duplicated().any() or set(dates) != set(pd.date_range(start, end)):
        raise ValueError('Faltan fechas reconciliadas publicadas o hay duplicados; no se usa fallback medido.')
    if (not data['caso_id'].eq(int(metadata['caso_id'])).all()
            or not data['estado_validacion'].eq('VALIDADO').all()
            or not data['es_activa'].eq(True).all()):
        raise ValueError('Version no validada/activa o caso inconsistente.')
    if set(trace.get('columnas_operacionales', [])) != set(FIELDS):
        raise ValueError('El contrato publicado no contiene las 47 columnas.')
    # El escritor canoniza las columnas alfabeticamente, no en orden visual Excel.
    digest = _m6_payload_digest(data, sorted(FIELDS))
    if digest != trace.get('payload_sha256') or _m6_payload_digest(official, sorted(FIELDS)) != digest:
        raise ValueError('Payload publicado o vista oficial difiere del UUID solicitado.')
    # Mismo orden de la vista, pero empates rechazados en vez de TOP 1 arbitrario.
    for day, group in candidates.groupby('Fecha'):
        keys = [(pd.Timestamp(x.fecha_validacion) if pd.notna(x.fecha_validacion) else pd.Timestamp('1900-01-01'),
                 int(x.validation_id) if pd.notna(x.validation_id) else 0) for x in group.itertuples()]
        top = max(keys)
        winners = [str(x).lower() for x,k in zip(group['run_id'],keys) if k == top]
        if winners != [run]:
            raise ValueError('Seleccion oficial ambigua o reemplazada por otro UUID.')
    if len(candidates.groupby('Fecha')) != len(data) or len(official) != len(data):
        raise ValueError('Cobertura oficial incompleta.')
    return dict(caso_id=int(metadata['caso_id']), run_id=run,
                solver_run_id=int(metadata['solver_run_id']), modelo_codigo=metadata['modelo_codigo'],
                fecha_inicio=start, fecha_fin=end, payload_sha256=digest)


def fetch_published_reconciled(engine, caso_id, run_id=None):
    """Una transaccion de lectura, sin mantenedores, staging ni solver."""
    caso_id = int(caso_id)
    if run_id is not None:
        run_id = str(uuid.UUID(str(run_id)))
    from lixiviacion.phase_flags import guard_connection
    with engine.connect() as conn:
        with conn.begin():
            guard_connection(conn)  # Exclusivamente DEV hasta autorizacion de despliegue.
            data = pd.read_sql_query(text('''SELECT * FROM inventar_SpcHidr.Datos_conciliados_of_ver WITH(HOLDLOCK)
                WHERE caso_id=:caso AND estado_validacion='VALIDADO' AND es_activa=1
                  AND (:run IS NULL OR run_id=CONVERT(uniqueidentifier,:run)) ORDER BY Fecha'''), conn,
                params={'caso':caso_id, 'run':run_id})
            if data.empty or data['run_id'].astype(str).str.lower().nunique() != 1:
                raise ValueError('Seleccione un caso M6 con un unico UUID reconciliado publicado completo.')
            run_id = str(data.iloc[0]['run_id'])
            logs = pd.read_sql_query(text('''SELECT l.totales_json,c.id caso_id,c.modelo_id,m.codigo modelo_codigo,
                c.fecha_inicio,c.fecha_fin,r.id solver_run_id,r.estado estado_solver
                FROM inventar_SpcHidr.rep_prod_ajuste_log l WITH(HOLDLOCK)
                JOIN DEV_SIIR.hidro.recon_caso c WITH(HOLDLOCK) ON c.id=l.caso_id
                JOIN DEV_SIIR.hidro.recon_modelo m WITH(HOLDLOCK) ON m.id=c.modelo_id
                JOIN DEV_SIIR.hidro.recon_solver_run r WITH(HOLDLOCK)
                  ON r.id=TRY_CONVERT(int,JSON_VALUE(l.totales_json,'$.solver_run_id')) AND r.caso_id=c.id
                WHERE l.run_id=:run AND l.caso_id=:caso AND l.ok=1'''),conn,params={'run':run_id,'caso':caso_id})
            if len(logs) != 1:
                raise ValueError('No existe trazabilidad unica del UUID publicado.')
            args={'ini':pd.to_datetime(data['Fecha']).min().date(), 'fin':pd.to_datetime(data['Fecha']).max().date()}
            official = pd.read_sql_query(text('''SELECT * FROM inventar_SpcHidr.vw_datos_conciliados_reporte WITH(HOLDLOCK)
                WHERE Fecha BETWEEN :ini AND :fin ORDER BY Fecha'''),conn,params=args)
            candidates = pd.read_sql_query(text('''SELECT Fecha,run_id,fecha_validacion,validation_id
                FROM inventar_SpcHidr.Datos_conciliados_of_ver WITH(HOLDLOCK)
                WHERE Fecha BETWEEN :ini AND :fin AND ISNULL(estado_validacion,'VALIDADO')='VALIDADO' ORDER BY Fecha'''),conn,params=args)
            identity = validate_published(data, logs.iloc[0].to_dict(), official, candidates)
    return data[['Fecha']+FIELDS].copy(), identity


def _write_cells(xml, values):
    root = ET.fromstring(xml)
    sheetdata = root.find(f'{{{NS}}}sheetData')
    def key(ref):
        letters=''.join(x for x in ref if x.isalpha()); n=0
        for x in letters:n=n*26+ord(x)-64
        return n
    for ref,value in values.items():
        number=int(''.join(x for x in ref if x.isdigit()))
        row=next((r for r in sheetdata if r.get('r')==str(number)),None)
        if row is None:
            row=ET.Element(f'{{{NS}}}row',{'r':str(number)});sheetdata.append(row)
        cell=next((c for c in row if c.get('r')==ref),None)
        if cell is None:
            cell=ET.Element(f'{{{NS}}}c',{'r':ref});row.append(cell)
        for child in list(cell):cell.remove(child)
        cell.attrib.pop('t',None)
        if value is None or (not isinstance(value,str) and pd.isna(value)):
            continue
        if isinstance(value,(pd.Timestamp,datetime)):
            value=to_excel(pd.Timestamp(value).to_pydatetime())
        if isinstance(value,str):
            cell.set('t','inlineStr');t=ET.SubElement(ET.SubElement(cell,f'{{{NS}}}is'),f'{{{NS}}}t')
            t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value
        else:
            if not math.isfinite(float(value)):raise ValueError('Numero no finito en Excel.')
            ET.SubElement(cell,f'{{{NS}}}v').text=str(value)
        row[:]=sorted(row,key=lambda c:key(c.get('r')))
    sheetdata[:]=sorted(sheetdata,key=lambda r:int(r.get('r')))
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def calcular_resumen_reconciliado_mtd(data, fecha_inicio, fecha_fin):
    """Desglose M6 por componentes; nunca resta el total heredado de Camiones."""
    dates = pd.to_datetime(data['Fecha']).dt.normalize()
    period = data.loc[dates.between(pd.Timestamp(fecha_inicio).normalize(),
                                    pd.Timestamp(fecha_fin).normalize())].copy()
    summary = calcular_resumen_mtd(period, fecha_fin)

    def total(*fields):
        values = period[list(fields)].apply(pd.to_numeric, errors='coerce')
        # No convertir ausencia de componentes en tonelaje cero.
        if values.empty or values.isna().any().any():
            return None
        # Primero el subtotal de cada fecha y despues el acumulado del caso,
        # igual que el bloque diario; no redondear los indicadores publicados.
        return float(values.sum(axis=1).sum())

    def result(real, plan):
        difference = None if real is None or plan is None else real - plan
        return dict(real=real, plan=plan, diferencia=difference,
                    varianza=None if difference is None or plan == 0 else difference / plan)

    rot = ('TMS_Rotopala_1_Real', 'TMS_Rotopala_2_Real')
    trucks = ('Camiones_TMS_Reclamo_Oxidos', 'Camiones_TMS_Reclamo_Sulfuros')
    summary['Rotopala'] = result(total(*rot), total('TMS_Rotopala_1_Plan', 'TMS_Rotopala_2_Plan'))
    summary['Total Camiones'] = result(total(*trucks), total('Camiones_TMS_plan'))
    summary['Total Ripios'] = result(total(*rot, *trucks), total('Total_Ripios_Incluye_Camiones_Plan'))
    return summary


def export_published_reconciled(data, identity, template_path=TEMPLATE):
    """Edicion puntual OOXML: conserva estilos, combinaciones y pagina de referencia."""
    start,end=identity['fecha_inicio'],identity['fecha_fin']
    dates=pd.to_datetime(data['Fecha']).dt.normalize()
    if dates.duplicated().any() or set(dates)!=set(pd.date_range(start,end)):
        raise ValueError('Periodo publicado incompleto.')
    wb=load_workbook(template_path,read_only=False,data_only=False)
    ws=wb['Generador Reporte Diario']
    expected={'D18':'Chancado TMS','E19':'Humedades','H19':'Sal','K19':'SRR TMS','O19':'Ley CuT',
      'Q19':'Apilado TMH','T19':'Apilado TMS','Y19':'Ley CuT','AA19':'Cobre Fino Apilado',
      'AC19':'Rotopala1','AH19':'Rotopala2','AM19':'Camiones TMS','AU19':'Total Ripios (Incluye Camiones)',
      'AW18':'Producción Cátodos'}
    if any(str(ws[k].value).strip()!=v for k,v in expected.items()):
        raise ValueError('Encabezados de plantilla incompatibles con el mapeo explicito.')
    subheaders = ('Real','Turno A','Turno B','Dia','Turno A','Turno B','Dia',
        'Turno A','Turno B','Dia','Plan','Real','Plan','Turno A','Turno B','Día',
        'Real','Plan','Campaña','Módulo','Avance','Real','Plan','Real','Plan',
        'Real','Plan','Campaña','Módulo','Avance','Real','Plan','Campaña','Módulo','Avance',
        'Reclamo Ox','Reclamo Su','Movido','Extraido','Total','Plan','Campaña','Módulo',
        'Real','Plan','Real','Plan')
    if len(set(FIELDS)) != 47 or any(str(ws[f'{col}20'].value).strip()!=header
                                    for (col,_),header in zip(COLUMN_MAP,subheaders)):
        raise ValueError('Las 47 columnas no corresponden al encabezado operacional verificado.')
    # Cada indicador mantiene su columna exacta; no se reutilizan datos del archivo.
    values={f'{col}{row}':None for row in range(21,53) for col in ['C',*[x for x,_ in COLUMN_MAP],'AY']}
    for day in pd.date_range(start.replace(day=1),start+pd.offsets.MonthEnd(0)):
        values[f'C{20+day.day}']=day
    for _,r in data.iterrows():
        row=20+pd.Timestamp(r['Fecha']).day
        for col,field in COLUMN_MAP:values[f'{col}{row}']=r[field]
    summary=calcular_resumen_reconciliado_mtd(data,start,end)
    values.update({'C3':'Datos Conciliados Reconciliados', 'I3':MESES_ES[end.month-1],
      'I4':f'FY{(end.year+(end.month>=7))%100:02d}', 'I5':end,
      'Z3':f'MTD {start:%d-%m-%Y} a {end:%d-%m-%Y}',
      'AG3':f'Caso {identity["caso_id"]} | Solver {identity["solver_run_id"]} | {start:%d/%m}–{end:%d/%m/%Y} | Fuera del caso: sin datos. AQ: Camiones_TMS_total heredado; puede diferir de componentes reconciliados.'})
    for name,row in FILAS_RESUMEN_MTD.items():
        for col,k in zip(('AB','AC','AD','AE'),('real','plan','varianza','diferencia')):
            values[f'{col}{row}']=summary[name][k]
    # Las filas no usadas del resumen no deben conservar valores de la referencia.
    for row in (10,11,12,13):
        for col in ('AB','AC','AD','AE'):values[f'{col}{row}']=None
    current=data.loc[dates==end].iloc[0]
    def fmt(v):return 'no disponible' if v is None or pd.isna(v) else f'{v:,.0f}'.replace(',','.')
    label=f'{end.day} de {MESES_ES[end.month-1]}, {end.year}'
    mail={'A1':'Datos para correo','A3':'Adjunto Producciones Conciliadas Reconciliadas.',
      'A4':f'Chancado, Apilado y Ripios al {label}.','A5':'Avances: información no disponible; fuente/metodología no verificadas.',
      'A6':f'Cátodos al {label}.','A8':f'Avances al {label}:',
      'A9':'Apilamiento: información no disponible','A10':'Ripios Rotopala 1: información no disponible',
      'A11':'Ripios Rotopala 2: información no disponible',
      'A13':f'Producción: caso {identity["caso_id"]}; acumulado {start:%d/%m}–{end:%d/%m/%Y}.',
      'A14':f'Producción de Cátodos [t] diario / acumulado: {fmt(current["Produccion_Catodos_Real"])} / {fmt(summary["Producción"]["real"])}',
      'A15':f'Apilado [t] diario / acumulado: {fmt(current["Apilado_TMS_Real"])} / {fmt(summary["Apilado"]["real"])}',
      'J3':'Resumen de datos','J4':'Check balance: información no disponible',
      'J5':'Sin metodología de balance verificada para este exportable.'}
    with ZipFile(template_path) as source:
        files={n:source.read(n) for n in source.namelist()}
    book=ET.fromstring(files['xl/workbook.xml']);rels=ET.fromstring(files['xl/_rels/workbook.xml.rels'])
    targets={r.get('Id'):r.get('Target').lstrip('/') for r in rels}
    sheets=book.find(f'{{{NS}}}sheets');keep=['Generador Reporte Diario','Datos para correo'];removed=[];paths={}
    for s in list(sheets):
        rid=s.get(f'{{{REL}}}id');path=targets[rid]
        path=path if path.startswith('xl/') else 'xl/'+path
        if s.get('name') not in keep:
            sheets.remove(s);removed.append(path)
            for r in list(rels):
                if r.get('Id')==rid:rels.remove(r)
        else:paths[s.get('name')]=path
    if [s.get('name') for s in sheets]!=keep:raise ValueError('Hojas de referencia inesperadas.')
    views=book.find(f'{{{NS}}}bookViews')
    if views is not None:
        for v in views:v.set('activeTab','0')
    names=book.find(f'{{{NS}}}definedNames')
    if names is not None:
        for n in list(names):
            local=n.get('localSheetId')
            if local in ('1','2'):names.remove(n)
            elif local=='3':n.set('localSheetId','1')
    files['xl/workbook.xml']=ET.tostring(book,encoding='utf-8',xml_declaration=True)
    files['xl/_rels/workbook.xml.rels']=ET.tostring(rels,encoding='utf-8',xml_declaration=True)
    files[paths[keep[0]]]=_write_cells(files[paths[keep[0]]],values)
    files[paths[keep[1]]]=_write_cells(files[paths[keep[1]]],mail)
    types=ET.fromstring(files['[Content_Types].xml'])
    for n in list(types):
        if n.get('PartName','').lstrip('/') in removed:types.remove(n)
    files['[Content_Types].xml']=ET.tostring(types,encoding='utf-8',xml_declaration=True)
    for path in removed:
        files.pop(path,None)
        folder,filename=path.rsplit('/',1);files.pop(folder+'/_rels/'+filename+'.rels',None)
    out=io.BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)
    return out.getvalue()


def build_reconciled_daily_excel(engine, caso_id):
    data,identity=fetch_published_reconciled(engine,caso_id)
    content=export_published_reconciled(data,identity)
    filename=(f'DatosConciliadosReconciliados_Caso{identity["caso_id"]}_'
              f'Solver{identity["solver_run_id"]}_{identity["fecha_inicio"]:%Y%m%d}_'
              f'{identity["fecha_fin"]:%Y%m%d}_{identity["run_id"]}.xlsx')
    return content,filename,identity
