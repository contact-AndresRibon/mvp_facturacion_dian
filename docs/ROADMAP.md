# ROADMAP — Mejoras pendientes del MVP Facturación Electrónica DIAN

Documento vivo. **Última actualización**: 2026-06-01. Mantener sincronizado con `AGENTS.md`.

---

## Contexto

El MVP está **funcional y desplegado** (FASES 1, 4A, 5A aplicadas + commit `3147c5d` en `main`). Las FASES marcadas abajo están **planificadas pero no ejecutadas**. Se deben hacer en tandas pequeñas y commiteables.

### Reglas de oro (no romper)

- **Multi-tenant**: toda tabla de negocio lleva `tenant_id`. Toda query que carga un objeto debe verificar `obj.tenant_id == user.tenant_id`. Ver `app/core/deps.py`.
- **Routers delgados**: solo orquestación HTTP. Lógica en `app/services/`.
- **Errores tipados**: `AppError`, `NotFoundError`, `ForbiddenError` desde `app/core/exceptions.py`. Nunca `HTTPException` ad-hoc en services.
- **Eventos de documento**: usar siempre `app.services.events.record_event` (no crear `DocumentEvent` directo).
- **Numeración atómica**: `SequenceService.next_number` ya tiene `with_for_update()`; no bypass.
- **DIAN mock**: `DIAN_ADAPTER=mock` único válido. `real` lanza `NotImplementedError`. Módulos UBL/XAdES/CUFE son stubs `TODO-DIAN` — **no llevar a producción sin reemplazar**.
- **Tests**: SQLite in-memory + `CELERY_TASK_ALWAYS_EAGER=true`. El fixture `auth_headers` crea admin; `require_admin` no rompe tests existentes.
- **Sin CI/lint/typecheck cableados** (no inventar `npm run lint`).
- **Stack en Docker**: `app` (uvicorn --workers 2) + `worker` (celery) + `db` (pg16) + `redis` (r7).
- **Bcrypt truncado a 72 bytes** pre-hash (`app/core/security.py`).
- **pyjwt[crypto]** y **bcrypt** directo. **NO** `python-jose` ni `passlib`.

---

## FASE 1 — Infra y seguridad base

### [1A–1I] ✅ COMPLETADAS (commit `3147c5d`)

Dockerfile multi-stage, `.dockerignore`, `docker-compose.yml` con networks/healthchecks/resource limits/logging rotación, `requirements.txt` pineado, `pyjwt[crypto]+bcrypt` (sin `python-jose`/`passlib`), `db/session.py` con pool tuning Postgres, `celery_app` con `acks_late`/`max_tasks_per_child=200`/`prefetch=1`/`broker_connection_retry_on_startup`, `tasks.py` con `autoretry+retry_backoff+jitter+time_limit=120`, idempotencia con `_is_terminal()` y check `status != SUBMITTED`, `app/api/v1/endpoints/health.py` con `/ready` (DB SELECT 1 + Redis broker ping → 503 si falla), `app/core/logging.py` con `structlog`+JSONRenderer+`ContextVar` `request_id_var`.

### [1J] ⏳ Pendiente — Rotar `SECRET_KEY` y actualizar `.env.example`

- **Qué**: generar un `SECRET_KEY` con `python -c "import secrets; print(secrets.token_hex(32))"`. Reemplazar el valor en `.env` (placeholder `dev-secret-change-in-production`) y en `.env.example`.
- **Impacto**: invalida TODOS los JWT emitidos hasta ahora (esperado en dev; en prod coordinar con usuarios).
- **Archivos**: `.env`, `.env.example` (línea con `SECRET_KEY=...`).
- **Verificación**: relogin desde `/login` UI; tokens nuevos válidos.
- **Commit sugerido**: `chore(security): rotate SECRET_KEY to secure random value`.

---

## FASE 2 — Seguridad

### [2A] ⏳ IDOR en notas crédito/débito (`customer_id`)

