from datetime import datetime
from scipy.optimize import newton
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import os
import numpy as np

####ingresar los datos
#####
fecha_cotizacion = '20/09/24' #cierre
bonos = []
cotizacion = []


def leer_archivo(file = 'bonos.txt'):
    global DATA, HEADS
    DATA = np.genfromtxt('bonos.txt', delimiter='\t',
                         dtype=None, encoding=None, names=True)
    HEADS = np.genfromtxt('bonos.txt', delimiter='\t', max_rows=1, dtype=str)
    return True

def leer_datos_USD(ticker, fecha = fecha_cotizacion):
    indice = np.where(DATA['Fecha']==fecha)[0]
    return DATA[ticker][indice][0]
    
def lista_ticker(ticker = 'all'):
    if ticker == 'all':
        encabezados = list(HEADS[1:])
        return encabezados
    elif any(ticker == HEADS):
        return ticker
    else:
        print("Opcion no válida, se usa por defecto AL30")
        return 'AL30'

def lista_bonos_y_cotizacion(bonardos, fecha = fecha_cotizacion):
    if type(bonardos) == list or type(bonardos) == tuple:
        n = len(bonardos)
        bono = []
        cotizacion = []
        for i in range(n):
            bono.append(bonardos[i].upper())
            cotizacion.append(leer_datos_USD(fecha, bono[i]))
        return bono,cotizacion
    elif type(bonardos) == str:
        bono = bonardos.upper()
        return leer_datos_USD(fecha, bono)

def calcular_fecha_supera_bono(fechas_pagos, flujos, valor_bono):
    flujos_acumulados = 0
    for fecha_pago, flujo in zip(fechas_pagos, flujos):
        flujos_acumulados += flujo
        if flujos_acumulados >= valor_bono:
            return (fecha_pago, flujos_acumulados)
    return ("No supera dentro del período", 0)

# Definir fechas de pago y flujos según el ticker

def obtener_fechas_y_flujos(ticker='AL30', filename='cashflow_bonos.txt'):
    ticker = ticker.upper()
    # Leer el archivo como un array de texto
    data = np.genfromtxt(filename, delimiter=',', dtype=str, encoding='utf-8', skip_header=1)
    
    # Inicializar un diccionario para almacenar la información
    informacion = {}
    
    for row in data:
        # Asumiendo que row[0] es el ticker
        fila_ticker = row[0].strip()
        fechas_pagos = row[1].strip().split(';')
        flujos = list(map(float, row[2].strip().split(';')))
        amortizacion = list(map(float, row[3].strip().split(';')))
        
        # Almacenar la información en el diccionario
        informacion[fila_ticker] = {
            'fechas_pagos': fechas_pagos,
            'flujos': flujos,
            'amortizacion': amortizacion
        }
    
    # Verificar si el ticker está en la información
    if ticker in informacion:
        datos = informacion[ticker]
        return datos['fechas_pagos'], datos['flujos']
    else:
        raise ValueError(f"Ticker {ticker} no encontrado en el archivo.")


def calcular_periodos(fecha_cotizacion, fechas_pagos):
    fecha_cotizacion = datetime.strptime(fecha_cotizacion, '%d/%m/%y')
    periodos = []
    for fecha_pago in fechas_pagos:
        fecha_pago = datetime.strptime(fecha_pago, '%d/%m/%y')
        periodo = (fecha_pago - fecha_cotizacion).days / 365.25
        periodos.append(periodo)
    return periodos

#colores de los puntos
def color_bonos(ticker):
    if ticker[0] == 'A':
        color_punto = 'red'
        lado = 'left'
    elif ticker[0] == 'G':
        color_punto  = 'black'
        lado = 'right'
    elif ticker[0] == 'B':
        color_punto  = 'blue'
        if ticker == 'BPD7D':
            lado = 'right'
        else:
            lado = 'left'
    return color_punto, lado

# Función para calcular el valor presente de los flujos de caja
def valor_presente(flujos, tir):
    return sum(flujo / (1 + tir) ** periodo for flujo, periodo in flujos)

