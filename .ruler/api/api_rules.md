# API Rules

Use FastAPI with thin routers.

Router responsibilities:

- Validate path/query/body inputs.
- Depend on database/session providers.
- Call service functions.
- Return Pydantic response models.
- Convert known service errors into HTTP errors.

Service responsibilities:

- Orchestrate business workflows.
- Call quant/data/RAG helpers.
- Persist auditable outputs.
- Return structured domain results.

Do not:

- Put full modelling logic in route files.
- Let route files calculate credit decisions directly.
- Return unexplained raw exceptions to users.