- **Archivo**: `app/services/credit_note_service.py:79` y `app/services/debit_note_service.py:76`.
- **Bug**: la nota carga `customer = session.get(Customer, customer_id)` sin verificar `customer.tenant_id == user.tenant_id`. Un usuario de tenant A puede crear nota contra un cliente de tenant B.
- **Fix**: tras el `session.get`, agregar `if customer.tenant_id != user.tenant_id: raise ForbiddenError(...)`.
- **Test**: `tests/test_idor.py::test_credit_note_other_tenant_customer_forbidden` + `test_debit_note_other_tenant_customer_forbidden`.
- **Commit sugerido**: `fix(security): validate customer tenant in credit/debit note creation (IDOR)`.

### [2B] ⏳ Cookie `secure` + `samesite` + TTL desde settings

- **Archivo**: `app/web/router.py:96` (`response.set_cookie("access_token", ..., httponly=True)`).
- **Cambio**: leer `settings.cookie_secure` y `settings.cookie_samesite` y `settings.cookie_max_age` desde `app/core/config.py`. Default dev: `secure=False, samesite="lax"`. Default prod (cuando `debug=False`): `secure=True, samesite="lax"`.
- **Commit sugerido**: `feat(security): cookie secure/samesite/max_age from settings`.

### [2C] ⏳ `/logout` POST + form CSRF-safe

- **Archivo**: `app/web/router.py:100-104` (handler GET actual) y `app/web/templates/base.html:28` (`<a href="/logout">`).
- **Cambio**: cambiar handler a `POST`, actualizar `base.html` a `<form method="post" action="/logout"><button type="submit">Salir</button></form>`. Mantener `SameSite=Lax` de 2B.
- **Test**: `tests/test_web_auth.py::test_logout_clears_cookie` (opcional, dado que el flujo UI no está cubierto).
- **Commit sugerido**: `feat(security): convert logout to POST form for CSRF safety`.

### [2D] ⏳ Defaults `debug=False`, `allow_public_register=False`

- **Archivo**: `app/core/config.py:11,14`.
- **Cambio**: `debug: bool = False`, `allow_public_register: bool = False`. Actualizar `.env` y `.env.example` para que DEV los sobreescriba a `True`.
- **Impacto**: en prod, `/docs` y `/redoc` quedan deshabilitados (2G) y `/api/v1/auth/register` rechaza.
- **Commit sugerido**: `chore(security): flip default debug/register to false`.

### [2E] ⏳ `require_admin` en endpoints de transición

- **Archivo**: `app/api/v1/endpoints/invoices.py:87` (transition_invoice), `app/api/v1/endpoints/credit_notes.py:51`, `app/api/v1/endpoints/debit_notes.py:51`.
- **Cambio**: importar `AdminUserDep` desde `app.core.deps` y agregar como dependencia. El helper ya existe (`app/core/deps.py:47`).
- **Test**: `tests/test_idor.py::test_transition_requires_admin` (con `auth_headers` existente el test ya cubre el path admin; crear `non_admin_headers` fixture y verificar 403).
- **Commit sugerido**: `feat(security): require admin role for document transitions`.

### [2F] ⏳ Sanitizar `number` antes de `Content-Disposition`

- **Archivos**: `app/api/v1/endpoints/invoices.py:143`, `credit_notes.py:106`, `debit_notes.py:104` (header `Content-Disposition: attachment; filename="<number>.pdf"`).
- **Riesgo**: `number` podría contener CRLF u otros caracteres de header injection.
- **Fix**: aplicar regex `^[A-Z0-9\-_.]{1,64}$` antes de usarlo; si no matchea, usar `f"document-{doc_id}.pdf"`.
- **Helper**: agregar `sanitize_filename(value: str, fallback: str) -> str` en `app/core/security.py` o un nuevo `app/core/strings.py`.
- **Test**: `tests/test_filename_safety.py` con casos vacíos, con CRLF, con espacios, con unicode.
- **Commit sugerido**: `fix(security): sanitize document number in Content-Disposition header`.

### [2G] ⏳ `docs_url`/`redoc_url` condicionales a `settings.debug`

- **Archivo**: `app/main.py:30-31` (`FastAPI(..., docs_url="/docs", redoc_url="/redoc")`).
- **Cambio**: pasar `docs_url="/docs" if settings.debug else None` y `redoc_url="/redoc" if settings.debug else None`. Idem `openapi_url`.
- **Commit sugerido**: `feat(security): gate Swagger/ReDoc/OpenAPI on debug mode`.

