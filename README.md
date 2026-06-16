# epub2audiobook

[![Tests](https://github.com/andresmarinabad/epub-to-audiobook/actions/workflows/ci-tests.yml/badge.svg?branch=main)](https://github.com/andresmarinabad/epub-to-audiobook/actions/workflows/ci-tests.yml)

Convierte archivos EPUB en audiolibros M4B chaptered usando Microsoft Edge TTS con **procesamiento paralelo de capítulos** y una interfaz web moderna.

## Características

- **Paralelo**: cada capítulo se convierte en un worker Celery independiente (`nproc - 2` workers)
- **Cola de mensajes**: Redis + Celery como broker de tareas (chord/group para orquestación)
- **Progreso en tiempo real**: Server-Sent Events (SSE) — barra por capítulo + barra general con cronómetro durante el merge
- **Portada automática**: extrae la imagen de cubierta del EPUB y la incrusta en el M4B
- **Editor de partes**: panel lateral para renombrar los marcadores `# Part N` antes de convertir
- **Sesión persistente**: al recargar la página reconecta automáticamente al trabajo en curso
- **Un trabajo a la vez**: bloquea iniciar una nueva conversión si hay una activa
- **Monitoring**: Flower para inspección visual de workers y tareas Celery
- **Logs estructurados**: structlog con salida JSON para fácil indexado
- **Frontend**: UI vanilla (HTML/CSS/JS) sin dependencias de build — nginx
- **Seguro**: API key requerida en todas las rutas (`X-API-Key`)
- **Arquitectura hexagonal**: dominio limpio, puertos/adaptadores, testeable
- **Gestor de paquetes**: uv (pyproject.toml)
- **Entorno dev**: Nix flakes (sin Python global requerido)

## Stack

| Componente         | Tecnología                    |
| ------------------ | ----------------------------- |
| Backend API        | FastAPI + uvicorn             |
| Workers            | Celery (N-2 CPUs en paralelo) |
| Broker / estado    | Redis 7                       |
| TTS                | Microsoft Edge TTS (edge-tts) |
| Audio              | pydub + ffmpeg → FLAC → M4B   |
| Monitoring workers | Flower                        |
| Frontend           | HTML/CSS/JS vanilla + nginx   |
| Paquetes Python    | uv (pyproject.toml)           |
| Entorno dev        | Nix flakes                    |

## Inicio rápido

### Con Docker Compose (recomendado)

```bash
git clone <repo> && cd epub-to-audiobook

# Configura tu API key
cp .env.example .env
# Edita .env y cambia API_KEY

docker compose up --build

# Servicios disponibles:
# http://localhost:8080  → Frontend
# http://localhost:5555  → Flower (monitoring Celery)
```

Los audiolibros generados aparecen en `./output/{job_id}/` en el mismo directorio del repo.

### Desarrollo local (Nix)

```bash
nix develop    # activa uv, ffmpeg, docker
cd backend
uv sync        # instala dependencias en .venv
```

## Estructura del proyecto

```
epub-to-audiobook/
├── .github/
│   └── workflows/
│       ├── ci-tests.yml        # pytest en cada push/PR
│       ├── ci-build-push.yml   # build + push a GHCR al cerrar PR
│       └── ci-release.yml      # crea GitHub Release al cerrar PR
├── docker-compose.yml
├── .env.example
├── flake.nix
├── output/                     # Audiolibros generados (bind-mount)
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── entrypoint-worker.sh
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_domain_models.py
│   │   ├── test_epub_reader.py
│   │   ├── test_redis_store_serialization.py
│   │   ├── test_audio_merger_metadata.py
│   │   ├── test_services.py
│   │   ├── test_api_auth.py
│   │   ├── test_api_jobs.py
│   │   └── test_api_epub.py
│   └── src/audiobook/
│       ├── domain/             # Entidades + puertos (sin deps externas)
│       ├── application/        # Casos de uso
│       └── infrastructure/     # Adaptadores, Celery, FastAPI
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
```

## Variables de entorno (`.env`)

| Variable             | Por defecto             | Descripción                                   |
| -------------------- | ----------------------- | --------------------------------------------- |
| `API_KEY`            | `changeme`              | Clave de autenticación (**cámbiala siempre**) |
| `REDIS_URL`          | `redis://redis:6379/0`  | URL del broker Redis                          |
| `WORKER_CONCURRENCY` | auto (`nproc-2`, min 1) | Capítulos en paralelo                         |
| `FRONTEND_PORT`      | `8080`                  | Puerto del frontend en el host                |
| `FLOWER_PORT`        | `5555`                  | Puerto de Flower en el host                   |
| `OUTPUT_DIR`         | `/app/output`           | Directorio de archivos generados              |

## Flujo de conversión

```
1. Upload EPUB  →  extrae TXT editable + portada (JPEG)
2. Usuario edita TXT, renombra partes, elige voz/pausas
3. POST /api/jobs  →  Redis almacena job + dispara Celery chord:
       group [convert_chapter_0, …, convert_chapter_N]  ← paralelo
       chord callback → merge_audiobook → M4B chaptered + portada
4. SSE stream  →  frontend actualiza barras en tiempo real
                  durante merge: barra animada + cronómetro
5. Descarga directa desde ./output/ o vía GET /api/jobs/{id}/download
```

## Tests

```bash
cd backend
uv sync --dev
uv run pytest
```

Los tests cubren:

- **Domain models**: `Job`, `Chapter`, cálculo de progreso, enums
- **EPUB reader**: `parse_txt` con distintos formatos de entrada
- **Serialización Redis**: roundtrip `_job_to_dict` / `_dict_to_job`
- **Metadata ffmpeg**: generación de `FFMETADATAFILE` con capítulos y tiempos
- **Application services**: `ConvertChapterService`, `ParseEpubService` con puertos mockeados
- **API auth**: rechazo sin API key y con clave incorrecta
- **API jobs**: GET status, POST validación, POST dispatch
- **API epub**: parse endpoint con extracción de portada

No requieren Redis, ffmpeg ni red (todo mockeado).

## CI/CD

| Workflow            | Trigger                             | Acción                                                |
| ------------------- | ----------------------------------- | ----------------------------------------------------- |
| `ci-tests.yml`      | push / PR con cambios en `backend/` | Ejecuta pytest                                        |
| `ci-build-push.yml` | PR mergeada a `master`              | Build + push a GHCR con tag `sha-{commit}` y `latest` |
| `ci-release.yml`    | PR mergeada a `master`              | Crea GitHub Release con semver automático             |

Las imágenes Docker se publican en GitHub Container Registry:

```
ghcr.io/<owner>/epub-to-audiobook/backend:sha-<commit>
ghcr.io/<owner>/epub-to-audiobook/frontend:sha-<commit>
```

Los workflows de build y release reutilizan los workflows de [CodeForgeGuild/ci-actions](https://github.com/CodeForgeGuild/ci-actions).

## CLI original (epub2tts-edge)

El script CLI sigue disponible en el entorno Nix:

```bash
nix develop
source $HOME/.local/share/epub2tts-edge-env/bin/activate
epub2tts-edge libro.epub
python3 fix_parts.py libro.txt
epub2tts-edge libro.txt --speaker es-ES-AlvaroNeural
```
