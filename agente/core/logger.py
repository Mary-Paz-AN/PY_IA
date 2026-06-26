"""
Módulo de logging y trazabilidad

1. logs/sesion_<id>.txt
   Transcripción COMPLETA de todo lo que se imprime en consola (Planner,
   Executor, Verifier, Chat).

2. logs/sesion_<id>.jsonl
   Un objeto JSON por turno de conversación con la traza estructurada
   completa: consulta, tool seleccionada, parámetros, resultado de la tool,
   validación, reintentos, mensaje de error y tiempo de respuesta.

3. logs/metricas.csv
   Una fila por turno con las métricas clave (tarea, éxito, reintentos,
   tiempo).
"""

import os
import re
import csv
import json
import sys
from datetime import datetime

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _quitar_ansi(texto: str) -> str:
    return _ANSI_RE.sub("", texto)

"""
Duplica todo lo escrito en un stream hacia un archivo de texto plano, quitando los códigos ANSI.
A partir de ahí, cualquier print() en cualquier módulo (planner.py, executor.py, verifier.py, agente.py) queda guardado automáticamente.
"""
class TeeArchivo:
    def __init__(self, stream_original, ruta_archivo: str):
        self.stream_original = stream_original
        carpeta = os.path.dirname(ruta_archivo)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        self.archivo = open(ruta_archivo, "a", encoding="utf-8")

    def write(self, texto):
        self.stream_original.write(texto)
        self.archivo.write(_quitar_ansi(texto))

    def flush(self):
        self.stream_original.flush()
        self.archivo.flush()

    def cerrar(self):
        self.archivo.close()

"""
Activa la captura de consola (.txt) y registra cada turno en .jsonl y metricas.csv.
"""
class RegistradorEjecucion:
    def __init__(self, carpeta: str = "logs"):
        os.makedirs(carpeta, exist_ok=True)
        self.carpeta = carpeta
        self.id_sesion = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.ruta_txt = os.path.join(carpeta, f"sesion_{self.id_sesion}.txt")
        self.ruta_jsonl = os.path.join(carpeta, f"sesion_{self.id_sesion}.jsonl")
        self.ruta_csv = os.path.join(carpeta, "metricas.csv")
        self._turno = 0
        self._tee = None
        self._inicializar_csv()

    # Redirige sys.stdout para que todos los print() también vaya al .txt.
    def activar_captura_consola(self) -> str:
        self._tee = TeeArchivo(sys.stdout, self.ruta_txt)
        sys.stdout = self._tee
        return self.ruta_txt

    # Crear metricas.csv con encabezado si todavía no existe. 
    # Se va acumulando entre sesiones para poder comparar varias corridas.
    def _inicializar_csv(self):
        if not os.path.exists(self.ruta_csv):
            with open(self.ruta_csv, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "id_sesion", "turno", "timestamp", "consulta", "task",
                    "validacion_ok", "reintentos", "tiempo_s", "hubo_error"
                ])

    """
    Registra un turno de conversación.

    Parámetros:
    consulta: str - lo que escribió el usuario
    estado_resultado: dict - lo que devolvió app.invoke() al final del turno
    tiempo_s: float - segundos que tardó ese turno (planner+executor+verifier)
    """
    def registrar_turno(self, *, consulta: str, estado_resultado: dict, tiempo_s: float) -> dict:
        self._turno += 1
        timestamp = datetime.now().isoformat(timespec="seconds")

        registro = {
            "id_sesion": self.id_sesion,
            "turno": self._turno,
            "timestamp": timestamp,
            "consulta": consulta,
            "task": estado_resultado.get("tool_seleccionada"),
            "parametros": estado_resultado.get("parametros"),
            "resultado_tool": estado_resultado.get("resultado_tool"),
            "validacion_ok": estado_resultado.get("validacion_ok"),
            "reintentos": estado_resultado.get("reintentos"),
            "mensaje_error": estado_resultado.get("mensaje_error"),
            "respuesta": estado_resultado.get("respuesta"),
            "tiempo_s": round(tiempo_s, 3),
        }

        # Evidencia estructurada completa 
        with open(self.ruta_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")

        # Evidencia tabular para métricas/figuras del artículo
        with open(self.ruta_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                self.id_sesion, self._turno, timestamp, consulta,
                registro["task"], registro["validacion_ok"], registro["reintentos"],
                registro["tiempo_s"], bool(registro["mensaje_error"]),
            ])

        return registro

    def cerrar(self):
        if self._tee:
            sys.stdout = self._tee.stream_original
            self._tee.cerrar()
            self._tee = None
