# Recibe la tool que el Planner selecciona y los parámetros que fueron extraidos por el Parser Input
# Ejecuta la función y guarda el resultado en el estado

from core.estadoAgente import EstadoAgente
from core.tools import (
    estimar_precio,
    buscar_vehiculos,
    explicar_prediccion
)

# Valores default para la busqueda y estimación de precio
DEFAULTS_BUSCAR = {
    "precio_max" : None,
    "precio_min" : None,
    "manufacturer" : None,
    "type" : None,
    "fuel" : None,
    "transmission" : None,
    "condition_min" : "good",
    "year_min" : None,
    "max_resultados": 5
}

DEFAULTS_ESTIMAR = {
    "year" : 2013, # mediana del dataset
    "manufacturer" : "ford", # marca más frecuente
    "model" : "unknown",
    "condition" : "good", # moda de 31%
    "cylinders" : "6 cylinders",
    "fuel" : "gas", # 84% del dataset
    "odometer" : 85_548, # mediana
    "title_status" : "clean", # 94.87% del dataset
    "transmission" : "automatic", # 77.72% del dataset
    "drive" : "4wd", # moda de 30.58%
    "type" : "sedan", # moda de 20.32%
    "paint_color"  : "white",
    "region" : "unknown",
    "state" : "ca"
}


# Combina parámetros del Input Parser con los valores por defecto
def _merge_params(defaults: dict, params: dict) -> dict:
    resultado = defaults.copy()
    if params:
        resultado.update({k: v for k, v in params.items() if v is not None})
    return resultado


"""
Ejecuta la tool seleccionada por el Planner con los parámetros extraídos por el Input Parser.

Lee del estado:
- tool_seleccionada : qué función llamar
- parametros : con qué argumentos llamarla

Escribe en el estado:
- resultado_tool : lo que devolvió la tool
- mensaje_error : descripción del error si la tool falla
"""
def nodo_executor(estado: EstadoAgente) -> dict:
    tool = estado.get("tool_seleccionada")
    parametros = estado.get("parametros") or {}

    print(f"\n\033[32m[Executor]\033[0m Tool seleccionada: {tool}")
    print(f"\033[32m[Executor]\033[0m Parámetros recibidos: {parametros}")

    if tool is None:
        print("\033[32m[Executor]\033[0m No hay tool que ejecutar. Proposito: 'otro'")
        return {
            "resultado_tool" : None,
            "mensaje_error" : None
        }

    try:
        if tool == "buscar_vehiculos":
            params_finales = _merge_params(DEFAULTS_BUSCAR, parametros)
            print(f"\033[32m[Executor]\033[0m Llamando buscar_vehiculos con: {params_finales}")
            resultado = buscar_vehiculos(**params_finales)

        elif tool == "estimar_precio":
            params_finales = _merge_params(DEFAULTS_ESTIMAR, parametros)
            print(f"\033[32m[Executor]\033[0m Llamando estimar_precio con: {params_finales}")
            resultado = estimar_precio(**params_finales)

        elif tool == "explicar_prediccion":
            params_finales = _merge_params(DEFAULTS_ESTIMAR, parametros)
            print(f"\033[32m[Executor]\033[0m Llamando explicar_prediccion con: {params_finales}")
            resultado = explicar_prediccion(**params_finales)

        else:
            raise ValueError(f"Tool desconocida: '{tool}'")

        print(f"\033[32m[Executor]\033[0m Tool ejecutada exitosamente")

        return {
            "resultado_tool" : resultado,
            "mensaje_error" : None
        }

    except Exception as e:
        print(f"\033[32m[Executor]\033[0m Error al ejecutar '{tool}': {e}")

        return {
            "resultado_tool" : None,
            "mensaje_error" : f"Error al ejecutar la herramienta '{tool}': {str(e)}"
        }

