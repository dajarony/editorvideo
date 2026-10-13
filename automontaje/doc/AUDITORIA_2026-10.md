# Auditoría de AEGS — octubre de 2026

Primera fase (F1) del plan para conectar AEGS con **Aura Motion Studio** (`dajarony/skilss-animacion`). Decisiones del usuario: la **narración manda en los tiempos** (se genera y mide la voz primero y la animación se renderiza a esa medida), AEGS se usa como **dependencia fijada** a un commit y los dos repositorios conservan su historial.

## Qué se ejecutó de verdad

| Qué | Dónde | Resultado |
| --- | --- | --- |
| Suite completa antes de tocar nada | Windows 11, Python 3.15, venv con `edge-tts`, `pydub`, `audioop-lts`, `pytest` | 85 pasan y **3 fallan**, los tres de Edge TTS real (`test_narracion.py`). En el log: dos `ConnectionResetError: [WinError 10054]` y dos `WSServerHandshakeError: 403`, es decir, **el propio servicio de Microsoft rechazó la conexión**, no solo un corte de red. |
| Mismo arranque sin carpeta temporal propia | Igual | 33 errores de entorno, todos `PermissionError: [WinError 5] Access is denied` sobre `%LOCALAPPDATA%\Temp\pytest-of-<usuario>`; con `--basetemp` dentro del repo desaparecen. *Observado en la sesión de auditoría; sin log guardado.* |
| `pip install -e automontaje` | venv limpio | **Fallaba**: `error: Multiple top-level packages discovered in a flat-layout: ['modulos', 'plantillas'].` Con el `pyproject.toml` original, setuptools no puede construir el paquete. *Observado en la sesión de auditoría; sin log guardado; se reproduce con cualquier commit anterior a F1.* |
| Suite después de F1 | Windows 11, Python 3.15 | **100 pasan y 4 se omiten** (los 4 de Edge TTS real, solo con `AEGS_TEST_INTERNET=1`); 2,7 s en vez de 18 s, porque ya no espera reintentos contra el servicio. |
| Instalación mínima después de F1 | venv limpio, `pip install -e "automontaje[dev]"` | Salida abajo (literal, filtrada a los paquetes relevantes). |
| CI | GitHub Actions, Ubuntu, Python 3.12 y 3.13, FFmpeg de apt | Disparado por el PR [dajarony/editorvideo#1](https://github.com/dajarony/editorvideo/pull/1) (el workflow corre en PRs y en `main`). Primer run [38312664839](https://github.com/dajarony/editorvideo/actions/runs/38312664839): success, 96 pasan y 3 se omiten. Run [38313546316](https://github.com/dajarony/editorvideo/actions/runs/38313546316) (commit `5ff48e2`): success, 98 pasan y 4 se omiten. Run con el código de cierre de F1 [38314082781](https://github.com/dajarony/editorvideo/actions/runs/38314082781) (commit `a79f622`): **success** en los dos Python, **100 pasan y 4 se omiten** con su motivo (incluido el test de la ruta relativa de FFmpeg, que es en Linux donde importa), y la comprobación de que no hay `torch` ni `whisper` en verde. |

Instalación mínima en un venv limpio (líneas literales de la salida, filtradas a los paquetes relevantes; la ruta local se sustituye por `<repo>`):

```text
$ pip install -e "automontaje[dev]"
--- pip list (filtrado)
aegs-automontaje  0.2.0     <repo>\automontaje
edge-tts          7.2.8
pydub             0.25.1
pytest            9.1.1
--- torch/whisper: []
--- aegs --help (desde fuera del repo)
usage: aegs [-h] [--skip-subs] [--skip-tts] [--no-cache] [--keep-temp]
            [--srt-sidecar] [-v]
```

## Qué NO se ejecutó

- **Edge TTS real**: el servicio respondió 403 en esta auditoría. Los 4 tests siguen ahí y se activan con `AEGS_TEST_INTERNET=1`. Para el flujo "narración primero" con voz real habrá que comprobar si el servicio acepta las peticiones desde este equipo o buscar alternativa; para CI y pruebas se usará una voz sintética offline (fase F3a).
- **Whisper** (subtítulos), **Demucs** (aislar voz) y **Real-ESRGAN** (superresolución): dependencias pesadas que no se instalaron.
- **Interfaz gráfica** (`interfaz.py`) y **editor de mejoras** (`mejorar_video.py`): fuera del alcance de la integración.
- **Un montaje completo de extremo a extremo** con vídeo real: llega en las fases F4–F6 del plan.

## Defectos encontrados y corregidos en F1

1. **El paquete no se podía instalar** (ver arriba). `pyproject.toml` declara ahora `py-modules = ["main", "configuracion"]` y `packages = ["modulos"]`.
2. **La instalación arrastraba PyTorch** (varios GB) por `openai-whisper`, que solo usan los subtítulos del automontaje. Pasa al extra opcional `subtitulos`; sin él, pedir subtítulos falla con `pip install "automontaje[subtitulos]"` en el mensaje.
3. **La suite dependía de internet**: 4 tests llaman al servicio de Microsoft. Uno de ellos (`test_genera_audio_sin_ffprobe_falla_graciosamente`) decía usar un mock que no existe y pasaba siempre porque su aserción no comprobaba nada, tras 12 s de reintentos. Los 4 llevan ahora la marca `internet` y se omiten con motivo visible salvo con `AEGS_TEST_INTERNET=1`.
4. **FFmpeg solo podía venir del PATH**, con unas 30 llamadas repartidas por seis módulos (y pydub por su cuenta). Ahora todas pasan por `utilidades.binario()`, que respeta `AEGS_FFMPEG` y `AEGS_FFPROBE` y las devuelve como ruta absoluta (una relativa fallaría en Linux cuando ffmpeg se ejecuta con otro directorio de trabajo, como en el montaje); pydub las usa solo si están definidas (sin ellas no cambia nada). Una ruta mala o no ejecutable da un error claro.
5. **`TESTING.md` estaba desactualizado**: decía 53 tests y había 88.

## Pendiente, fuera del alcance de F1

- La herramienta de subtítulos del **editor de mejoras** (`mejoras.py`, `anadir_subtitulos_automaticos`) usa otra librería, `faster-whisper`, y su mensaje recomienda `pip install faster-whisper`. No se ha unificado con el extra `subtitulos` del automontaje.
- La falta de Whisper solo se detecta en la fase 4, después de narrar, mezclar y montar.

## El conflicto de tiempos con la animación

En el montaje actual (`montador_video.py`):

```text
duracion_escena = pausa_antes + duracion_narracion + pausa_despues
```

Si el clip dura **más**, se recorta; si dura **menos**, se congela su último fotograma (`tpad=stop_mode=clone`). Con un clip de Motion Canvas eso corta la animación a medias o la deja parada. Además, las transiciones `crossfade` solapan escenas y cambian la duración total.

Solución acordada (fase F3a): **narración primero**. AEGS genera y mide la voz (`--solo-narracion`), Aura Motion Studio renderiza cada escena exactamente a esa duración, y AEGS monta con `--duracion-estricta`, que falla en vez de recortar o congelar y solo admite cortes secos.

## Evidencia de F3a — C7: instalación desde una rueda

Rueda construida con el código de cierre de F3a (el mismo árbol que pasa el último gate de la fase; se rehace en cada intento que toca el código), instalada en un venv limpio de Python 3.15 en una carpeta temporal **fuera del repositorio**; `aegs` se ejecuta desde allí. Salida literal; solo se sustituyen la ruta del repositorio por `<repo>` y la de la carpeta temporal por `<tmp>`. `ok` y `exit=` los imprime el propio script de la prueba (el código de salida de `aegs` se capturó sin tuberías por medio). El aviso de pydub (`Couldn't find ffmpeg`) lo emite pydub al importarse, antes de que AEGS le indique `AEGS_FFMPEG`/`AEGS_FFPROBE`; sale en las dos órdenes y no impide nada: la segunda valida, narra y escribe las duraciones con exit 0.

```text
$ python -m venv venv-wheel   # cwd: carpeta temporal fuera del repositorio
ok
$ venv-wheel/Scripts/python -m pip wheel <repo>/automontaje --no-deps -w dist -q
aegs_automontaje-0.2.0-py3-none-any.whl
$ venv-wheel/Scripts/python -m pip install dist/*.whl -q
$ venv-wheel/Scripts/python -m pip list | grep -iE "aegs|edge|torch|whisper"
aegs-automontaje  0.2.0
edge-tts          7.2.8
$ venv-wheel/Scripts/aegs --help
<tmp>\venv-wheel\Lib\site-packages\pydub\utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
  warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)
usage: aegs [-h] [--skip-subs] [--skip-tts] [--no-cache] [--keep-temp]
            [--srt-sidecar] [--solo-narracion] [--duracion-estricta] [-v]
            ruta_proyecto

AEGS — Sistema de Automontaje de Vídeo. Convierte un proyecto.json en un vídeo final con narración, música y subtítulos.

positional arguments:
  ruta_proyecto        Ruta a la carpeta que contiene proyecto.json

options:
  -h, --help           show this help message and exit
  --skip-subs          Omite la fase de subtítulos aunque el JSON los pida.
  --skip-tts           No regenera narraciones; usa solo lo que ya hay en
                       disco.
  --no-cache           Ignora la caché TTS y fuerza regenerar todas las voces.
  --keep-temp          Conserva la carpeta de clips temporales tras
                       renderizar.
  --srt-sidecar        Genera SRT pero NO lo quema en el vídeo (modo sidecar).
  --solo-narracion     Valida y genera la narración
                       (narracion_duraciones.json) y se detiene, sin montar
                       vídeo. Los clips aún pueden no existir.
  --duracion-estricta  Cada clip debe durar lo que su escena (±1 fotograma):
                       si no, falla en vez de recortarlo o congelarlo. Solo
                       admite transiciones 'cut'.
  -v, --verbose        Logging detallado en consola.

Ejemplos:
  python main.py ./mi_video/
  python main.py ./mi_video/ --skip-subs
  python main.py ./mi_video/ --no-cache --keep-temp
exit=0
$ venv-wheel/Scripts/aegs demo --solo-narracion   # motor "sintetico", sin clips; AEGS_FFMPEG/AEGS_FFPROBE definidas
<tmp>\venv-wheel\Lib\site-packages\pydub\utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
  warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)
2026-10-13 00:00:00 [INFO] ╔═══════════════════════════════════════════════════════╗
2026-10-13 00:00:00 [INFO] ║     AEGS — SISTEMA DE AUTOMONTAJE DE VÍDEO          ║
2026-10-13 00:00:00 [INFO] ║  Proyecto: demo                                      ║
2026-10-13 00:00:00 [INFO] ╚═══════════════════════════════════════════════════════╝
2026-10-13 00:00:01 [INFO]   ✓ FFmpeg detectado: ffmpeg version N-92722-gf22fcd4483 Copyright (c) 2000-2018 t
2026-10-13 00:00:01 [INFO] 
2026-10-13 00:00:01 [INFO] ━━━ FASE 0: Verificando integridad del proyecto ━━━
2026-10-13 00:00:01 [INFO] Validación completada: 1 escenas, 2 warnings, 0 errores.
2026-10-13 00:00:01 [WARNING]   ⚠ Clip inválido o ausente en 'hola': Archivo no encontrado: <tmp>\demo\clips\hola.mp4
2026-10-13 00:00:01 [WARNING]   ⚠ No se definió sección 'musica'. El vídeo se montará solo con narración.
2026-10-13 00:00:01 [INFO]   ✓ Proyecto validado correctamente.
2026-10-13 00:00:01 [INFO] 
2026-10-13 00:00:01 [INFO] ━━━ FASE 1: Generando narración (sintetico) ━━━
2026-10-13 00:00:01 [INFO]   ✓ Narración sintética 'hola' (2.540s)
2026-10-13 00:00:01 [INFO] Duraciones guardadas en narracion_duraciones.json
2026-10-13 00:00:01 [INFO] 
2026-10-13 00:00:01 [INFO]   --solo-narracion: duraciones en output/narracion_duraciones.json. Sin montaje.
exit=0
$ cat demo/output/narracion_duraciones.json
{
  "hola": {
    "archivo": "output/narracion/hola.wav",
    "duracion_real_seg": 2.54
  }
}
```

La misma instalación desde Git (`pip install "aegs-automontaje @ git+https://github.com/dajarony/editorvideo@<commit>#subdirectory=automontaje"`) se probó también con el commit `d3dba46` (WIP de F3a): `aegs --help` mostraba las dos opciones nuevas y no se instalaron `torch` ni `whisper`. *Esa salida no se guardó; la evidencia de C7 es la de la rueda.*
