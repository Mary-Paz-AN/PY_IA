from core.estadoAgente import EstadoAgente
from nodos.executor import nodo_executor, DEFAULTS_BUSCAR, DEFAULTS_ESTIMAR

# Valores válidos para validación de campos categóricos
CONDICIONES_VALIDAS = {
    'salvage', 'fair', 'good', 'excellent', 'like new', 'new'
}

COMBUSTIBLES_VALIDOS = {
    'gas', 'diesel', 'hybrid', 'electric', 'other'
}

TRANSMISIONES_VALIDAS = {
    'automatic', 'manual', 'other'
}

TIPOS_VALIDOS = {
    'sedan', 'suv', 'pickup', 'truck', 'coupe',
    'hatchback', 'wagon', 'van', 'convertible', 'mini-van', 'other'
}

# Distintos typos cometidos por LLM
CORRECCIONES_TYPOS = {
    'condition': {
        'excelent' : 'excellent',
        'excelente': 'excellent',
        'like-new' : 'like new',
        'likenew' : 'like new',
        'fair ' : 'fair',
        'goo' : 'good',
    },
    'fuel': {
        'gasoline' : 'gas',
        'petrol' : 'gas',
        'hibrido' : 'hybrid',
        'electrico': 'electric',
    },
    'transmission': {
        'auto' : 'automatic',
        'manual ' : 'manual',
    },
    'type': {
        'suv' : 'SUV',
        'pick-up' : 'pickup',
        'pick up' : 'pickup',
        'minivan' : 'mini-van',
    }
}

# Rango válido de precios, esto según el dataset de entrenamiento
PRECIO_MIN_DATASET = 500
PRECIO_MAX_DATASET = 100_000

UMBRAL_POCOS_RESULTADOS = 5

# Máximo de reintentos
MAX_REINTENTOS = 2


# Funciones auxiliares

"""
Detecta y corrige typos en los valores categóricos del Planner.

Retorna:
tuple:
- dict con los parámetros corregidos
- list de advertencias sobre las correcciones aplicadas
"""
def _corregir_typos(parametros: dict) -> tuple[dict, list[str]]:
    parametros_corregidos = parametros.copy()
    advertencias = []

    for campo, correcciones in CORRECCIONES_TYPOS.items():
        if campo in parametros_corregidos:
            valor_original = str(parametros_corregidos[campo]).lower().strip()

            if valor_original in correcciones:
                valor_corregido = correcciones[valor_original]
                parametros_corregidos[campo] = valor_corregido
                advertencias.append(f"Se corrigió '{campo}': '{valor_original}' por '{valor_corregido}'")

    return parametros_corregidos, advertencias


"""
Verifica que los valores categóricos sean válidos según el dataset.

Retorna:
list de advertencias sobre valores inválidos detectados
"""
def _validar_valores_categoricos(parametros: dict) -> list[str]:
    advertencias = []

    if 'condition' in parametros and parametros['condition'] is not None:
        if parametros['condition'].lower() not in CONDICIONES_VALIDAS:
            advertencias.append(
                f"Condición '{parametros['condition']}' no reconocida. "
                f"Valores válidos: {', '.join(sorted(CONDICIONES_VALIDAS))}"
            )

    if 'condition_min' in parametros and parametros['condition_min'] is not None:
        if parametros['condition_min'].lower() not in CONDICIONES_VALIDAS:
            advertencias.append(
                f"Condición mínima '{parametros['condition_min']}' no reconocida. "
                f"Se usará 'good' por defecto."
            )
            parametros['condition_min'] = 'good'

    if 'fuel' in parametros and parametros['fuel'] is not None:
        if parametros['fuel'].lower() not in COMBUSTIBLES_VALIDOS:
            advertencias.append(
                f"Combustible '{parametros['fuel']}' no reconocido. "
                f"Valores válidos: {', '.join(sorted(COMBUSTIBLES_VALIDOS))}"
            )

    if 'transmission' in parametros and parametros['transmission'] is not None:
        if parametros['transmission'].lower() not in TRANSMISIONES_VALIDAS:
            advertencias.append(
                f"Transmisión '{parametros['transmission']}' no reconocida. "
                f"Valores válidos: {', '.join(sorted(TRANSMISIONES_VALIDAS))}"
            )

    return advertencias