### [2H] ⏳ CORS — validar `cors_origins` configurado en prod

- **Archivo**: `app/main.py:34-40`.
- **Cambio**: si `settings.cors_origins` está vacío y `debug=False`, loguear warning y usar `[]` (no permitir ninguno). Si está `["*"]` y `debug=False`, fallar al startup.
- **Test**: `tests/test_cors.py::test_cors_strict_in_prod`.
- **Commit sugerido**: `feat(security): strict CORS policy in production`.

---

## FASE 3 — Concurrencia y locking

### [3A] ⏳ `SequenceService.next_number` con retry `IntegrityError`

- **Archivo**: `app/services/sequence_service.py:43-60`.
- **Estado actual**: ya usa `with_for_update()` antes del `SELECT ... FOR UPDATE`. Pero la creación inicial de la fila `DocumentSequence` no tiene try/except `IntegrityError` — carrera residual entre requests concurrentes contra el primer `INSERT`.
- **Fix**: envolver el `INSERT` inicial en `try/except IntegrityError: session.rollback(); re-fetch with_for_update()`.
- **Test**: `tests/test_sequence.py::test_concurrent_next_number_no_duplicate` (lanzar N corutinas con `asyncio.gather` y verificar que no hay duplicados).
- **Commit sugerido**: `fix(concurrency): handle IntegrityError on initial sequence row creation`.

### [3B] ⏳ `with_for_update` en `DocumentWorkflowService`

- **Archivo**: `app/services/document_workflow_service.py`.
- **Lugares** (6 transiciones de estado): líneas 78, 176, 223, 323, 367, 467 (cada `session.get(Invoice|CreditNote|DebitNote, id)` antes de cambiar status).
- **Fix**: cambiar a `session.get(..., with_for_update=True)` (SQLAlchemy 2.x). En SQLite (tests) el lock es no-op.
- **Test**: `tests/test_workflow.py::test_concurrent_sign_only_one_succeeds` (dos requests `sign` simultáneos; solo una debe tener éxito).
- **Commit sugerido**: `fix(concurrency): add row-level locks to document workflow transitions`.

### [3C] ⏳ `IDOR` en `DocumentEvent` query

- **Archivo**: `app/services/document_workflow_service.py:500-515` (`list_events`).
- **Estado actual**: ya filtra por `DocumentEvent.tenant_id == user.tenant_id` ✅. Solo confirmar que tests cubren el path.
- **Test**: agregar a `tests/test_workflow.py`.

---

## FASE 4 — Observabilidad

### [4A] ✅ COMPLETADO (commit `3147c5d`)

`app/core/logging.py` con `structlog` (JSONRenderer, TimeStamper ISO/UTC), `ContextVar` `request_id_var`, `configure_logging()` y `get_logger(name)`.

### [4B] ⏳ Wire `configure_logging()` + setear `request_id_var` en middleware

- **Archivos**: `app/main.py` (lifespan/startup) y `app/main.py:RequestIdMiddleware` (clase definida cerca de línea 60).
- **Cambio**:
  1. Llamar `configure_logging()` al inicio del lifespan.
  2. En el middleware, dentro de `dispatch`: `request_id_var.set(request.headers.get("X-Request-ID", str(uuid4())))` antes de procesar.
  3. Loguear `http.request.start` y `http.request.end` con `method`, `path`, `status_code`, `duration_ms`.
- **Verificación**: `docker compose logs api` debe mostrar JSON con `request_id` y `event`.
- **Commit sugerido**: `feat(observability): wire structlog and request_id contextvar`.

### [4C] ⏳ Handler global de `Exception` con log estructurado

- **Archivo**: `app/main.py` (después de `register_exception_handlers`).
- **Cambio**: agregar `@app.exception_handler(Exception)` que loguea `error.unhandled` con stack trace, `request_id`, `path`, `method`; devuelve 500 con `{"detail": "Internal server error", "request_id": "..."}`. **Cuidado**: no loguear password, JWT, ni payloads sensibles.
- **Test**: `tests/test_error_handler.py::test_unhandled_exception_returns_500_with_request_id` (forzar raising en endpoint de test).
- **Commit sugerido**: `feat(observability): global exception handler with structured logging`.

