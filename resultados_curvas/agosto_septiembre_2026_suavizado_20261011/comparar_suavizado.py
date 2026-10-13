from pathlib import Path
import shutil,sys,json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(r'C:\Users\5330\Desktop\HidroNueva\DashReportabilidadSIIR')
old=root/'resultados_curvas/agosto_septiembre_2026_20261011'
out=root/'resultados_curvas/agosto_septiembre_2026_suavizado_20261011'
before=pd.read_csv(old/'detalle_diario.csv',parse_dates=['date'])
after=pd.read_csv(out/'detalle_diario.csv',parse_dates=['date'])
fig,axes=plt.subplots(1,2,figsize=(13,4),sharey=True)
for ax,scenario in zip(axes,['actual','envolvente']):
    for frame,label,color in [(before,'Antes','#64748B'),(after,'Corregido','#E86D1F')]:
        p=frame[(frame.material=='SULFUROS')&(frame.pila=='P22')&(frame.escenario==scenario)].sort_values('date')
        ax.plot(p.date,100*p.factor_drenaje_real,label=label,color=color,linewidth=2)
    ax.axvline(pd.Timestamp('2026-08-08'),linestyle=':',color='#64748B')
    ax.set_title('P22 · '+('rampa actual' if scenario=='actual' else 'techo por edad experimental'))
    ax.grid(alpha=.15);ax.legend();ax.tick_params(axis='x',rotation=30)
axes[0].set_ylabel('Factor de drenaje (%)')
fig.suptitle('Empalme entre ventanas: agosto 2026')
fig.tight_layout();fig.savefig(out/'comparacion_empalme_P22.png',dpi=160);plt.close(fig)
checks=pd.read_csv(out/'cierres_por_caso_pad.csv')
ledger=checks[checks.magnitud.isin(['q_pls_final','fino_pls_final'])].pivot(index=['escenario','material','caso_id'],columns='magnitud',values='inventario_declarado').reset_index().sort_values(['escenario','material','caso_id'])
ledger=ledger.rename(columns={'q_pls_final':'volumen_aporte_m3','fino_pls_final':'cobre_aporte_t'})
ledger['cu_aporte_acumulado_t']=ledger.groupby(['escenario','material']).cobre_aporte_t.cumsum()
ledger['stock_inicial_minimo_requerido_t']=ledger.groupby(['escenario','material']).cu_aporte_acumulado_t.cummax().clip(lower=0)
ledger['stock_disponible_verificado']=False
ledger.to_csv(out/'balance_inventario.csv',index=False,encoding='utf-8-sig')
summary=json.loads((out/'resumen.json').read_text(encoding='utf-8'))
note='''# Empalme suave y balance de cobre

El salto de SULFUROS/P22 con techo por edad pasó de 14,51 a 0,52 puntos porcentuales.
En la rampa actual, la bajada pasó de 1,82 a 0,63 puntos porcentuales. La continuación
después de los 30 días conserva el factor heredado y limita cambios a 3 puntos
porcentuales por día calendario, como parámetro provisional.

La compensación del piso conserva masa de Cu por separado del volumen. Se corrigió
el exceso de 0,632 t Cu de Caso 8. Cierran los 64 balances de ambos escenarios,
incluyendo los términos pendientes: no equivale a demostrar stock disponible.

`balance_inventario.csv` separa volumen y Cu requerido por PAD y ventana. Positivo
es aporte desde inventario; negativo es retención. El stock inicial mínimo se
calcula como el máximo de aportes netos acumulados bajo esta hipótesis. No mide
la existencia física de ese stock, ni lo asigna a la recuperación de las pilas.
Para validar la explicación física faltan inventarios medidos al inicio y cierre.

El techo por edad sigue siendo experimental. Agosto usa Casos oficiales 5–8;
septiembre muestra riego observado y PLS proxy, sin reconciliación. El ensayo
usa el snapshot local, sin SQL ni guardado de runs.
'''
(out/'CAMBIOS_Y_BALANCE.md').write_text(note,encoding='utf-8')
for name in ['replay_suavizado.py','graficar_suavizado.py','comparar_suavizado.py']:
    shutil.copy2(Path(__file__).parent/name,out/name)
print(ledger[['escenario','material','caso_id','cobre_aporte_t','stock_inicial_minimo_requerido_t']].to_string(index=False))