"""
Va cambiando los parametros de la busqeuda de forma gradual para obtener resultados

Retorna:
tuple:
- dict con los parámetros relajados
- str describiendo
"""
def _cambiar_parametros_busqueda(parametros: dict) -> tuple[dict, str]:
    params = parametros.copy()
    descripcion = ""

    # Orden: primero condición, combustible, transmisión, fabricante, año mínimo
    if 'condition_min' in params and params['condition_min'] != 'fair':
        params['condition_min'] = 'fair'
        descripcion = "se redujo la condición mínima a 'fair'"

    elif 'fuel' in params and params['fuel'] is not None:
        params['fuel'] = None
        descripcion = "se eliminó el filtro de combustible"

    elif 'transmission' in params and params['transmission'] is not None:
        params['transmission'] = None
        descripcion = "se eliminó el filtro de transmisión"

    elif 'manufacturer' in params and params['manufacturer'] is not None:
        params['manufacturer'] = None
        descripcion = "se eliminó el filtro de fabricante"

    elif 'year_min' in params and params['year_min'] is not None:
        params['year_min'] = None
        descripcion = "se eliminó el filtro de año mínimo"

    elif 'precio_max' in params and params['precio_max'] is not None:
        params['precio_max'] = params['precio_max'] * 1.2
        descripcion = f"se aumentó el precio máximo un 20% a ${params['precio_max']:,.0f}"

    else:
        descripcion = "no se pudo hacer más cambios a los parámetros"

    return params, descripcion


