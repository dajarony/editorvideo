# 📐 Historial de Diseño — AEGS

> Consolidación de todos los documentos de arquitectura (STDG) generados durante el diseño inicial del sistema.
> Fuente: archivos "# STDG - Mapa Global de Arquitectura*.txt" de la raíz del proyecto.

---

## Decisión 1 — Arquitectura en módulos independientes

**Fecha:** 2026-04-28 (diseño inicial)

El sistema se construyó como 6 módulos completamente independientes con contratos JSON entre ellos. Ningún módulo llama al siguiente directamente — el orquestador `main.py` los encadena.

```
Módulo 0  validador.py        → verifica el proyecto antes de procesar nada
Módulo 1  narracion.py        → genera MP3 por escena (Edge TTS)
Módulo 2  mezclador_audio.py  → mezcla voz + música con ducking
Módulo 3  montador_video.py   → monta clips con transiciones (FFmpeg)
Módulo 4  subtitulos.py       → subtítulos sincronizados (Whisper)
Módulo 5  main.py             → orquestador: ejecuta los módulos en orden
```

**Por qué:** si un módulo falla, el error es localizado. Puedes re-ejecutar desde cualquier fase sin repetir todo. Los módulos son testeables de forma independiente.

---

## Decisión 2 — JSON como contrato único

El archivo `proyecto.json` es la única interfaz entre el usuario y el sistema. No hay GUI, no hay argumentos complejos de línea de comandos para el contenido. Solo un JSON que describe el vídeo completo.

**Campos del contrato definidos desde el inicio:**

| Campo | Tipo | Obligatorio |
|-------|------|-------------|
| `titulo` | string | ✅ |
| `idioma` | string | ✅ |
| `narrador.voz` | string | ✅ |
| `narrador.velocidad` | string | No (default +0%) |
| `escenas[].id` | string | ✅ |
| `escenas[].clip` | string | ✅ |
| `escenas[].texto_narracion` | string | ✅ |
| `escenas[].pausa_antes_seg` | float | No (default 0) |
| `escenas[].transicion_entrada` | string | No (default cut) |
| `musica` | object | No |
| `subtitulos` | object | No |

---

## Decisión 3 — 4 ajustes técnicos críticos (diseño inicial)

Detectados antes de escribir código. Evitaron bugs graves:

### Ajuste 1 — FFprobe unificado
Una sola función `obtener_info_media(path)` en `utilidades.py`. Sin duplicar código de ffprobe en validador, narración y montaje. Todos usan la misma función y el mismo formato de salida.

### Ajuste 2 — WAV interno, AAC solo al final
Toda la mezcla de audio se hace en WAV (sin compresión, sin pérdida). Solo al exportar el MP4 final se comprime a AAC 192k. Esto evita acumulación de artefactos de compresión en el ducking.

### Ajuste 3 — Verificación post-generación TTS
Después de generar cada MP3, comprobar que:
1. El archivo existe en disco
2. Su duración es ≥ 0.5 segundos

Si falla → reintentar. Si falla otra vez → error controlado con mensaje claro.

### Ajuste 4 — Whisper usa MP3 limpio, no el audio mezclado
La música añade ruido y baja la precisión de Whisper al 30-40%. La solución: transcribir cada MP3 de narración individualmente (sin música) y luego sumar el offset matemático del timeline.

Resultado: subtítulos precisos al milisegundo, independientemente del volumen o tipo de música.

---

## Decisión 4 — Pipeline unidireccional estricto

El flujo nunca va hacia atrás. Si una fase falla, el sistema para completamente con código de salida 1 y un mensaje de error claro. No hay reintentos entre fases, no hay fallbacks silenciosos.

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fin
  ↓         ↓        ↓        ↓        ↓
Error?    Error?   Error?   Error?   Error?
  │         │        │        │        │
  └─────────┴────────┴────────┴────── sys.exit(1)
```

**Por qué:** un error en fase 2 con fase 3 ejecutada produce resultados inconsistentes y difíciles de debuggear. Mejor fallar rápido y limpio.

---

## Decisión 5 — Logging dual desde el inicio

Dos salidas de log desde el primer módulo:
- **Consola**: nivel INFO (lo que necesita ver el usuario)
- **Archivo** (`logs/proceso.log`): nivel DEBUG (todo, para debuggear)

El FileHandler se activa solo cuando se conoce la ruta del proyecto (en `main.py`, antes de ejecutar el pipeline).

---

## Decisión 6 — SUME DOCBLOCK en cada archivo

Cada archivo Python comienza con un bloque estándar que documenta:
- Tipo de módulo
- Dependencias
- Entradas esperadas
- Acciones que realiza
- Salidas que produce

Esto hace el código autoexplicativo sin necesidad de documentación externa para entender el rol de cada archivo.

---

## Evolución del sistema: v0.1.0 → v0.2.0

| Aspecto | v0.1.0 | v0.2.0 |
|---------|--------|--------|
| Caché TTS | No | ✅ SHA-1 |
| Reintentos TTS | 1 | 3 con backoff |
| Validación narrador | Solo voz | Dict completo + tipado |
| Validación clip_inicio | No | ✅ vs duración real |
| Transición crossfade | Falsa (dip-to-black) | ✅ xfade real |
| Check FFmpeg | No | ✅ al arranque |
| CLI | Solo ruta | argparse con 6 flags |
| SRT encoding | utf-8 | utf-8-sig (BOM Windows) |
| Modo sidecar | No | ✅ |
| pyproject.toml | No | ✅ |
| README en raíz | No | ✅ |
| Integración IA externa | No | ✅ Higgsfield MCP |

---

*Ver [ROADMAP.md](ROADMAP.md) para las mejoras planificadas.*
*Ver [CHANGELOG.md](CHANGELOG.md) para el historial completo de cambios.*