"""
# Prueba
if __name__ == "__main__":

    print(" Prueba 1: buscar_vehiculos")
    estado_prueba_1 = {
        "messages" : [],
        "consulta_usuario" : "busco un SUV automático por menos de $15,000",
        "proposito" : "buscar",
        "parametros" : {
            "precio_max"  : 15000,
            "type" : "SUV",
            "transmission": "automatic"
        },
        "tool_seleccionada" : "buscar_vehiculos",
        "resultado_tool" : None,
        "validacion_ok" : None,
        "mensaje_error" : None,
        "respuesta_final" : None,
        "num_reintentos" : 0
    }

    resultado_1 = nodo_executor(estado_prueba_1)
    print(f"\nResultado:")
    print(f" Total encontrados: {resultado_1['resultado_tool']['total_encontrados']}")
    print(f" Primer vehículo: {resultado_1['resultado_tool']['vehiculos'][0]}")
    print(f" Disponib. limitada: {resultado_1['resultado_tool']['disponibilidad_limitada']}")


    print("\n")
    print("Prueba 2: estimar_precio")
    estado_prueba_2 = {
        "messages" : [],
        "consulta_usuario"  : "cuánto vale un Toyota Camry 2018 con 50,000 millas",
        "proposito" : "estimar",
        "parametros" : {
            "year" : 2018,
            "manufacturer" : "toyota",
            "model" : "camry",
            "odometer" : 50000,
            "condition" : "good",
            "fuel" : "gas",
            "transmission" : "automatic",
            "type" : "sedan"
        },
        "tool_seleccionada" : "estimar_precio",
        "resultado_tool" : None,
        "validacion_ok" : None,
        "mensaje_error" : None,
        "respuesta_final" : None,
        "num_reintentos" : 0
    }

    resultado_2 = nodo_executor(estado_prueba_2)
    print(f"\nResultado:")
    print(f" Precio estimado: ${resultado_2['resultado_tool']['precio_estimado']:,.2f}")
    print(f" Rango confianza: ${resultado_2['resultado_tool']['rango_confianza'][0]:,.0f} - ${resultado_2['resultado_tool']['rango_confianza'][1]:,.0f}")


    print("\n")
    print(" Prueba 3: explicar_prediccion")
    estado_prueba_3 = {
        "messages" : [],
        "consulta_usuario" : "por qué ese Toyota vale eso?",
        "proposito" : "explicar",
        "parametros" : {
            "year" : 2018,
            "manufacturer" : "toyota",
            "model" : "camry",
            "odometer" : 50000,
            "condition" : "good",
            "fuel" : "gas",
            "transmission" : "automatic",
            "type" : "sedan"
        },
        "tool_seleccionada" : "explicar_prediccion",
        "resultado_tool" : None,
        "validacion_ok" : None,
        "mensaje_error" : None,
        "respuesta_final" : None,
        "num_reintentos" : 0
    }

    resultado_3 = nodo_executor(estado_prueba_3)
    print(f"\nResultado:")
    print(f" Precio estimado: ${resultado_3['resultado_tool']['precio_estimado']:,.2f}")
    print(f" Precio base: ${resultado_3['resultado_tool']['precio_base']:,.2f}")
    print(f" Factores:")
    for factor in resultado_3['resultado_tool']['factores_principales']:
        signo = "+" if factor['contribucion_usd'] > 0 else ""
        print(f"  {factor['variable']:<30} {signo}${factor['contribucion_usd']:,.2f}  ({factor['direccion']})")

    print("\n" )
    print(" Prueba 4: tool desconocida (manejo de error)")
    estado_prueba_4 = {
        **estado_prueba_1,
        "tool_seleccionada": "tool_inexistente"
    }

    resultado_4 = nodo_executor(estado_prueba_4)
    print(f"\nResultado:")
    print(f" resultado_tool: {resultado_4['resultado_tool']}")
    print(f" mensaje_error: {resultado_4['mensaje_error']}")
"""