# Contexto de aplicación — MVP Facturación Electrónica DIAN

Documento de referencia para agentes, desarrolladores y futuras iteraciones. Describe qué es el sistema, cómo está armado y qué funcionalidades están alineadas con productos como **Siigo Facturación**.

---

## 1. Propósito del producto

SaaS **multi-tenant** para empresas colombianas que necesitan:

- Gestionar **terceros** (clientes) y **productos/servicios**
- Emitir **facturas electrónicas** y **notas crédito/débito**
- Llevar **estados** del documento hasta envío DIAN (mock en MVP)
- **Firmar** y almacenar XML/PDF
- Consultar **indicadores** y reportes básicos de ventas
- Integrarse vía **API REST** con otros sistemas

**No es un ERP:** sin nómina, inventario avanzado, contabilidad completa ni BI pesado.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| API | FastAPI 0.115+, OpenAPI en `/docs` |
| ORM | SQLModel / SQLAlchemy 2 |
| BD | PostgreSQL 16 |
| Migraciones | Alembic |
| Auth | JWT (HS256), bcrypt |
| Jobs | Celery + Redis |
| PDF | ReportLab |
| UI | Jinja2 + HTMX (forms) |
| Contenedores | Docker Compose (`api`, `db`, `redis`, `worker`) |

---

## 3. Arquitectura (capas)

```
app/
├── api/v1/endpoints/     # REST controllers
├── web/                  # UI server-rendered
├── services/             # Reglas de negocio
├── models/               # Entidades SQLModel
├── schemas/              # DTOs Pydantic
├── domain/               # Enums + máquina de estados
├── integrations/         # DIAN, firma, UBL (stubs)
├── pdf/, storage/, audit/, workers/
└── core/                 # config, security, deps, exceptions
```

**Multi-tenancy:** `tenant_id` en tablas de negocio; JWT incluye `sub` (user) y `tenant_id`.

**Flujo típico:** Router → `get_current_user` → Service → AuditLog / DocumentEvent → DB + filesystem.

---

## 4. Modelo de datos (resumen)

| Entidad | Uso |
|---------|-----|
| `Tenant` | Empresa emisora (NIT, razón social, config facturación) |
| `User` | Usuario por tenant (`admin` / `operator`) |
| `Customer` | Tercero cliente |
| `Product` | Catálogo con precio e IVA % |
| `Invoice` + `InvoiceLine` | Factura electrónica |
| `CreditNote` + `CreditNoteLine` | Nota crédito (referencia factura) |
| `DebitNote` + `DebitNoteLine` | Nota débito (referencia factura) |
| `DocumentSequence` | Numeración `PREFIJO-000001` por tenant/tipo |
| `DocumentEvent` | Historial por documento |
| `AuditLog` | Auditoría de acciones de usuario |

---

## 5. Máquina de estados de documentos

Estados: `draft` → `signed` → `submitted` → `accepted` | `rejected` (+ `cancelled`).

Acciones API: `sign`, `submit`, `accept`, `reject`, `cancel`.

- **Editar** solo en `draft`
- **Enviar DIAN** (Celery) desde `signed` con XML firmado
- Worker mock puede pasar directo a `accepted` / `rejected`

Definición: `app/domain/state_machine.py`

---

## 6. Integraciones (MVP = mocks)

| Módulo | Archivo | Estado |
|--------|---------|--------|
| UBL 2.1 | `integrations/ubl/builder.py` | Stub, `TODO-DIAN` |
| Firma XAdES | `integrations/signing/mock_signer.py` | Mock CUFE/CUDE |
| DIAN | `integrations/dian/mock_adapter.py` | Mock envío |
| PDF | `pdf/generator.py` | ReportLab básico |
| Storage | `storage/local_storage.py` | `data/documents/tenants/{id}/` |

Variables: `DIAN_ADAPTER=mock`, `MOCK_DIAN_ACCEPT_RATE=1.0`

---

## 7. API REST (`/api/v1`)

