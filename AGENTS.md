# AGENTS.md — MVP Facturación Electrónica DIAN

Guía compacta para sesiones de OpenCode. Para detalles extensos de producto/arquitectura ver `README.md` y `docs/APP_CONTEXT.md`.

## Stack y layout

- **Stack:** FastAPI 0.115 · SQLModel/SQLAlchemy 2 · PostgreSQL 16 · Alembic · Celery 5 + Redis 7 · ReportLab (PDF) · Jinja2 + HTMX (UI server-rendered) · structlog (logs JSON).
- **Entrypoints:**
  - API + UI: `app/main.py:create_app()` → `app = create_app()` en el módulo.
  - Worker: `app/workers/celery_app:celery_app` — invocar con `celery -A app.workers.celery_app worker`.
- **Capas:** `app/api/v1/endpoints/` (REST fino) · `app/web/` (UI HTMX, `app/web/router.py`) · `app/services/` (lógica) · `app/models/` (SQLModel) · `app/schemas/` (Pydantic) · `app/domain/` (enums + state machine) · `app/integrations/{dian,signing,ubl}/` (todo MOCK) · `app/audit/`, `app/workers/`, `app/storage/`, `app/pdf/`, `app/core/`.
- **Multi-tenant:** toda tabla de negocio lleva `tenant_id`; el JWT (`app/core/security.py:create_access_token`) carga `tenant_id` en el payload. Los servicios **deben** comprobar `obj.tenant_id == user.tenant_id` — no bypass. `app/core/deps.py:require_admin` existe y se usa en algunos endpoints (ver endpoints específicos en cada archivo).
- **Eventos de documento:** helper compartido en `app/services/events.py:record_event`. El workflow (`app/services/document_workflow_service.py:DocumentWorkflowService._record_event`) y los workers (`app/workers/tasks.py`) lo usan para escribir en `DocumentEvent`.

## Levantar con Docker (camino más rápido)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

- API/Swagger: http://localhost:8000/docs · UI: http://localhost:8000/ · Health: `/health` (root, shallow liveness).
- Credenciales demo: `admin@demo.com` / `demo1234`.
- El seed (`scripts/seed_demo.py`) es **idempotente** sobre `admin@demo.com`: si ya existe, imprime y sale.

**Infra del compose** (`docker-compose.yml`):

- 4 servicios: `db` (Postgres 16 alpine), `redis` (7 alpine), `api`, `worker`. 2 networks: `internal` (db+redis+api+worker) y `edge` (api, expone `:8000`).
- Healthchecks en los 4 servicios; `api` y `worker` usan `depends_on: condition: service_healthy`.
- `api` corre `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers` (sobre la imagen multi-stage).
- Volúmenes nombrados `postgres_data` y `document_data` (este último montado en `/app/data/documents`).
- Logging `json-file` con `max-size: 10m, max-file: 3`. Resource limits por servicio.

**Dockerfile** (multi-stage):

- Stage `builder`: compila wheels con `gcc` + `libpq-dev` en `python:3.12-slim-bookworm`.
- Stage `runtime`: instala desde wheels en imagen limpia con `libpq5`, `curl`, `tini`. USER `app` (uid/gid 1000, no-root). WORKDIR `/app`. HEALTHCHECK contra `http://localhost:8000/health`.
- Variables de runtime en `app/core/config.py:Settings`; nunca hardcodear.

## Levantar local (sin Docker)

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
# Ajustar .env: DATABASE_URL -> localhost:5432, REDIS/CELERY_* -> localhost
alembic upgrade head
uvicorn app.main:app --reload
# Worker en otra terminal:
celery -A app.workers.celery_app worker --loglevel=info
```

**Gotcha compose vs local:** en `docker-compose.yml` el bloque `environment:` define `DATABASE_URL`/`REDIS_URL`/`CELERY_BROKER_URL` apuntando a los servicios `db`/`redis` (no a `localhost`). El bloque `env_file: .env` carga el resto. Para desarrollo local, `.env` debe usar `localhost` en `DATABASE_URL`/`REDIS_URL`/`CELERY_*`.

## Tests

```bash
pytest -v
```

`pytest.ini` define `testpaths=tests` y `pythonpath=.`. **Particularidades críticas** (`tests/conftest.py`):

- **SQLite in-memory** (`StaticPool`) — Postgres NO es necesario para tests.
- `CELERY_TASK_ALWAYS_EAGER=true` (`tests/conftest.py:12`) → las tareas corren sincrónicamente, no se necesita Redis ni worker corriendo. `app/workers/celery_app.py` lee esta var y activa `task_always_eager + task_eager_propagates`.
- Las variables de entorno (`DATABASE_URL=sqlite://`, `SECRET_KEY=test-secret-key`, `ALLOW_PUBLIC_REGISTER=true`, `CELERY_TASK_ALWAYS_EAGER=true`) se setean **antes** de importar `app.main`; **no reordenar** esos imports (líneas 1-12 antes de `from app.main import app`).
- Fixtures: `client` (TestClient con `app.dependency_overrides[get_session]`), `auth_headers` (Bearer de un `/api/v1/auth/register` fresco — el `RegisterRequest` crea el user con `role=ADMIN`, por lo que `require_admin` no rompe tests existentes), `session`.
- Esquema se crea/borra por función (no compartir estado entre tests).

