# Save as: refresh_content.py
# Run from: wisdom-agent directory

import asyncio
from backend.services.content_extractor import get_content_extractor
from backend.database.db import get_db_session
from sqlalchemy import text

CREW_URL = 'https://www.citizensforethics.org/reports-investigations/crew-reports/how-president-trump-is-dismantling-our-democracy-one-piece-at-a-time/'

async def refresh_crew_content():
    # 1. Re-extract with new settings
    print("Extracting content with favor_recall=True...")
    extractor = get_content_extractor()
    result = await extractor.extract_from_url(CREW_URL)
    
    print(f"Extracted: {result.word_count} words, {len(result.content)} chars")
    
    # 2. Find the resource in DB
    with get_db_session() as session:
        # Find resource by URL
        row = session.execute(
            text("SELECT id, title, word_count FROM kb_resources WHERE url LIKE '%citizensforethics%dismantling%'")
        ).fetchone()
        
        if not row:
            print("Resource not found in database!")
            return
            
        resource_id, title, old_word_count = row
        print(f"Found resource #{resource_id}: {title}")
        print(f"Old word count: {old_word_count}, New word count: {result.word_count}")
        
        # 3. Update just the content
        session.execute(
            text("""
                UPDATE kb_resources 
                SET content = :content, 
                    word_count = :word_count,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "content": result.content,
                "word_count": result.word_count,
                "id": resource_id
            }
        )
        session.commit()
        print(f"✓ Updated resource #{resource_id} with new content")
        
        # 4. Verify the parse still exists
        parse_count = session.execute(
            text("SELECT COUNT(*) FROM parsed_resources WHERE resource_id = :id"),
            {"id": resource_id}
        ).scalar()
        print(f"✓ Parsed versions preserved: {parse_count} parse(s) still linked")

if __name__ == "__main__":
    asyncio.run(refresh_crew_content())