### [4D] ⏳ Métricas básicas (Prometheus opcional)

- **Estado**: NO prioritario. Documentar como follow-up.

---

## FASE 5 — Refactors y tests

### [5A] ✅ COMPLETADO (commit `3147c5d`)

`app/services/events.py:record_event` como helper único. `document_workflow_service._record_event` y `tasks.py` lo consumen.

### [5B] ⏳ `selectinload` en listados (N+1)

- **Archivos**: `app/services/invoice_service.py:35-37` (`_to_response` con queries extras), y equivalentes en `credit_note_service.py`, `debit_note_service.py`.
- **Fix**: en `list_invoices`/`list_credit_notes`/`list_debit_notes`, agregar `.options(selectinload(Invoice.customer), selectinload(Invoice.lines))` (o el equivalente del modelo) antes del `.all()`.
- **Verificación**: `EXPLAIN ANALYZE` antes/después en Postgres con datos semilla; número de queries debe bajar de O(N) a O(1).
- **Commit sugerido**: `perf(queries): use selectinload to eliminate N+1 in document listings`.

### [5C] ⏳ Tests nuevos (suite ~12 tests)

Ubicación: `tests/`. Fijarse en `tests/conftest.py` (fixtures `client`, `auth_headers`, `session`).

| Archivo | Tests |
|---|---|
| `tests/test_idor.py` | `test_credit_note_other_tenant_customer_forbidden`, `test_debit_note_other_tenant_customer_forbidden`, `test_transition_requires_admin` (non-admin headers) |
| `tests/test_sequence.py` | `test_concurrent_next_number_no_duplicate`, `test_next_number_advances_on_each_call` |
| `tests/test_workflow.py` | `test_concurrent_sign_only_one_succeeds`, `test_reject_to_signed_transition_not_allowed`, `test_list_events_filters_by_tenant` |
| `tests/test_filename_safety.py` | `test_empty_number_uses_fallback`, `test_crlf_in_number_uses_fallback`, `test_unicode_in_number_uses_fallback` |
| `tests/test_health.py` | `test_ready_returns_503_when_db_down` (mockear session con error), `test_ready_returns_503_when_redis_down` |

- **Commit sugerido**: `test: cover IDOR, concurrency, filename safety, health checks`.

### [5D] ⏳ Refactor de `DocumentService[T]` genérico (NO en esta tanda)

- **Archivo**: `app/services/invoice_service.py`, `credit_note_service.py`, `debit_note_service.py` (~300 LOC cada uno con duplicación).
- **Por qué NO ahora**: requiere tipado genérico, manejo de `DocumentType` enum en `_to_response`, y refactor masivo. Estimado: 2-3 sesiones + nueva tanda de tests.
- **Roadmap**: planificar para Q3.

---

## Roadmap de producto (más allá de hardening)

Funcionalidades clave que el MVP **necesita** antes de salir a clientes reales (no son bugs, son features):

### [P0] Crítico para producción

- **DIAN real**: implementar `app/integrations/dian/gateway.py` con cliente HTTP a DIAN (certificación + habilitación). Reemplazar `mock_adapter.py` con `real_adapter.py`. `DIAN_ADAPTER=real` debe estar gated por flag.
- **Firma XAdES-EPES real**: reemplazar `app/integrations/signing/mock_signer.py` con implementación basada en `python-cryptography` + `lxml`. Necesita `.p12` del cliente.
- **UBL 2.1 real**: `app/integrations/ubl/builder.py` actualmente stub. Generar XML conforme a `DIAN_UBL20_CE_v1_0.pdf` (InvoiceType, CreditNoteType, DebitNoteType).
- **CUFE/CUDE conforme**: hoy es `sha384("{id}:{digest}")` truncado — **no válido legalmente**. Debe calcularse según Anexo Técnico DIAN.
- **Catálogos DIAN**: `app/integrations/dian/catalogs/` debe mapear códigos (tipo documento, tipo persona, municipio, etc.) a `code` y `name` oficiales.
- **Numeración autorizada**: hoy el cliente mete prefijo arbitrario. La DIAN exige **resolución de facturación** (rango `SETT-1` a `SETT-99999`) cargada por tenant en `/settings/billing`.
- **Eventos RADIAN**: para facturas electrónicas, la DIAN notifica acuse/recibo. Hoy no se modela.
- **Recepción de facturas del emisor-receptor**: el modelo asume que solo emitimos. Faltan endpoints para que un cliente nos envíe su factura.

