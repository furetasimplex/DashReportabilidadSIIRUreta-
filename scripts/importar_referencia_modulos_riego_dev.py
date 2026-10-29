"""Preview DEV explicito; nunca examina carpetas ni interpreta PDF/Excel.

Persistir requiere --persistir Y el mismo contexto POST administrativo del backend.
No crea autenticacion alternativa para ejecutar escrituras desde una terminal.
"""
from pathlib import Path
import sys,argparse,hashlib,json,uuid,io,contextlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from env_loader import load_app_env
from lixiviacion import irrigation_modules_db as db, irrigation_modules_model as model

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fecha',required=True)
    parser.add_argument('--pad',required=True,type=int,help='Identidad SQL del PAD')
    parser.add_argument('--parcela',required=True,type=int,help='Identidad SQL de parcela, no numero visible')
    parser.add_argument('--cantidad-modulos',default=None)
    parser.add_argument('--archivo',required=True,type=Path)
    parser.add_argument('--fuente',required=True)
    flags=parser.add_mutually_exclusive_group()
    flags.add_argument('--dry-run',action='store_true')
    flags.add_argument('--persistir',action='store_true')
    args=parser.parse_args(argv);load_app_env()
    if not args.archivo.is_file():parser.error('El archivo explicito no existe.')
    origin=hashlib.sha256(args.archivo.read_bytes()).hexdigest()
    with contextlib.redirect_stdout(io.StringIO()):
        preview=db.preview_reference(args.fecha,args.pad,args.parcela,args.cantidad_modulos)
    result=dict(modo='dry-run',archivo=str(args.archivo),fuente=args.fuente,hash_archivo=origin,preview=preview)
    if args.persistir:
        # _actor exige sesion POST/admin/Origin/flags existentes. Sin ese contexto
        # no hay INSERT; no se acepta un usuario arbitrario por linea de comandos.
        with contextlib.redirect_stdout(io.StringIO()):
            result['persistencia']=db.import_reference(dict(fecha=args.fecha,pad_id=args.pad,parcela_id=args.parcela,
                cantidad=args.cantidad_modulos,archivo=str(args.archivo),fuente=args.fuente,hash_origen=origin,
                context_token=preview['snapshot']['context_token'],idempotency_key=str(uuid.uuid4())))
        result['modo']='persistido'
    print(model.dump(result))
    return result
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
