# MVP SaaS Facturación Electrónica Colombia (DIAN-ready)

> **Contexto para desarrollo:** ver [docs/APP_CONTEXT.md](docs/APP_CONTEXT.md) (arquitectura, endpoints, paridad Siigo, TODO-DIAN).

Monolito modular en **FastAPI + PostgreSQL + SQLModel + Celery + Redis** para emitir facturas y notas crédito con arquitectura preparada para integración DIAN (stubs/mocks en MVP).

## Requisitos

- Docker y Docker Compose
- Python 3.12+ (opcional, para desarrollo local sin Docker)

## Inicio rápido (Docker)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

- **API / Swagger:** http://localhost:8000/docs
- **UI web:** http://localhost:8000/
- **Health:** http://localhost:8000/health

### Credenciales demo (seed)

- Email: `admin@demo.com`
- Password: `demo1234`

## Desarrollo local (sin Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
# Ajustar DATABASE_URL a PostgreSQL local
alembic upgrade head
uvicorn app.main:app --reload
```

Worker Celery (otra terminal):

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

## Ejemplos API

### Registro tenant + admin

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "legal_name": "Mi Empresa SAS",
    "nit": "900111222",
    "email": "empresa@miempresa.com",
    "admin_email": "admin@miempresa.com",
    "admin_password": "miPassword123",
    "admin_full_name": "Juan Admin"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@demo.com&password=demo1234"
```

### Crear factura

```bash
TOKEN="<access_token>"
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<uuid-cliente>",
    "issue_date": "2026-05-19",
    "lines": [{"product_id": "<uuid-producto>", "quantity": 2}]
  }'
```

### Firmar factura (mock)

```bash
curl -X POST http://localhost:8000/api/v1/invoices/<id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "sign"}'
```

### Encolar envío DIAN (mock Celery)

```bash
curl -X POST http://localhost:8000/api/v1/invoices/<id>/submit-dian \
  -H "Authorization: Bearer $TOKEN"
```

## Arquitectura

| Capa | Ubicación |
|------|-----------|
| API REST | `app/api/v1/` |
| UI HTMX | `app/web/` |
| Servicios | `app/services/` |
| Integración DIAN | `app/integrations/dian/` (mock) |
| Firma | `app/integrations/signing/` (mock) |
| UBL stub | `app/integrations/ubl/` |
| PDF | `app/pdf/` |
| Auditoría | `app/audit/` |
| Workers | `app/workers/` |

## Puntos TODO-DIAN

- Resolución y numeración oficial
- CUFE/CUDE según anexo técnico
- XML UBL 2.1 conforme
- Firma XAdES con certificado
- Adaptador real `DianGateway` (producción/habilitación)

## Licencia

Uso interno / MVP.
