"""
Wisdom Agent - Fact Checker Diagnostic Script (Fixed)

Run from the wisdom-agent folder:
    python diagnose_factcheck.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix import path - add the project root to Python's path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def ok(msg):
    print(f"{GREEN}✓ PASS:{RESET} {msg}")

def fail(msg, detail=None):
    print(f"{RED}✗ FAIL:{RESET} {msg}")
    if detail:
        print(f"  {RED}→ {detail}{RESET}")

def warn(msg):
    print(f"{YELLOW}⚠ WARN:{RESET} {msg}")

def section(title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")


async def main():
    print(f"\n{BOLD}WISDOM AGENT FACT CHECKER DIAGNOSTIC{RESET}")
    print("This script tests each component of the fact-checking pipeline.\n")

    # =========================================================================
    section("1. ENVIRONMENT VARIABLES")
    # =========================================================================
    
    env_vars = {
        "CLAIMBUSTER_API_KEY": os.getenv("CLAIMBUSTER_API_KEY"),
        "GOOGLE_FACT_CHECK_API_KEY": os.getenv("GOOGLE_FACT_CHECK_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }
    
    for var, value in env_vars.items():
        if value:
            ok(f"{var} is set ({len(value)} chars)")
        else:
            if var in ["CLAIMBUSTER_API_KEY", "GOOGLE_FACT_CHECK_API_KEY"]:
                warn(f"{var} not set (fact-checking will use LLM fallback)")
            else:
                warn(f"{var} not set")

    # =========================================================================
    section("2. DATABASE CONNECTION")
    # =========================================================================
    
    try:
        from backend.database.connection import get_db_session
        from sqlalchemy import text
        with get_db_session() as db:
            result = db.execute(text("SELECT 1")).scalar()
            if result == 1:
                ok("Database connection works")
    except Exception as e:
        fail("Database connection failed", str(e))
        return

    # =========================================================================
    section("3. PROVIDER REGISTRY")
    # =========================================================================
    
    try:
        from backend.providers import get_provider_registry, ProviderType
        registry = get_provider_registry()
        ok("Provider registry initialized")
        
        # Check each provider
        for ptype in ProviderType:
            provider = registry.get_provider(ptype)
            if provider:
                try:
                    available = await provider.is_available()
                    if available:
                        ok(f"Provider {ptype.value}: available")
                    else:
                        warn(f"Provider {ptype.value}: registered but not available")
                except Exception as e:
                    fail(f"Provider {ptype.value}: error checking availability", str(e))
            else:
                warn(f"Provider {ptype.value}: not registered")
                
    except ImportError as e:
        fail("Could not import provider registry", str(e))
        print(f"\n  This likely means backend/providers/__init__.py is missing or broken.")
    except Exception as e:
        fail("Provider registry error", str(e))

    # =========================================================================
    section("4. SERVICE INITIALIZATION")
    # =========================================================================
    
    services = {}
    
    # Content extraction
    try:
        from backend.services.content_extraction_service import get_content_extraction_service
        services['content'] = get_content_extraction_service()
        ok("Content extraction service initialized")
    except Exception as e:
        fail("Content extraction service failed", str(e))
    
    # Claim extraction
    try:
        from backend.services.claim_extraction_service import get_claim_extraction_service
        services['claims'] = get_claim_extraction_service()
        ok("Claim extraction service initialized")
    except Exception as e:
        fail("Claim extraction service failed", str(e))
    
    # Fact check
    try:
        from backend.services.fact_check_service import get_fact_check_service
        services['factcheck'] = get_fact_check_service()
        ok("Fact check service initialized")
    except Exception as e:
        fail("Fact check service failed", str(e))
    
    # Logic analysis
    try:
        from backend.services.logic_analysis_service import get_logic_analysis_service
        services['logic'] = get_logic_analysis_service()
        ok("Logic analysis service initialized")
    except Exception as e:
        fail("Logic analysis service failed", str(e))
    
    # Wisdom evaluation
    try:
        from backend.services.wisdom_evaluation_service import get_wisdom_evaluation_service
        services['wisdom'] = get_wisdom_evaluation_service()
        ok("Wisdom evaluation service initialized")
    except Exception as e:
        fail("Wisdom evaluation service failed", str(e))

    # =========================================================================
    section("5. LLM ROUTER")
    # =========================================================================
    
    try:
        from backend.services.llm_router import get_llm_router
        llm = get_llm_router()
        ok("LLM router initialized")
        
        # Test a simple completion
        try:
            response = llm.complete(
                messages=[{"role": "user", "content": "Say 'test' and nothing else."}],
                temperature=0
            )
            if response and len(response) > 0:
                ok(f"LLM completion works (response: '{response[:50].strip()}')")
            else:
                fail("LLM returned empty response")
        except Exception as e:
            fail("LLM completion failed", str(e))
            
    except Exception as e:
        fail("LLM router initialization failed", str(e))

    # =========================================================================
    section("6. TEST PIPELINE ON EXISTING REVIEW")
    # =========================================================================
    
    test_content = """
    The Earth is approximately 4.5 billion years old. Scientists have determined 
    this through radiometric dating of meteorites. The moon was formed about 
    4.5 billion years ago when a Mars-sized object collided with Earth.
    """
    
    # Test claim extraction directly
    if 'claims' in services:
        try:
            from backend.database.connection import get_db_session
            from backend.database.fact_check_models import ContentReview
            from sqlalchemy import select
            
            with get_db_session() as db:
                existing = db.execute(
                    select(ContentReview).limit(1)
                ).scalar_one_or_none()
                
                if existing:
                    test_review_id = existing.id
                    ok(f"Found existing review ID {test_review_id} for testing")
                else:
                    warn("No existing reviews found - create one via the UI first, then re-run")
                    test_review_id = None
            
            if test_review_id:
                # Test claim extraction
                print("\nTesting claim extraction on sample text...")
                try:
                    claims = await services['claims'].extract_claims(test_review_id, test_content)
                    if claims:
                        ok(f"Claim extraction returned {len(claims)} claims")
                        for i, claim in enumerate(claims[:3]):
                            text = claim.get('claim_text', 'N/A')[:60]
                            print(f"    Claim {i+1}: {text}...")
                    else:
                        warn("Claim extraction returned no claims (LLM may not be parsing JSON correctly)")
                except Exception as e:
                    fail("Claim extraction raised exception", str(e))
                    import traceback
                    traceback.print_exc()
                
                # Test fact checking
                print("\nTesting fact check service...")
                try:
                    if 'factcheck' in services and claims:
                        results = await services['factcheck'].fact_check_claims(test_review_id, claims)
                        if results:
                            ok(f"Fact check returned {len(results)} results")
                            for r in results[:3]:
                                verdict = r.get('verdict', 'N/A')
                                error = r.get('error', None)
                                text = r.get('claim_text', 'N/A')[:40]
                                if error:
                                    print(f"    ERROR: {text}... → {error}")
                                else:
                                    print(f"    {verdict}: {text}...")
                        else:
                            warn("Fact check returned empty results")
                    elif not claims:
                        warn("Skipping fact check test - no claims to check")
                except Exception as e:
                    fail("Fact check raised exception", str(e))
                    import traceback
                    traceback.print_exc()

                # Test logic analysis  
                print("\nTesting logic analysis...")
                try:
                    if 'logic' in services:
                        result = await services['logic'].analyze_logic(test_review_id, test_content)
                        if result:
                            ok(f"Logic analysis completed")
                            if result.get('main_conclusion'):
                                print(f"    Main conclusion: {result['main_conclusion'][:60]}...")
                        else:
                            warn("Logic analysis returned empty result")
                except Exception as e:
                    fail("Logic analysis raised exception", str(e))
                    import traceback
                    traceback.print_exc()

                # Test wisdom evaluation
                print("\nTesting wisdom evaluation...")
                try:
                    if 'wisdom' in services:
                        await services['wisdom'].evaluate_wisdom(test_review_id, test_content)
                        ok("Wisdom evaluation completed (check database for results)")
                except Exception as e:
                    fail("Wisdom evaluation raised exception", str(e))
                    import traceback
                    traceback.print_exc()
                        
        except Exception as e:
            fail("Pipeline test setup failed", str(e))
            import traceback
            traceback.print_exc()

    # =========================================================================
    section("7. CHECK DATABASE FOR RESULTS")
    # =========================================================================
    
    try:
        from backend.database.connection import get_db_session
        from backend.database.fact_check_models import (
            ContentReview, ExtractedClaim, FactCheckResult, 
            LogicAnalysis, WisdomEvaluation
        )
        from sqlalchemy import select, func
        
        with get_db_session() as db:
            # Count records
            reviews = db.execute(select(func.count()).select_from(ContentReview)).scalar()
            claims = db.execute(select(func.count()).select_from(ExtractedClaim)).scalar()
            fact_results = db.execute(select(func.count()).select_from(FactCheckResult)).scalar()
            logic = db.execute(select(func.count()).select_from(LogicAnalysis)).scalar()
            wisdom = db.execute(select(func.count()).select_from(WisdomEvaluation)).scalar()
            
            print(f"Database record counts:")
            print(f"  Content Reviews:    {reviews}")
            print(f"  Extracted Claims:   {claims}")
            print(f"  Fact Check Results: {fact_results}")
            print(f"  Logic Analyses:     {logic}")
            print(f"  Wisdom Evaluations: {wisdom}")
            
            if claims > 0 and fact_results == 0:
                warn("Claims exist but no fact check results - fact checking is failing")
            if reviews > 0 and logic == 0:
                warn("Reviews exist but no logic analyses - logic analysis is failing")
            if reviews > 0 and wisdom == 0:
                warn("Reviews exist but no wisdom evaluations - wisdom evaluation is failing")
                
    except Exception as e:
        fail("Database check failed", str(e))

    # =========================================================================
    section("SUMMARY & NEXT STEPS")
    # =========================================================================
    
    print("""
Based on the results above:

1. If PROVIDER issues → Check backend/providers/__init__.py and related files
2. If LLM issues → Check API keys in .env and backend/services/llm_router.py  
3. If SERVICE init issues → Check the specific service file that failed
4. If PIPELINE test issues → The traceback shows exactly where it breaks
5. If DATABASE shows 0 results → The pipeline isn't completing successfully

Copy this entire output and paste it at the start of your next Claude session
along with the relevant files from the Priority 1 list in your fix plan.
""")


if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Note: python-dotenv not installed, using system environment variables")
    
    asyncio.run(main())
