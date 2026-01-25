#!/usr/bin/env python3
"""
Test Script: Argument Builder Feature

Tests the parsing service and argument builder endpoints.
Run this after integrating the new files to verify everything works.

Usage:
    python test_argument_builder.py [--base-url http://localhost:8000]

Prerequisites:
    - Wisdom Agent server running
    - At least one KB resource exists (or use --create-test-resource)
"""

import argparse
import requests
import json
import sys
from typing import Optional


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

# Sample content for testing (if no resource exists)
SAMPLE_CONTENT = """
# The Case for Preserving Liberal Democracy

## Introduction

Liberal democracy is under threat worldwide. This document argues that preserving 
democratic institutions is essential for human flourishing and outlines the main 
challenges we face.

## Main Arguments

### 1. Democracy Enables Human Flourishing

Democratic systems allow individuals to participate in decisions that affect their lives.
Studies show that democracies have higher levels of human development (HDI scores 
averaging 0.85 vs 0.65 for autocracies). Citizens in democracies report higher life 
satisfaction and have greater economic mobility.

According to the 2023 Freedom House report, "countries rated Free have GDP per capita 
three times higher than those rated Not Free."

### 2. Democratic Institutions Provide Accountability

Free press, independent judiciary, and regular elections create checks on power.
Without these, corruption flourishes. Transparency International data shows that 
the 20 least corrupt countries are all democracies.

"Sunlight is the best disinfectant" - Louis Brandeis

### 3. Current Threats Are Serious

Multiple indicators show democratic backsliding:
- V-Dem Institute reports 35 countries experienced democratic decline in 2023
- Press freedom has declined for 12 consecutive years (RSF data)
- Trust in institutions at historic lows in many Western democracies

## Recommendations

1. Strengthen civic education
2. Support independent journalism
3. Reform campaign finance
4. Protect electoral integrity

## Conclusion

The evidence is clear: democracy, while imperfect, provides the best framework for 
human flourishing. We must actively work to preserve and strengthen democratic 
institutions.

Sources:
- Freedom House Annual Report 2023
- V-Dem Democracy Report 2023
- Transparency International CPI 2023
"""


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_health_check(base_url: str) -> bool:
    """Test the argument builder health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{base_url}{API_PREFIX}/arguments/health")
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get("status") in ["healthy", "degraded"]:
            print("✅ Health check PASSED")
            return True
        else:
            print("❌ Health check FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Health check ERROR: {e}")
        return False


def test_stats(base_url: str) -> bool:
    """Test the stats endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Stats Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{base_url}{API_PREFIX}/arguments/stats")
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ Stats endpoint PASSED")
            return True
        else:
            print("❌ Stats endpoint FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Stats endpoint ERROR: {e}")
        return False


def create_test_resource(base_url: str) -> Optional[int]:
    """Create a test KB resource for parsing"""
    print("\n" + "="*60)
    print("SETUP: Creating Test Resource")
    print("="*60)
    
    try:
        # First, create a collection
        collection_response = requests.post(
            f"{base_url}{API_PREFIX}/knowledge/collections",
            json={
                "name": "Test Collection - Argument Builder",
                "description": "Test collection for argument builder feature",
                "collection_type": "research"
            }
        )
        
        if collection_response.status_code not in [200, 201]:
            print(f"Failed to create collection: {collection_response.text}")
            return None
        
        collection = collection_response.json()
        collection_id = collection.get("id")
        print(f"Created collection: {collection_id}")
        
        # Now create a resource with sample content
        resource_response = requests.post(
            f"{base_url}{API_PREFIX}/knowledge/collections/{collection_id}/resources",
            json={
                "name": "Test Article - Democracy Arguments",
                "description": "Sample article for testing argument extraction",
                "resource_type": "article",
                "source_type": "text",
                "content": SAMPLE_CONTENT
            }
        )
        
        if resource_response.status_code not in [200, 201]:
            print(f"Failed to create resource: {resource_response.text}")
            return None
        
        resource = resource_response.json()
        resource_id = resource.get("id")
        print(f"✅ Created test resource: {resource_id}")
        return resource_id
        
    except Exception as e:
        print(f"❌ Failed to create test resource: {e}")
        return None


def get_existing_resource(base_url: str) -> Optional[int]:
    """Get an existing KB resource ID"""
    try:
        response = requests.get(f"{base_url}{API_PREFIX}/knowledge/collections")
        if response.status_code != 200:
            return None
        
        collections = response.json()
        if not collections:
            return None
        
        # Get resources from first collection
        collection_id = collections[0].get("id")
        resources_response = requests.get(
            f"{base_url}{API_PREFIX}/knowledge/collections/{collection_id}/resources"
        )
        
        if resources_response.status_code != 200:
            return None
        
        resources = resources_response.json()
        if resources:
            return resources[0].get("id")
        
        return None
        
    except:
        return None


