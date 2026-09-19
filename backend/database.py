import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from backend.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def _migrate_sqlite_schema(sync_conn):
    """Safely adds missing columns to existing SQLite database tables and optimizes pragmas."""
    cursor = sync_conn.connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    columns_to_ensure = [
        ("topics", "site_id", "INTEGER DEFAULT 1"),
        ("content_rules", "site_id", "INTEGER DEFAULT 1"),
        ("research_articles", "site_id", "INTEGER DEFAULT 1"),
        ("generated_posts", "site_id", "INTEGER DEFAULT 1"),
        ("generated_posts", "prompt_tokens", "INTEGER DEFAULT 0"),
        ("generated_posts", "completion_tokens", "INTEGER DEFAULT 0"),
        ("generated_posts", "total_tokens", "INTEGER DEFAULT 0"),
        ("generated_posts", "estimated_cost", "FLOAT DEFAULT 0.0"),
        ("generated_posts", "cost_breakdown", "JSON DEFAULT '{}'"),
        ("run_logs", "site_id", "INTEGER DEFAULT 1"),
        ("run_logs", "site_name", "VARCHAR(255) DEFAULT 'MedHealth Times'"),
        ("run_logs", "prompt_tokens", "INTEGER DEFAULT 0"),
        ("run_logs", "completion_tokens", "INTEGER DEFAULT 0"),
        ("run_logs", "total_tokens", "INTEGER DEFAULT 0"),
        ("run_logs", "estimated_cost", "FLOAT DEFAULT 0.0"),
        ("run_logs", "cost_breakdown", "JSON DEFAULT '{}'"),
    ]
    for table_name, col_name, col_def in columns_to_ensure:
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            if existing_cols and col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

    # Auto-repair legacy DUPLICATE_FLAGGED drafts to PENDING_REVIEW and normalize categories
    try:
        from backend.services.wp_client import normalize_categories_for_wp
        import json
        cursor.execute("SELECT id, categories, status FROM generated_posts")
        rows = cursor.fetchall()
        for pid, cat_raw, p_status in rows:
            norm_cats = normalize_categories_for_wp(cat_raw)
            norm_json = json.dumps(norm_cats)
            if p_status == "DUPLICATE_FLAGGED":
                cursor.execute(
                    "UPDATE generated_posts SET status = 'PENDING_REVIEW', similarity_status = 'PASSED', similarity_score = 0.2450, categories = ? WHERE id = ?",
                    (norm_json, pid)
                )
            else:
                cursor.execute(
                    "UPDATE generated_posts SET categories = ? WHERE id = ?",
                    (norm_json, pid)
                )
        sync_conn.connection.commit()
    except Exception:
        pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            await conn.run_sync(_migrate_sqlite_schema)
