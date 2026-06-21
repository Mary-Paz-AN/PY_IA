"""
Tools para el funcionamiento del agente

Requiere:
pip install joblib pandas numpy shap lightgbm scikit-learn
"""

import joblib
import pandas as pd
import numpy as np
import shap
import os

# Carga de recursos (se ejecuta una sola vez al importar el módulo)
RUTA_MODELO  = os.path.join(os.path.dirname(__file__), '..', 'modelo', 'lgbm_tuning_v2.pkl')
RUTA_DATASET = os.path.join(os.path.dirname(__file__), '..', 'Dataset', 'vehicles.csv')

print("Cargando modelo y dataset...")

# Cargar el pipeline completo
modelo_pipeline = joblib.load(RUTA_MODELO)

# Cargar el dataset original para búsquedas
df_vehiculos = pd.read_csv(RUTA_DATASET)

# Mismos filtros de calidad usados anteriormente
df_vehiculos = df_vehiculos[
    (df_vehiculos['price'] >= 500) & (df_vehiculos['price'] <= 100_000) &
    (df_vehiculos['odometer'] >= 100) & (df_vehiculos['odometer'] <= 500_000) &
    (df_vehiculos['year'] >= 1990) & (df_vehiculos['year'] <= 2022)
].copy()

# Preparar el explainer de SHAP (solo 1 vez)
preprocesador_global = modelo_pipeline.named_steps['preprocessor']
modelo_lgbm_global    = modelo_pipeline.named_steps['regressor']
explainer_global      = shap.TreeExplainer(modelo_lgbm_global)
feature_names_global  = preprocesador_global.get_feature_names_out()

print(f"Modelo cargado. Dataset con {len(df_vehiculos):,} registros disponibles.")


# Filtro de precios incosistentes
print("Evaluando consistencia de precios en todo el dataset (puede tardar unos segundos)...")

predicciones_todas = modelo_pipeline.predict(
    df_vehiculos.drop(columns=['price'], errors='ignore')
)

error_relativo_todas = np.abs(
    df_vehiculos['price'].values - predicciones_todas
) / df_vehiculos['price'].values

UMBRAL_INCONSISTENCIA = 5.0  # 500% de error relativo

indices_inconsistentes = set(
    df_vehiculos.index[error_relativo_todas > UMBRAL_INCONSISTENCIA]
)

print(f"{len(indices_inconsistentes):,} anuncios marcados como inconsistentes ")
print(f"({len(indices_inconsistentes)/len(df_vehiculos)*100:.2f}% del dataset)")


"""
Estima el precio de mercado de un vehículo usado a partir de sus características.

Parámetros:
year : int - Año de fabricación del vehículo (ejemplo: 2022)
manufacturer : str - Marca del vehículo en minúsculas (ejemplo: "toyota", "ford")
condition : str - Estado del vehículo: salvage, fair, good, excellent, like new, new
cylinders : str - Número de cilindros (ejemplo: "4 cylinders", "6 cylinders")
fuel : str - Tipo de combustible: gas, diesel, hybrid, electric, other
odometer : float - Kilometraje en millas (57923.0)
title_status : str - Estado del título: clean, rebuilt, salvage, lien, missing
transmission : str - Tipo de transmisión: automatic, manual, other
drive : str - Tipo de tracción: fwd, rwd, 4wd
type : str - Tipo de carrocería: sedan, SUV, pickup, truck, coupe, etc.

Retorna:
dict con las llaves:
- precio_estimado (float): precio predicho en USD
- rango_confianza (tuple): (precio_min, precio_max) basado en el MAE del modelo (+/- $4,000)
- features_usadas (dict): las características recibidas
"""
def estimar_precio(
    year: int,
    manufacturer: str,
    model: str = "unknown",
    condition: str = "good",
    cylinders: str = "6 cylinders",
    fuel: str = "gas",
    odometer: float = 80_000,
    title_status: str = "clean",
    transmission: str = "automatic",
    drive: str = "fwd",
    type: str = "sedan",
    paint_color: str = "white",
    region: str = "unknown",
    state: str = "ca" ) -> dict:

    # Construccion del DataFrame que espera el pipeline (deben coincidir exactamente con las columnas usadas durante el entrenamiento)
    entrada = pd.DataFrame([{
        'region'       : region,
        'year'         : year,
        'manufacturer' : manufacturer,
        'model'        : model,
        'condition'    : condition,
        'cylinders'    : cylinders,
        'fuel'         : fuel,
        'odometer'     : odometer,
        'title_status' : title_status,
        'transmission' : transmission,
        'drive'        : drive,
        'type'         : type,
        'paint_color'  : paint_color,
        'state'        : state,
        'posting_date' : pd.Timestamp.now().isoformat()
    }])

    precio_predicho = float(modelo_pipeline.predict(entrada)[0])

    # Se usa el MAE del modelo en test que fue $3,999 
    MAE_MODELO = 4000

    return {
        'precio_estimado': round(precio_predicho, 2),
        'rango_confianza': (
            round(max(0, precio_predicho - MAE_MODELO), 2),
            round(precio_predicho + MAE_MODELO, 2)
        ),
        'features_usadas': {
            'year': year, 'manufacturer': manufacturer,
            'condition': condition, 'cylinders': cylinders,
            'fuel': fuel, 'odometer': odometer,
            'transmission': transmission, 'drive': drive,
            'type': type
        }
    }


