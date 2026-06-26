import json
import time
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from core.estadoAgente import EstadoAgente, estado_inicial
from core.logger import RegistradorEjecucion
from nodos.executor import nodo_executor
from nodos.verifier import nodo_verifier
from nodos.planner import run_planner

"""
Adaptador que conecta run_planner() con el grafo LangGraph.

Lee del estado:
- consulta_usuario: texto del usuario
- messages: historial para contexto

Escribe en el estado:
- tool_seleccionada: qué tool usar
- parametros: con qué argumentos
- intencion: tipo de tarea
- mensaje_error: si el Planner falla
"""
def nodo_planner(estado: EstadoAgente) -> dict:
    consulta = estado.get("consulta_usuario", "")

    # Construir contexto de la conversación para el Planner
    historial = estado.get("messages", [])

    if historial:
        lineas = []

        for m in historial[-4:]:

            # Si LangGraph devuelve HumanMessage / AIMessage
            if isinstance(m, HumanMessage):
                lineas.append(f"\033[95m Usted:\033[0m {m.content}")

            elif isinstance(m, AIMessage):
                lineas.append(f"\033[94m Agente:\033[0m {m.content}")

            # Compatibilidad por si todavía existe algún dict
            elif isinstance(m, dict):
                rol = m.get("role", "")
                contenido = m.get("content", "")

                if rol == "user":
                    lineas.append(f"\033[95m Usted:\033[0m {contenido}")
                else:
                    lineas.append(f"\033[94m Agente:\033[0m {contenido}")

        contexto = "\n".join(lineas)

        # Debug
        if historial:
            print(f"\033[31m[Memoria]\033[0m {len(historial)} mensaje(s) recuperado(s)")

        for m in historial:
            print(f"\033[31m[Memoria]\033[0m {type(m).__name__}")

        consulta_contexto = (
            f"Historial reciente:\n"
            f"{contexto}\n\n"
            f"Nueva consulta: {consulta}"
        )

    else:
        consulta_contexto = consulta

    print(f"\n\033[33m[Planner]\033[0m Procesando: '{consulta}'")

    try:
        plan = run_planner(consulta_contexto)

        # Mapeo de nombres de parámetros Planner → Executor
        parametros_mapeados = {}
        task = plan["task"]

        for clave, valor in plan["parameters"].items():

            if clave == "price_max":
                parametros_mapeados["precio_max"] = valor

            elif clave == "condition":

                if task == "buscar_vehiculos":
                    parametros_mapeados["condition_min"] = valor
                else:
                    parametros_mapeados["condition"] = valor

            elif clave == "condition_min":

                if task == "buscar_vehiculos":
                    parametros_mapeados["condition_min"] = valor
                else:
                    parametros_mapeados["condition"] = valor

            else:
                parametros_mapeados[clave] = valor

        print(
            f"\033[33m[Planner]\033[0m "
            f"Task: {task} | Parámetros: "
            f"{json.dumps(parametros_mapeados, ensure_ascii=False)}"
        )

        return {
            "tool_seleccionada": task,
            "parametros": parametros_mapeados,
            "intencion": task,
            "mensaje_error": None,
            "resultado_tool": None,
            "validacion_ok": None,
            "respuesta": None,
            "reintentos": 0
        }

    except Exception as e:
        print(f"\033[33m[Planner]\033[0m Error: {e}")

        return {
            "tool_seleccionada": None,
            "parametros": {},
            "intencion": "otro",
            "mensaje_error": f"No se pudo interpretar su consulta: {str(e)}",
            "resultado_tool": None,
            "validacion_ok": False,
            "respuesta": "Lo siento, no se entendió su consulta. ¿Puede reformularla?",
            "reintentos": 0
        }

"""
Decide el siguiente nodo después del Verifier.

Si el Verifier marcó validacion_ok=False y quedan reintentos, vuelve al Executor con nuevos parámetros.
Si validacion_ok=True o se agotaron los reintentos, termina.
"""
def enrutar_despues_verifier(estado: EstadoAgente) -> Literal["executor", "__end__"]:
    validacion_ok  = estado.get("validacion_ok")
    reintentos = estado.get("reintentos", 0)
    resultado = estado.get("resultado_tool")

    # Si hay respuesta final, termina
    if estado.get("respuesta"):
        return END

    # Si falló pero quedan reintentos y el Verifier ya actualizó los parámetros, se vuelve al Executor
    if not validacion_ok and reintentos < 2 and resultado is None:
        return "executor"

    return END


