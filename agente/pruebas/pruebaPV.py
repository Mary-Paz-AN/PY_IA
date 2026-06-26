# Prueba de la integración entre el Planner y el Executor

import json
from nodos.planner  import run_planner
from nodos.executor import nodo_executor

# Conecta el Planner con el Executor
def planner_executor(consulta: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  Consulta: {consulta}")
    print(f"{'='*60}")

    print("\nPlanner interpretando consulta...")
    plan = run_planner(consulta)
    task = plan["task"]
    print(f"Task: {plan['task']}")
    print(f"Parámetros: {json.dumps(plan['parameters'], ensure_ascii=False)}")

    if "metadata" in plan:
        print(f"Metadata: {json.dumps(plan['metadata'], ensure_ascii=False)}")
    
    parametros_mapeados = {}
    for clave, valor in plan["parameters"].items():

        # price_max → precio_max (siempre)
        if clave == "price_max":
            parametros_mapeados["precio_max"] = valor

        # condition → depende de la task
        elif clave == "condition":
            if task == "buscar_vehiculos":
                # buscar_vehiculos espera condition_min
                parametros_mapeados["condition_min"] = valor
            else:
                # estimar_precio y explicar_prediccion esperan condition
                parametros_mapeados["condition"] = valor

        # condition_min → depende de la task
        elif clave == "condition_min":
            if task == "buscar_vehiculos":
                parametros_mapeados["condition_min"] = valor
            else:
                # Si el Planner manda condition_min para estimar, 
                # lo convertimos a condition
                parametros_mapeados["condition"] = valor

        else:
            parametros_mapeados[clave] = valor

    estado = {
        "messages" : [],
        "consulta_usuario" : consulta,
        "proposito" : plan["task"],
        "parametros" : parametros_mapeados,
        "tool_seleccionada" : plan["task"], 
        "resultado_tool" : None,
        "validacion_ok" : None,
        "mensaje_error" : None,
        "respuesta" : None,
        "reintentos" : 0
    }

    # Executor
    print("\nExecutor ejecutando tool...")
    resultado = nodo_executor(estado)

    # Mostrar resultado 
    print("\nResultado:")

    if resultado["mensaje_error"]:
        print(f"Error: {resultado['mensaje_error']}")

        return {"plan": plan, "resultado": resultado}

    tool = plan["task"]
    datos = resultado["resultado_tool"]

    if tool == "buscar_vehiculos":
        print(f" Total encontrados: {datos['total_encontrados']:,}")
        print(f" Disponib. limitada: {datos['disponibilidad_limitada']}")

        print(f"\n Top {len(datos['vehiculos'])} vehículos recomendados:")
        for i, v in enumerate(datos["vehiculos"], 1):
            print(f"\n    {i}. {v['manufacturer'].title()} {v['model'].title()} {v['year']}")
            print(f" Precio: ${v['price']:,.0f}")
            print(f" Odómetro: {v['odometer']:,.0f} millas")
            print(f" Condición: {v['condition']}")
            print(f" Tipo: {v['type']}")

    elif tool == "estimar_precio":
        print(f" Precio estimado: ${datos['precio_estimado']:,.2f}")
        print(f" Rango de confianza: ${datos['rango_confianza'][0]:,.0f} – ${datos['rango_confianza'][1]:,.0f}")

        print(f"\n Características usadas:")
        for k, v in datos["features_usadas"].items():
            print(f"       {k:<16} : {v}")

    return {"plan": plan, "resultado": resultado}



# Casos de prueba
if __name__ == "__main__":

    casos = [
        # Búsqueda con precio máximo
        "Tengo $12,000 y quiero un Toyota económico",

        # Búsqueda con tipo y transmisión
        "Busco una pickup Ford automática, máximo $8,000",

        # Estimación de precio con km
        "Quiero vender un Toyota Corolla 2019 con 70,000 km",

        # Estimación con millas
        "¿Cuánto vale un Ford F-150 2019 con 35,000 millas en excelente condición?",

        # Búsqueda con combustible específico
        "Busco un SUV híbrido por menos de $20,000",
    ]

    resultados_totales = []

    for consulta in casos:
        try:
            resultado = planner_executor(consulta)
            hay_error = resultado["resultado"].get("mensaje_error") is not None
            resultados_totales.append({
                "consulta" : consulta,
                "ok"       : not hay_error,
                "task"     : resultado["plan"]["task"],
                "error"    : resultado["resultado"].get("mensaje_error")
            })

        except Exception as e:
            print(f"\nError en consulta '{consulta}': {e}")
            resultados_totales.append({
                "consulta" : consulta,
                "ok" : False,
                "error" : str(e)
            })

    # Resumen final
    print(f"\n{'='*60}")
    print("  RESUMEN DE PRUEBAS")
    print(f"{'='*60}")
    exitosas = sum(1 for r in resultados_totales if r["ok"])
    print(f"  Exitosas : {exitosas}/{len(casos)}")
    print(f"  Fallidas : {len(casos) - exitosas}/{len(casos)}")
    print()
    for r in resultados_totales:
        estado_str = "✓" if r["ok"] else "✗"
        task_str   = r.get("task", "")
        error_str  = f" ← {r['error']}" if not r["ok"] else ""
        print(f"  {estado_str} [{task_str:<20}] {r['consulta'][:40]}{error_str}")