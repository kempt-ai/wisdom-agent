#!/usr/bin/env python3
"""
Show what prompt is actually being sent to the LLM for parsing.
This helps diagnose if the prompt is asking for hierarchical arguments or just flat claims.
"""

import requests
import json

API_BASE = "http://localhost:8000"


def inspect_parsed_structure(parsed_id: int):
    """
    Fetch a parsed resource and show its complete JSON structure.
    This reveals what the LLM actually returned.
    """
    print("=" * 80)
    print(f"INSPECTING PARSED RESOURCE #{parsed_id}")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_BASE}/api/arguments/parsed/{parsed_id}")
        
        if response.status_code != 200:
            print(f"✗ Could not fetch: {response.status_code}")
            return
        
        parsed = response.json()
        
        # Show metadata
        print("\n📊 Metadata:")
        print(f"  Parse level: {parsed.get('parse_level')}")
        print(f"  Parser model: {parsed.get('parser_model')}")
        print(f"  Created: {parsed.get('created_at')}")
        print(f"  Cost: ${parsed.get('parsing_cost_dollars', 0):.6f}")
        
        # Get and parse the structure JSON
        structure_json = parsed.get('structure_json')
        
        if not structure_json:
            print("\n✗ No structure_json found!")
            return
        
        if isinstance(structure_json, str):
            structure = json.loads(structure_json)
        else:
            structure = structure_json
        
        # Show complete structure with formatting
        print("\n📋 COMPLETE JSON STRUCTURE:")
        print("─" * 80)
        print(json.dumps(structure, indent=2))
        print("─" * 80)
        
        # Analysis
        print("\n🔍 STRUCTURE ANALYSIS:")
        
        # Top-level fields
        print(f"\n  Top-level fields: {list(structure.keys())}")
        
        # Main thesis
        thesis = structure.get('main_thesis', '')
        print(f"\n  Main thesis length: {len(thesis)} chars")
        
        # Arguments
        arguments = structure.get('arguments', [])
        print(f"\n  Arguments array length: {len(arguments)}")
        
        if arguments:
            print(f"  ✓ Arguments exist!")
            print(f"\n  First argument structure:")
            first_arg = arguments[0]
            print(f"    Keys: {list(first_arg.keys())}")
            print(f"    Title: {first_arg.get('title', 'N/A')}")
            print(f"    Claims in this argument: {len(first_arg.get('claims', []))}")
            
            # Show all argument titles
            print(f"\n  All argument titles:")
            for i, arg in enumerate(arguments, 1):
                print(f"    {i}. {arg.get('title', 'Untitled')}")
        else:
            print(f"  ✗ Arguments array is empty!")
        
        # Top-level claims (shouldn't exist in hierarchical structure)
        top_claims = structure.get('claims', [])
        print(f"\n  Top-level claims array length: {len(top_claims)}")
        
        if top_claims:
            print(f"  ⚠️  Top-level claims found! This suggests flat structure.")
            print(f"\n  First claim:")
            first_claim = top_claims[0]
            print(f"    Keys: {list(first_claim.keys())}")
            if 'claim_text' in first_claim:
                print(f"    Text: {first_claim['claim_text'][:100]}...")
        
        # Sources
        sources = structure.get('sources_cited', [])
        print(f"\n  Sources cited: {len(sources)}")
        if sources:
            print(f"    {sources[:3]}...")
        
        # Diagnosis
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        
        if arguments and len(arguments) > 0:
            print("\n✓ HIERARCHICAL structure detected")
            print("  The LLM is returning properly nested arguments with claims")
            print("  If UI shows 'Arguments: 0', the problem is in counting/display logic")
        elif top_claims and len(top_claims) > 0:
            print("\n✗ FLAT structure detected")
            print("  The LLM is returning claims but not organizing them into arguments")
            print("  The parsing prompt likely doesn't request hierarchical structure")
        else:
            print("\n❓ UNCLEAR structure")
            print("  No arguments and no top-level claims found")
            print("  The parsing may have failed or returned unexpected format")
        
    except json.JSONDecodeError as e:
        print(f"\n✗ JSON error: {e}")
        print("The structure_json contains invalid JSON - parsing failed mid-stream")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def compare_parse_levels(resource_id: int):
    """
    Compare how different parse levels structure the same resource.
    """
    print("\n" + "=" * 80)
    print(f"COMPARING PARSE LEVELS FOR RESOURCE #{resource_id}")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_BASE}/api/arguments/resource/{resource_id}/parses")
        
        if response.status_code != 200:
            print(f"✗ Could not fetch parses: {response.status_code}")
            return
        
        parses = response.json()
        
        if not parses:
            print("No parses found for this resource")
            return
        
        print(f"\nFound {len(parses)} parse(s):\n")
        
        # Sort by parse level
        level_order = {"light": 1, "standard": 2, "full": 3}
        parses.sort(key=lambda p: level_order.get(p.get('parse_level', 'unknown'), 99))
        
        for parse in parses:
            parse_id = parse.get('id')
            level = parse.get('parse_level', 'unknown')
            model = parse.get('parser_model', 'unknown')
            
            print(f"{'─' * 80}")
            print(f"Parse #{parse_id} - {level.upper()} level")
            print(f"Model: {model}")
            print(f"{'─' * 80}")
            
            # Get full structure
            detail_response = requests.get(f"{API_BASE}/api/arguments/parsed/{parse_id}")
            if detail_response.status_code == 200:
                detail = detail_response.json()
                structure_json = detail.get('structure_json')
                
                if structure_json:
                    if isinstance(structure_json, str):
                        structure = json.loads(structure_json)
                    else:
                        structure = structure_json
                    
                    args = structure.get('arguments', [])
                    claims = structure.get('claims', [])
                    
                    print(f"  Arguments: {len(args)}")
                    print(f"  Top-level claims: {len(claims)}")
                    
                    if args:
                        print(f"  Argument titles:")
                        for arg in args[:5]:  # Show first 5
                            print(f"    - {arg.get('title', 'Untitled')}")
                        if len(args) > 5:
                            print(f"    ... and {len(args) - 5} more")
            print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Inspect parsed structure in detail")
    parser.add_argument(
        "--parsed-id",
        type=int,
        help="Specific parsed resource ID to inspect"
    )
    parser.add_argument(
        "--resource-id",
        type=int,
        help="Compare all parses for this resource"
    )
    
    args = parser.parse_args()
    
    if args.parsed_id:
        inspect_parsed_structure(args.parsed_id)
    elif args.resource_id:
        compare_parse_levels(args.resource_id)
    else:
        print("Usage:")
        print("  Inspect specific parse:  --parsed-id 10")
        print("  Compare all levels:      --resource-id 4")