"""
Construye y compila el grafo LangGraph con memoria.

Retorna:
app : CompiledGraph - El agente compilado listo para ejecutar
"""
def construir_agente():
    # Crear el grafo con el estado compartido
    grafo = StateGraph(EstadoAgente)

    # Registrar los tres nodos
    grafo.add_node("planner", nodo_planner)
    grafo.add_node("executor", nodo_executor)
    grafo.add_node("verifier", nodo_verifier)

    # Definir el flujo principal
    grafo.set_entry_point("planner")
    grafo.add_edge("planner" , "executor")
    grafo.add_edge("executor", "verifier")

    # Después del Verifier, terminar o reintentar
    grafo.add_conditional_edges(
        "verifier",
        enrutar_despues_verifier,
        { "executor" : "executor", END : END }
    )

    # Memoria persistente entre turnos
    # MemorySaver guarda el estado en RAM
    memoria = MemorySaver()

    # Compilar el grafo con la memoria
    app = grafo.compile(checkpointer=memoria)

    return app


"""
Interfaz de chat interactiva en consola.

Parámetros:
app: grafo compilado
thread_id: identificador de sesión (permite múltiples conversaciones paralelas con diferentes IDs)
"""
def chat(app, thread_id: str = "sesion_1", guardar_evidencia: bool = True):
    # Configuración de la sesión 
    # El thread_id es lo que permite que la memoria sea persistente entre turnos
    config = {"configurable": {"thread_id": thread_id}}

    # Rwgistrar evidncia del funcionaiento
    registrador = RegistradorEjecucion(carpeta="logs") if guardar_evidencia else None
    if registrador:
        ruta_txt = registrador.activar_captura_consola()
        print(f"[Evidencia] Transcripción de esta sesión: {ruta_txt}")
        print(f"[Evidencia] Traza estructurada (JSONL): {registrador.ruta_jsonl}")
        print(f"[Evidencia] Métricas acumuladas (CSV): {registrador.ruta_csv}")

    print("\n" + "-"*90)
    print("  Agente de Recomendación y Predicción de Vehículos Usados")
    print("-"*90)
    print("Funciones:")
    print("- Buscar vehículos: 'busco un SUV automático por menos de $15,000'")
    print("- Estimar precio: 'cuánto vale un Toyota Camry 2019 con 50k millas'")
    print("- Explicar precio: 'por qué ese carro vale eso'")
    print("Nota: Escribí 'salir' para terminar")
    print("-"*90 + "\n")

    try:
        while True:
            try:
                consulta = input("\033[95m Usted:\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nAdiós!")
                break

            if not consulta:
                continue

            if consulta.lower() in ["salir", "exit", "quit", "s", "e", "q"]:
                print("\nAdios! Suerte con la búsqueda de vehículos.")
                break

            # Construir el estado inicial para este turno
            estado = estado_inicial(consulta)

            # Ejecutar el grafo, midiendo tiempo de respuesta para las métricas
            inicio = time.time()
            try:
                resultado = app.invoke(estado, config=config)
                tiempo_turno = time.time() - inicio

                # Mostrar la respuesta final
                respuesta = resultado.get("respuesta", "")
                if respuesta:
                    print(f"\n\033[36mAgente:\033[0m \n{respuesta}\n")
                else:
                    print("\n\033[36mAgente:\033[0m No pude generar una respuesta. Intente otra vez.\n")

                # Guardar evidencia estructurada de este turno (jsonl + csv)
                if registrador:
                    registrador.registrar_turno(
                        consulta=consulta,
                        estado_resultado=resultado,
                        tiempo_s=tiempo_turno
                    )

                # Guardar el turno en el historial de mensajes
                estado_actualizado = {
                    "messages": [
                        HumanMessage(content=consulta),
                        AIMessage(content=respuesta)
                    ]
                }

                app.update_state(config, estado_actualizado)

            except Exception as e:
                tiempo_turno = time.time() - inicio
                print(f"\nError inesperado: {e}")
                print("Por favor intentente de nuevo.\n")

                if registrador:
                    registrador.registrar_turno(
                        consulta=consulta,
                        estado_resultado={"mensaje_error": str(e), "respuesta": None},
                        tiempo_s=tiempo_turno
                    )
    finally:
        if registrador:
            print(f"\n[Evidencia] Sesión guardada en logs/ (id: {registrador.id_sesion})")
            registrador.cerrar()

# Inicio
if __name__ == "__main__":
    print("Iniciando agente...")
    app = construir_agente()
    print("\033[92m¡Agente listo!\033[0m")
    chat(app)