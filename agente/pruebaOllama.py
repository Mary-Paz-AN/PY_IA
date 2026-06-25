# Archivo para probar que Ollama este funcionando 
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