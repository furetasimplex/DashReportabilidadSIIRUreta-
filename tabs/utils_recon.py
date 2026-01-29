from scipy import sparse
import numpy as np
from gekko import GEKKO
import pandas as pd
from openpyxl import load_workbook


def balance_core(mediciones,error,fn="Normal",u=1,cf=1,cw=1,expk=1,cp=1):

    #mediciones[:,1] = mediciones[:,1]/100
    deltas = [5,16,17]
    deltas = [i-1 for i in deltas]
    deltas = np.array(deltas)

    matriz = np.array([[ 1.,   2.,  -3.,   0.,   0.],
           [  3.,  -4,   0.,    0.,   0.],
           [  4.,  -5,  -6.,   -7.,   0.],
           [  6.,  8.,  10.,   -12.,  0.],
           [  7.,  9.,  11.,  -13.,   0.],
           [ 12.,  13., -14., -15.,   0.],
           [ 14., -16., -18., -21., -24.],
           [ 15., -17., -19., -22., -23.],
           [ 18.,  19., 0.,   -20., 0.],
	         [ 25., -8., -9.,    0. , 0.]])

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

    #u = m.Var(value=u)
    #u.lower = 0.01
    #u.upper = 1

    def cauchy(r):
        return u**2*m.log(1+r**2/u**2)
    def normal(r):
        return r**2
    def nueva(r):
      a=0.65
      c=3.0
      A = c**2*a*(1-a)**2/2
      B = c*2*(1-(1-a**3))/6
      res = m.if3(c-m.abs(r),c**2*(1-(1-a*r**2/c**2)**3)/6,A*m.log(1+r**2/c**2)+B)
      return res

    def fair(r):
      res = 2*cf**2*(m.abs(r)/cf-m.log(1+m.abs(r)/cf))
      return res
    def expo(r):
      res = 1-m.exp(-(m.abs(r)/cp)**expk)
      return res
    def Welsch(r):
      res = cw**2*(1-m.exp(-(r/cw)**2))/2
      return res
    if fn =="Cauchy":
      fun_ob = cauchy
    elif fn =="Normal":
      fun_ob = normal
    elif fn =="Fair":
      fun_ob = fair
    elif fn =="Welsch":
      fun_ob = Welsch
    elif fn =="Nueva":
      fun_ob = nueva
    elif fn =="exp":
      fun_ob = expo

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
        ob[i] =  fun_ob(r)
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
            ob_finos[i,k] =fun_ob(r)
        ob_finos= m.sum(ob_finos)
    obj_finos_sum = m.sum(ob_finos)

    m.Obj(ob+obj_finos_sum)
    m.options.SOLVER=3
    m.options.MAX_ITER=2000
    m.options.IMODE = 2

    for i,xi in enumerate(x):
        if error.iloc[i, 0]==0:
            x[i].lower = tms_medicion[i]
            x[i].upper = tms_medicion[i]
            x[i].value = tms_medicion[i]
        elif tms_medicion[i]==0:
            x[i].lower = 0
            x[i].upper = 0
            x[i].value = 0
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
            elif mediciones_leyes[k][i]==0:
                  x_c[i,k].lower = 0
                  x_c[i,k].upper = 0
                  x_c[i,k].value = 0
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
    m.solve(disp=False,debug=0)

    m.options.COLDSTART=0
    m.solve(disp=False,debug=0)

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

    nombres_flujos = ['Flujo 01','Flujo 02', 'Flujo 03', 'Flujo 04', 'Flujo 05', 'Flujo 06',
           'Flujo 07', 'Flujo 08', 'Flujo 09', 'Flujo 10', 'Flujo 11',
           'Flujo 12', 'Flujo 13', 'Flujo 14', 'Flujo 15', 'Flujo 16',
           'Flujo 17', 'Flujo 18', 'Flujo 19', 'Flujo 20', 'Flujo 21', 'Flujo 22', 'Flujo 23', 'Flujo 24', 'Flujo 25']
    nodos_names = ["N1",'Chancado', 'Silo', "N4","N5",'Aglomerado',
           'Apilado Sulfuro', 'Apilado Óxido', 'N9',"N10"]#,"Mina-Aglomerado"]

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

    #b_masa_ini[1] = b_masa_ini[1]/x_values[2]*100
    #b_masa_ini[2] = b_masa_ini[2]/x_values[3]*100
    ##b_masa_ini[10] = b_masa_ini[10]/x_values[2]*100
    #b_fino_ini_Cu[10] = b_fino_ini_Cu[10]/(x_values[2]*x_c_values[2,0])*100
    masa_df = pd.DataFrame(nodos_names)
    masa_df["Desbalance masa inicial"] = b_masa_ini
    masa_df["Desbalance masa"] = b_masa
    masa_df["Desbalance fino inicial Cu"] = b_fino_ini_Cu
    masa_df["Desbalance fino Cu"] = b_fino_Cu
    masa_ini = pd.DataFrame(nodos_names)
    print("MASA DF 67")
    print(masa_df)
    return resultados, masa_df, masa_ini


