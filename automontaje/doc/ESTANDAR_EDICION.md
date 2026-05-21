# 🎬 Estándar de Edición AEGS

> Guía de referencia para crear montajes fluidos y profesionales con el sistema AEGS.
> Basado en la experiencia del proyecto "El Pliegue Perfecto" y las correcciones realizadas.

---

## 📐 Reglas de Edición

### Regla 1 — Duración exacta
Cada clip debe durar exactamente lo que dura su narración (pausa_antes + voz + pausa_despues).
No más, no menos. Si el clip es más corto, haz loop. Si es más largo, recórtalo con `clip_fin_seg`.

### Regla 2 — Vídeo real en momentos de acción
Los momentos de acción, tensión o cambio deben usar clips de vídeo real.
Las imágenes estáticas se reservan para momentos reflexivos o de voz en off tranquila.

### Regla 3 — Pan suave en imágenes estáticas
Nunca usar zoom en imágenes estáticas — produce temblor (jitter).
Usar siempre pan horizontal o vertical con escala máxima del 20%:
- `pan_right` / `pan_left` → escala al 120% del ancho
- `pan_up` / `pan_down` → escala al 120% del alto

### Regla 4 — Transiciones estándar
```
Inicio del vídeo  → fade_from_black
Entre escenas     → crossfade (0.7s)
Final del vídeo   → fade_to_black
```
No mezclar tipos de transición sin motivo. La consistencia crea ritmo.

### Regla 5 — Música siempre presente
La música nunca para. Solo baja cuando habla el narrador (ducking automático).
- `volumen_base`: 0.35–0.45 (se escucha en silencios)
- `volumen_durante_voz`: 0.08–0.12 (casi desaparece bajo la voz)
- `fade_in_segundos`: 3.0–4.0
- `fade_out_segundos`: 4.0–6.0

---

## 🎥 Estructura recomendada por duración de vídeo

### Vídeo corto (1–2 minutos)
| Elemento | Cantidad recomendada |
|----------|---------------------|
| Escenas totales | 4–6 |
| Clips de vídeo real | 2–3 (momentos clave) |
| Imágenes con pan | 2–3 (reflexión, contexto) |
| Duración narración por escena | 10–20s |

### Vídeo medio (2–4 minutos) — como El Pliegue Perfecto
| Elemento | Cantidad recomendada |
|----------|---------------------|
| Escenas totales | 8–12 |
| Clips de vídeo real | 5–8 (mínimo 1 por acto) |
| Imágenes con pan | 4–6 |
| Duración narración por escena | 10–25s |

### Documental largo (5–10 minutos)
| Elemento | Cantidad recomendada |
|----------|---------------------|
| Escenas totales | 15–25 |
| Clips de vídeo real | 12–18 |
| Imágenes con pan | 6–10 |
| Duración narración por escena | 15–30s |

---

## 📦 Especificaciones técnicas recomendadas

```json
{
  "resolucion": "1280x720",
  "fps": 30,
  "narrador": {
    "voz": "es-ES-AlvaroNeural",
    "velocidad": "-5%"
  },
  "musica": {
    "volumen_base": 0.40,
    "volumen_durante_voz": 0.10,
    "fade_in_segundos": 4.0,
    "fade_out_segundos": 5.0
  },
  "subtitulos": {
    "tamano": 26,
    "color": "white",
    "borde": "black",
    "posicion": "bottom"
  }
}
```

> Para YouTube/redes sociales usar `1920x1080`. Para pruebas y renders rápidos usar `1280x720`.

---

## 🔁 Cómo manejar clips cortos (loop)

Si un clip de vídeo dura menos que su narración, hacer loop antes de pasarlo a AEGS:

```bash
ffmpeg -stream_loop -1 -i clip_original.mp4 -t DURACION_NECESARIA \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -g 60 -an clip_looped.mp4
```

Regla de oro: **ningún clip debe requerir extensión de más de 3 segundos**.
Si necesita más, hacer loop o buscar un clip más largo.

