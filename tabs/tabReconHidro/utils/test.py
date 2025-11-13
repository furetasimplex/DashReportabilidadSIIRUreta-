import numpy as np
from scipy import sparse
import pandas as pd

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



# Define el nombre de tu archivo y la columna que quieres leer
nombre_archivo_excel = "Datos imput\Datos-input julio 2025.xlsx"
nombre_de_la_columna = "Cu"  # <-- Cambia esto

try:
    # 1. Cargar el archivo Excel en un DataFrame de Pandas
    # Por defecto, lee la primera hoja del archivo
    df = pd.read_excel(nombre_archivo_excel)

    # 2. Seleccionar la columna específica por su nombre
    # Esto crea un objeto de tipo 'Series' de Pandas
    columna_series = df[nombre_de_la_columna]

    # 3. Convertir la columna (Series) a una lista de Python
    # Este es el "array" que estás buscando
    mi_array = columna_series.tolist()

    # 4. Imprimir el resultado
    print(f"Columna '{nombre_de_la_columna}' leída como array:")
    print(mi_array)

except FileNotFoundError:
    print(f"Error: No se encontró el archivo en la ruta: {nombre_archivo_excel}")
except KeyError:
    print(f"Error: La columna '{nombre_de_la_columna}' no se encontró en el archivo.")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")

try:
    # 1. Cargar el archivo Excel en un DataFrame de Pandas
    # Por defecto, lee la primera hoja del archivo
    df = pd.read_excel(nombre_archivo_excel)

    # 2. Seleccionar la columna específica por su nombre
    # Esto crea un objeto de tipo 'Series' de Pandas
    columna_series = df[nombre_de_la_columna]

    # 3. Convertir la columna (Series) a una lista de Python
    # Este es el "array" que estás buscando
    mi_array2 = columna_series.tolist()

    # 4. Imprimir el resultado
    print(f"Columna '{nombre_de_la_columna}' leída como array:")
    print(mi_array2)

except FileNotFoundError:
    print(f"Error: No se encontró el archivo en la ruta: {nombre_archivo_excel}")
except KeyError:
    print(f"Error: La columna '{nombre_de_la_columna}' no se encontró en el archivo.")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")


columna_1 = mi_array
columna_2 = mi_array2
columna_1 = np.array(columna_1)
columna_2 = np.array(columna_2)

print(matriz@np.multiply(columna_1,columna_2))
