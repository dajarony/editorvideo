# 📋 Referencia del Contrato JSON

El archivo `proyecto.json` es la **única interfaz** del sistema. Define qué clips usar, qué narrar, cómo mezclar el audio y qué transiciones aplicar.

---

## Estructura Completa

```json
{
  "titulo": "string (obligatorio)",
  "idioma": "string (obligatorio, ej: 'es', 'en')",
  "estilo": "string (opcional, descriptivo)",
  "resolucion": "string (opcional, default: '1920x1080')",
  "fps": "number (opcional, default: 30)",
  "narrador": { ... },
  "musica": { ... },
  "transiciones": { ... },
  "subtitulos": { ... },
  "escenas": [ ... ]
}
```

---

## Campos Raíz

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `titulo` | string | ✅ | — | Título del proyecto |
| `idioma` | string | ✅ | — | Código ISO 639-1 (`es`, `en`, `pt`, `fr`) |
| `estilo` | string | ❌ | — | Descripción libre del estilo (documentativo) |
| `resolucion` | string | ❌ | `1920x1080` | Resolución del vídeo final |
| `fps` | number | ❌ | `30` | Frames por segundo del vídeo final |

---

## Objeto `narrador`

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `motor` | string | ❌ | `edge-tts` | `edge-tts` (voz real, necesita red) o `sintetico` (voz de **prueba** sin red: un tono por palabra, determinista, cuya duración crece con cada carácter del texto; para CI y para medir tiempos, no para publicar) |
| `voz` | string | ✅ con `edge-tts` | — | Nombre de la voz Edge TTS (no se usa con `sintetico`) |
| `velocidad` | string | ❌ | `+0%` | Ajuste de velocidad (`-5%`, `+10%`, etc.) |
| `volumen` | string | ❌ | `+0%` | Ajuste de volumen |

---

## Objeto `musica`

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `fuente` | string | ✅ | — | Siempre `"archivo"` |
| `archivo` | string | ✅ | — | Ruta relativa al MP3 de música |
| `volumen_base` | number | ❌ | `0.30` | Volumen cuando NO hay voz (0.0–1.0) |
| `volumen_durante_voz` | number | ❌ | `0.08` | Volumen cuando HAY voz — ducking (0.0–1.0) |
| `fade_in_segundos` | number | ❌ | `2.0` | Duración del fade-in al inicio |
| `fade_out_segundos` | number | ❌ | `2.0` | Duración del fade-out al final |

### Cómo Funciona el Ducking

```
Volumen
  0.30 ───────╲          ╱───────╲          ╱────────
               ╲ 200ms  ╱         ╲ 200ms  ╱
  0.08          ╲──────╱           ╲──────╱
                 [VOZ]               [VOZ]
```

La transición entre `volumen_base` y `volumen_durante_voz` es suavizada con un fade de 200ms (configurable en `configuracion.py` como `FADE_DUCK_MS`).

---

## Objeto `subtitulos`

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `generar` | boolean | ✅ | `false` | Activar/desactivar subtítulos |
| `fuente` | string | ❌ | `Arial` | Familia de fuente para los subtítulos |
| `tamano` | number | ❌ | `24` | Tamaño del texto en píxeles |
| `color` | string | ❌ | `white` | Color del texto |
| `borde` | string | ❌ | `black` | Color del borde |
| `posicion` | string | ❌ | `bottom` | Posición en pantalla |

---

## Objeto `transiciones`

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `tipo_default` | string | ❌ | `crossfade` | Transición por defecto |
| `duracion_default_segundos` | number | ❌ | `1.5` | Duración del efecto |

---

## Array `escenas[]`

Cada escena es un objeto con:

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `id` | string | ✅ | — | Identificador único (sin espacios) |
| `clip` | string | ✅ | — | Ruta relativa al clip de vídeo |
| `texto_narracion` | string | ✅ | — | Texto que el narrador dirá |
| `clip_inicio_seg` | number | ❌ | `0` | Segundo donde empieza el recorte |
| `clip_fin_seg` | number | ❌ | `null` | Segundo donde termina (null = hasta el final) |
| `pausa_antes_seg` | number | ❌ | `0` | Silencio antes de la narración |
| `pausa_despues_seg` | number | ❌ | `0` | Silencio después de la narración |
| `transicion_entrada` | string | ❌ | `cut` | Efecto visual al entrar |
| `transicion_salida` | string | ❌ | `cut` | Efecto visual al salir |

### Duración de una Escena

La duración de cada escena se calcula automáticamente:

```
duracion_escena = pausa_antes + duracion_narracion + pausa_despues
```

Si el clip es más corto que la duración necesaria, el sistema congela el último frame. Si es más largo, lo recorta.

Con `montaje.duracion_estricta` (o `--duracion-estricta`) no hace ninguna de las dos cosas: si un clip no dura lo que su escena (±1 fotograma), el montaje falla con un error que nombra la escena y las dos duraciones. Es el modo de **narración primero** de Aura Motion Studio: se mide la voz (`--solo-narracion`), se renderiza cada animación a esa medida y se monta sin tocarla. Con `--solo-narracion` los clips aún pueden no existir (solo se avisa); en el montaje estricto, una escena sin entrada en `narracion_duraciones.json` también es un error. Cada escena ocupa `round(fin × fps) − round(inicio × fps)` fotogramas de una rejilla acumulada (.5 se redondea hacia arriba), así que el total no deriva aunque haya muchas escenas. Se mide la pista de vídeo del clip, no la del contenedor, y un clip sin pista de vídeo es un error.

### Transiciones Soportadas

| Valor | Efecto |
|-------|--------|
| `cut` | Corte directo (sin efecto) |
| `fade_from_black` | Aparece gradualmente desde negro |
| `fade_to_black` | Desaparece gradualmente a negro |
| `crossfade` | Dip-to-black: fade out rápido + fade in rápido |

---

## Objeto `montaje`

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `duracion_estricta` | boolean | ❌ | `false` | Cada clip debe durar exactamente lo que su escena (±1 fotograma); si no, error en vez de recortar o congelar. Solo admite transiciones `cut`: un fundido solaparía escenas y cambiaría la duración total. |

---

## Ejemplo Completo

```json
{
  "titulo": "El Poder del Silencio",
  "idioma": "es",
  "resolucion": "1920x1080",
  "fps": 30,
  "narrador": {
    "voz": "es-ES-AlvaroNeural",
    "velocidad": "-5%"
  },
  "musica": {
    "fuente": "archivo",
    "archivo": "musica/ambient_piano.mp3",
    "volumen_base": 0.30,
    "volumen_durante_voz": 0.08,
    "fade_in_segundos": 3.0,
    "fade_out_segundos": 5.0
  },
  "subtitulos": {
    "generar": true,
    "fuente": "Arial",
    "tamano": 24
  },
  "escenas": [
    {
      "id": "intro",
      "clip": "clips/intro.mp4",
      "texto_narracion": "En un mundo lleno de ruido...",
      "pausa_antes_seg": 2.0,
      "pausa_despues_seg": 1.5,
      "transicion_entrada": "fade_from_black",
      "transicion_salida": "crossfade"
    },
    {
      "id": "cierre",
      "clip": "clips/cierre.mp4",
      "texto_narracion": "El silencio no es vacío. Es espacio.",
      "pausa_antes_seg": 1.0,
      "pausa_despues_seg": 3.0,
      "transicion_entrada": "crossfade",
      "transicion_salida": "fade_to_black"
    }
  ]
}
```
