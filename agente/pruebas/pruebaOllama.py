# Archivo para probar que Ollama este funcionando 

# 1. Instalar Ollama desde la web
# 2. En una terminal:
#   1. ollama pull qwen3
#   2. pip install ollama

from ollama import chat

response = chat(
    model='qwen3',
    messages=[
        {
            'role': 'user',
            'content': 'Responde únicamente: FUNCIONA'
        }
    ]
)

print(response['message']['content'])