# Save as: diagnose_extraction.py
# Run from: wisdom-agent directory

import asyncio
import trafilatura
import requests

URL = 'https://www.citizensforethics.org/reports-investigations/crew-reports/how-president-trump-is-dismantling-our-democracy-one-piece-at-a-time/'

def test_extraction():
    print("=" * 60)
    print("CREW ARTICLE EXTRACTION DIAGNOSTIC")
    print("=" * 60)
    
    # Test 1: Can trafilatura fetch?
    print("\n1. TRAFILATURA FETCH TEST")
    downloaded = trafilatura.fetch_url(URL)
    print(f"   trafilatura.fetch_url returned: {len(downloaded) if downloaded else 0} chars")
    
    # Test 2: Try requests with proper headers
    print("\n2. REQUESTS WITH USER-AGENT")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        print(f"   HTTP Status: {response.status_code}")
        print(f"   HTML length: {len(response.text)} chars")
        html = response.text
    except Exception as e:
        print(f"   Error: {e}")
        html = downloaded
    
    if not html:
        print("\n   ERROR: Could not download page!")
        return
    
    # Test 3: Extract with different settings
    print("\n3. EXTRACTION COMPARISON")
    
    # Default
    content_default = trafilatura.extract(html)
    print(f"   Default:        {len(content_default) if content_default else 0} chars, "
          f"{len(content_default.split()) if content_default else 0} words")
    
    # With favor_recall (captures more)
    content_recall = trafilatura.extract(html, favor_recall=True)
    print(f"   favor_recall:   {len(content_recall) if content_recall else 0} chars, "
          f"{len(content_recall.split()) if content_recall else 0} words")
    
    # With everything enabled
    content_full = trafilatura.extract(
        html, 
        favor_recall=True, 
        include_tables=True,
        include_comments=False,
        include_formatting=True
    )
    print(f"   Full settings:  {len(content_full) if content_full else 0} chars, "
          f"{len(content_full.split()) if content_full else 0} words")
    
    # Test 4: Check for timeline markers
    print("\n4. TIMELINE CONTENT CHECK")
    test_content = content_full or content_recall or content_default
    if test_content:
        months = ['January 2025', 'February 2025', 'March 2025', 'April 2025', 
                  'May 2025', 'June 2025', 'July 2025', 'August 2025',
                  'September 2025', 'October 2025', 'November 2025']
        found = [m for m in months if m in test_content]
        missing = [m for m in months if m not in test_content]
        print(f"   Months found:   {len(found)}/11 - {found}")
        print(f"   Months missing: {missing}")
        
        # Check for specific dates
        if 'Jan 20, 2025' in test_content:
            print("   ✓ First timeline entry (Jan 20) found")
        else:
            print("   ✗ First timeline entry (Jan 20) NOT found")
            
        if 'Nov 20, 2025' in test_content:
            print("   ✓ Late timeline entry (Nov 20) found")
        else:
            print("   ✗ Late timeline entry (Nov 20) NOT found")
    
    # Test 5: Show what your content_extractor would store
    print("\n5. PREVIEW OF EXTRACTED CONTENT")
    if test_content:
        print(f"   First 500 chars:\n   {test_content[:500]}")
        print(f"\n   Last 500 chars:\n   {test_content[-500:]}")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    if content_full and len(content_full) > 10000:
        print("   ✓ Full extraction works - update content_extractor.py to use favor_recall=True")
    elif content_recall and len(content_recall) > 5000:
        print("   ✓ Recall mode captures more - update content_extractor.py to use favor_recall=True")
    else:
        print("   ✗ Trafilatura not capturing timeline - may need fallback extractor")

if __name__ == "__main__":
    test_extraction()
