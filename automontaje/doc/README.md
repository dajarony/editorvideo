# 🎬 AEGS — Sistema de Automontaje de Vídeo

> **A**utomated **E**diting & **G**eneration **S**ystem

Sistema automatizado de edición de vídeo basado en Python que transforma clips de vídeo, narración generada por IA y música de fondo en un producto audiovisual final con subtítulos incrustados.

---

## Índice de Documentación

| Documento | Descripción |
|-----------|-------------|
| [INSTALACION.md](INSTALACION.md) | Requisitos, instalación paso a paso, verificación |
| [GUIA_USO.md](GUIA_USO.md) | Cómo crear un proyecto y ejecutar el sistema |
| [CONTRATO_JSON.md](CONTRATO_JSON.md) | Referencia completa del formato `proyecto.json` |
| [ARQUITECTURA.md](ARQUITECTURA.md) | Diseño del sistema, módulos y flujo de datos |
| [API_MODULOS.md](API_MODULOS.md) | Documentación técnica de cada módulo y función |
| [TESTING.md](TESTING.md) | Suite de tests, cobertura y cómo ejecutar |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios y bugs corregidos |

---

## Descripción Rápida

El usuario define un proyecto en un archivo `proyecto.json` con:
- Clips de vídeo para cada escena
- Texto de narración por escena
- Configuración de música de fondo
- Opciones de transiciones y subtítulos

El sistema ejecuta automáticamente:

```
Validar → Narrar (TTS) → Mezclar Audio → Montar Vídeo → Subtitular
```

Y genera un vídeo final listo para publicar.

## Ejecución Rápida

```bash
pip install -e "automontaje[dev]"          # desde la raíz del repositorio
aegs /ruta/a/mi_proyecto/
```

Los subtítulos automáticos necesitan el extra opcional `subtitulos` (Whisper, que instala PyTorch).

## Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Lenguaje | Python 3.11+ |
| Narración | Edge TTS (Microsoft, gratuito) |
| Procesamiento de audio | PyDub |
| Procesamiento de vídeo | FFmpeg / FFprobe |
| Transcripción | OpenAI Whisper (opcional, extra `subtitulos`) |
| Testing | Pytest |
