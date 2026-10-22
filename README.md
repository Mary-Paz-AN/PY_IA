# Sistema de Recomendación de Vehículos Usados

Sistema de predicción de precios y recomendación de vehículos usados basado en
Machine Learning e integrado en un agente inteligente con capacidad de consulta
en lenguaje natural. Desarrollado como proyecto del curso Inteligencia Artificial
(IC 6200) en el Instituto Tecnológico de Costa Rica.

El artículo completo está disponible en: [Sistema de Recomendación de Vehículos Usados Basado en Machine Learning e Integrado en un Agente Inteligente](https://github.com/Mary-Paz-AN/PY_IA/blob/main/Paper/paper.pdf)

## Descripción

El sistema aborda el problema de la asimetría de información en el mercado de
vehículos usados. A partir de 426,880 anuncios reales de Craigslist, se entrenó
un modelo LightGBM capaz de estimar el precio de mercado de un vehículo a partir
de sus características, con un error absoluto medio (MAE) de $3,999 y un R² de
0.762 sobre el conjunto de prueba.

El modelo fue integrado en un agente inteligente construido con LangGraph que
recibe consultas en lenguaje natural, invoca el modelo como herramienta y retorna
recomendaciones justificadas mediante explicaciones generadas con SHAP.

## Funcionalidades

- **Estimación de precio:** dado un vehículo con sus características, el agente
  estima su precio de mercado con un rango de confianza de ±$4,000.
- **Búsqueda de vehículos:** dado un presupuesto y preferencias del usuario, el
  agente filtra el dataset y retorna los mejores candidatos ordenados por
  relación calidad-precio.
- **Explicación de predicciones:** el agente descompone cada predicción en
  contribuciones individuales por variable usando SHAP, identificando los
  factores que suben o bajan el precio estimado.

  ## Arquitectura

Usuario (lenguaje natural)
↓
Planner (Qwen3 / Ollama)
↓
Executor (LightGBM Pipeline)
↓
Verifier (validación + reintento automático)
↓
Respuesta justificada al usuario

El estado compartido entre nodos es gestionado por LangGraph con memoria
persistente entre turnos mediante `MemorySaver`.

## Resultados del Modelo

| Modelo            | MAE ($) | R²    | Gap R² |
|-------------------|---------|-------|--------|
| Regresión Lineal  | 5,510   | 0.655 | —      |
| Ridge             | 5,633   | 0.670 | 0.017  |
| Decision Tree     | 5,866   | 0.637 | 0.019  |
| XGBoost           | 4,157   | 0.786 | 0.044  |
| Random Forest     | 3,798   | 0.797 | 0.124  |
| **LightGBM**      | **3,987**| **0.798** | **0.058** |

LightGBM fue seleccionado como modelo final por su mejor balance entre
precisión y generalización. Tras dos rondas de optimización de hiperparámetros
con `RandomizedSearchCV`, el modelo final (*Tuning v2*) obtuvo MAE de $3,999
y R² de 0.762 en el test set, representando una mejora del 27.4% respecto al
baseline de Regresión Lineal.

## Estructura del Proyecto


## Reproducibilidad

Todos los experimentos utilizan `SEED = 42` fijado globalmente. La partición
de datos es temporal (no aleatoria): 70% train, 15% validación, 15% test,
respetando el orden cronológico de `posting_date` para prevenir data leakage.

## Variables más influyentes (SHAP)

| Variable   | Importancia SHAP ($) |
|------------|----------------------|
| year       | 6,054                |
| odometer   | 3,188                |
| cylinders  | 2,560                |
| fuel_gas   | 2,070                |
| drive_fwd  | 1,565                |

El año de fabricación y el kilometraje dominan la predicción, confirmando
las correlaciones identificadas en el análisis exploratorio (r=0.58 y r=-0.54).

## Tecnologías

- **ML:** LightGBM, scikit-learn, XGBoost, SHAP, Optuna
- **Agente:** LangGraph, LangChain, Ollama, Qwen3
- **Datos:** pandas, NumPy
- **Entorno:** Python 3.10+

## Autores

- Andrés Bonilla Solano - andbonilla@estudiantec.cr
- Mary Paz Álvarez Navarrete - mar01alvarez@estudiantec.cr

Instituto Tecnológico de Costa Rica - Escuela de Ingeniería en Computación - 2026
