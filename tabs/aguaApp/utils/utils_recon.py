import os

import pandas as pd

import numpy as np

import string

from gekko import GEKKO

from openpyxl import load_workbook

from scipy import sparse



def balance_core_hidro(mediciones, error):

    """

    Función reconciliación

    ...


    Argumentos

    ----------

    mediciones: array

        array de mediciones shape (n,m), n = número de flujos, m = número de elementos + 1

    error: array

        array de tolerancias shape (n,m), n = número de flujos, m = número de elementos + 1


    Salidas

    -------

    resultados : DataFrame pandas

        dataframe de mediciones reconciliadas shape (n,m), n = número de flujos, m = número de elementos + 1

    masa_ini: DataFrame pandas

        dataframe de desbalances datos iniciales shape (j,k), j = número de nodos, k = número de elementos + 1

    masa_df: DataFrame pandas

        dataframe de desbalances datos reconciliados shape (j,k), j = número de nodos, k = número de elementos + 1

    """
    matriz = np.array([[ 5., -65.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [  4., -64.,  -8.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [  3.,  -4.,  -5.,  -6.,  -7.,   0.,   0.,   0.,   0.,   0.],
                [  1.,   2.,  -9., -10., -59.,   0.,   0.,   0.,   0.,   0.],
                [  8.,   9., -62., -63.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 10., -11., -12.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 11., -61.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 12., -13., -14.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [  7.,  39., -40., -60., -66.,   0.,   0.,   0.,   0.,   0.],
                [ 14., -15., -16.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 16.,  35., -38., -57., -50.,   0.,   0.,   0.,   0.,   0.],
                [ 32.,  33.,  40.,  15.,   6., -34., -35., -67., -39.,   0.],
                [ 27., -33., -56.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 22.,  28., -32., -55.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 26.,  29., -30., -54.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 20.,  21., -23., -53.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 30.,  38.,  25., -26., -27., -28., -31., -52., -29., -44.],
                [ 23.,  37.,  19., -20., -21., -22., -24., -51., -43.,   0.],
                [ 24.,  31., -41.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 18., -19., -25.,   0.,   0.,   0.,   0.,   0.,   0.,   0.],
                [ 34., -37., -36., -49.,  -58.,   0.,   0.,   0.,   0.,   0.],
                [ 13.,  17.,  36., -68., -18.,   0.,   0.,   0.,   0.,   0.]])

    deltas = [51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60]
    deltas = np.array(deltas)-1


    nodos_names = column_headers = [
        "SGO - Potable", "Campamento", "FCAB", "Reservorio", "Mina", "Partición SGO",
        "SGO - Industrial", "Particion Lix", "EW", "Partición refino Súlfuro",
        "Refino Sulfuro", "SX", "Piscina PLS Súlfuros", "Piscina PLS Óxidos",
        "Piscina ILS Súlfuros", "Piscina ILS Óxidos", "Pila sulfuros", "Pila óxidos",
        "Botadero", "Partición aglomerado","Piscina Refino Oxido","Aglomerado"
        ]

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

    inventarios = 2*(mediciones >= 0)-1
    mediciones = np.abs(mediciones)
    m = GEKKO(remote=False)
    x = m.Array(m.Var,(matriz.shape[1]))
    tms_medicion = mediciones
    balance_TMS = np.dot(matriz,x)
    ob = m.Array(m.Var, mediciones.shape[0])

    for i in range(mediciones.shape[0]):
            if tms_medicion[i]==0:
                divisor = 1
            else:
                if error.iloc[i, 0] == 0:

                  divisor = 1
                else:
                     divisor = tms_medicion[i]*error.iloc[i, 0]

            ob[i] = np.abs((x[i]-tms_medicion[i])/divisor)**2
    ob = m.sum(ob)

    m.Obj(ob)
    m.options.SOLVER=3
    m.options.MAX_ITER=2000
    m.options.IMODE = 2

    for i,xi in enumerate(x):

            if i in deltas:
                if error.iloc[i, 0]==0:
                  x[i].lower = tms_medicion[i]
                  x[i].upper = tms_medicion[i]
                  x[i].value = tms_medicion[i]
                elif inventarios[i]>0:
                  x[i].lower = 0
                  x[i].upper = 1e6
                  x[i].value = tms_medicion[i]
                else:
                  x[i].lower = -1e6
                  x[i].upper = 0
                  x[i].value = tms_medicion[i]
            else:
              if error.iloc[i, 0]==0:
                  x[i].lower = tms_medicion[i]
                  x[i].upper = tms_medicion[i]
                  x[i].value = tms_medicion[i]
              else:
                  x[i].value = tms_medicion[i]
                  x[i].lower = 0
                  x[i].upper = 1e6


    tol = 0
    for i in range(matriz.shape[0]):

            m.Equation(m.abs(balance_TMS[i])==tol)


    m.options.COLDSTART=2
    m.solve(disp=False,debug=0)

    m.options.COLDSTART=0
    m.solve(disp=True,debug=0)

    x_values = np.empty(x.shape[0])

    for i in range(x.shape[0]):

            x_values[i]=x[i].value[0]

    b_masa = np.dot(matriz,x_values)
    x_values = np.multiply(x_values,inventarios)
    b_masa_ini = np.dot(matriz,mediciones*inventarios)
    print(x_values)
 
    nombres_flujos = [
        "Ingreso Agua ADASA a Reservorio",
        "Ingreso Agua IAS a Reservorio",
        "Ingreso Agua FCAB a TK 128",
        "Salida  Agua TK 128 a Campamento",
        "Salida  Agua TK 128 a SGO potable",
        "Salida  Agua TK 128 a SX",
        "Salida  Agua TK 128 a EW",
        "Salida  Agua de Campamento a Mina",
        "Salida Agua Reservorio a Mina",
        "Salida Agua Reservorio a Particion SGO",
        "Salida Particion SGO a SGO Industrial",
        "Salida Particion SGO a Particion Lix",
        "Salida Particion Lix a Aglomerado",
        "Salida Particion Lix a Particion de Sulfuro",
        "Salida Particion de Sulfuro a SX",
        "Salida Particion de Sulfuro a Refino Sulfuro",
        "Entrada Agua Humedad mineral a Aglomerado",
        "Salida de Agua de Aglomerado a Particion Aglomerado",
        "Salida de Agua de Particion Aglomerado a Pila Oxido",
        "Salida de Agua de Pila Oxido a ILS Oxido",
        "Salida agua Drenaje Pila Oxido aa ILS Oxido",
        "Salida de Agua de Pila Oxido a PLS Oxido",
        "Salida de Agua desde ILS Oxido a Pila Oxido",
        "Salida Agua desde Pila Oxido a Botadero",
        "Salida de Agua de Particion Aglomerado a Pila Sulfuro",
        "Salida de Agua de Pila de Sulfuro a ILS Sulfuro",
        "Salida de Agua de Pila de Sulfuro a PLS Sulfuro",
        "Salida de Agua de Pila de Sulfuro a PLS Oxido (Bleed)",
        "Salida agua Drenaje Pila Sulfuro a ILS Sulfuro",
        "Salida de Agua de ILS Sulfuro a Pila Sulfuro",
        "Salida de Agua de pila Sulfuro a Botadero",
        "Salida de Agua de PLS Oxido a SX",
        "Salida de Agua de PLS Sulfuro  a SX",
        "Salida de Agua de SX a Refino Oxido",
        "Salida de Agua de SX a Refino Sulfuro",
        "Salida Agua Refino Oxido a Aglomerado",
        "Salida Agua desde Refino Oxido a Pila Oxido",
        "Salida de Agua  de Refino Sulfuro a Pila Sulfuro",
        "Salida de Agua de SX a EW",
        "Salida de Agua de EW a SX",
        "Salida desde botadero",
        "Evaporacion Reservorio",
        "Evaporacion Pila Oxido",
        "Evaporacion Pila Sulfuro",
        "Evaporacion Piscina ILS Oxido",
        "Evaporacion Piscina PLS Oxido",
        "Evaporacion Piscina PLS Sulfuro",
        "Evaporacion Piscina ILS Sulfuro",
        "Evaporacion Piscina Refino Oxido",
        "Evaporacion Piscina Refino Sulfuro",
        "Delta  Stock Agua Pilas Óxidos",
        "Delta Stock Agua Pilas Sulfuros",
        "Delta  Stock Agua Piscina ILS Óxidos",
        "Delta Stock Agua Piscina ILS Sulfuros",
        "Delta Stock Agua Piscina PLS Óxidos",
        "Delta Stock Agua Piscina PLS Sulfuros",
        "Delta Stock Agua Refino Sulfuro",
        "Delta Stock Agua Refino Oxido",
        "Delta Stock Agua Reservorio",
        "Delta Stock Agua EW",
        "Consumo Agua Reservorio  SGO Industrial",
        "Consumo Agua Potable Mina 1",
        "Consumo Agua PotableMina 2",
        "Consumo Agua Potable SGO Campamento",
        "Consumo Agua Potable SGO Potable",
        "Consumo Agua Potable EW",
        "Consumos de Agua en SX",
        "Area Seca "
        ]


    resultados= pd.DataFrame(nombres_flujos,columns=["Flujo"])
    resultados["Masa recon"] =  x_values
    masa_df = pd.DataFrame(nodos_names)
    masa_ini = pd.DataFrame(nodos_names)
    masa_ini["Desbalance masa"] = b_masa_ini
    masa_df["Desbalance masa"] = b_masa
    return resultados, masa_df,masa_ini
