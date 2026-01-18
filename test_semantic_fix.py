#!/usr/bin/env python3
"""
Test script for Google Fact Check semantic mismatch fix.

This tests that the fact-checker correctly distinguishes between:
- Fact-checks about what someone SAID (their claims)
- Fact-checks about WHO someone IS (their position/role)

Run with: python test_semantic_fix.py

Requires: Backend running at localhost:8000
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

# Test cases with longer content to pass minimum character thresholds
# The claim extraction service requires ~100+ characters
TEST_CASES = [
    {
        "name": "RFK Jr. Position (the bug case)",
        "content": """
        According to recent news reports, Robert F. Kennedy Jr. has been appointed 
        to a senior position in the federal government. RFK Jr. is the Health Secretary, 
        having been nominated by the President and confirmed by the Senate. This 
        appointment has been controversial given his previous public statements on 
        various health topics. His role will involve overseeing the Department of 
        Health and Human Services and setting health policy priorities.
        """,
        "key_claim": "RFK Jr. is the Health Secretary",
        "description": "Should NOT be marked false based on his vaccine misinformation fact-checks",
        "expected_behavior": "Should use LLM verification, not external fact-checks about vaccines"
    },
    {
        "name": "Actual vaccine claim",
        "content": """
        There has been ongoing debate about vaccine safety in recent years. Some 
        people continue to believe that vaccines cause autism in children, despite 
        extensive scientific research disproving this claim. The original study 
        that suggested this link was retracted and its author lost his medical 
        license. Major health organizations worldwide have confirmed that vaccines 
        do not cause autism and are safe and effective for children.
        """,
        "key_claim": "vaccines cause autism in children",
        "description": "SHOULD find and use existing fact-checks",
        "expected_behavior": "Should find external fact-checks and return 'false'"
    },
    {
        "name": "Super PAC rules",
        "content": """
        Campaign finance in the United States operates under complex rules established 
        by the Federal Election Commission and shaped by Supreme Court decisions. 
        Super PACs can raise unlimited amounts of money from corporations, unions, 
        and individuals. However, they are prohibited from donating directly to or 
        coordinating with political campaigns. This system was largely established 
        after the Citizens United decision in 2010, which fundamentally changed 
        how money flows in American elections.
        """,
        "key_claim": "Super PACs can raise unlimited amounts of money",
        "description": "Should NOT be affected by fact-checks about specific donations",
        "expected_behavior": "Should verify the general rule, not specific donation claims"
    },
]


def create_review(content: str) -> dict:
    """Create a review for content."""
    response = requests.post(
        f"{BASE_URL}/api/reviews",
        json={
            "source_type": "text",
            "source_content": content.strip()
        },
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json()


def get_review(review_id: int) -> dict:
    """Get review results."""
    response = requests.get(f"{BASE_URL}/api/reviews/{review_id}")
    response.raise_for_status()
    return response.json()


def wait_for_completion(review_id: int, max_wait: int = 180) -> dict:
    """Poll until review is complete."""
    start = time.time()
    while time.time() - start < max_wait:
        review = get_review(review_id)
        status = review.get("status", "unknown")
        
        if status == "completed":
            return review
        elif status == "failed":
            print(f"  ❌ Review failed: {review.get('error', 'unknown error')}")
            return review
        
        print(f"  ⏳ Status: {status}... waiting")
        time.sleep(5)
    
    print(f"  ⚠️ Timeout after {max_wait}s")
    return get_review(review_id)


def analyze_result(review: dict, test_case: dict) -> None:
    """Analyze and display the result."""
    claims = review.get("claims", [])
    
    if not claims:
        print("  ⚠️ No claims extracted")
        return
    
    print(f"\n  📊 Found {len(claims)} claim(s)")
    
    # Find the claim most relevant to our test
    key_claim_lower = test_case["key_claim"].lower()
    
    for i, claim in enumerate(claims, 1):
        claim_text = claim.get("claim_text", "")
        fact_result = claim.get("fact_check_result") or {}  # Handle None
        
        # Check if this claim matches our key claim
        is_key_claim = key_claim_lower in claim_text.lower()
        marker = "🎯" if is_key_claim else "  "
        
        verdict = fact_result.get("verdict", "unknown") if fact_result else "pending"
        confidence = fact_result.get("confidence", 0)
        providers = fact_result.get("providers_used", [])
        external_matches = fact_result.get("external_matches", [])
        web_sources = fact_result.get("web_sources", [])
        explanation = (fact_result.get("explanation", "") or "")[:150]
        
        print(f"\n  {marker} Claim {i}: {claim_text[:70]}...")
        print(f"     Verdict: {verdict} (confidence: {confidence:.2f})")
        print(f"     Providers: {providers}")
        
        if external_matches:
            print(f"     External matches: {len(external_matches)}")
            for match in external_matches[:2]:
                match_claim = match.get("claim_text", "")[:50]
                match_rating = match.get("rating", "unknown")
                print(f"       - \"{match_claim}...\" → {match_rating}")
        
        if web_sources:
            print(f"     Web sources: {len(web_sources)}")
        
        if explanation:
            print(f"     Explanation: {explanation}...")
        
        # Special analysis for the RFK Jr. bug case
        if is_key_claim and test_case["name"] == "RFK Jr. Position (the bug case)":
            if external_matches:
                # Check if any external match is about vaccines (the bug)
                vaccine_matches = [m for m in external_matches 
                                   if "vaccin" in m.get("claim_text", "").lower()
                                   or "autism" in m.get("claim_text", "").lower()]
                if vaccine_matches:
                    print("\n  ❌ BUG DETECTED: Using vaccine fact-checks for position claim!")
                    print(f"     Found {len(vaccine_matches)} irrelevant vaccine-related match(es)")
                else:
                    print("\n  ✅ External matches appear relevant (not about vaccines)")
            else:
                if "llm" in str(providers).lower() or "llm_fallback" in providers:
                    print("\n  ✅ Correctly used LLM verification (no irrelevant external matches)")
                else:
                    print("\n  ℹ️  No external matches found")


def run_tests():
    """Run all test cases."""
    print("=" * 70)
    print("GOOGLE FACT CHECK SEMANTIC MISMATCH FIX - TEST SUITE")
    print("=" * 70)
    
    # Check backend is running
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            raise Exception("Backend not responding correctly")
    except Exception as e:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print(f"   Error: {e}")
        print("\nMake sure the backend is running:")
        print("   uvicorn backend.main:app --reload")
        sys.exit(1)
    
    print(f"✅ Backend connected at {BASE_URL}")
    print(f"\nNote: Each test may take 30-60 seconds for LLM analysis...\n")
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'='*70}")
        print(f"Key claim: \"{test_case['key_claim']}\"")
        print(f"Expected: {test_case['expected_behavior']}")
        print("-" * 70)
        
        try:
            # Create review
            print("Creating review...")
            result = create_review(test_case["content"])
            review_id = result.get("id")
            print(f"  Review ID: {review_id}")
            
            # Wait for completion
            print("Waiting for analysis (this may take a minute)...")
            review = wait_for_completion(review_id)
            
            # Analyze results
            analyze_result(review, test_case)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    print("=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    print("\nInterpretation guide:")
    print("1. RFK Jr. position claim should NOT show vaccine-related external matches")
    print("   - If it shows vaccine fact-checks → BUG STILL PRESENT")
    print("   - If it uses LLM verification → FIX WORKING")
    print("2. Vaccine claim SHOULD find relevant fact-checks with 'false' verdict")
    print("3. Super PAC claim should verify the rule itself, not specific cases")


if __name__ == "__main__":
    run_tests()