# Función para calcular la TIR
def calcular_tir(valor_bono, flujos):
    def funcion_a_minimizar(tir):
        return valor_presente(flujos, tir) - valor_bono
    # Estimación inicial de la TIR
    tir_decimal = newton(funcion_a_minimizar, 0.05)
    return tir_decimal  # Ya en decimal
    
def calcular_tir_y_maduracion(ticker, valor_bono, fecha_cotizacion):
    # Definir fechas de pago y flujos según el ticker
    fechas_pagos,flujos = obtener_fechas_y_flujos(ticker)

    # Calcular los períodos en años desde la fecha de cotización
    periodos = calcular_periodos(fecha_cotizacion, fechas_pagos)

    # Recalcular flujos con los períodos correctos
    flujos_recalculados = [(flujo, periodo) for flujo, periodo in zip(flujos, periodos)]

    # Calcular la TIR
    tir = calcular_tir(valor_bono, flujos_recalculados)

    # Determinar la maduración
    fecha_vencimiento = datetime.strptime(fechas_pagos[-1], '%d/%m/%y')
    fecha_cotizacion_dt = datetime.strptime(fecha_cotizacion, '%d/%m/%y')
    maduracion = (fecha_vencimiento - fecha_cotizacion_dt).days / 365.25

    # Calcular la fecha en la que el flujo de caja supera el valor del bono
    fecha_supera_bono, flujo_acumulado = calcular_fecha_supera_bono(fechas_pagos, flujos, valor_bono)

    return (tir * 100, maduracion, fecha_supera_bono, flujo_acumulado)

def graficar_curva_rendimiento_y_punto(ticker, rango_precio, precio_actual, residual, fecha_cotizacion, label):
    precios = np.arange(rango_precio[0], rango_precio[1], 1.)
    n = len(precios)
    tir = []
    paridades = []

    for i in range(n):
        tir_bono = calcular_tir_y_maduracion(ticker, precios[i], fecha_cotizacion)[0]
        tir.append(tir_bono)
        paridades.append((precios[i] / residual) * 100)  # Calcular paridad

    plt.plot(paridades, np.array(tir, float), label=label)
    
    # Calcular y graficar el punto específico de la TIR para la paridad actual
    tir_actual = calcular_tir_y_maduracion(ticker, precio_actual, fecha_cotizacion)[0]
    paridad_actual = (precio_actual / residual) * 100
    color_punto, lado = color_bonos(ticker)
    plt.scatter( paridad_actual, tir_actual, color=color_punto, zorder=5)  
    plt.text( paridad_actual, tir_actual, f'{ticker}', fontsize=9, ha=lado)

def graficar_punto(ticker, precio_actual, residual, fecha_cotizacion, label):
    
    # Calcular y graficar el punto específico de la TIR para la paridad actual
    tir_actual = calcular_tir_y_maduracion(ticker, precio_actual, fecha_cotizacion)[0]
    paridad_actual = (precio_actual / residual) * 100
    color_punto, lado = color_bonos(ticker)
    plt.scatter( paridad_actual, tir_actual, color=color_punto, zorder=5)
    plt.text( paridad_actual, tir_actual, f'{ticker}', fontsize=9, ha=lado)

def calcular_duracion_modificada(flujos, periodos, tir, n_periodos):

    # Cálculo de la duración de Macaulay
    duracion_macaulay = sum(periodo * (flujo / (1 + tir) ** periodo) for flujo, periodo in zip(flujos, periodos))
    valor_presente_total = sum(flujo / (1 + tir) ** periodo for flujo, periodo in zip(flujos, periodos))
    duracion_macaulay /= valor_presente_total
    
    # Duración modificada
    duracion_modificada = duracion_macaulay / (1 + tir / n_periodos)
    
    return duracion_modificada