---

## 🖼️ Cómo convertir imágenes estáticas a clips (Ken Burns sin jitter)

```bash
# Pan derecha (el más natural para imágenes panorámicas)
ffmpeg -loop 1 -i imagen.png \
  -vf "scale=1536:720,crop=1280:720:x='min(256*t/DURACION,255)':y=0,setsar=1,fps=30" \
  -t DURACION -r 30 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -g 60 clip.mp4

# Pan izquierda
ffmpeg -loop 1 -i imagen.png \
  -vf "scale=1536:720,crop=1280:720:x='max(256-256*t/DURACION,0)':y=0,setsar=1,fps=30" \
  -t DURACION -r 30 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -g 60 clip.mp4

# Pan arriba
ffmpeg -loop 1 -i imagen.png \
  -vf "scale=1280:864,crop=1280:720:x=0:y='min(144*t/DURACION,143)',setsar=1,fps=30" \
  -t DURACION -r 30 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -g 60 clip.mp4

# Pan abajo
ffmpeg -loop 1 -i imagen.png \
  -vf "scale=1280:864,crop=1280:720:x=0:y='max(144-144*t/DURACION,0)',setsar=1,fps=30" \
  -t DURACION -r 30 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -g 60 clip.mp4
```

**Nunca usar `zoompan`** — produce jitter/temblor inevitable en imágenes estáticas.

---

## 🎙️ Voces recomendadas en español

| Voz | Perfil | Mejor para |
|-----|--------|-----------|
| `es-ES-AlvaroNeural` | Grave, reflexivo | Documentales, narración seria |
| `es-ES-ElviraNeural` | Clara, neutral | Tutoriales, explicaciones |
| `es-MX-JorgeNeural` | Cálido, accesible | Vídeos divulgativos |
| `es-AR-TomasNeural` | Dinámico | Noticias, reportajes |

Velocidad recomendada para narración documental: `-3%` a `-5%`

---

## ⚡ Checklist antes de lanzar AEGS

- [ ] Todos los clips tienen duración mayor o igual a su narración
- [ ] Las imágenes están convertidas a MP4 con pan (no zoom)
- [ ] La música dura más que el vídeo completo (o AEGS la hace loop)
- [ ] `clip_fin_seg: null` en clips que se usan enteros
- [ ] `clip_inicio_seg` y `clip_fin_seg` correctos en clips recortados
- [ ] Al menos 1 escena con `fade_from_black` al inicio
- [ ] Al menos 1 escena con `fade_to_black` al final

---

## 🎬 Estándar de clips por proyecto

Para un montaje fluido **sin loops visibles**, la regla es:

| Duración del vídeo | Clips de vídeo real mínimos | Imágenes con pan máx |
|--------------------|-----------------------------|----------------------|
| 1–2 minutos | 4–5 | 3 |
| 2–4 minutos | 8–10 | 5 |
| 5–10 minutos | 15–18 | 8 |

**Estándar recomendado para canal YouTube**: **10 clips de vídeo real** por vídeo de 3 minutos.
Cada clip debe tener al menos la duración de su narración — sin necesidad de loop.

---

## 📺 Viñeta de canal para YouTube

Una viñeta (o bumper) es la marca visual del canal. Hay dos tipos:

### Tipo 1 — Intro animada (inicio del vídeo, 3–5 segundos)

Aparece antes de que empiece el contenido. Crea identidad de canal.

**Estructura recomendada:**
```
0.0s → Fade from black
0.5s → Título del canal aparece (texto grande, centrado)
1.5s → Subtítulo o eslogan (texto pequeño)
3.0s → Fade to black → arranca el vídeo
```

**Cómo integrarlo en AEGS** — añadir como primera escena sin narración:
```json
{
  "id": "00_intro_canal",
  "clip": "clips/vineta_intro.mp4",
  "clip_inicio_seg": 0,
  "clip_fin_seg": 4,
  "texto_narracion": " ",
  "pausa_antes_seg": 0,
  "pausa_despues_seg": 0,
  "transicion_entrada": "fade_from_black",
  "transicion_salida": "crossfade"
}
```

