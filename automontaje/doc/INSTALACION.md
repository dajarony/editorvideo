# 📦 Guía de Instalación

## Requisitos del Sistema

| Requisito | Versión Mínima | Verificación |
|-----------|---------------|-------------|
| Python | 3.11+ | `python --version` |
| FFmpeg | 4.0+ | `ffmpeg -version` |
| FFprobe | (incluido con FFmpeg) | `ffprobe -version` |
| Internet | Requerido para TTS | Para generar narración |

---

## Paso 1: Instalar Python

Descargar desde [python.org](https://www.python.org/downloads/) (versión 3.11 o superior).

> **Nota Python 3.13+**: El sistema incluye la dependencia `audioop-lts` para compatibilidad con Python 3.13, donde el módulo `audioop` fue eliminado.

---

## Paso 2: Instalar FFmpeg

### Windows (recomendado)

```powershell
winget install ffmpeg
```

O descargar manualmente desde [ffmpeg.org/download.html](https://ffmpeg.org/download.html):
1. Descargar el build para Windows (versión `full` o `essentials`)
2. Extraer el ZIP
3. Añadir la carpeta `bin/` al PATH del sistema:
   - Buscar "Variables de entorno" en el menú Inicio
   - Editar `Path` → Nuevo → Pegar la ruta al `bin/` de FFmpeg

### macOS

```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install ffmpeg
```

### Verificación

```bash
ffmpeg -version   # Debe mostrar la versión
ffprobe -version  # Debe mostrar la versión
```

---

## Paso 3: Instalar Dependencias Python

```bash
# Desde la raíz del repositorio. Instalación mínima (sin PyTorch):
pip install -e "automontaje[dev]"

# Opcional, solo para subtítulos automáticos (Whisper arrastra PyTorch, varios GB):
pip install -e "automontaje[subtitulos]"
```

`pip install -r automontaje/requirements.txt` sigue funcionando y tampoco instala Whisper.

### Dependencias Principales

| Paquete | Propósito |
|---------|----------|
| `edge-tts` | Generación de narración (Microsoft Edge TTS) |
| `pydub` | Manipulación de audio (mezcla, ducking, fades) |
| `audioop-lts` | Compatibilidad PyDub con Python 3.13+ |
| `openai-whisper` | Transcripción para subtítulos. **Opcional**: extra `subtitulos` |
| `pytest` | Framework de testing |
| `pytest-asyncio` | Soporte async para tests de TTS |

> **Nota sobre Whisper**: es opcional y solo hace falta para los subtítulos. Instala PyTorch (varios GB) y la primera ejecución descarga el modelo (~140 MB para `base`).

---

## Paso 4: Verificar Instalación

```bash
# Verificar que todo importa correctamente
python -c "
import edge_tts; print('✓ edge-tts')
from pydub import AudioSegment; print('✓ pydub')
print('¡Todas las dependencias OK!')
"

# Ejecutar tests (desde la raíz del repositorio)
python -m pytest automontaje/tests -q
```

---

## Resolución de Problemas

### `ModuleNotFoundError: No module named 'audioop'`
**Causa**: Python 3.13+ eliminó el módulo `audioop`.
**Solución**: `pip install audioop-lts`

### `aiodns needs a SelectorEventLoop on Windows`
**Causa**: El event loop por defecto de Windows no es compatible con aiodns.
**Solución**: Ya está corregido en el código (`narracion.py` configura `WindowsSelectorEventLoopPolicy`).

### `RuntimeWarning: Couldn't find ffmpeg or avconv`
**Causa**: FFmpeg no está en el PATH del sistema.
**Solución**: Instalar FFmpeg y verificar con `ffmpeg -version`, o indicar los binarios con `AEGS_FFMPEG` y `AEGS_FFPROBE` (rutas completas). Todo AEGS, pydub incluido, usa esas rutas si están definidas.

### `ModuleNotFoundError: No module named 'whisper'`
**Causa**: Whisper no instalado (es una dependencia pesada).
**Solución**: `pip install -e "automontaje[subtitulos]"` (es opcional y pesado).
