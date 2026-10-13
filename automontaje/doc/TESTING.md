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
| `test_entorno.py` | 16 | Dependencias, FFmpeg configurable, Whisper opcional, tests de internet | Ninguna |
| `test_integracion_aura.py` | 25 (33 casos con los parámetros) | Narración primero: voz sintética, `--solo-narracion`, duración estricta | FFmpeg para 16 casos (se omiten con motivo si no está) |
| **Total** | **129** (137 casos) | | |

---

## Qué Se Testea

### Utilidades (14 tests; algunos ejemplos)
- Logger se crea con nivel DEBUG
- Handler de consola presente
- FileHandler crea directorio y archivo
- ffprobe con archivo inexistente retorna error
- ffprobe con archivo inválido no crashea
- Limpieza de carpeta existente funciona
- Limpieza de carpeta inexistente no falla

### Validador (17 tests; algunos ejemplos)
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

### Subtítulos (8 tests; algunos ejemplos)
- Conversión de 0.0s → `00:00:00,000`
- Conversión con milisegundos
- Conversión con minutos
- Conversión con horas
- Valores típicos de subtítulos
- Precisión al milisegundo

### Entorno (16 tests, `test_entorno.py`)
- `openai-whisper` no es dependencia obligatoria y está en el extra `subtitulos`; `pytest` en `dev`
- Sin `AEGS_TEST_INTERNET` se omiten los 4 tests de Edge TTS y ninguno queda sin la marca `internet`
- `binario()`: sin variables usa el PATH; `AEGS_FFMPEG`/`AEGS_FFPROBE` tienen prioridad y se devuelven como ruta absoluta; ruta inexistente o nombre desconocido dan error claro
- Una ruta relativa sigue funcionando aunque ffmpeg se ejecute en otra carpeta (`cwd`)
- `obtener_info_media` usa la variable y, si está mal, devuelve su error en vez de lanzar una excepción
- Ningún módulo ni `main.py` llama a ffmpeg/ffprobe sin pasar por `binario()`
- pydub usa las variables solo si están definidas; sin ellas no cambia nada
- Sin Whisper, los subtítulos fallan con `pip install "automontaje[subtitulos]"` en el mensaje

### Integración con Aura Motion Studio (25 tests, `test_integracion_aura.py`)
- Voz sintética: mismo texto y velocidad dan el mismo SHA-256; cada carácter alarga la narración (también a `+50%`); más velocidad, menos duración; velocidad mal formada es un error controlado; no usa Edge TTS
- Validación: motor desconocido o que no es texto; `escenas` mal tipadas en modo estricto dan error, no excepción; con duración estricta solo se admite `cut`; sin ella `crossfade` sigue valiendo; con `requiere_clips=False` un clip ausente es aviso y lo demás se sigue validando
- Flujo real con FFmpeg: `--solo-narracion` sin clips todavía; `--solo-narracion --skip-tts` se rechaza; clips a medida dan la suma de las escenas (±1 fotograma), también con 10 escenas que no caen en un fotograma exacto (sin deriva acumulada); un clip 1 s más largo o más corto falla, nombra la escena y las dos duraciones y no deja `video_final.mp4` (ni el de una ejecución anterior, tampoco si falla la validación); un clip con el vídeo 1 s más corto pero el audio hasta el final también falla (no se congela); el flag `--duracion-estricta` activa el modo; `montar_video_proyecto` funciona con una ruta de proyecto relativa
- Borde de la tolerancia en `calcular_timeline`: ±1 fotograma pasa, ±2 fallan; la rejilla redondea .5 hacia arriba; un clip sin pista de vídeo falla; una escena sin narración falla en modo estricto y se omite sin él

### Narración TTS (4 tests, todos con red: `AEGS_TEST_INTERNET=1`)
- Edge TTS genera archivo MP3 real (> 1KB)
- Velocidad `-5%` funciona
- Texto largo genera archivo más grande
- Sin ffprobe no rompe la ejecución (ojo: su aserción solo comprueba que `exito` sea booleano, no qué ocurre; ver la auditoría)

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
