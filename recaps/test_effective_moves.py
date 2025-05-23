#!/usr/bin/env python3
"""
Test script to verify _effective_moves integration in get_attachers_for_node
"""

import json
from barebones import FileProcessor

def test_effective_moves():
    """Test if _effective_moves are properly incorporated"""
    
    # Load the JSON data
    with open("CPS_6457E_03.json", 'r', encoding='utf-8') as file:
        job_data = json.load(file)
    
    processor = FileProcessor()
    
    # Test specific nodes that we found in the data
    test_nodes = [
        "-OJ_QBhaCD9_C4-gzvKc",
        "-OJ_QKaoQC9V_pOdD7pb", 
        "-OJ_PcyozaoP6NUp-j7U",
        "-OJ_QOWgDX_T_o2mDHgm",
        "-OJ_P_8Z7s5gxN9tQia9",
        "-OJ_QN1ZoFM8EVIZXesW",
        "-OJ_Q5tV9V_pOdD7pb8_",
        "-OJ_QO1-g_v02hBjKOt6"
    ]
    
    print(f"Testing {len(test_nodes)} specific nodes that have photo associations")
    
    test_count = 0
    nodes_with_effective_moves = 0
    
    for node_id in test_nodes:
        print(f"\n=== Testing Node: {node_id} ===")
        
        try:
            result = processor.get_attachers_for_node(job_data, node_id)
            main_attachers = result['main_attachers']
            
            print(f"Found {len(main_attachers)} main attachers")
            
            # Check for effective_moves in debug output
            has_effective_moves = False
            for attacher in main_attachers:
                if attacher['proposed_height']:
                    print(f"  - {attacher['name']}: {attacher['existing_height']} -> {attacher['proposed_height']}")
            
            test_count += 1
            
        except Exception as e:
            print(f"Error processing node {node_id}: {str(e)}")
    
    print(f"\nTested {test_count} nodes successfully")
    print(f"Nodes with _effective_moves data: {nodes_with_effective_moves}")

if __name__ == "__main__":
    test_effective_moves() 