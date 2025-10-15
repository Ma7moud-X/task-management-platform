# Task Management SaaS Platform

## Architecture Overview and Tenancy Design
The system uses a single-database, shared-schema multi-tenancy model. Every table includes an org_id column, and all queries are scoped to the current organization via middleware that extracts org_id from the JWT claim.

This approach was chosen over schema-per-tenant for simplicity, operational efficiency, and lower resource overhead. Indexing on org_id ensures query performance remains strong as tenant count grows. Tenant isolation is enforced at the application layer, with every API endpoint validating that the requested resource belongs to the user's organization.

## Setup and Local Run Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Backend
Create a virtual environment and install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Set environment variables (see .env.example)

Run database migrations:
```bash
alembic upgrade head
```

Start the server:
```bash
uvicorn app.main:app --reload
```

Start the Celery worker (for background tasks like CSV export):
```bash
celery -A celery_app worker --pool=solo --loglevel=info
```

### Frontend
Install dependencies:
```bash
cd frontend
pnpm install
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local`

Start the dev server:
```bash
pnpm dev
```

## Real-Time Implementation
Real-time task updates are handled via WebSockets. Clients connect to `GET /ws/{org_id}` and receive broadcast messages for created, updated, and deleted events within their organization.

The backend uses Redis pub/sub to decouple event production from consumption. When a task is modified, the API publishes a message to a Redis channel scoped to the org_id. All WebSocket workers subscribed to that channel forward the event to connected clients.

This ensures low-latency updates while maintaining tenant isolation—clients only receive events for their own organization.

## Scaling and Security Trade-offs

### Security:
- JWT access tokens are short-lived; refresh tokens are stored securely in the database.
- Role-based authorization is enforced server-side on every request.
- OTP adds a second factor for email/password logins; Google OAuth2 provides passwordless alternative.

### Scaling:
- Single-database design simplifies backups and migrations but requires careful indexing on org_id.
- Redis pub/sub scales horizontally with WebSocket workers.
- Background jobs (e.g., CSV export) run asynchronously via Celery to avoid blocking API requests.

### Trade-offs:
- Shared schema reduces operational complexity vs. schema-per-tenant but requires rigorous query scoping.
- In-memory session storage was avoided; all state is derived from JWT or database.

## Future Plans
- Implement task filtering capabilities in the frontend
- Add functionality to assign tasks to other organization members through the frontend
- Implement comprehensive test coverage for both backend and frontend
- Implement rate limiting for API endpoints
- Add Docker support with multi-stage builds for optimized container images
- Set up GitHub Actions CI pipeline for automated testing and deployment