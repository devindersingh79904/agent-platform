# Database Migrations

Yuno Agent Studio uses Alembic for database migrations.

## Naming Convention

Migration IDs are sequential and human-readable. They must start with a 3-digit number.
Example:
- `001_initial_complete_schema`
- `002_add_user_table`
- `003_add_new_feature`

## Generating Migrations

If you use Docker:
```bash
make migration-docker name=your_migration_name
```
Then rename the generated file in `backend/alembic/versions/` to follow the sequential numbering, and update the `revision = '...'` variable inside the file.

If you develop locally:
```bash
make migration name=your_migration_name
```

## Running Migrations

Using Docker:
```bash
make migrate-docker
```

Locally:
```bash
make migrate
```
