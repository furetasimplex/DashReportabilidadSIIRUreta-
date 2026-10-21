"""python -m balance_m6_contingencia.prepare <M6_generado.sql> --out auditorias/..."""
import argparse
from pathlib import Path
from .build_sql import build

def main():
    parser=argparse.ArgumentParser(description='Preparar capa/preview M6 desde fórmulas vigentes; no conecta ni despliega SQL.')
    parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if 'auditorias' not in args.out.resolve().parts:raise ValueError('Guardar preparaciones en auditorias/.')
    args.out.mkdir(parents=True,exist_ok=True)
    destination=args.out/'sp_m6_antes.sql'
    source=args.source.read_text(encoding='utf8')
    if destination.exists() and destination.read_text(encoding='utf8')!=source:raise ValueError('El respaldo ya existe y es diferente.')
    destination.write_text(source,encoding='utf8')
    print(build(args.out))

if __name__=='__main__':main()
