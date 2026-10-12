# 🧪 Testing

## Ejecutar Tests

```bash
# Desde la raíz del repositorio
python -m pytest automontaje/tests -q

# Incluir los tests que llaman al servicio real de Edge TTS (necesitan red)
AEGS_TEST_INTERNET=1 python -m pytest automontaje/tests -q
```

Sin `AEGS_TEST_INTERNET=1`, los tests marcados `internet` aparecen como omitidos con su motivo. CI (`.github/workflows/ci.yml`) ejecuta la suite en Ubuntu con Python 3.12 y 3.13 sin esos tests.

### Solo un módulo específico

```bash
python -m pytest automontaje/tests/test_validador.py -v
python -m pytest automontaje/tests/test_montador.py -v
AEGS_TEST_INTERNET=1 python -m pytest automontaje/tests/test_narracion.py -v     # Requiere internet
```

---

## Suite de Tests

| Archivo | Tests | Módulo | Dependencias Externas |
|---------|-------|--------|----------------------|
| `test_utilidades.py` | 14 | Utilidades | Ninguna |
| `test_validador.py` | 17 | Módulo 0 | Ninguna |
| `test_configuracion_y_audio.py` | 12 | Config + Módulo 2 | PyDub |
| `test_montador.py` | 11 | Módulo 3 | Ninguna |
| `test_subtitulos.py` | 8 | Módulo 4 | Ninguna |
| `test_narracion.py` | 4 | Módulo 1 | Los 4 llaman a Edge TTS real: solo con `AEGS_TEST_INTERNET=1` |
| `test_contrato_edicion.py` | 7 | Contratos de edición | Ninguna |
| `test_editor_comandos.py` | 10 | Editor por comandos | Ninguna |
| `test_mejoras.py` | 5 | Mejoras | Ninguna |
| `test_entorno.py` | 14 | Dependencias, FFmpeg configurable, Whisper opcional, tests de internet | Ninguna |
| **Total** | **102** | | |

---

## Qué Se Testea

### Utilidades (7 tests)
- Logger se crea con nivel DEBUG
- Handler de consola presente
- FileHandler crea directorio y archivo
- ffprobe con archivo inexistente retorna error
- ffprobe con archivo inválido no crashea
- Limpieza de carpeta existente funciona
- Limpieza de carpeta inexistente no falla

### Validador (12 tests)
- Sin `proyecto.json` → error
- JSON con sintaxis inválida → error
- Campos obligatorios faltantes → error
- Escenas vacías → error
- IDs duplicados → error
- Sin texto de narración → error
- Texto muy corto → warning
- Clip inexistente → error
- Música inexistente → error
- Sin música → warning
- Voz desconocida → warning
- `clip_fin < clip_inicio` → error

### Configuración y Audio (12 tests)
- Lista de voces no vacía
- Voz AlvaroNeural existe
- Archivo proyecto es `.json`
- Constantes con valores correctos
- `lineal_a_db(1.0)` = 0 dB
- `lineal_a_db(0.5)` ≈ -6 dB
- `lineal_a_db(0.0)` = -120 dB (silencio)
- Rangos típicos de ducking correctos

### Montador (11 tests)
- Sin `duraciones.json` → FileNotFoundError
- Timeline calcula duraciones correctas
- Timeline se guarda en disco
- Duración total = suma de escenas
- Filtros contienen scale, fps, tpad
- `fade_from_black` → `fade=t=in`
- `fade_to_black` → `fade=t=out`
- `crossfade` → fades cortos
- `cut` → sin fades

### Subtítulos (7 tests)
- Conversión de 0.0s → `00:00:00,000`
- Conversión con milisegundos
- Conversión con minutos
- Conversión con horas
- Valores típicos de subtítulos
- Precisión al milisegundo

### Narración TTS (4 tests)
- Edge TTS genera archivo MP3 real (> 1KB)
- Velocidad `-5%` funciona
- Texto largo genera archivo más grande
- Sin ffprobe falla graciosamente (no crashea)

---

## Fixtures Compartidos

Definidos en `conftest.py`:

| Fixture | Descripción |
|---------|-------------|
| `proyecto_temp` | Crea proyecto temporal con JSON y estructura |
| `datos_proyecto_valido` | Devuelve el dict del JSON |
| `duraciones_fake` | Crea `narracion_duraciones.json` falso |

---

## Limitaciones Conocidas

- **Sin FFmpeg**: Los tests de módulos 2, 3, y 4 que ejecutan FFmpeg no se pueden probar sin la herramienta instalada.
- **Tests TTS**: Requieren conexión a internet activa.
- **Whisper**: No se testea directamente (dependencia pesada). La función `segundos_a_srt` se testea aislada.