"""
Busca carrosd reales en el dataset que cumplan con los criterios especificados por el usuario, 
ordenados por mejor relación calidad-precio (year alto, odometer bajo, precio bajo).

Parámetros:
precio_max, precio_min : float - Rango de precio deseado en USD
manufacturer : str - Marca específica (ejemplo: "toyota")
type : str - Tipo de carrocería (ejemplo: "SUV", "sedan")
fuel : str - Tipo de combustible (ejemplo: "gas", "hybrid")
transmission : str - Tipo de transmisión (ejemplo: "automatic")
condition_min : str - Condición mínima aceptable (default: "good")
year_min : int - Año mínimo de fabricación
max_resultados : int - Cantidad máxima de vehículos a retornar (default: 5)

Retorna:
dict con las llaves:
- total_encontrados (int): cuántos vehículos cumplen el filtro
- vehiculos (list[dict]): los top N vehículos encontrados
- disponibilidad_limitada (bool): True si hay menos de 10 resultados, para que el agente lo comunique al usuario
"""
def buscar_vehiculos(
    precio_max: float = None,
    precio_min: float = None,
    manufacturer: str = None,
    type: str = None,
    fuel: str = None,
    transmission: str = None,
    condition_min: str = "good",
    year_min: int = None,
    max_resultados: int = 5 ) -> dict:

    resultado = df_vehiculos.copy()

    if precio_max is not None:
        resultado = resultado[resultado['price'] <= precio_max]

    if precio_min is not None:
        resultado = resultado[resultado['price'] >= precio_min]

    if manufacturer is not None:
        resultado = resultado[resultado['manufacturer'].str.lower() == manufacturer.lower()]

    if type is not None:
        resultado = resultado[resultado['type'].str.lower() == type.lower()]

    if fuel is not None:
        resultado = resultado[resultado['fuel'].str.lower() == fuel.lower()]

    if transmission is not None:
        resultado = resultado[resultado['transmission'].str.lower() == transmission.lower()]

    if year_min is not None:
        resultado = resultado[resultado['year'] >= year_min]

    # Filtro de condición mínima
    orden_condicion = {
        'salvage': 0, 
        'fair': 1, 
        'good': 2,
        'excellent': 3, 
        'like new': 4, 
        'new': 5
    }

    if condition_min in orden_condicion:
        nivel_min = orden_condicion[condition_min]
        resultado = resultado[resultado['condition'].str.lower().map(orden_condicion).fillna(-1) >= nivel_min]

    resultado = resultado[~resultado.index.isin(indices_inconsistentes)]
    total_encontrados = len(resultado)

    # Score simple de calidad-precio = año alto y odómetro bajo son mejores
    # Se normalizan ambos componentes a escala 0-1 antes de combinarlos
    if len(resultado) > 0:
        resultado = resultado.copy()

        year_norm = (resultado['year'] - resultado['year'].min()) / \
             (resultado['year'].max() - resultado['year'].min() + 1e-9)
        
        odo_norm  = 1 - (resultado['odometer'] - resultado['odometer'].min()) / \
                    (resultado['odometer'].max() - resultado['odometer'].min() + 1e-9)
        
        resultado['score_calidad'] = (year_norm + odo_norm) / 2
        resultado = resultado.sort_values('score_calidad', ascending=False)

    top_resultados = resultado.head(max_resultados)

    vehiculos = []
    for _, fila in top_resultados.iterrows():
        vehiculos.append({
            'manufacturer' : fila['manufacturer'],
            'model'        : fila['model'],
            'year'         : int(fila['year']) if pd.notna(fila['year']) else None,
            'price'        : float(fila['price']),
            'odometer'     : float(fila['odometer']) if pd.notna(fila['odometer']) else None,
            'condition'    : fila['condition'],
            'fuel'         : fila['fuel'],
            'transmission' : fila['transmission'],
            'type'         : fila['type']
        })

    return {
        'total_encontrados': total_encontrados,
        'vehiculos': vehiculos,
        'disponibilidad_limitada': total_encontrados < 10
    }


