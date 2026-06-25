from ollama import chat
import json

SYSTEM_PROMPT = """
Eres un planner para un sistema de vehículos usados.

Debes analizar la solicitud del usuario.

Tu respuesta SIEMPRE debe tener EXACTAMENTE esta estructura:

{
  "task": "...",
  "parameters": { ... },
  "metadata": { ... }
}

Solo puedes usar estos parámetros. No inventes otros nombres:

Para estimar_precio y buscar_vehiculos:
  - manufacturer    (string)  Marca del vehículo. Ej: "toyota", "ford", "honda"
  - year            (integer) Año de fabricación. Ej: 2021
  - condition       (string)  Estado del vehículo: "new", "like new", "excellent", "good", "fair", "salvage"
  - cylinders       (string)  Número de cilindros: "4 cylinders", "6 cylinders", "8 cylinders"
  - fuel            (string)  Tipo de combustible: "gas", "diesel", "hybrid", "electric"
  - odometer        (float)   Kilometraje en millas. Convierte km a millas si es necesario (1 km = 0.621371 millas)
  - transmission    (string)  Tipo de transmisión: "automatic", "manual", "other"
  - type            (string)  Tipo de vehículo: "sedan", "SUV", "pickup", "truck", "coupe", "hatchback", "wagon", "van", "convertible", "mini-van", "other"
  - title_status    (string)  Estado del título: "clean", "rebuilt", "salvage", "lien", "missing", "parts only"

Solo para buscar_vehiculos:
  - price_max       (float)   Precio máximo que el usuario está dispuesto a pagar

Solo puedes usar estas tareas(tasks). Nunca inventes otros nombres de tareas:

1. estimar_precio
   El usuario quiere conocer el precio de mercado de un vehículo usado a partir de sus características.

2. buscar_vehiculos
   El usuario quiere recomendaciones de vehículos. Busca carros reales en el dataset que cumplan 
   con los criterios especificados por el usuario, ordenados por mejor relación calidad-precio (year alto, odometer bajo, precio bajo)

Devuelve EXCLUSIVAMENTE un JSON válido.

No expliques nada.
No agregues texto adicional.

REGLAS IMPORTANTES:
  - El modelo específico del vehículo (Corolla, Mustang, Civic, etc.) NO es un parámetro.
    Captúralo en el campo "metadata" pero NO lo pongas en "parameters".
  - El campo metadata es opcional. Solo inclúyelo cuando el usuario mencione información que no forma parte de parameters.
  - Si el usuario menciona kilómetros, conviértelos a millas antes de poner el valor en odometer.
  - Solo incluye en "parameters" los campos que el usuario mencionó explícitamente.
  - Si un campo no fue mencionado, no lo incluyas.
  - title_status por defecto es "clean" si el usuario no dice lo contrario.
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
    assert plan["task"] in ["estimar_precio", "buscar_vehiculos"], \
        f"Tarea no reconocida: {plan['task']}"
    return plan

if __name__ == "__main__":
    casos = [
        "Quiero vender un Toyota Corolla 2019 con 70000 km",
        "Tengo $12000 y quiero un Toyota económico",
        "Busco una pickup Ford automática, máximo $8,000",
        "¿Cuánto vale un Ford 2019 con 35,000 millas en excelente condición?",
    ]

    for caso in casos:
        print(f"\nEntrada : {caso}")
        print("-" * 50)
        plan = run_planner(caso)
        print(json.dumps(plan, indent=2, ensure_ascii=False))