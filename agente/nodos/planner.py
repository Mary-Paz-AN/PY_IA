from ollama import chat
import json

SYSTEM_PROMPT = """
Eres un planner para un sistema de recomendación de vehículos usados.

Debes analizar la solicitud del usuario y devolver un plan estructurado.

Tu respuesta SIEMPRE debe tener EXACTAMENTE esta estructura JSON:

{
  "task": "...",
  "parameters": { ... },
  "metadata": { ... }
}


TAREAS DISPONIBLES:
Solo puedes usar estas tres tareas. Nunca inventes otros nombres:

1. estimar_precio
   Cuándo usarla: el usuario quiere saber cuánto vale un vehículo específico, quiere venderlo, o pregunta por su precio de mercado.
   Ejemplos:
     - "¿Cuánto vale un Toyota Corolla 2019 con 50,000 millas?"
     - "Quiero vender mi Ford F-150 2018"
     - "¿Cuánto me darían por mi carro?"

2. buscar_vehiculos
   Cuándo usarla: el usuario quiere encontrar o que le recomienden vehículos según su presupuesto o preferencias.
   Ejemplos:
     - "Busco un SUV automático por menos de $15,000"
     - "Tengo $12,000 y quiero un Toyota económico"
     - "Recomiéndame pickups Ford baratas"

3. explicar_prediccion
   Cuándo usarla: el usuario pregunta POR QUÉ el modelo dio cierto precio, qué factores influyeron, o pide una explicación de una predicción anterior.
   Esta tarea usa los mismos parámetros que estimar_precio.
   Ejemplos:
     - "¿Por qué vale eso?"
     - "Explícame cómo llegaste a ese precio"
     - "¿Qué factores afectaron el precio?"
     - "¿Por qué ese carro es tan caro/barato?"
     - "Dame más detalles sobre esa estimación"
     - "¿Qué variables consideraste?"
     - "¿Cómo se llegó a esa estimación?"
   IMPORTANTE: si el usuario hace referencia a un vehículo mencionado antes en la conversación (con "ese", "ese carro", "ese precio"), 
   reutiliza los mismos parámetros de la consulta anterior.


PARÁMETROS DISPONIBLES:
Para estimar_precio y explicar_prediccion:
  - manufacturer    (string)  Marca. Ej: "toyota", "ford", "honda"
  - year            (integer) Año de fabricación. Ej: 2021
  - condition       (string)  "new", "like new", "excellent", "good", "fair", "salvage"
  - cylinders       (string)  "4 cylinders", "6 cylinders", "8 cylinders"
  - fuel            (string)  "gas", "diesel", "hybrid", "electric", "other"
  - odometer        (float)   Kilometraje en millas. Si el usuario dice km, convertir multiplicando por 0.621371
  - transmission    (string)  "automatic", "manual", "other"
  - drive           (string)  "fwd", "rwd", "4wd"
  - type            (string)  "sedan", "SUV", "pickup", "truck", "coupe", "hatchback", "wagon", "van", "convertible", "mini-van", "other"
  - title_status    (string)  "clean", "rebuilt", "salvage", "lien", "missing", "parts only". Por defecto: "clean"

Para buscar_vehiculos (además de los anteriores excepto odometer):
  - price_max       (float)   Precio máximo en USD


REGLAS IMPORTANTES:
  1. Devuelve EXCLUSIVAMENTE un JSON válido. Sin texto adicional. Sin explicaciones. Sin bloques de código. Sin comillas triples.

  2. El modelo específico (Corolla, Mustang, Civic) NO es un parámetro. Ponlo en "metadata" con la clave "model".

  3. El campo "metadata" es opcional. Solo inclúyelo si hay información relevante que no encaja en "parameters".

  4. Solo incluye en "parameters" los campos mencionados explícitamente por el usuario. No inventes valores.

  5. Si el usuario menciona kilómetros, conviértelos a millas antes de asignar el valor a "odometer".

  6. Para explicar_prediccion: si el usuario dice "ese carro", "eso", "ese precio" o hace referencia implícita a algo dicho antes,
    usa los parámetros del vehículo mencionado anteriormente en la conversación.

  7. Si no puedes determinar la tarea con certeza, elige "buscar_vehiculos" como valor por defecto.
"""
# === === === Prueba Inicial === === === 
# Ejemplo para estimar_precio
# user_input = "Quiero vender un Toyota Corolla 2021 con 70000 km"

# Ejemplo para buscar_vehiculos
# user_input = "Tengo $12000 y quiero un Toyota económico"

'''
response = chat(
    model="qwen3",
    messages=[
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_input
        }
    ]
)

print(response["message"]["content"])
'''

# === === === === === === === === === === === ===

def run_planner(user_input: str) -> dict:
    """
    Ejecuta el Planner con la entrada del usuario.
    Retorna el plan estructurado como diccionario.
    Esta función será llamada por el orquestador de LangGraph.
    """
    response = chat(
        model="qwen3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_input}
        ]
    )

    plan = json.loads(response["message"]["content"])

    # Validación mínima del plan
    assert "task" in plan, "El plan no tiene campo 'task'"
    assert "parameters" in plan, "El plan no tiene campo 'parameters'"
    assert plan["task"] in ["estimar_precio", "buscar_vehiculos", "explicar_prediccion"], \
        f"Tarea no reconocida: {plan['task']}"
    return plan

if __name__ == "__main__":
    casos = [
        "Quiero vender un Toyota Corolla 2019 con 70000 km",
        "Tengo $12000 y quiero un Toyota económico",
        "Busco una pickup Ford automática, máximo $8,000",
        "¿Cuánto vale un Ford 2019 con 35,000 millas en excelente condición?",
        "Cómo se llegó a esa estimación?"
    ]

    for caso in casos:
        print(f"\nEntrada : {caso}")
        print("-" * 50)
        plan = run_planner(caso)
        print(json.dumps(plan, indent=2, ensure_ascii=False))