# Nodo Verifier
"""
Valida el resultado del Executor y decide si mostrarlo al usuario
o reintentar con parámetros más flexibles.

Lee del estado:
- tool_seleccionada: qué tool se ejecutó
- resultado_tool: qué devolvió el Executor
- mensaje_error: si el Executor reportó un error
- parametros: parámetros originales de la búsqueda
- reintentos: cuántos reintentos se han hecho

Escribe en el estado:
- validacion_ok: True si la respuesta es aceptable
- respuesta: texto formateado para el usuario
- mensaje_error: advertencias o errores detectados
- parametros: parámetros relajados si hubo reintento
- reintentos: contador actualizado
"""
def nodo_verifier(estado: EstadoAgente) -> dict:
    tool = estado.get("tool_seleccionada")
    resultado = estado.get("resultado_tool")
    error_previo  = estado.get("mensaje_error")
    parametros = estado.get("parametros") or {}
    reintentos = estado.get("reintentos") or 0
    consulta = estado.get("consulta_usuario", "")

    advertencias  = []

    print(f"\n\033[94m[Verifier]\033[0m Validando resultado de '{tool}' "
          f"(reintento {reintentos}/{MAX_REINTENTOS})")

    # Error: la tool fallo
    if error_previo and resultado is None:
        print(f"\033[94m[Verifier]\033[0m Error crítico detectado: {error_previo}")

        if reintentos >= MAX_REINTENTOS:
            return {
                "validacion_ok"  : False,
                "respuesta": (
                    f"Lo siento, no pude completar su solicitud después de "
                    f"{MAX_REINTENTOS} intentos. "
                    f"Por favor, intenta reformular su consulta."
                ),
                "mensaje_error" : error_previo,
                "reintentos" : reintentos
            }

        params_new, descripcion = _cambiar_parametros_busqueda(parametros)
        print(f"\033[94m[Verifier]\033[0m Reintentando... {descripcion}")

        nuevo_estado = {**estado,
                        "parametros" : params_new,
                        "reintentos" : reintentos + 1,
                        "mensaje_error" : None}
        
        nuevo_resultado = nodo_executor(nuevo_estado)

        # Pasar el resultado del reintento por el Verifier para formatearlo
        estado_reintento = {**nuevo_estado, **nuevo_resultado}
        return nodo_verifier(estado_reintento)

    # Error: resultado nulo sin error explicito
    if resultado is None:
        print("\033[94m[Verifier]\033[0m Resultado nulo sin error reportado")
        return {
            "validacion_ok" : False,
            "respuesta": "No se pudo obtener un resultado. Por favor reformule su consulta.",
            "mensaje_error" : "Resultado nulo inesperado"
        }

    # Corrección de typos en parámetros
    parametros_corregidos, typos_encontrados = _corregir_typos(parametros)
    if typos_encontrados:
        advertencias.extend(typos_encontrados)
        print(f"\033[94m[Verifier]\033[0m Typos corregidos: {typos_encontrados}")

    # Validación de valores categóricos
    advertencias_categoricas = _validar_valores_categoricos(parametros_corregidos)
    if advertencias_categoricas:
        advertencias.extend(advertencias_categoricas)
        print(f"\033[94m[Verifier]\033[0m Valores inválidos: {advertencias_categoricas}")

    # Validaciones específicas por tool
    if tool == "buscar_vehiculos":
        total = resultado.get("total_encontrados", 0)

        # Si no hay resultados se hace un reintento automatico
        if total == 0:
            print("\033[94m[Verifier]\033[0m Sin resultados, reintentando con nuevos parametros...")

            if reintentos >= MAX_REINTENTOS:
                return {
                    "validacion_ok"  : False,
                    "respuesta": (
                        "No se encontraron vehículos que cumplan con todos sus criterios "
                        "después de varios intentos. Le sugiero ampliar el presupuesto "
                        "o ser más flexible con alguna otra característica."
                    ),
                    "mensaje_error" : "Sin resultados tras reintentos",
                    "reintentos" : reintentos
                }

            params_new, descripcion = _cambiar_parametros_busqueda(parametros)
            print(f"\033[94m[Verifier]\033[0m Generando nuevos parámetros... {descripcion}")

            nuevo_estado = {**estado,
                            "parametros" : params_new,
                            "reintentos" : reintentos + 1,
                            "mensaje_error" : None}
            nuevo_resultado = nodo_executor(nuevo_estado)

            # Pasar el resultado del reintento por el Verifier para formatearlo
            estado_reintento = {**nuevo_estado, **nuevo_resultado}
            return nodo_verifier(estado_reintento)

        # Si hay pocos resultados se da una advertencia pero se continua
        if total < UMBRAL_POCOS_RESULTADOS:
            advertencias.append(
                f"Solo se encontraron {total} vehículos con esos criterios. "
                f"Podrías ampliar el presupuesto o ser más flexible con alguna otra característica."
            )

        # Disponibilidad limitada 
        if resultado.get("disponibilidad_limitada"):
            advertencias.append(
                "Hay disponibilidad limitada de vehículos con esas características."
            )

        # Verificar coherencia con el tipo de vehículo en los resultados
        vehiculos = resultado.get("vehiculos", [])
        if vehiculos and "type" in parametros:
            tipo_solicitado = parametros["type"].lower()

            tipos_encontrados = {
                str(v.get("type", "")).lower()
                for v in vehiculos
                if v.get("type") and str(v.get("type")) != "nan"
            }

            if tipo_solicitado not in tipos_encontrados and tipos_encontrados:
                advertencias.append(
                    f"Nota: se solicitó tipo '{parametros['type']}' pero los resultados "
                    f"incluyen tipos: {', '.join(tipos_encontrados)}."
                )

    elif tool == "estimar_precio":
        precio = resultado.get("precio_estimado", 0)

        # Precio fuera del rango del dataset
        if precio < PRECIO_MIN_DATASET or precio > PRECIO_MAX_DATASET:
            advertencias.append(
                f"El precio estimado (${precio:,.0f}) está fuera del rango habitual "
                f"del modelo (${PRECIO_MIN_DATASET:,}–${PRECIO_MAX_DATASET:,}). "
                f"La predicción puede ser menos confiable."
            )

        # Verificar coherencia del tipo de vehículo y los parámetros
        features = resultado.get("features_usadas", {})
        if features.get("type") == "sedan" and "type" not in parametros:
            advertencias.append(
                "Se usó 'sedan' como tipo por defecto. Si su vehículo es de otro "
                "tipo (pickup, SUV, truck), especifiquelo para una estimación más precisa."
            )

    elif tool == "explicar_prediccion":
        factores = resultado.get("factores_principales", [])
        if not factores:
            advertencias.append(
                "No se pudieron calcular los factores explicativos. "
                "La predicción de precio sigue siendo válida."
            )

    # Formatear la respuesta final
    respuesta = _formatear_respuesta(tool, resultado, consulta, advertencias)
    print(f"\033[94m[Verifier]\033[0m Validación OK. {len(advertencias)} advertencia(s)")

    return {
        "validacion_ok"  : True,
        "respuesta": respuesta,
        "mensaje_error"  : "\n".join(advertencias) if advertencias else None,
        "reintentos" : reintentos
    }


