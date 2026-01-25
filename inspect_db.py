from backend.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    # List all tables
    result = conn.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    print("=== ALL TABLES ===")
    for row in result:
        print(f"  {row[0]}")

    # Check extracted_claims columns
    print("\n=== EXTRACTED_CLAIMS COLUMNS ===")
    try:
        result = conn.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'extracted_claims'
                ORDER BY ordinal_position
            """)
        )
        for row in result:
            print(f"  {row[0]}: {row[1]}")
    except Exception as e:
        print(f"  Table does not exist: {e}")