### [P1] Producto

- **Reportes**: dashboard con totales emitidos/anulados/pendientes por mes. Hoy no hay vista `/reports`.
- **Exportación contable**: ZIP con XML+PDF+CSV para enviar a contador.
- **Multi-moneda**: UBL 2.1 lo permite, hoy hardcoded a COP.
- **Impuestos adicionales**: solo IVA manejado. Falta INC, IC, RETE-FUENTE, RETE-ICA, etc.
- **Notas crédito parciales**: hoy la nota crédito reemplaza el total de la factura. UBL permite referenciar líneas específicas.
- **Plantillas de email**: envío de factura al cliente final con link de descarga del PDF/QR.
- **QR en PDF**: `app/pdf/builder.py` debe incluir QR con CUFE + URL de validación DIAN.
- **Multi-idioma**: solo español. Catálogos en español (decimales con `,`).

### [P2] Plataforma

- **Rate limiting**: `slowapi` o `fastapi-limiter` con Redis. Hoy cualquier IP puede hacer 1000 logins/s.
- **Backups automáticos**: `pg_dump` programado + subida a S3. Sin script.
- **Alertas**: Slack/email cuando un worker falla 5 veces seguidas o un tenant no emite hace 30 días.
- **SSO/SAML**: para clientes enterprise. Hoy solo email+password.
- **API versioning**: estamos en `/api/v1` pero no hay estrategia deprecation. Documentar.
- **OpenAPI client gen**: generar SDK Python/TS automáticamente del `openapi.json`.
- **Webhooks**: notificar al cliente cuando una factura es aceptada/rechazada.
- **Auditoría con retención**: hoy `AuditLog` crece sin tope. Política de retención 365 días.

### [P3] Nice-to-have

- **Modo claro/oscuro** en UI (solo es server-rendered HTML+HTMX; puede ser CSS toggle).
- **Búsqueda full-text** en facturas (Postgres `tsvector` o Meilisearch).
- **Notificaciones en UI** (toast) — hoy todo es `flash` message en redirect.
- **Drag & drop upload** de XML de proveedor (recepción).
- **Plantillas personalizables de PDF** (logo, colores, footer).

---

## Convenciones y recordatorios

- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `perf:`, `refactor:`, `docs:`).
- **Branches**: `main` (protegida), feature branches `feat/<slug>`, fixes `fix/<slug>`.
- **Mensajes de commit**: imperativo presente + cuerpo con bullets si hay múltiples cambios.
- **PRs**: 1 feature/fix por PR. Body debe enlazar a este `ROADMAP.md` (e.g. `Refs ROADMAP §2A`).
- **No commitear**:
  - `.env` (ya en `.gitignore`)
  - `data/` (ya en `.gitignore`)
  - `__pycache__/`, `*.pyc` (ya en `.gitignore`)
  - **Secrets**: NUNCA pegar tokens, passwords, `SECRET_KEY` en código o commits.

---

## Procedimiento de actualización

Cada vez que se cierre una fase:
1. Marcar la tarea como ✅ en este archivo.
2. Actualizar la fecha de "Última actualización" arriba.
3. Commitear con prefijo `docs:`.
4. Si el cambio toca el `AGENTS.md`, sincronizarlo.
5. Push a `main`.

---

## Referencias

- `AGENTS.md` — contexto del repo, comandos, gotchas.
- `docs/APP_CONTEXT.md` — modelo de datos, paridad Siigo, decisiones de producto.
- `README.md` — setup, ejemplos curl, variables de entorno.
- `.env.example` — plantilla de configuración.