"""
Genera el texto de respuesta que verá el usuario.
"""
def _formatear_respuesta(
    tool: str,
    resultado: dict,
    consulta: str,
    advertencias: list[str] ) -> str:
    lineas = []

    if tool == "buscar_vehiculos":
        vehiculos = resultado.get("vehiculos", [])
        total = resultado.get("total_encontrados", 0)

        lineas.append(f"Se encontraron {total:,} vehículos que coinciden con su búsqueda.")
        lineas.append(f"Aquí están las mejores {len(vehiculos)} opciones:\n")

        for i, v in enumerate(vehiculos, 1):
            manufacturer = str(v.get('manufacturer', 'Desconocido')).title()
            model = str(v.get('model', '')).title()
            year = v.get('year', '-')
            precio = v.get('price', 0)
            odometro = v.get('odometer', 0)
            condicion = v.get('condition', '-')
            tipo = v.get('type', '-')

            lineas.append(f"{i}. {manufacturer} {model} ({year})")
            lineas.append(f" Precio: ${precio:,.0f}")
            lineas.append(f" Odómetro: {odometro:,.0f} millas")
            lineas.append(f" Condición: {condicion}")
            lineas.append(f" Tipo: {tipo}")
            lineas.append("")

    elif tool == "estimar_precio":
        precio = resultado.get("precio_estimado", 0)
        rango = resultado.get("rango_confianza", (0, 0))
        features = resultado.get("features_usadas", {})

        lineas.append(f"Precio estimado de mercado: ${precio:,.2f}")
        lineas.append(
            f"Rango de confianza: ${rango[0]:,.0f} – ${rango[1]:,.0f} "
            f"(basado en el error promedio del modelo de ±$4,000)\n"
        )

        lineas.append("Características consideradas:")
        for k, v in features.items():
            lineas.append(f"   • {k:<16}: {v}")

    elif tool == "explicar_prediccion":
        precio = resultado.get("precio_estimado", 0)
        base = resultado.get("precio_base", 0)
        factores = resultado.get("factores_principales", [])

        lineas.append(f"Precio estimado: ${precio:,.2f}")
        lineas.append(f"Precio base del mercado: ${base:,.2f}\n")

        lineas.append("Factores que explican el precio:")
        for f in factores:
            signo = "+" if f["contribucion_usd"] > 0 else ""
            up_down = "⬆" if f["contribucion_usd"] > 0 else "⬇"
            variable = f["variable"].replace("num__", "").replace("nom__", "").replace("ord__", "")
            lineas.append(
                f"{up_down} {variable:<28} "
                f"{signo}${f['contribucion_usd']:,.2f}  ({f['direccion']})"
            )

    # Adevertencias
    if advertencias:
        lineas.append("\n Advertencia(s):")
        for adv in advertencias:
            lineas.append(f"   - {adv}")

    return "\n".join(lineas)

