from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://career_copilot_db_rdgf_user:VhR7SX330XQKdS4Udqtpu4p62ykPyucZ@dpg-d99jk0d7vvec73fm7ht0-a.ohio-postgres.render.com/career_copilot_db_rdgf')

with engine.connect() as conn:
    print('search_path:', conn.execute(text("SHOW search_path")).fetchone())
    print('schemas:', conn.execute(text("SELECT schema_name FROM information_schema.schemata")).fetchall())
    print('tables:', conn.execute(text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')")).fetchall())
    print('alembic_version rows:', conn.execute(text("SELECT * FROM alembic_version")).fetchall())
    print('pgvector installed:', conn.execute(text("SELECT * FROM pg_extension WHERE extname='vector'")).fetchall())