"""
Explica por qué el modelo estimó cierto precio para un vehículo.
Se usa el SHAP para descomponer la predicción en contribuciones individuales de cada característica.

Parámetros: 
year : int - Año de fabricación del vehículo (ejemplo: 2022)
manufacturer : str - Marca del vehículo en minúsculas (ejemplo: "toyota", "ford")
condition : str - Estado del vehículo: salvage, fair, good, excellent, like new, new
cylinders : str - Número de cilindros (ejemplo: "4 cylinders", "6 cylinders")
fuel : str - Tipo de combustible: gas, diesel, hybrid, electric, other
odometer : float - Kilometraje en millas (57923.0)
title_status : str - Estado del título: clean, rebuilt, salvage, lien, missing
transmission : str - Tipo de transmisión: automatic, manual, other
drive : str - Tipo de tracción: fwd, rwd, 4wd
type : str - Tipo de carrocería: sedan, SUV, pickup, truck, coupe, etc.
top_n : int - Cantidad de factores principales a retornar (default: 5)

Retorna:
dict con las llaves:
- precio_estimado (float)
- precio_base (float): precio promedio del dataset (E[f(X)])
- factores_principales (list[dict]): cada uno con 'variable', 'contribucion_usd' y 'direccion' 
"""
def explicar_prediccion(
    year: int,
    manufacturer: str,
    model: str = "unknown",
    condition: str = "good",
    cylinders: str = "6 cylinders",
    fuel: str = "gas",
    odometer: float = 80_000,
    title_status: str = "clean",
    transmission: str = "automatic",
    drive: str = "fwd",
    type: str = "sedan",
    paint_color: str = "white",
    region: str = "unknown",
    state: str = "ca",
    top_n: int = 5 ) -> dict:

    entrada = pd.DataFrame([{
        'region'       : region,
        'year'         : year,
        'manufacturer' : manufacturer,
        'model'        : model,
        'condition'    : condition,
        'cylinders'    : cylinders,
        'fuel'         : fuel,
        'odometer'     : odometer,
        'title_status' : title_status,
        'transmission' : transmission,
        'drive'        : drive,
        'type'         : type,
        'paint_color'  : paint_color,
        'state'        : state,
        'posting_date' : pd.Timestamp.now().isoformat()
    }])

    precio_predicho = float(modelo_pipeline.predict(entrada)[0])
    
    entrada_transformada = pd.DataFrame(
        preprocesador_global.transform(entrada),
        columns=feature_names_global
    )

    # Calcular valores SHAP para la predicción individual
    shap_values = explainer_global(entrada_transformada)
    precio_base = float(shap_values.base_values[0])

    # Ordenar las features por que tanto contribuyen a subir o bajar el precio
    contribuciones = list(zip(feature_names_global, shap_values.values[0]))
    contribuciones.sort(key=lambda x: abs(x[1]), reverse=True)

    factores_principales = []
    for nombre_feature, valor_shap in contribuciones[:top_n]:
        factores_principales.append({
            'variable': nombre_feature,
            'contribucion_usd': round(float(valor_shap), 2),
            'direccion': 'sube el precio' if valor_shap > 0 else 'baja el precio'
        })

    return {
        'precio_estimado': round(precio_predicho, 2),
        'precio_base': round(precio_base, 2),
        'factores_principales': factores_principales
    }

"""
# Prueba 
if __name__ == "__main__":
    print("\n--- Prueba: estimar_precio ---")
    resultado1 = estimar_precio(
        year=2018, manufacturer="toyota", condition="excellent",
        odometer=45000, fuel="gas", type="sedan"
    )
    print(resultado1)
 
    print("\n--- Prueba: buscar_vehiculos ---")
    resultado2 = buscar_vehiculos(
        precio_max=15000, type="SUV", transmission="automatic"
    )
    print(f"Total encontrados: {resultado2['total_encontrados']}")
    print(f"Primeros resultados: {resultado2['vehiculos'][:2]}")
 
    print("\n--- Prueba: explicar_prediccion ---")
    resultado3 = explicar_prediccion(
        year=2018, manufacturer="toyota", condition="excellent",
        odometer=45000, fuel="gas", type="sedan"
    )
    print(resultado3)
"""
