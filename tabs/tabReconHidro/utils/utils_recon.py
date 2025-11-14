from scipy import sparse
import numpy as np
from gekko import GEKKO
import pandas as pd
from openpyxl import load_workbook


def balance_core(mediciones,error,fn="Normal",u=1,cf=1,cw=1,expk=1,cp=1):

    #mediciones[:,1] = mediciones[:,1]/100
    deltas = [ 16,  17,  35,  36,  56,  60,  63,  65,  66,  69,  70,  73,  76,
        78, 101, 102, 103, 105, 108, 110, 111, 112, 113]
    deltas = [i-1 for i in deltas]
    deltas = np.array(deltas)

    matriz = np.array([[   1.,    2.,   -3.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [   3.,   -4.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [   4.,   -5.,   -6.,   -7.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [   6.,    8.,   10.,  -12.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [   7.,    9.,   11.,  -13.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  12.,   13.,   14.,   15.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  14.,  -18.,  -21.,  -16.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  15.,  -19.,  -22.,  -17.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  18.,   19.,  -20.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  24.,   29.,   42.,   44.,   45.,  -49.,  -50.,  -51.,  -57.,
         -58.,  -27.,  -56.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  23.,   28.,   39.,   40.,   41.,   43.,   46.,  -47.,  -48.,
         -67.,  -68.,  -26.,  -66.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  55.,   59.,  -43.,  -44.,  -61.,  -60.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  51.,  -45.,  -62.,  -63.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  50.,  -64.,  -83.,  -84.,  -85.,  -86.,  -65.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  48.,   49.,   54.,  -79.,  -80.,  -81.,  -82.,  -77.,  -78.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  47.,  -41.,  -75.,  -76.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  54.,  -52.,  -42.,  -39.,  -40.,  -74.,  -73.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  38.,  -70.,  -72.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  37.,  -54.,  -46.,  -71.,  -69.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  33.,  -37.,  -38.,  -34.,  -35.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  30.,   31.,   34.,  -32.,  -33.,  -36.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  79.,   80.,   81.,   82.,   83.,   84.,   85.,   86.,   92.,
          93.,   94.,   95.,   88.,   89.,   90.,   91.,   96.,   97.,
          98.,   99., -100.,  -54.,  -55.,  -87., -101., -102., -103.],
       [ 100., -104., -106., -107.,  -96.,  -97.,  -98.,  -99., -105.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [ 106.,  107., -109., -108.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [ 109., -114., -115., -110., -111., -112., -113.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.],
       [  25.,   -8.,   -9.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,
           0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.,    0.]])

    lista_rows = []
    lista_columns = []
    lista_data = []
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            if matriz[i,j] != 0:
                lista_rows.append(i)
                col = int(np.abs(matriz[i,j])-1)
                lista_columns.append(col)
                lista_data.append(np.sign(matriz[i,j]))
    coo = sparse.coo_array((lista_data, (lista_rows, lista_columns)))
    matriz = coo.toarray()

    for k in deltas:
        bool_values = matriz[:,k] != 0
        matriz[bool_values,k] = -np.sign(mediciones[k,0])
    inventarios_masa = 2*(mediciones[:,0] >= 0)-1
    mediciones[:,0] = np.abs(mediciones[:,0])
    m = GEKKO(remote=False)
    n_components = 1
    x = m.Array(m.Var,(matriz.shape[1]))
    x_c = m.Array(m.Var,(matriz.shape[1],n_components))
    tms_medicion = mediciones[:,0]

    mediciones_leyes = []
    for k in range(n_components):
        leyes_medicion = mediciones[:,k+1]
        mediciones_leyes.append(leyes_medicion)

    balances = []
    Masa_finos = m.Array(m.Var,(matriz.shape[1],n_components))
    balance_TMS = np.dot(matriz,x)

    for k in range(n_components):
        Masa_finos[:,k] = np.multiply(x,x_c[:,k])
    for k in range(n_components):
        balances.append(np.dot(matriz,Masa_finos[:,k]))

    def normal(r):
        return r**2

    vector = np.array([1]*mediciones.shape[0])
    for i in range(mediciones.shape[0]):
        if mediciones[i,0]==0:
            vector[i] = 0
    ob = m.Array(m.Var, mediciones.shape[0])
    for i in range(mediciones.shape[0]):
        if tms_medicion[i]==0:
            divisor = 1
        else:
            if error.iloc[i,0] == 0:
                divisor = 1
            else:
                divisor = tms_medicion[i]*error.iloc[i,0]
        r = (x[i]-tms_medicion[i])/divisor
        ob[i] =  normal(r)
    ob = m.sum(ob)
    ob_finos = m.Array(m.Var, (mediciones.shape[0],n_components))
    for k in range(n_components):
        for i in range(mediciones.shape[0]):
            if mediciones_leyes[k][i]==0:
                divisor = 1
            else:
                if error.iloc[i,k+1] == 0:
                    divisor = 1
                else:
                    divisor = mediciones_leyes[k][i]*error.iloc[i,k+1]
            r = (x_c[i,k]-mediciones_leyes[k][i])/divisor
            ob_finos[i,k] =normal(r)
        ob_finos= m.sum(ob_finos)
    obj_finos_sum = m.sum(ob_finos)

    m.Obj(ob+obj_finos_sum)
    m.options.SOLVER=3
    m.options.MAX_ITER=20000
    m.options.IMODE = 2

    for i,xi in enumerate(x):
        if error.iloc[i, 0]==0:
            x[i].lower = tms_medicion[i]
            x[i].upper = tms_medicion[i]
            x[i].value = tms_medicion[i]
        else:
            x[i].value = tms_medicion[i]
            x[i].lower = 0
            x[i].upper = 5e9

    for k in range(n_components):
        for i,xi in enumerate(x_c):
            if error.iloc[i,k+1]==0:
                  x_c[i,k].lower = mediciones_leyes[k][i]
                  x_c[i,k].upper = mediciones_leyes[k][i]
                  x_c[i,k].value = mediciones_leyes[k][i]
            elif i in deltas:
                  x_c[i,k].lower = -100
                  x_c[i,k].upper = 100
                  x_c[i,k].value = mediciones_leyes[k][i]
            else:
                  x_c[i,k].value = mediciones_leyes[k][i]
                  x_c[i,k].lower = 0
                  x_c[i,k].upper = 1
    tol = 0
    for i in range(matriz.shape[0]):
            m.Equation(m.abs(balance_TMS[i])==tol)

    for k in range(n_components):
       for i in range(matriz.shape[0]):
            m.Equation(m.abs(balances[k][i])==tol)

    m.options.COLDSTART=2
    m.solve(disp=True,debug=0)

    m.options.COLDSTART=0
    m.solve(disp=True,debug=0)

    x_c_values = np.empty((x_c.shape[0],n_components))
    x_values = np.empty(x.shape[0])
    for i in range(x.shape[0]):
        x_values[i]=x[i].value[0]

    for k in range(n_components):
        for i in range(x_c.shape[0]):
            x_c_values[i,k]=x_c[i,k].value[0]

    M_finos = np.zeros((x_values.shape[0],n_components))
    for k in range(n_components):
        M_finos[:,k] = np.multiply(x_values,x_c_values[:,k])
    b_fino_Cu = np.dot(matriz,M_finos[:,0])
    b_masa = np.dot(matriz,x_values)

    def get_error(x,m):

        res =  np.zeros((x.shape[0],1))
        for i in range(x.shape[0]):
            if m[i]==0:
                res[i]=0
            elif m[i]==0 and x[i]>0:
                res[i]=100
            else:
                res[i]=(x[i]-m[i])/m[i]*100
        return res

    b_masa_ini = np.dot(matriz,mediciones[:,0])
    b_fino_ini_Cu = np.dot(matriz,mediciones[:,0]*mediciones[:,1])

    nombres_flujos = ['Alimentación Rajo a Chancado', 'Alimentación Chancado',
       'Alimentación Silo', 'Inventario Silo',
       'Alimentación Mineral a Nodo 4 Tambor 1',
       'Alimentación Mineral a Nodo 5 Tambor 2',
       'Alimentación SRR a aglomerado tambor 1',
       'Alimentación SRR a aglomerado tambor 2',
       'Alimentación SAL tambor 1', 'Alimentación SAL tambor 2',
       'Alimentación Aglomerado Tambor 1',
       'Alimentación Aglomerado Tambor 2',
       'Alimentación aglomerado Pad Sulfuros',
       'Alimentación aglomerado Pad Oxidos', 'Inventario pad sulfuros',
       'Inventario pad oxidos', 'Salida ripios pad sulfuros',
       'Salida ripios pad oxidos', 'Salida ripios a botaderos',
       'Ripios pad sulfuros reclamados por camiones',
       'Ripios pad oxidos reclamados por camiones',
       'Transferencia Cu PAD Óxidos', 'Transferencia Cu PAD Sulfuros',
       'Mineral SRR', 'Compensación de Masa PAD Óxidos',
       'Compensación de Masa PAD Sulfuros', 'Ácido Sulfúrico Aglomerado',
       'Ácido Sulfúrico Aglomerado',
       'Mineral alimentado De Pozo a PAD DUMP',
       'Mineral alimentado De Stock a PAD DUMP',
       'Descarte mineral lixiviado', 'Transferencia de Cobre',
       'Compensación de masa', 'Inventario Cu PAD DUMP Solución',
       'Inventario Cu PAD DUMP Mineral', 'PLS DUMP a piscina PLS DUMP',
       'PLS DUMP a piscina Refino DUMP', 'Refino Óxidos a PAD Óxidos',
       'Refino Óxidos a aglomerado', 'ILS Óxidos a PAD Óxidos',
       'Refino Óxidos a aglomerado', 'Refino Sulfuros a PAD Óxidos',
       'Refino Sulfuros a PAD Sulfuros', 'ILS Sulfuros a PAD Sulfuros',
       'PLS DUMP a PAD Óxidos', 'ILS PAD Óxidos a piscina ILS Óxidos',
       'PLS PAD Óxidos a piscina PLS Óxidos',
       'Bleed a piscina PLS Óxidos',
       'PLS PAD Sulfuros a piscina PLS sulfuros',
       'ILS PAD Sulfuros a piscina ILS Sulfuros',
       'Refino Óxidos a piscina Refino DUMP',
       'PLS DUMP a piscina PLS Óxidos',
       'Refino SX a piscina Refino Óxidos',
       'Refino SX a piscina Refino Sulfuros',
       'Inventario Cu PAD Sulfuros', 'Pérdidas por Humedad PAD Sulfuros',
       'Pérdidas por evaporación PAD Sulfuros',
       'Agua make up a piscina refino sulfuros',
       'Inventario Cu piscina Refino Sulfuros',
       'Pérdidas por evaporación piscina Refino Sulfuros',
       'Pérdidas por evaporación piscina ILS Sulfuros',
       'Inventario Cu piscina ILS Sulfuros',
       'Pérdidas por evaporación piscina PLS Sulfuros',
       'Inventario Cu Piscina PLS Sulfuros', 'Inventario Cu PAD Óxidos',
       'Pérdidas por humedad PAD Óxidos',
       'Pérdidas por evaporación PAD Óxidos', 'Inventario Cu PLS DUMP',
       'Inventario Cu Refino DUMP',
       'Pérdidas por evaporación piscina PLS DUMP',
       'Pérdidas por evaporación piscina Refino DUMP',
       'Inventario Cu Refino Óxido',
       'Pérdidas por evaporación piscina Refino Óxidos',
       'Pérdidas por evaporación piscina ILS Óxidos',
       'Inventario Cu ILS Óxidos',
       'Pérdidas por evaporación piscina PLS Óxidos',
       'Inventario Cu PLS Óxidos', 'PLS Óxido Tren A', 'PLS Óxido Tren B',
       'PLS Óxido Tren C', 'PLS Óxido Tren D', 'PLS Sulfuro Tren A',
       'PLS Sulfuro Tren B', 'PLS Sulfuro Tren C', 'PLS Sulfuro Tren D',
       'Pérdidass de Cobre SX', 'Ácido Sulfúrico Tren A',
       'Ácido Sulfúrico Tren B', 'Ácido Sulfúrico Tren C',
       'Ácido Sulfúrico Tren D', 'Agua make up Tren A',
       'Agua make up Tren B', 'Agua make up Tren C',
       'Agua make up Tren D', 'Electrolito Pobre Tren A',
       'Electrolito Pobre Tren B', 'Electrolito Pobre Tren C',
       'Electrolito Pobre Tren D', 'Electrolito Rico a EW',
       'Inventario orgánico cargado', 'Inventario Electrolito pobre',
       'Inventario Electrolito rico', 'Electrolito desechado',
       'Inventario Solución EW', 'Compensación de masa Cátodos  A EW',
       'Transferencia de Cobre EW a Cátodos', 'Inventrio Cobre colgado',
       'Cobre metálico EW a Patio Cátodos', 'Inventario Cátodos Spence',
       'Inventario Cátodos Off', 'Inventario B-Off',
       'Inventario Cátodos sin clasificar', 'Cátodos por camiones',
       'Cátodos por tren']
    nodos_names = ['Nodos','N1','Chancado','Silo','N3','N4','Aglomerado','Pad Sulfuros','Pad Oxidos','Nodo Ripios',
        'Lix (Pad Sulf)','Lix (Pad Ox)','Refino sulfuro','ILS Sulf','PLS Sulf','PLS Ox','ILS Ox','Refino ox','Refino DUMP',
        'PLS DUMP','PAD DUMP','PAD DUMP TRANSF','SX','EW','EW cobre matálico','Cátodos','SRR correas']

    resultados= pd.DataFrame(nombres_flujos,columns=["Flujo"])
    resultados["Masa medida"] =  np.multiply(mediciones[:,0],inventarios_masa)
    resultados["Masa recon"] =  np.multiply(x_values,inventarios_masa)
    resultados["Error masa"] =  get_error(x_values,mediciones[:,0])

    resultados["Ley medida Cu"] =  mediciones[:,1]*100
    resultados["Ley recon Cu" ] =  x_c_values[:,0]*100
    resultados["Error ley Cu"] =  get_error(x_c_values[:,0],mediciones[:,1])

    resultados["Fino medida Cu"] =  mediciones[:,1]*mediciones[:,0]
    resultados["Fino recon Cu" ] =  x_c_values[:,0]*x_values
    resultados["Error Fino Cu"] =  get_error(x_c_values[:,0]*x_values,mediciones[:,0]*mediciones[:,1])

  
    masa_df = pd.DataFrame(nodos_names)
    masa_df["Desbalance masa inicial"] = b_masa_ini
    masa_df["Desbalance masa"] = b_masa
    masa_df["Desbalance fino inicial Cu"] = b_fino_ini_Cu
    masa_df["Desbalance fino Cu"] = b_fino_Cu
    masa_ini = pd.DataFrame(nodos_names)

    return resultados, masa_df, masa_ini