def graficar_paridad_vs_duracion_modificada(tickers, precios, residuales, fecha_cotizacion, n_periodos=2):

    duraciones_modificadas = []
    paridades = []

    for ticker, precio, residual in zip(tickers, precios, residuales):
        tir, maduracion, _, _ = calcular_tir_y_maduracion(ticker, precio, fecha_cotizacion)
        fechas_pagos, flujos = obtener_fechas_y_flujos(ticker)
        periodos = calcular_periodos(fecha_cotizacion, fechas_pagos)
        duracion_modificada = calcular_duracion_modificada(flujos, periodos, tir/100, n_periodos)
        
        duraciones_modificadas.append(duracion_modificada)
        paridades.append((precio / residual) * 100)  # Calcular paridad

    # Graficar
    plt.figure(figsize=(10, 6))
    for i, ticker in enumerate(tickers):
        color_punto, lado = color_bonos(ticker)
        plt.scatter(duraciones_modificadas[i], paridades[i], color= color_punto )
        plt.text(duraciones_modificadas[i], paridades[i], f'{ticker}', fontsize=9, ha=lado)

    plt.title('Paridad vs Maduración Modificada')
    plt.xlabel('Maduración Modificada')
    plt.ylabel('Paridad (%)')
    plt.grid(True)
    plt.show()

def graficar_maduracion_vs_tir(tickers, precios, residuales, fecha_cotizacion, n_periodos=2):
    duraciones_modificadas = []
    tir_values = []

    for ticker, precio, residual in zip(tickers, precios, residuales):
        tir, maduracion, _, _ = calcular_tir_y_maduracion(ticker, precio, fecha_cotizacion)
        fechas_pagos, flujos = obtener_fechas_y_flujos(ticker)
        periodos = calcular_periodos(fecha_cotizacion, fechas_pagos)
        duracion_modificada = calcular_duracion_modificada(flujos, periodos, tir/100, n_periodos)
        
        duraciones_modificadas.append(duracion_modificada)
        tir_values.append(tir)

    plt.figure(figsize=(10, 6))
    for i, ticker in enumerate(tickers):
        color_punto, lado = color_bonos(ticker)
        plt.scatter(duraciones_modificadas[i], tir_values[i], color=color_punto)
        plt.text(duraciones_modificadas[i], tir_values[i], f'{ticker}', fontsize=9, ha=lado)

    plt.title('Maduración Modificada vs TIR')
    plt.xlabel('Maduración Modificada')
    plt.ylabel('TIR (%)')
    plt.grid(True)
    plt.show()
    


def residual_bonos(ticker):
    n = len(ticker)
    valor_par = []
    intereses_acumulados = []
    residual = []
    for i in range(n):
        if ticker[i] == 'BPY26':
            valor_par = 100.0083
            intereses_acumulados = 0.0083
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'BPJ5D':
            valor_par = 83.34
            intereses_acumulados = 0.0
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'BPA7D':
            valor_par = 103.2778
            intereses_acumulados = 0.2778
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'BPB7D':
            valor_par = 103.2778
            intereses_acumulados = 0.2778
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'BPC7D':
            valor_par = 103.2778
            intereses_acumulados = 0.2778
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'BPD7D':
            valor_par = 103.2778
            intereses_acumulados = 0.2778
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'AL29':
            valor_par = 100.1417
            intereses_acumulados = 0.1417
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'AL30':
            valor_par = 96.102
            intereses_acumulados = 0.102
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'AL35':
            valor_par = 100.5844
            intereses_acumulados = 0.5844
            residual.append( valor_par - intereses_acumulados)
        elif ticker[i] == 'AE38':
            valor_par = 100.7083
            intereses_acumulados = 0.7083
            residual.append( valor_par - intereses_acumulados)
        elif ticker[i] == 'AL41':
            valor_par = 100.4958
            intereses_acumulados = 0.4958
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD29':
            valor_par = 100.1417
            intereses_acumulados = 0.1417
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD30':
            valor_par = 96.102
            intereses_acumulados = 0.102
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD35':
            valor_par = 100.5844
            intereses_acumulados = 0.5844
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD38':
            valor_par = 100.7083
            intereses_acumulados = 0.7083
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD41':
            valor_par = 100.4958
            intereses_acumulados = 0.4958
            residual.append(valor_par - intereses_acumulados)
        elif ticker[i] == 'GD46':
            valor_par = 100.5844
            intereses_acumulados = 0.5844
            residual.append(valor_par - intereses_acumulados)
    return residual