def test_parse_estimate(base_url: str, resource_id: int) -> bool:
    """Test parsing cost estimation"""
    print("\n" + "="*60)
    print("TEST 3: Parse Estimate")
    print("="*60)
    
    try:
        response = requests.post(
            f"{base_url}{API_PREFIX}/arguments/parse/estimate",
            params={"resource_id": resource_id}
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ Parse estimate PASSED")
            return True
        else:
            print("❌ Parse estimate FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Parse estimate ERROR: {e}")
        return False


def test_parse_resource(base_url: str, resource_id: int) -> Optional[int]:
    """Test parsing a resource"""
    print("\n" + "="*60)
    print("TEST 4: Parse Resource")
    print("="*60)
    
    try:
        response = requests.post(
            f"{base_url}{API_PREFIX}/arguments/parse",
            json={
                "resource_id": resource_id,
                "force_reparse": True,
                "extract_claims": True
            }
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get("success"):
            print("✅ Parse resource PASSED")
            print(f"   - Main thesis: {data.get('main_thesis', 'N/A')[:100]}...")
            print(f"   - Claims extracted: {data.get('claim_count', 0)}")
            print(f"   - Evidence extracted: {data.get('evidence_count', 0)}")
            print(f"   - Cost: ${data.get('cost_dollars', 0):.6f}")
            return data.get("parsed_resource_id")
        else:
            print(f"❌ Parse resource FAILED: {data.get('error_message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Parse resource ERROR: {e}")
        return None


def test_get_outline(base_url: str, resource_id: int) -> bool:
    """Test getting the outline view"""
    print("\n" + "="*60)
    print("TEST 5: Get Outline View")
    print("="*60)
    
    try:
        response = requests.get(
            f"{base_url}{API_PREFIX}/arguments/resource/{resource_id}/outline"
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Resource: {data.get('resource_name')}")
            print(f"Main Thesis: {data.get('main_thesis', 'N/A')[:100]}...")
            print(f"Total Claims: {data.get('total_claims', 0)}")
            print(f"Total Evidence: {data.get('total_evidence', 0)}")
            print(f"Outline nodes: {len(data.get('outline', []))}")
            
            # Print first level of outline
            print("\nOutline Structure:")
            for node in data.get('outline', [])[:5]:
                print(f"  - [{node.get('node_type')}] {node.get('title', 'N/A')[:60]}...")
                for child in node.get('children', [])[:2]:
                    print(f"      - [{child.get('node_type')}] {child.get('title', 'N/A')[:50]}...")
            
            print("✅ Get outline PASSED")
            return True
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
            print("❌ Get outline FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Get outline ERROR: {e}")
        return False


def test_get_claims(base_url: str, parsed_resource_id: int) -> bool:
    """Test getting claims for a parsed resource"""
    print("\n" + "="*60)
    print("TEST 6: Get Claims")
    print("="*60)
    
    try:
        response = requests.get(
            f"{base_url}{API_PREFIX}/arguments/parsed/{parsed_resource_id}/claims"
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Claims returned: {len(data) if isinstance(data, list) else 'N/A'}")
        
        if response.status_code == 200 and isinstance(data, list):
            # Print first few claims
            print("\nSample Claims:")
            for claim in data[:3]:
                print(f"  - [{claim.get('claim_type')}] {claim.get('claim_text', 'N/A')[:70]}...")
                print(f"    Evidence items: {len(claim.get('evidence', []))}")
            
            print("✅ Get claims PASSED")
            return True
        else:
            print("❌ Get claims FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Get claims ERROR: {e}")
        return False


def test_resource_status(base_url: str, resource_id: int) -> bool:
    """Test the resource parse status endpoint"""
    print("\n" + "="*60)
    print("TEST 7: Resource Parse Status")
    print("="*60)
    
    try:
        response = requests.get(
            f"{base_url}{API_PREFIX}/arguments/resource/{resource_id}/status"
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ Resource status PASSED")
            return True
        else:
            print("❌ Resource status FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Resource status ERROR: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test Argument Builder Feature")
    parser.add_argument(
        "--base-url", 
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the Wisdom Agent server (default: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--create-test-resource",
        action="store_true",
        help="Create a test resource if none exists"
    )
    parser.add_argument(
        "--resource-id",
        type=int,
        help="Specific resource ID to test with"
    )
    parser.add_argument(
        "--skip-parsing",
        action="store_true",
        help="Skip the parsing test (if resource already parsed)"
    )
    
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    
    print("="*60)
    print("ARGUMENT BUILDER FEATURE TEST")
    print("="*60)
    print(f"Base URL: {base_url}")
    
    # Track results
    results = {}
    
    # Test 1: Health check
    results["health"] = test_health_check(base_url)
    
    # Test 2: Stats
    results["stats"] = test_stats(base_url)
    
    # Get or create a resource for testing
    resource_id = args.resource_id
    
    if not resource_id:
        resource_id = get_existing_resource(base_url)
        
    if not resource_id and args.create_test_resource:
        resource_id = create_test_resource(base_url)
    
    if not resource_id:
        print("\n⚠️  No resource available for parsing tests.")
        print("   Use --create-test-resource to create one, or --resource-id to specify one.")
    else:
        print(f"\nUsing resource ID: {resource_id}")
        
        # Test 3: Parse estimate
        results["estimate"] = test_parse_estimate(base_url, resource_id)
        
        # Test 4: Parse resource
        parsed_resource_id = None
        if not args.skip_parsing:
            parsed_resource_id = test_parse_resource(base_url, resource_id)
            results["parse"] = parsed_resource_id is not None
        else:
            print("\n⏭️  Skipping parse test (--skip-parsing)")
            # Try to get existing parsed resource ID
            status_response = requests.get(
                f"{base_url}{API_PREFIX}/arguments/resource/{resource_id}/status"
            )
            if status_response.status_code == 200:
                status = status_response.json()
                if status.get("is_parsed"):
                    parsed_resource_id = status.get("parsed_resource_id")
        
        # Test 5: Get outline
        results["outline"] = test_get_outline(base_url, resource_id)
        
        # Test 6: Get claims (if we have a parsed resource)
        if parsed_resource_id:
            results["claims"] = test_get_claims(base_url, parsed_resource_id)
        
        # Test 7: Resource status
        results["status"] = test_resource_status(base_url, resource_id)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print("-"*60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Argument Builder is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