def desbalances(mediciones,error,fn="Normal",u=1,cf=1,cw=1,expk=1,cp=1):

    #mediciones[:,1] = mediciones[:,1]/100
    deltas = [5,16,17]
    deltas = [i-1 for i in deltas]
    deltas = np.array(deltas)

    matriz = np.array([[ 1.,   2.,  -3.,   0.,   0.],
           [  3.,  -4,   0.,    0.,   0.],
           [  4.,  -5,  -6.,   -7.,   0.],
           [  6.,  8.,  10.,   -12.,  0.],
           [  7.,  9.,  11.,  -13.,   0.],
           [ 12.,  13., -14., -15.,   0.],
           [ 14., -16., -18., -21., -24.],
           [ 15., -17., -19., -22., -23.],
           [ 18.,  19., 0.,   -20., 0.],
	         [ 25., -8., -9.,    0. , 0.]])

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


    b_masa_ini = np.dot(matriz,mediciones[:,0])
    b_fino_ini_Cu = np.dot(matriz,mediciones[:,0]*mediciones[:,1])

    nombres_flujos = ['Flujo 01','Flujo 02', 'Flujo 03', 'Flujo 04', 'Flujo 05', 'Flujo 06',
           'Flujo 07', 'Flujo 08', 'Flujo 09', 'Flujo 10', 'Flujo 11',
           'Flujo 12', 'Flujo 13', 'Flujo 14', 'Flujo 15', 'Flujo 16',
           'Flujo 17', 'Flujo 18', 'Flujo 19', 'Flujo 20', 'Flujo 21', 'Flujo 22', 'Flujo 23', 'Flujo 24', 'Flujo 25']
    nodos_names = ["N1",'Chancado', 'Silo', "N4","N5",'Aglomerado',
           'Apilado Sulfuro', 'Apilado Óxido', 'N9',"N10"]#,"Mina-Aglomerado"]

    resultados= pd.DataFrame(nombres_flujos,columns=["Flujo"])
    resultados["Masa medida"] =  np.multiply(mediciones[:,0],inventarios_masa)
    resultados["Masa recon"] =  0
    resultados["Error masa"] =  0

    resultados["Ley medida Cu"] =  mediciones[:,1]*100
    resultados["Ley recon Cu" ] =  0
    resultados["Error ley Cu"] =  0

    resultados["Fino medida Cu"] =  mediciones[:,1]*mediciones[:,0]
    resultados["Fino recon Cu" ] =  0
    resultados["Error Fino Cu"] =  0

    #b_masa_ini[1] = b_masa_ini[1]/x_values[2]*100
    #b_masa_ini[2] = b_masa_ini[2]/x_values[3]*100
    ##b_masa_ini[10] = b_masa_ini[10]/x_values[2]*100
    #b_fino_ini_Cu[10] = b_fino_ini_Cu[10]/(x_values[2]*x_c_values[2,0])*100
    masa_df = pd.DataFrame(nodos_names)
    masa_df["Desbalance masa inicial"] = b_masa_ini
    masa_df["Desbalance masa"] = 0
    masa_df["Desbalance fino inicial Cu"] = b_fino_ini_Cu
    masa_df["Desbalance fino Cu"] = 0
    masa_ini = pd.DataFrame(nodos_names)

    return resultados, masa_df, masa_ini