"""
# Prueba 
if __name__ == "__main__":

    print("=" * 60)
    print("  Prueba 1: resultado válido de buscar_vehiculos")
    print("=" * 60)
    estado_ok = {
        "messages"          : [],
        "consulta_usuario"  : "busco un SUV automático por menos de $15,000",
        "intencion"         : "buscar",
        "parametros"        : {"precio_max": 15000, "type": "SUV", "transmission": "automatic"},
        "tool_seleccionada" : "buscar_vehiculos",
        "resultado_tool"    : {
            "total_encontrados"    : 21805,
            "disponibilidad_limitada": False,
            "vehiculos": [
                {"manufacturer": "chevrolet", "model": "trax ls", "year": 2020,
                 "price": 14990.0, "odometer": 1323.0, "condition": "excellent",
                 "fuel": "gas", "transmission": "automatic", "type": "SUV"},
                {"manufacturer": "toyota", "model": "rav4", "year": 2019,
                 "price": 13500.0, "odometer": 25000.0, "condition": "good",
                 "fuel": "gas", "transmission": "automatic", "type": "SUV"}
            ]
        },
        "validacion_ok"     : None,
        "mensaje_error"     : None,
        "respuesta"   : None,
        "reintentos"    : 0
    }
    resultado_1 = nodo_verifier(estado_ok)
    print(f"\nValidación OK : {resultado_1['validacion_ok']}")
    print(f"Advertencias  : {resultado_1['mensaje_error']}")
    print(f"\nRespuesta final:\n{resultado_1['respuesta']}")

    print("\n" + "=" * 60)
    print("  Prueba 2: sin resultados → reintento automático")
    print("=" * 60)
    estado_sin_resultados = {
        "messages"          : [],
        "consulta_usuario"  : "busco un Ferrari eléctrico por menos de $5,000",
        "intencion"         : "buscar",
        "parametros"        : {
            "precio_max"  : 5000,
            "manufacturer": "ferrari",
            "fuel"        : "electric"
        },
        "tool_seleccionada" : "buscar_vehiculos",
        "resultado_tool"    : {
            "total_encontrados"    : 0,
            "disponibilidad_limitada": True,
            "vehiculos"            : []
        },
        "validacion_ok"     : None,
        "mensaje_error"     : None,
        "respuesta"   : None,
        "reintentos"    : 0
    }
    resultado_2 = nodo_verifier(estado_sin_resultados)
    print(f"\nValidación OK : {resultado_2.get('validacion_ok')}")
    print(f"Advertencias  : {resultado_2.get('mensaje_error')}")
    print(f"\nRespuesta:\n{resultado_2.get('respuesta', '')[:300]}")

    print("\n" + "=" * 60)
    print("  Prueba 3: typo en condition → corrección automática")
    print("=" * 60)
    estado_typo = {
        "messages"          : [],
        "consulta_usuario"  : "Ford F-150 2019 en excelent condición",
        "intencion"         : "estimar",
        "parametros"        : {
            "year"        : 2019,
            "manufacturer": "ford",
            "condition"   : "excelent",  # typo intencional
            "odometer"    : 35000
        },
        "tool_seleccionada" : "estimar_precio",
        "resultado_tool"    : {
            "precio_estimado" : 33420.22,
            "rango_confianza" : (29420.0, 37420.0),
            "features_usadas" : {
                "year": 2019, "manufacturer": "ford",
                "condition": "good", "odometer": 35000,
                "type": "sedan"
            }
        },
        "validacion_ok"     : None,
        "mensaje_error"     : None,
        "respuesta"   : None,
        "reintentos"    : 0
    }
    resultado_3 = nodo_verifier(estado_typo)
    print(f"\nValidación OK : {resultado_3['validacion_ok']}")
    print(f"Advertencias  : {resultado_3['mensaje_error']}")
    print(f"\nRespuesta:\n{resultado_3['respuesta']}")

    print("\n" + "=" * 60)
    print("  Prueba 4: error crítico → reintento y fallo final")
    print("=" * 60)
    estado_error = {
        "messages"          : [],
        "consulta_usuario"  : "busco algo imposible",
        "intencion"         : "buscar",
        "parametros"        : {"precio_max": 100},
        "tool_seleccionada" : "buscar_vehiculos",
        "resultado_tool"    : None,
        "validacion_ok"     : None,
        "mensaje_error"     : "Error al ejecutar la herramienta",
        "respuesta"   : None,
        "reintentos"    : MAX_REINTENTOS  # ya agotó los reintentos
    }
    resultado_4 = nodo_verifier(estado_error)
    print(f"\nValidación OK : {resultado_4['validacion_ok']}")
    print(f"\nRespuesta:\n{resultado_4['respuesta']}")
"""