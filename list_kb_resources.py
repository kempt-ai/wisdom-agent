#!/usr/bin/env python3
"""
List all Knowledge Base resources using the API.
Make sure the backend is running first (uvicorn backend.main:app --reload)
"""

import requests
import json

API_BASE = "http://localhost:8000"


def list_kb_resources():
    """List all KB resources with their IDs."""
    print("=" * 80)
    print("KNOWLEDGE BASE RESOURCES")
    print("=" * 80)
    
    try:
        # Get all collections
        response = requests.get(f"{API_BASE}/api/knowledge/collections")
        
        if response.status_code != 200:
            print(f"\n✗ Error: API returned {response.status_code}")
            print(f"   Make sure backend is running: uvicorn backend.main:app --reload")
            return
        
        collections = response.json()
        
        if not collections:
            print("\n⚠️  No collections found. Create some resources first!")
            return
        
        print(f"\nFound {len(collections)} collection(s)\n")
        
        total_resources = 0
        all_resources = []
        
        for collection in collections:
            coll_name = collection.get('name', 'Unnamed Collection')
            print(f"📁 Collection: {coll_name}")
            print(f"   ID: {collection.get('id', 'N/A')}")
            print(f"   Description: {collection.get('description', 'N/A')}")
            
            # Get resources in this collection
            coll_id = collection.get('id')
            if not coll_id:
                print(f"   └─ (no ID found)")
                continue
                
            res_response = requests.get(
                f"{API_BASE}/api/knowledge/collections/{coll_id}/resources"
            )
            
            if res_response.status_code != 200:
                print(f"   └─ (error loading resources: {res_response.status_code})")
                continue
            
            resources = res_response.json()
            
            if not resources:
                print(f"   └─ (no resources)")
            else:
                print(f"   └─ {len(resources)} resource(s):")
                for resource in resources:
                    total_resources += 1
                    all_resources.append(resource)
                    
                    # Get title - try multiple possible field names
                    title = (resource.get('title') or 
                            resource.get('name') or 
                            resource.get('url', 'Untitled')[:50] or 
                            'Untitled Resource')
                    
                    # Truncate title if too long
                    if len(title) > 60:
                        title = title[:60] + "..."
                    
                    # Show content length - handle if content is not present
                    content = resource.get('content', '')
                    if content is None:
                        content = ''
                    content_len = len(content)
                    content_kb = content_len / 1024
                    
                    res_id = resource.get('id', '?')
                    res_type = resource.get('resource_type') or resource.get('type', 'unknown')
                    
                    print(f"      [{res_id}] {title}")
                    print(f"          Type: {res_type}")
                    print(f"          Content: {content_kb:.1f} KB ({content_len:,} chars)")
                    
                    url = resource.get('url')
                    if url:
                        if len(url) > 70:
                            url = url[:70] + "..."
                        print(f"          URL: {url}")
                    
                    # Debug: show available fields
                    # print(f"          Fields: {list(resource.keys())}")
            
            print()
        
        print("─" * 80)
        print(f"Total: {total_resources} resource(s) across {len(collections)} collection(s)")
        print("─" * 80)
        
        # Suggest resources for testing
        if total_resources > 0:
            print("\n🧪 To test parsing truncation:")
            print("   python diagnose_parsing_truncation.py --resource-id <ID> --compare-all")
            print("\n💡 Tip: Pick a larger resource (>5 KB) to test truncation issues")
            
            # Sort by size
            all_resources.sort(
                key=lambda r: len(r.get('content', '') or ''),
                reverse=True
            )
            
            if all_resources:
                print("\n📊 Largest resources (good for testing):")
                for i, resource in enumerate(all_resources[:5]):
                    title = (resource.get('title') or 
                            resource.get('name') or 
                            resource.get('url', '')[:50] or 
                            'Untitled')
                    if len(title) > 50:
                        title = title[:50] + "..."
                    
                    content = resource.get('content', '') or ''
                    size = len(content)
                    res_id = resource.get('id', '?')
                    print(f"   [{res_id}] {title} ({size/1024:.1f} KB)")
    
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to backend!")
        print("   Make sure it's running: uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def show_resource_details(resource_id: int):
    """Show detailed information about a specific resource."""
    print("=" * 80)
    print(f"RESOURCE DETAILS: ID #{resource_id}")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_BASE}/api/knowledge/resources/{resource_id}")
        
        if response.status_code == 404:
            print(f"\n✗ Resource #{resource_id} not found")
            return
        elif response.status_code != 200:
            print(f"\n✗ Error: API returned {response.status_code}")
            return
        
        resource = response.json()
        
        # Show all available fields
        print(f"\nAvailable fields: {list(resource.keys())}")
        
        title = (resource.get('title') or 
                resource.get('name') or 
                resource.get('url', '')[:50] or 
                'Untitled')
        
        print(f"\nTitle: {title}")
        print(f"Type: {resource.get('resource_type') or resource.get('type', 'unknown')}")
        print(f"Created: {resource.get('created_at', 'unknown')}")
        
        url = resource.get('url')
        if url:
            print(f"URL: {url}")
        
        content = resource.get('content', '') or ''
        content_len = len(content)
        print(f"\nContent length: {content_len:,} characters ({content_len / 1024:.1f} KB)")
        
        # Estimate tokens
        tokens = content_len // 4
        print(f"Estimated tokens: {tokens:,}")
        
        # Show first 500 chars of content
        if content:
            print(f"\nContent preview:")
            print("─" * 80)
            preview = content[:500]
            print(preview)
            if len(content) > 500:
                print("...")
            print("─" * 80)
        
        print("\n🧪 Test this resource:")
        print(f"   python diagnose_parsing_truncation.py --resource-id {resource_id} --compare-all")
    
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to backend!")
        print("   Make sure it's running: uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="List KB resources via API")
    parser.add_argument(
        "--resource-id",
        type=int,
        help="Show details for specific resource ID"
    )
    
    args = parser.parse_args()
    
    if args.resource_id:
        show_resource_details(args.resource_id)
    else:
        list_kb_resources()
