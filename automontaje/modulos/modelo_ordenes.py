"""SUME DOCBLOCK: intérprete opcional de órdenes mediante un modelo Ollama local.

Solo propone un contrato. La interfaz lo muestra y el usuario decide ejecutarlo.
No se envía el vídeo al modelo ni se ejecuta ningún comando generado por este.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contrato_edicion import listar_herramientas, validar_contrato_herramientas


def interpretar_orden(texto: str, modelo: str | None = None) -> dict:
    nombre = modelo or os.environ.get("AEGS_MODELO", "").strip()
    if not nombre:
        raise RuntimeError("Configura AEGS_MODELO con un modelo instalado en Ollama.")
    if not isinstance(texto, str) or not texto.strip() or len(texto) > 4000:
        raise ValueError("Escribe una orden de entre 1 y 4000 caracteres.")
    catalogo = listar_herramientas()
    instrucciones = (
        "Convierte la orden del usuario en un JSON con la clave 'herramientas'. "
        "Usa solo nombres y parámetros del catálogo proporcionado. "
        "Los tiempos se refieren al vídeo original. Si algo es ambiguo o no está en el catálogo, "
        "no inventes herramientas. No generes comandos FFmpeg.\nCatálogo: "
        + json.dumps(catalogo, ensure_ascii=False)
    )
    cuerpo = json.dumps({"model": nombre, "stream": False, "format": "json",
                         "messages": [{"role": "system", "content": instrucciones},
                                      {"role": "user", "content": texto}]},
                        ensure_ascii=False).encode("utf-8")
    peticion = Request("http://127.0.0.1:11434/api/chat", data=cuerpo,
                       headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(peticion, timeout=90) as respuesta:
            datos = json.load(respuesta)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Ollama local no respondió: {exc}") from exc
    try:
        propuesta = json.loads(datos["message"]["content"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("El modelo no devolvió un contrato JSON válido.") from exc
    validacion = validar_contrato_herramientas(propuesta)
    if not validacion["valido"]:
        raise ValueError("La orden propuesta no pasó la validación: " + "; ".join(validacion["errores"]))
    if not validacion["contrato"]["herramientas"]:
        raise ValueError("El modelo no encontró ninguna edición compatible.")
    return validacion["contrato"]