#Hacer los rangos
def rango_bonos(ticker):
    n = len(ticker)
    rango = []
    for i in range(n):
        if ticker[i][0] == 'B':
            if ticker[i] == 'BPJ5D':
                rango.append([70.,84.])
            rango.append([65., 100.])
        elif ticker[i][0] == 'A' or ticker[i][0] == 'G':
            if ticker[i][2:] =='30':
                rango.append([36., 96.])
            else:
                rango.append([40., 100.])
    return rango


# Graficar cada bono con el punto específico
def graficar_bonos_en_rango(ticker,residual,cotizacion,rango,fecha):
    n = len(ticker)
    for i in range(n):
        if ticker[i][0] == 'B':
            graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
            if ticker[i] == 'BPJ5D':
                graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i][0] == 'A':
            graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i] == 'GD46':
            graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i][0] == 'G' and not(ticker[i] == 'GD46'):
            graficar_punto(ticker[i], cotizacion[i], residual[i], fecha_cotizacion, ticker[i])

    # Configuración de la gráfica
    plt.title(fecha_cotizacion)
    plt.ylabel("TIR [%]")
    plt.xlabel("Paridad [USD]")
    plt.legend()
    plt.grid()
    plt.show()
    return True

##inicio
####ingresar los datos
#####


def graficar_bonos_en_rango_save(ticker, residual, cotizacion, rango, fecha, nombre_imagen):
    n = len(ticker)
    
    # Aumentar el tamaño de la figura
    plt.figure(figsize=(15, 9))  # Tamaño de la figura en pulgadas
    
    for i in range(n):
        if ticker[i][0] == 'B':
            if ticker[i] == 'BPJ5D':
                graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
            else:
                graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i][0] == 'A':
            graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i] == 'GD46':
            graficar_curva_rendimiento_y_punto(ticker[i], rango[i], cotizacion[i], residual[i], fecha, ticker[i])
        elif ticker[i][0] == 'G' and ticker[i] != 'GD46':
            graficar_punto(ticker[i], cotizacion[i], residual[i], fecha, ticker[i])

    # Configuración de la gráfica
    plt.title(fecha)
    plt.ylabel("TIR [%]")
    plt.xlabel("Paridad [USD]")
    plt.legend()
    plt.grid()

    # Guardar la gráfica en un archivo de imagen con mayor resolución (aumentando DPI)
    plt.savefig(nombre_imagen, dpi=300)  # Aumentar el DPI para mejorar la calidad
    plt.close()

def crear_gif_de_bonos(velocidad_gif = 1.0):
    # Leer las fechas y los datos
    FECHA = list(DATA['Fecha'])[-2::-1]
    bonos = ['AL29', 'GD29', 'AL30', 'GD30', 'AL35', 'GD35', 'AE38', 'GD38', 'AL41', 'GD41', 'GD46', 'BPJ5D', 'BPY26', 'BPC7D', 'BPD7D']
    residual = residual_bonos(bonos)
    rango = rango_bonos(bonos)

    # Lista para almacenar los nombres de los archivos de imagen
    imagenes = []

    # Crear gráficas para cada fecha y guardarlas como imágenes
    for i, fecha in enumerate(FECHA):
        nombre_imagen = f"grafico_bonos_{i}.png"
        cotizacion = list(leer_datos_USD(bonos, fecha))
        graficar_bonos_en_rango_save(bonos, residual, cotizacion, rango, fecha, nombre_imagen)
        imagenes.append(nombre_imagen)

    # Crear el GIF a partir de las imágenes
    with imageio.get_writer('bonos_animacion.gif', mode='I', duration= velocidad_gif) as writer:
        for imagen in imagenes:
            frame = imageio.imread(imagen)
            writer.append_data(frame)

    # Eliminar los archivos de imagen temporal
    for imagen in imagenes:
        os.remove(imagen)

    print("GIF creado exitosamente: bonos_animacion.gif")

# Ejecutar la función para crear el GIF
leer_archivo()
crear_gif_de_bonos(0.25)




'''
# Llamar a la función para graficar
graficar_paridad_vs_duracion_modificada(tickers, precios, residuales, fecha_cotizacion)

graficar_maduracion_vs_tir(tickers, precios, residuales, fecha_cotizacion)

'''