### Auth
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`

### Tenant
- `GET/PATCH /tenants/me` — incluye config facturación (prefijos, resolución)

### Maestros
- CRUD `/customers`, `/products`

### Documentos
- CRUD parcial `/invoices` + `transition`, `submit-dian`, `events`, `pdf`
- `/credit-notes`, `/debit-notes` (misma semántica)

### Analytics (estilo Siigo)
- `GET /dashboard` — KPIs del tenant
- `GET /reports/sales` — ventas por periodo
- `GET /reports/top-products` — top N productos

### Auditoría
- `GET /audit-logs` (solo `admin`)

---

## 8. UI web (rutas)

| Ruta | Función |
|------|---------|
| `/` | Dashboard con indicadores |
| `/login`, `/logout` | Sesión cookie JWT |
| `/customers`, `/customers/new` | Terceros |
| `/products`, `/products/new` | Productos |
| `/invoices`, `/invoices/new`, `/invoices/{id}` | Facturas + filtros |
| `/credit-notes`, `/credit-notes/new` | Notas crédito |
| `/debit-notes`, `/debit-notes/new` | Notas débito |
| `/reports` | Reportes ventas / top productos |
| `/settings/billing` | Config facturación tenant |

Layout: sidebar tipo Siigo (`base.html` + `style.css`).

---

## 9. Variables de entorno

Ver `.env.example`. Claves principales:

- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`
- `ALLOW_PUBLIC_REGISTER`, `STORAGE_PATH`
- `DIAN_ADAPTER`, `MOCK_DIAN_ACCEPT_RATE`
- `INVOICE_PREFIX`, `CREDIT_NOTE_PREFIX`, `DEBIT_NOTE_PREFIX` (defaults globales)

---

## 10. Comandos operativos

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

- UI: http://localhost:8000/
- API: http://localhost:8000/docs
- Demo: `admin@demo.com` / `demo1234`

---

## 11. Paridad con Siigo Facturación

Referencia: [Siigo Facturación Electrónica](https://www.siigo.com/facturacion-electronica)

| Funcionalidad Siigo | Estado en nuestro MVP | Notas |
|---------------------|----------------------|-------|
| Factura electrónica en línea | ✅ Implementado | Flujo draft → firmar → DIAN mock |
| Notas crédito | ✅ Implementado | Referencia a factura |
| Notas débito | ✅ Implementado | Mismo patrón que NC |
| Gestión terceros | ✅ API + UI CRUD | |
| Gestión productos | ✅ API + UI CRUD | |
| Impuestos automáticos (IVA) | ✅ Por línea / producto | Catálogo DIAN: TODO |
| Indicadores ventas (dashboard) | ✅ KPIs + ventas periodo | Similar a indicador "ventas" Siigo |
| Top productos vendidos | ✅ Reporte top 4/10 | Similar a Siigo |
| Reportes por periodo | ✅ `/reports` | |
| Estados documento en tiempo real | ✅ Status + eventos | |
| Moneda extranjera | ⚠️ Campo `currency` | Sin TRM automática |
| Resolución DIAN / numeración | ⚠️ Campos tenant + secuencia | Validación legal: TODO-DIAN |
| Forma de pago / vencimiento | ✅ En factura | |
| Cotizaciones / CRM | ❌ Fuera de alcance | |
| Cartera / cobranza WhatsApp | ❌ Fuera de alcance | Interfaz futura posible |
| Mercado Pago | ❌ Fuera de alcance | |
| App móvil | ❌ Fuera de alcance | API lista para cliente móvil |
| Contabilidad sincronizada | ❌ Fuera de alcance | |
| Documento soporte compras | ❌ Fuera de alcance | |
| Recepción facturas proveedor | ❌ Fuera de alcance | |

---

## 12. Puntos TODO-DIAN (legales / técnicos)

No implementar sin especificación oficial:

1. Resolución de facturación y rangos autorizados
2. CUFE / CUDE (fórmula Anexo técnico)
3. XML UBL 2.1 conforme Anexo 1.9
4. Firma XAdES-EPES con certificado
5. Web services DIAN / proveedor tecnológico
6. Catálogos: tipo documento, municipio, régimen, motivos NC/ND

---

## 13. Tests

```bash
pytest -v
```

Cobertura: auth, facturas (crear/firmar/PDF), notas crédito, dashboard/reportes (si aplica).

---

## 14. Convenciones de código

- Código en **inglés** (nombres de módulos, clases, endpoints)
- Documentación de producto en **español**
- Servicios orquestan; routers delgados
- `AuditService.log` en mutaciones relevantes
- Errores: `AppError`, `NotFoundError` en `core/exceptions.py`

---

## 15. Roadmap sugerido (post-MVP)

1. Adaptador DIAN real (habilitación → producción)
2. Envío email PDF al tercero
3. Cotizaciones → conversión a factura
4. Roles/permisos granulares por módulo
5. Webhooks para integraciones B2B

---

*Última actualización: alineado con iteración "pulido Siigo". Mantener este archivo al añadir módulos o endpoints.*
