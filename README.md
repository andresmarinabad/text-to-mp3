# Epub to Audiobook

Convierte libros EPUB a audiolibros M4B con marcadores de capítulo usando **Microsoft Edge TTS** — voz neuronal gratuita, sin API key.

## Requisitos

```bash
nix develop    # activa el entorno (Python 3.11, epub2tts-edge, ffmpeg, espeak-ng)
```

## Uso

```bash
# 1. Extraer texto del EPUB
epub2tts-edge libro.epub

# 2. Editar libro.txt (opcional)
#    - Primera línea:  Title: Título
#    - Segunda línea:  Author: Autor
#    - Capítulos:      # Capítulo 1
#    - Eliminar índices, notas legales, etc.
#
#    fix_parts.py reemplaza marcadores # Part N con títulos reales del índice:
python3 fix_parts.py libro.txt

# 3. Generar M4B con marcadores de capítulo
epub2tts-edge libro.txt --cover libro.png --speaker es-ES-AlvaroNeural
```

## Voces disponibles

Algunas voces en español:

| Voz | Género | Variante |
|---|---|---|
| `es-ES-AlvaroNeural` | M | España |
| `es-ES-ElviraNeural` | F | España |
| `es-MX-JorgeNeural` | M | México |
| `es-MX-DaliaNeural` | F | México |
| `es-AR-TomasNeural` | M | Argentina |
| `es-AR-ElenaNeural` | F | Argentina |

```bash
# Ver todas las voces disponibles
edge-tts --list-voices | grep es-
```