**Generar la viñeta con FFmpeg (solo texto, sin clip externo):**
```bash
ffmpeg -f lavfi -i color=c=black:size=1280x720:duration=4:rate=30 \
  -vf "drawtext=text='NOMBRE DEL CANAL':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2-30:enable='between(t,0.5,3.5)',
       drawtext=text='Subtítulo o eslogan':fontcolor=gray:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40:enable='between(t,1.0,3.5)',
       fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5" \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p vineta_intro.mp4
```

---

### Tipo 2 — Outro / End card (últimos 10 segundos)

Aparece al final del vídeo. Sirve para retener al espectador en el canal.

**Estructura recomendada:**
```
0.0s → Fade from black (o crossfade desde última escena)
1.0s → "¿Te ha gustado el vídeo?" (texto)
2.5s → "Suscríbete al canal" (texto grande)
5.0s → Nombre del canal + redes sociales
8.0s → Fade to black
```

**Cómo integrarlo en AEGS** — añadir como última escena:
```json
{
  "id": "99_outro",
  "clip": "clips/vineta_outro.mp4",
  "clip_inicio_seg": 0,
  "clip_fin_seg": 10,
  "texto_narracion": " ",
  "pausa_antes_seg": 0,
  "pausa_despues_seg": 0,
  "transicion_entrada": "crossfade",
  "transicion_salida": "fade_to_black"
}
```

**Generar el outro con FFmpeg:**
```bash
ffmpeg -f lavfi -i color=c=black:size=1280x720:duration=10:rate=30 \
  -vf "drawtext=text='¿Te ha gustado?':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=200:enable='between(t,1,9)',
       drawtext=text='SUSCRÍBETE':fontcolor=yellow:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2-20:enable='between(t,2.5,9)',
       drawtext=text='NOMBRE DEL CANAL':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+80:enable='between(t,5,9)',
       fade=t=in:st=0:d=0.8,fade=t=out:st=9:d=1.0" \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p vineta_outro.mp4
```

---

### Tipo 3 — Viñeta visual (efecto cinematográfico)

Borde oscuro suave alrededor del frame en todas las escenas. Da un look de cine.
Se puede aplicar a nivel de proyecto en FFmpeg con:

```
vignette=PI/4
```

> Esta mejora está planificada en la **Fase E del roadmap** (efectos visuales por escena).

---

## 📋 Estructura completa de proyecto con viñeta

```
proyecto/
├── proyecto.json
├── clips/
│   ├── vineta_intro.mp4        ← 4s intro del canal
│   ├── escena_01.mp4
│   ├── escena_02.mp4
│   ├── ...
│   ├── escena_10.mp4
│   └── vineta_outro.mp4        ← 10s end card
├── musica/
│   └── fondo.mp3
└── output/
    └── video_final.mp4         ← listo para subir
```

**Total clips recomendado**: 10 escenas + 1 intro + 1 outro = **12 clips por vídeo**

---

## ✅ Checklist antes de lanzar AEGS

- [ ] Todos los clips tienen duración mayor o igual a su narración
- [ ] Las imágenes están convertidas a MP4 con pan (no zoom)
- [ ] La música dura más que el vídeo completo (o AEGS la hace loop)
- [ ] `clip_fin_seg: null` en clips que se usan enteros
- [ ] `clip_inicio_seg` y `clip_fin_seg` correctos en clips recortados
- [ ] Primera escena con `fade_from_black` (o viñeta intro)
- [ ] Última escena con `fade_to_black` (o viñeta outro)
- [ ] Viñeta intro incluida como escena 00
- [ ] Outro incluido como escena 99

---

*Documento generado el 2026-05-01 basado en la producción de "El Pliegue Perfecto".*
*Ver [ROADMAP.md](ROADMAP.md) para las mejoras planificadas (Fase C: imágenes nativas, Fase H: intro/outro automáticos).*
