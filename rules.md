You are building a production-grade Financial Operating System (FOS) for MSMEs using PostgreSQL.

STRICT RULES:

Architecture:

* Multi-tenant SaaS using company_id as strict isolation key
* Every query MUST enforce tenant isolation (company_id or RLS)
* Microservices (FastAPI)
* Event-driven system (Kafka/RabbitMQ)
* Outbox pattern for reliability
* APIs must be idempotent

Database (PostgreSQL):

* Use normalized relational schema
* UUID as primary keys
* Strong foreign keys and constraints
* Use transactions for all financial operations
* JSONB only for metadata/OCR data
* Proper indexing (composite indexes)
* Use Row-Level Security (RLS)

Accounting:

* Immutable double-entry ledger
* No UPDATE/DELETE on ledger entries (enforce via triggers)
* Journal entries must always balance
* Use reversal entries for correction

Security:

* JWT authentication
* RBAC enforced on every request
* PAN encrypted (AES-256)
* HTTPS + rate limiting

Audit:

* Append-only audit logs
* Store before/after state
* Include actor_id, timestamp
* Tamper-evident (hash chaining)

OCR:

* OCR primary, VLM fallback
* Confidence threshold 0.85
* No auto-save without user confirmation

Performance:

* ACID compliance mandatory
* Optimized queries + indexing

OUTPUT MUST INCLUDE:

1. System architecture
2. PostgreSQL schema (tables + relations + constraints)
3. API endpoints
4. Transaction flow
5. Validation rules
6. Edge cases