## DIAN está mockeado

- `DIAN_ADAPTER=mock` es el **único** valor válido. `real` lanza `NotImplementedError` en `app/integrations/dian/mock_adapter.py:47` (gateway abstracto en `gateway.py` — Protocol, adapter mock en `mock_adapter.py`).
- `MOCK_DIAN_ACCEPT_RATE` (0.0–1.0) controla probabilidad de rechazo en el mock.
- **Todo** lo siguiente es stub marcado `TODO-DIAN` (ver `docs/APP_CONTEXT.md`): UBL 2.1 (`app/integrations/ubl/builder.py`), XAdES-EPES (`app/integrations/signing/mock_signer.py`), `DianGateway` real, CUFE/CUDE conforme, catálogos DIAN. **No llevar a producción** sin reemplazar estos módulos.
- El "CUFE" en código es `sha384("{id}:{digest}")` truncado a 96 chars (`app/integrations/signing/mock_signer.py`) — no es válido legalmente.

## Workers (DIAN submit)

`app/workers/celery_app.py` configura:

- `task_acks_late=True`, `task_reject_on_worker_lost=True`, `worker_max_tasks_per_child=200`, `worker_prefetch_multiplier=1` — seguridad ante cierres bruscos / OOM.
- Cola por defecto `dian` con routing explícito a `submit_invoice_to_dian`, `submit_credit_note_to_dian`, `submit_debit_note_to_dian`.
- `broker_connection_retry_on_startup=True`.

`app/workers/tasks.py` define los kwargs de las 3 tasks en `_TASK_KWARGS`:

- `autoretry_for=(ConnectionError, TimeoutError, OperationalError)`, `retry_backoff=True`, `retry_backoff_max=300`, `retry_jitter=True`, `max_retries=5`.
- `acks_late=True`, `time_limit=120`, `soft_time_limit=100`.
- **Idempotencia**: cada task verifica `status` antes de actuar — `_is_terminal(...)` (accepted/rejected/cancelled) → skip; `status != SUBMITTED` → skip. Evita re-procesar si Celery reencola. Loguea `dian.submit.skipped_terminal` / `skipped_not_submitted`.

## DB engine

`app/db/session.py:engine` aplica tuning solo para Postgres (no SQLite):

- `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=3600`, `pool_timeout=30`.
- `echo=settings.debug` (verbose solo en dev).
- SQLite (tests) usa `connect_args={"check_same_thread": False}` sin pool config.

## Concurrencia (locking)

- `app/services/sequence_service.py:next_number` usa `with_for_update()` en el `SELECT` de `DocumentSequence` antes de incrementar y `flush` (Postgres) — evita carrera en numeración. En SQLite (tests) el lock es no-op.
- `app/services/document_workflow_service.py` aún NO usa `with_for_update` en sus lookups de transiciones — **race window conocido** si dos requests firman la misma factura a la vez (ver informe de seguridad).

## Health checks

- `GET /health` (en `app/main.py:create_app`) — liveness shallow, siempre `{"status": "ok"}`. No toca DB ni Redis.
- `GET /api/v1/health` (en `app/api/v1/endpoints/health.py:liveness`) — mismo payload, montado bajo el prefix `/api/v1`.
- `GET /api/v1/ready` (en `app/api/v1/endpoints/health.py:readiness`) — chequea DB (`SELECT 1`) + Redis (broker ping). Devuelve 503 si alguno falla. Es el endpoint que el healthcheck de Docker debería usar idealmente (actualmente el Dockerfile apunta a `/health` por simplicidad).

## Logging

- `app/core/logging.py` configura `structlog` con `JSONRenderer` + `TimeStamper` ISO/UTC + `ContextVar` `request_id_var`. Llamar `configure_logging()` al startup del proceso (workers y api).
- `get_logger(__name__)` retorna un `BoundLogger` con `event`-style API (`log.info("dian.submit.start", document_id=...)`).
- `RequestIdMiddleware` (en `app/main.py`) aún **no setea el ContextVar** — el módulo está listo pero la integración con el middleware está pendiente.

## Auth crypto

- `app/core/security.py` usa **`pyjwt[crypto]`** (no `python-jose`) y **`bcrypt`** directo (no `passlib`). API pública intacta: `create_access_token`, `decode_access_token`, `verify_password`, `get_password_hash`.
- Truncado de password a 72 bytes antes de hashear (límite de bcrypt).
- Hashes existentes en `data/` (formato `$2b$`) siguen siendo válidos con la nueva implementación — no se requiere re-seed.
- Cambio de lib invalida tokens JWT emitidos con la lib anterior (esperado en dev, problema en prod → coordinar rotación).

## Máquina de estados de documentos

Definida en `app/domain/state_machine.py`:

