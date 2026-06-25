# Define el estado compartido entre todos los nodos del agente.
# pip install langgraph 
from typing import TypedDict, Optional, List, Annotated
from langgraph.graph.message import add_messages


"""
Estado compartido entre todos los nodos del agente.

Cada campo es llenado por un nodo específico y leído
por los nodos siguientes. Los campos opcionales pueden
ser None si el nodo correspondiente aún no corrió.
"""
class EstadoAgente(TypedDict):
    messages: Annotated[list, add_messages]
    consulta_usuario: Optional[str]
    proposito: Optional[str]
    parametros: Optional[dict]
    tool_seleccionada: Optional[str]
    resultado_tool: Optional[dict]
    validacion_ok: Optional[bool]
    mensaje_error: Optional[str]
    respuesta: Optional[str]
    reintentos: Optional[int]


"""
Crea el estado inicial para una nueva consulta del usuario.

Parámetros:
consulta : str - El mensaje que escribió el usuario

Retorna: 
dict con todos los campos del EstadoAgente inicializados
"""
def estado_inicial(consulta: str) -> dict:
    return {
        "messages"         : [],
        "consulta_usuario" : consulta,
        "proposito"        : None,
        "parametros"       : None,
        "tool_seleccionada": None,
        "resultado_tool"   : None,
        "validacion_ok"    : None,
        "mensaje_error"    : None,
        "respuesta"  : None,
        "reintentos"   : 0
    }


"""
# Prueba
if __name__ == "__main__":
    # Instanciar el estado
    estado = estado_inicial("busco un SUV automático por menos de $15,000")

    print("Estado inicial creado correctamente:")
    for clave, valor in estado.items():
        print(f"  {clave:<20}: {valor}")

    print("\nCampos del EstadoAgente:")
    for campo in EstadoAgente.__annotations__:
        print(f"  {campo}")
"""