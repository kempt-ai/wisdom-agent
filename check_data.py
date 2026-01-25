from backend.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM extracted_claims"))
    count = result.scalar()
    print(f"extracted_claims has {count} rows")
    
    result = conn.execute(text("SELECT COUNT(*) FROM extracted_evidence"))
    count = result.scalar()
    print(f"extracted_evidence has {count} rows")