```
draft --sign--> signed --submit--> submitted --accept--> accepted
                                            \--reject--> rejected
draft|signed --cancel--> cancelled
```

- **Editable** solo en `draft` (`EDITABLE_STATUSES`).
- **Submit-DIAN** solo desde `signed` (`DIAN_SUBMITTABLE_STATUSES`).
- **Notas crédito/débito** requieren factura referenciada en `signed|submitted|accepted` (`REFERENCE_INVOICE_STATUSES`).
- Acciones API: `sign`, `submit`, `accept`, `reject`, `cancel` (POST `/api/v1/{invoices,credit-notes,debit-notes}/{id}/transition`).
- Endpoints para encolar envío a DIAN: `/submit-dian` — dispara Celery (`app/workers/tasks.py`), no envía directo.

## Prefijos de numeración

- Default global en `app/core/config.py:Settings`: `invoice_prefix=SETT`, `credit_note_prefix=NC`, `debit_note_prefix=ND` (formato `PREFIJO-000001`).
- Configurable por tenant vía UI `/settings/billing` o API `PATCH /api/v1/tenants/me`. Migración: `alembic/versions/002_siigo_features.py`.
- Numeración por tenant/tipo en `app/models/document_sequence.py`. Resolución en `app/services/sequence_service.py`.

## Configuración y entorno

- Toda config pasa por `app/core/config.py:Settings` (pydantic-settings, lee `.env`). `get_settings()` está cacheado con `lru_cache`.
- **Alembic** ignora el placeholder de `alembic.ini` y lee `DATABASE_URL` desde `app.core.config` (`alembic/env.py`). Verificar que `.env` tiene la URL correcta antes de `alembic upgrade head`.
- **Storage:** `STORAGE_PATH` (default `./data/documents`) layout `tenants/{tenant_id}/{invoice|credit_note|debit_note}/{doc_id}.xml|.pdf` (`app/storage/local_storage.py`). Directorio `data/` está en `.gitignore`; en Docker se monta como volumen `document_data`.
- **Auth:** JWT HS256 vía `pyjwt`, bcrypt directo. Variable crítica: `SECRET_KEY` (placeholder en `.env.example`, **rotar antes de cualquier despliegue no-dev**; cambiar invalida todos los tokens existentes).

## Convenciones del repo

- **Código en inglés**, **documentación de producto en español** (ver `docs/APP_CONTEXT.md`).
- Routers delgados, lógica en `app/services/`.
- Mutaciones relevantes loguean con `AuditService.log` (`app/audit/service.py`).
- Errores esperados: `AppError`, `NotFoundError`, `ForbiddenError` desde `app/core/exceptions.py` (registrados vía `register_exception_handlers` en `app/main.py`).
- Cada request lleva `X-Request-ID` (generado si falta) por `RequestIdMiddleware` (`app/main.py`).

## Sin CI / lint / typecheck cableados

**No hay** workflows en `.github/`, ni `.pre-commit-config.yaml`, ni `pyproject.toml`/`ruff.toml`/`mypy.ini`. `requirements-dev.txt` lista `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov`, `pip-audit` pero **ninguno está configurado para correr automáticamente**. **Las únicas puertas de verificación** hoy son:

- `pytest -v`
- `alembic upgrade head` (para cambios de modelo)

No inventes comandos tipo `npm run lint` o `ruff check .` — no están cableados (aunque ruff está instalado vía dev requirements).

## Gotchas comunes

- **Reordenar imports en `tests/conftest.py`** rompe los tests (env vars deben setearse antes de importar `app.main`).
- `RegisterRequest` crea el user con `role=ADMIN` por default (`app/services/auth_service.py`) → `require_admin` no rompe los tests existentes.
- El endpoint `/api/v1/invoices/{id}/pdf` devuelve `application/pdf` con bytes que empiezan en `%PDF` (`tests/test_invoices.py`).
- `ALLOW_PUBLIC_REGISTER=true` (default) habilita `POST /api/v1/auth/register`; poner en `false` en producción para multi-tenant cerrado.
- Login UI usa **cookie** `access_token` (`app/web/router.py:login_submit`); API usa **Bearer header**. Son canales distintos — los tests solo usan Bearer.
- El `<a href="/logout">` en `app/web/templates/base.html:28` es un GET; cambiar a form POST si se quiere CSRF-safe.
- `app/services/{credit_note,debit_note}_service.py` aceptan `customer_id` opcional del payload sin validar `customer.tenant_id == user.tenant_id` → **IDOR conocido**: un user puede crear nota crédito/débito con un customer de otro tenant. Fix documentado en informe de seguridad.
- `sequence_service.py` tiene `with_for_update` pero **no try/except IntegrityError** en creación inicial de la fila `DocumentSequence` — carrera residual entre requests concurrentes contra el primer `INSERT` puede explotar.

## Archivos de referencia

- Detalle de producto, modelo de datos, paridad Siigo, roadmap: `docs/APP_CONTEXT.md`.
- Comandos crudos, ejemplos curl: `README.md`.
- Variables de entorno: `.env.example`.
