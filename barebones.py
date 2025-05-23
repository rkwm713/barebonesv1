import pandas as pd
import json
import datetime
import os
import math
from collections import defaultdict

# === Constants for Attachment and Span Labels ===
EXISTING_ATTACHMENT_HEIGHT = "Attachment Height - Existing"
MR_MOVE = "MR Move"
EFFECTIVE_MOVE = "Effective Move"
PROPOSED_ATTACHMENT_HEIGHT = "Attachment Height - Proposed"

EXISTING_SPAN_HEIGHT = "Mid-Span Existing"
SPAN_MR_MOVE = "Span MR Move"
SPAN_EFFECTIVE_MOVE = "Span Effective Move"
SPAN_PROPOSED_HEIGHT = "Mid-Span Proposed"

# === Excel Configuration ===
EXCEL_DATA_START_ROW = 4  # Data will start on row 5 (can be easily changed here)


class ProcessingLogger:
    """Logger to track processing details and skipped items"""
    def __init__(self):
        self.node_logs = []
        self.skip_reasons = defaultdict(int)
        self.statistics = {
            'total_nodes': 0,
            'nodes_with_neutral': 0,
            'nodes_without_neutral': 0,
            'total_items': defaultdict(int),
            'items_processed': defaultdict(int),
            'items_skipped': defaultdict(int)
        }
        self.current_node = None
    
    def log_node_start(self, node_id, scid, neutral_height):
        """Start logging for a new node"""
        self.statistics['total_nodes'] += 1
        if neutral_height is not None:
            self.statistics['nodes_with_neutral'] += 1
            neutral_str = f"{int(neutral_height)//12}'-{int(neutral_height)%12}\""
        else:
            self.statistics['nodes_without_neutral'] += 1
            neutral_str = "None (no filter applied)"
        
        self.current_node = {
            'node_id': node_id,
            'scid': scid,
            'neutral_height': neutral_height,
            'neutral_height_str': neutral_str,
            'items': []
        }
    
    def log_item_processed(self, category, item_info):
        """Log a successfully processed item"""
        self.statistics['total_items'][category] += 1
        self.statistics['items_processed'][category] += 1
        
        if self.current_node:
            self.current_node['items'].append({
                'status': 'processed',
                'category': category,
                'info': item_info
            })
    
    def log_item_skipped(self, category, item_info, reason):
        """Log a skipped item with reason"""
        self.statistics['total_items'][category] += 1
        self.statistics['items_skipped'][category] += 1
        self.skip_reasons[reason] += 1
        
        if self.current_node:
            self.current_node['items'].append({
                'status': 'skipped',
                'category': category,
                'info': item_info,
                'reason': reason
            })
    
    def end_node(self):
        """Finish logging for current node"""
        if self.current_node:
            self.node_logs.append(self.current_node)
            self.current_node = None
    
    def write_summary(self, filename):
        """Write processing summary to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== PROCESSING SUMMARY ===\n")
            f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Node statistics
            f.write("NODE STATISTICS:\n")
            f.write(f"- Total nodes processed: {self.statistics['total_nodes']}\n")
            if self.statistics['total_nodes'] > 0:
                percent_with = (self.statistics['nodes_with_neutral'] / self.statistics['total_nodes']) * 100
                percent_without = (self.statistics['nodes_without_neutral'] / self.statistics['total_nodes']) * 100
                f.write(f"- Nodes with neutral wire: {self.statistics['nodes_with_neutral']} ({percent_with:.1f}%)\n")
                f.write(f"- Nodes without neutral: {self.statistics['nodes_without_neutral']} ({percent_without:.1f}%)\n")
            f.write("\n")
            
            # Item statistics
            total_items = sum(self.statistics['total_items'].values())
            total_processed = sum(self.statistics['items_processed'].values())
            total_skipped = sum(self.statistics['items_skipped'].values())
            
            f.write("ITEM STATISTICS:\n")
            f.write(f"- Total items found: {total_items}\n")
            for category, count in self.statistics['total_items'].items():
                f.write(f"  - {category.capitalize()} items: {count}\n")
            f.write("\n")
            
            if total_items > 0:
                f.write(f"ITEMS PROCESSED: {total_processed} ({(total_processed/total_items)*100:.1f}%)\n")
                f.write(f"ITEMS SKIPPED: {total_skipped} ({(total_skipped/total_items)*100:.1f}%)\n\n")
            
            # Skip reason breakdown
            if self.skip_reasons:
                f.write("SKIP REASON BREAKDOWN:\n")
                sorted_reasons = sorted(self.skip_reasons.items(), key=lambda x: x[1], reverse=True)
                for reason, count in sorted_reasons:
                    percent = (count / total_skipped) * 100 if total_skipped > 0 else 0
                    f.write(f"- {reason}: {count} ({percent:.1f}%)\n")
                f.write("\n")
            
            # Detailed node logs (sample)
            f.write("DETAILED NODE LOGS (first 10 nodes with skipped items):\n")
            nodes_with_skips = 0
            for node_log in self.node_logs:
                skipped_items = [item for item in node_log['items'] if item['status'] == 'skipped']
                if skipped_items and nodes_with_skips < 10:
                    nodes_with_skips += 1
                    f.write(f"\n[Node ID: {node_log['node_id']}, SCID: {node_log['scid']}]\n")
                    f.write(f"- Neutral height: {node_log['neutral_height_str']}\n")
                    total_node_items = len(node_log['items'])
                    processed_items = len([item for item in node_log['items'] if item['status'] == 'processed'])
                    f.write(f"- Items: {total_node_items} total ({processed_items} processed, {len(skipped_items)} skipped)\n")
                    
                    # Show some processed items
                    for item in node_log['items'][:5]:
                        if item['status'] == 'processed':
                            f.write(f"  ✓ {item['info']}\n")
                        else:
                            f.write(f"  ✗ {item['info']} - {item['reason']}\n")
                    
                    if len(node_log['items']) > 5:
                        f.write(f"  ... and {len(node_log['items']) - 5} more items\n")


class FileProcessor:
    def __init__(self, output_dir=None):
        # Centralized path management with fallback logic
        if output_dir:
            self.downloads_path = output_dir
        elif os.environ.get('DYNO'):  # Heroku sets DYNO environment variable
            self.downloads_path = "/tmp"
        elif os.environ.get('RENDER'):  # Render deployment
            self.downloads_path = "/tmp" # Common for Render to use /tmp or a dedicated disk mount
        else:
            # Local development - use a dedicated temp directory within the project or user's temp
            import tempfile
            # Using a subdirectory in the system's temp directory for better organization
            self.downloads_path = os.path.join(tempfile.gettempdir(), "barebones_outputs")

        # Ensure the directory exists
        os.makedirs(self.downloads_path, exist_ok=True)
        
        self.job_data = None
        self.logger = ProcessingLogger()

    def load_json(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def format_height_feet_inches(self, total_in):
        if not isinstance(total_in, (int, float)):
            # Consider logging this as a warning if it's unexpected
            return ""

        # Ensure we are working with a value that can be accurately processed by divmod
        # Round to nearest inch first to handle potential floating point inaccuracies from source data
        # then convert to integer for divmod.
        try:
            # Attempt to convert to float first for flexibility, then round, then int.
            # This handles cases where total_in might be a string representation of a number.
            processed_total_in = int(round(float(str(total_in))))
        except (ValueError, TypeError):
            # Log error or return empty if conversion fails
            # Consider logging here: logger.warning(f"Invalid input for height formatting: {total_in}")
            return ""

        feet, inches = divmod(processed_total_in, 12)
        
        # Explicitly handle the case where inches might become 12 due to rounding or input.
        # Although divmod should yield inches < 12, this is a safeguard.
        if inches == 12: # This condition should ideally not be met if processed_total_in is correctly calculated.
            feet += 1
            inches = 0
        
        # Ensure inches are always less than 12, adjusting feet if necessary.
        # This is a stronger safeguard.
        if inches >= 12:
             extra_feet, inches = divmod(inches, 12)
             feet += extra_feet

        result = f"{feet}'-{inches}\""
        return result

    def get_attachers_from_node_trace(self, job_data, node_id):
        attachers = {}
        node_info = job_data.get("nodes", {}).get(node_id, {})
        photo_ids = node_info.get("photos", {})
        main_photo_id = next((pid for pid, pdata in photo_ids.items() if pdata.get("association") == "main"), None)
        if not main_photo_id:
            return {}
        photo_data = job_data.get("photos", {}).get(main_photo_id, {})
        photofirst_data = photo_data.get("photofirst_data", {})
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        # First pass: collect all power wires to find the lowest one
        power_wires = {}
        for category in ["wire", "equipment", "guying"]:
            for item in photofirst_data.get(category, {}).values():
                trace_id = item.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                trace_entry = trace_data[trace_id]
                company = trace_entry.get("company", "").strip()
                type_label = trace_entry.get("cable_type", "") if category in ["wire", "guying"] else trace_entry.get("equipment_type", "")
                if not type_label:
                    continue
                
                # Check if it's a power wire (CPS owned)
                if company.lower() == "cps energy" and type_label.lower() in ["primary", "neutral", "street light"]:
                    measured = item.get("_measured_height")
                    if measured is not None:
                        try:
                            measured = float(measured)
                            power_wires[type_label] = (measured, trace_id)
                        except:
                            continue
        
        # Find the lowest power wire
        lowest_power_wire = None
        lowest_height = float('inf')
        for wire_type, (height, trace_id) in power_wires.items():
            if height < lowest_height:
                lowest_height = height
                lowest_power_wire = (wire_type, trace_id)
        
        # Second pass: collect all non-power wires and only the lowest power wire
        for category in ["wire", "equipment", "guying"]:
            for item in photofirst_data.get(category, {}).values():
                trace_id = item.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                trace_entry = trace_data[trace_id]
                company = trace_entry.get("company", "").strip()
                type_label = trace_entry.get("cable_type", "") if category in ["wire", "guying"] else trace_entry.get("equipment_type", "")
                if not type_label:
                    continue
                
                # Skip if it's a power wire that's not the lowest one
                if company.lower() == "cps energy" and type_label.lower() in ["primary", "neutral", "street light"]:
                    if not lowest_power_wire or trace_id != lowest_power_wire[1]:
                        continue
                
                attacher_name = type_label if company.lower() == "cps energy" else f"{company} {type_label}"
                attachers[attacher_name] = trace_id
        return attachers

    def get_heights_for_node_trace_attachers(self, job_data, node_id, attacher_trace_map):
        heights = {}
        photo_ids = job_data.get("nodes", {}).get(node_id, {}).get("photos", {})
        main_photo_id = next((pid for pid, pdata in photo_ids.items() if pdata.get("association") == "main"), None)
        if not main_photo_id:
            return heights
        photofirst_data = job_data.get("photos", {}).get(main_photo_id, {}).get("photofirst_data", {})
        all_sections = {**photofirst_data.get("wire", {}), **photofirst_data.get("equipment", {}), **photofirst_data.get("guying", {})}
        for attacher_name, trace_id in attacher_trace_map.items():
            for item in all_sections.values():
                if item.get("_trace") != trace_id:
                    continue
                measured = item.get("_measured_height")
                mr_move = item.get("mr_move", 0)
                if measured is not None:
                    try:
                        measured = float(measured)
                        mr_move = float(mr_move) if mr_move else 0.0
                        proposed = measured + mr_move
                        existing_fmt = self.format_height_feet_inches(measured)
                        proposed_fmt = "" if abs(proposed - measured) < 0.01 else self.format_height_feet_inches(proposed)
                        heights[attacher_name] = (existing_fmt, proposed_fmt)
                        break
                    except Exception as e:
                        print(f"Height parse error: {str(e)}")
        return heights

    def get_neutral_wire_height(self, job_data, node_id):
        """Find the height of the neutral wire for a given node"""
        # Get the node's photos
        node_photos = job_data.get("nodes", {}).get(node_id, {}).get("photos", {})
        # Find the main photo
        main_photo_id = next((pid for pid, pdata in node_photos.items() if pdata.get("association") == "main"), None)
        
        if main_photo_id:
            # Get photofirst_data from the main photo
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            photofirst_data = photo_data.get("photofirst_data", {})
            
            # Get trace_data
            trace_data = job_data.get("traces", {}).get("trace_data", {})
            
            # Look through wire section for neutral wire
            for wire in photofirst_data.get("wire", {}).values():
                trace_id = wire.get("_trace")
                if trace_id and trace_id in trace_data:
                    trace_info = trace_data[trace_id]
                    company = trace_info.get("company", "").strip()
                    cable_type = trace_info.get("cable_type", "").strip()
                    
                    if company.lower() == "cps energy" and cable_type.lower() == "neutral":
                        measured_height = wire.get("_measured_height")
                        if measured_height is not None:
                            try:
                                return float(measured_height)
                            except (ValueError, TypeError):
                                continue
        return None

    def get_attachers_for_node(self, job_data, node_id):
        """Get all attachers for a node including guying and drip loops"""
        # Store main pole attachers
        main_attacher_data = []
        
        # Get neutral wire height
        neutral_height = self.get_neutral_wire_height(job_data, node_id)
        
        # Get SCID for logging
        node_props = job_data.get("nodes", {}).get(node_id, {}).get("attributes", {})
        scid_data = node_props.get("scid", {})
        scid = next(iter(scid_data.values()), "Unknown") if scid_data else "Unknown"
        
        # Start logging for this node
        self.logger.log_node_start(node_id, scid, neutral_height)
        
        # Get the node's photos
        node_photos = job_data.get("nodes", {}).get(node_id, {}).get("photos", {})
        # Find the main photo
        main_photo_id = next((pid for pid, pdata in node_photos.items() if pdata.get("association") == "main"), None)
        
        if not main_photo_id:
            print(f"DEBUG_SKIP: Node {node_id} - No main photo found.")
            self.logger.end_node()
            return {'main_attachers': [], 'reference_spans': [], 'backspan': {'data': [], 'bearing': ""}}
        
        # Get photofirst_data from the main photo
        photo_data = job_data.get("photos", {}).get(main_photo_id, {})
        photofirst_data = photo_data.get("photofirst_data", {})
        
        if not photofirst_data:
            print(f"DEBUG_SKIP: Node {node_id} - No photofirst_data in main photo {main_photo_id}.")
            self.logger.end_node()
            return {'main_attachers': [], 'reference_spans': [], 'backspan': {'data': [], 'bearing': ""}}
        
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        # NEW: For debugging or if you want to include all if neutral is not found
        if neutral_height is None:
            print(f"WARNING: Node {node_id} - Neutral wire not found. Height filter for non-primary items will be less restrictive or disabled for this pole.")
        
        # Process all categories in unified way
        for category in ["wire", "equipment", "guying"]:
            print(f"DEBUG: Node {node_id} - Processing category: {category}")
            item_count_in_category = 0
            
            for item_key, item_value in photofirst_data.get(category, {}).items():
                item_count_in_category += 1
                
                # Ensure item_value is a dictionary
                if not isinstance(item_value, dict):
                    self.logger.log_item_skipped(category, f"Item {item_key}", "Not a dictionary")
                    continue
                
                trace_id = item_value.get("_trace")
                if not trace_id:
                    self.logger.log_item_skipped(category, f"Item {item_key}", "No trace ID")
                    continue
                    
                if trace_id not in trace_data:
                    self.logger.log_item_skipped(category, f"Item {item_key} (trace {trace_id})", "Trace not found in trace_data")
                    continue
                
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                
                # Get type based on category
                item_type_str = ""
                if category == "wire":
                    item_type_str = trace_info.get("cable_type", "").strip()
                    if item_type_str.lower() == "primary":  # Skip primary power lines
                        self.logger.log_item_skipped(category, f"{company} {item_type_str}", "Primary wire (skipped)")
                        continue
                elif category == "equipment":
                    item_type_str = trace_info.get("equipment_type", "").strip()
                    if not item_type_str:
                        # fallback to the item's own field
                        item_type_str = item_value.get("equipment_type", "").strip()
                        print(f"DEBUG: Fallback to photofirst equipment_type for item in node {node_id}: {item_type_str}")
                elif category == "guying":
                    item_type_str = trace_info.get("cable_type", "").strip()  # Katapult uses cable_type for guying traces
                
                if not company or not item_type_str:
                    self.logger.log_item_skipped(category, f"Item {item_key} (Trace: {trace_id})", f"Missing company ('{company}') or type ('{item_type_str}')")
                    continue
                
                # Build attacher name
                attacher_name = f"{company} {item_type_str}"
                if category == "guying":  # Optionally add a suffix for clarity
                    attacher_name += " (Guy)"
                
                # Get measured height
                measured_height_str = item_value.get("_measured_height")
                measured_height_val = None
                
                if measured_height_str is not None:
                    try:
                        measured_height_val = float(measured_height_str)
                    except (ValueError, TypeError):
                        self.logger.log_item_skipped(category, attacher_name, f"Invalid measured height: {measured_height_str}")
                        continue
                else:
                    self.logger.log_item_skipped(category, attacher_name, "No measured height")
                    continue
                
                # Neutral height filtering logic
                # Apply this filter only if neutral_height was successfully determined
                if neutral_height is not None:
                    if measured_height_val > neutral_height:
                        # This specific check is to skip items *above* the neutral
                        self.logger.log_item_skipped(category, attacher_name, f"Above neutral height ({neutral_height}\")")
                        continue
                
                # Check if this is a down guy below neutral (for guying category)
                is_down_guy = False
                if category == "guying" and measured_height_val is not None and neutral_height is not None:
                    if measured_height_val < neutral_height:
                        is_down_guy = True
                        attacher_name = f"{company} {item_type_str} (Down Guy)"
                
                # Special handling for guying - only include if it's a down guy
                if category == "guying" and not is_down_guy:
                    self.logger.log_item_skipped(category, attacher_name, "Guy wire not below neutral")
                    continue
                
                # Get movement data
                mr_move_str = item_value.get("mr_move", "0")  # Default to "0" string to handle None
                effective_moves = item_value.get("_effective_moves", {})
                
                # Format heights
                existing_height_fmt = self.format_height_feet_inches(measured_height_val)
                proposed_height_fmt = ""
                
                # Calculate total move
                total_move_inches = 0.0
                try:
                    total_move_inches = float(mr_move_str if mr_move_str is not None else 0.0)
                except (ValueError, TypeError):
                    pass  # total_move_inches remains 0.0
                
                if isinstance(effective_moves, dict):
                    for move_val_str in effective_moves.values():
                        try:
                            total_move_inches += float(move_val_str if move_val_str is not None else 0.0)
                        except (ValueError, TypeError):
                            continue
                
                if abs(total_move_inches) > 0.01:  # Only calculate proposed if there's a significant move
                    proposed_height_val = measured_height_val + total_move_inches
                    proposed_height_fmt = self.format_height_feet_inches(proposed_height_val)
                
                # Add to main attachers
                main_attacher_data.append({
                    'name': attacher_name,
                    'existing_height': existing_height_fmt,
                    'proposed_height': proposed_height_fmt,
                    'raw_height': measured_height_val,  # Keep raw for sorting
                    'is_proposed': trace_info.get("proposed", False)  # For movement summary
                })
                
                # Log successful processing
                self.logger.log_item_processed(category, f"{attacher_name} ({existing_height_fmt})")
                
                print(f"DEBUG: Main attacher {attacher_name} - mr_move: {mr_move_str}, effective_moves: {effective_moves}, total_move: {total_move_inches}")
            
            print(f"DEBUG: Node {node_id} - Processed {item_count_in_category} items in category: {category}")
        
        print(f"DEBUG: Node {node_id} - Total main attachers before sort: {len(main_attacher_data)}")
        
        # Sort by height from highest to lowest
        main_attacher_data.sort(key=lambda x: x['raw_height'], reverse=True)
        
        # Get reference spans
        reference_spans = self.get_reference_attachers(job_data, node_id)
        
        # Get backspan data
        backspan_data, backspan_bearing = self.get_backspan_attachers(job_data, node_id)
        
        # End logging for this node
        self.logger.end_node()
        
        # Return all three types of data
        return {
            'main_attachers': main_attacher_data,
            'reference_spans': reference_spans,
            'backspan': {
                'data': backspan_data,
                'bearing': backspan_bearing
            }
        }

    def get_lowest_heights_for_connection(self, job_data, connection_id):
        """Get the lowest heights for communication and CPS electrical attachments in a connection
        Returns: (lowest_com_formatted, lowest_cps_formatted)
        """
        print(f"DEBUG: Processing connection {connection_id} for lowest heights")
        lowest_com = float('inf')
        lowest_cps = float('inf')
        
        # Get the connection data
        connection_data = job_data.get("connections", {}).get(connection_id, {})
        if not connection_data:
            print(f"WARNING: No connection data found for {connection_id}")
            return "", ""
            
        # Get sections from the connection
        sections = connection_data.get("sections", {})
        if not sections:
            print(f"WARNING: No sections found for connection {connection_id}")
            return "", ""
            
        print(f"DEBUG: Found {len(sections)} sections in connection {connection_id}")
        
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        wire_count = 0
        equipment_count = 0
        cps_matches = 0
        com_matches = 0
        
        # Look through each section's photos
        for section_id, section_data in sections.items():
            photos = section_data.get("photos", {})
            main_photo_id = next((pid for pid, pdata in photos.items() if pdata.get("association") == "main"), None)
            if not main_photo_id:
                continue
                
            # Get photofirst_data
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            photofirst_data = photo_data.get("photofirst_data", {})
            
            # Process wire data
            for wire in photofirst_data.get("wire", {}).values():
                wire_count += 1
                trace_id = wire.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                    
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                cable_type = trace_info.get("cable_type", "").strip()
                measured_height = wire.get("_measured_height")
                
                if measured_height is not None:
                    try:
                        height = float(measured_height)
                        
                        # Enhanced CPS Energy electrical matching - more flexible company name check
                        cps_variations = ["cps energy", "cps", "cpse"]
                        is_cps = any(cps_var in company.lower() for cps_var in cps_variations)
                        
                        # For CPS ENERGY electrical (Neutral or Street Light)
                        if is_cps and cable_type.lower() in ["neutral", "street light"]:
                            lowest_cps = min(lowest_cps, height)
                            cps_matches += 1
                        # For communication attachments (non-CPS companies)
                        elif not is_cps and company:  # Only non-empty, non-CPS companies
                            lowest_com = min(lowest_com, height)
                            com_matches += 1
                    except (ValueError, TypeError):
                        continue
            
            # Also check equipment section for CPS electrical equipment
            for equipment in photofirst_data.get("equipment", {}).values():
                equipment_count += 1
                trace_id = equipment.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                    
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                equipment_type = trace_info.get("equipment_type", "").strip()
                measured_height = equipment.get("_measured_height")
                
                if measured_height is not None:
                    try:
                        height = float(measured_height)
                        
                        # Enhanced CPS Energy electrical matching
                        cps_variations = ["cps energy", "cps", "cpse"]
                        is_cps = any(cps_var in company.lower() for cps_var in cps_variations)
                        
                        # For CPS electrical equipment (transformers, switches, etc.)
                        if is_cps and equipment_type:
                            lowest_cps = min(lowest_cps, height)
                            cps_matches += 1
                        # For communication equipment (non-CPS companies)
                        elif not is_cps and company:  # Only non-empty, non-CPS companies
                            lowest_com = min(lowest_com, height)
                            com_matches += 1
                    except (ValueError, TypeError):
                        continue
        
        print(f"DEBUG: Processed {wire_count} wires, {equipment_count} equipment items")
        print(f"DEBUG: Found {cps_matches} CPS matches, {com_matches} communication matches")
        
        # Format the heights
        lowest_com_formatted = ""
        if lowest_com != float('inf'):
            feet = int(lowest_com) // 12
            inches = round(lowest_com - (feet * 12))
            lowest_com_formatted = f"{feet}'-{inches}\""
            
        lowest_cps_formatted = ""
        if lowest_cps != float('inf'):
            feet = int(lowest_cps) // 12
            inches = round(lowest_cps - (feet * 12))
            lowest_cps_formatted = f"{feet}'-{inches}\""
            
        print(f"DEBUG: Connection {connection_id} - Lowest Com: {lowest_com_formatted}, Lowest CPS: {lowest_cps_formatted}")
        
        return lowest_com_formatted, lowest_cps_formatted

    def bearing_degrees(self, lat1, lon1, lat2, lon2):
        """
        Great-circle bearing from point-1 to point-2.
        Returns 0°…360°   (0 = true north, 90 = east).
        """
        φ1, φ2 = math.radians(float(lat1)), math.radians(float(lat2))
        Δλ     = math.radians(float(lon2) - float(lon1))

        x = math.sin(Δλ) * math.cos(φ2)
        y = math.cos(φ1) * math.sin(φ2) - \
            math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)

        θ = math.degrees(math.atan2(x, y))
        return (θ + 360) % 360            # normalise to 0-360
    
    def to_cardinal(self, deg, points=16):
        """
        Map a bearing to 'N', 'NE', … .
        points = 8 →  N, NE, E, SE, S, SW, W, NW
        points = 16 → N, NNE, NE …  (default)
        """
        names = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        step = 360 / points
        index = int((deg + step/2) // step) % points
        if points == 16:
            return names[index]
        # 8-point fallback
        return names[index*2]
    
    def cardinal_between_nodes(self, job_data, pole_id, ref_id, conn):
        """Return 'N', 'NE', … from pole → reference."""
        pole = job_data["nodes"].get(pole_id, {})
        lat1, lon1 = pole.get("latitude"), pole.get("longitude")

        # fallback: use first survey point if pole lacks coordinates
        if None in (lat1, lon1):
            first_section = next(iter(conn.get("sections", {}).values()), {})
            lat1, lon1 = first_section.get("latitude"), first_section.get("longitude")

        ref = job_data["nodes"].get(ref_id, {})
        lat2, lon2 = ref.get("latitude"), ref.get("longitude")

        if None in (lat1, lon1, lat2, lon2):
            return "??"                   # can't solve direction

        bearing = self.bearing_degrees(lat1, lon1, lat2, lon2)
        return self.to_cardinal(bearing)  # default 16-point rose
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate the bearing between two points
        Returns tuple of (degrees, cardinal_direction)"""
        # Calculate bearing
        bearing = self.bearing_degrees(lat1, lon1, lat2, lon2)
        
        # Convert to cardinal direction (8-point compass)
        cardinal = self.to_cardinal(bearing, points=8)
        
        return (bearing, cardinal)

    def get_backspan_attachers(self, job_data, current_node_id):
        """Find backspan attachers by finding a connection where current_node_id matches node_id_2"""
        backspan_data = []
        bearing = ""
        
        # Get neutral wire height
        neutral_height = self.get_neutral_wire_height(job_data, current_node_id)
        
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        # Find the connection where our current_node_id matches node_id_2
        backspan_connection = None
        for conn_id, conn_data in job_data.get("connections", {}).items():
            if conn_data.get("node_id_2") == current_node_id:
                backspan_connection = conn_data
                # Calculate bearing from coordinates
                sections = conn_data.get("sections", {})
                if sections:
                    first_section = next(iter(sections.values()))
                    if first_section:
                        lat = first_section.get("latitude")
                        lon = first_section.get("longitude")
                        if lat and lon:
                            # Get the from pole coordinates
                            from_node = job_data.get("nodes", {}).get(current_node_id, {})
                            from_photos = from_node.get("photos", {})
                            if from_photos:
                                main_photo_id = next((pid for pid, pdata in from_photos.items() if pdata.get("association") == "main"), None)
                                if main_photo_id:
                                    photo_data = job_data.get("photos", {}).get(main_photo_id, {})
                                    if photo_data and "latitude" in photo_data and "longitude" in photo_data:
                                        from_lat = photo_data["latitude"]
                                        from_lon = photo_data["longitude"]
                                        # Calculate bearing
                                        degrees, cardinal = self.calculate_bearing(from_lat, from_lon, lat, lon)
                                        bearing = f"{cardinal} ({int(degrees)}°)"
                break
        
        if not backspan_connection:
            return [], ""
            
        # Get the sections data from the backspan connection
        sections = backspan_connection.get("sections", {})
        
        # For each attacher, find the lowest measured height across all sections
        attacher_sections = {}
        for section_id, section_data in sections.items():
            photos = section_data.get("photos", {})
            main_photo_id = next((pid for pid, pdata in photos.items() if pdata.get("association") == "main"), None)
            if not main_photo_id:
                continue
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            if not photo_data:
                continue
            photofirst_data = photo_data.get("photofirst_data", {})
            if not photofirst_data:
                continue
            # Wires
            for wire in photofirst_data.get("wire", {}).values():
                trace_id = wire.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                cable_type = trace_info.get("cable_type", "").strip()
                if cable_type.lower() == "primary":
                    continue
                measured_height = wire.get("_measured_height")
                mr_move = wire.get("mr_move", 0)
                effective_moves = wire.get("_effective_moves", {})
                if company and cable_type and measured_height is not None:
                    try:
                        measured_height = float(measured_height)
                        attacher_name = f"{company} {cable_type}"
                        # If this attacher is not yet in the dict or this section has a lower height, update
                        if attacher_name not in attacher_sections or measured_height < attacher_sections[attacher_name]["measured_height"]:
                            attacher_sections[attacher_name] = {
                                "measured_height": measured_height,
                                "mr_move": mr_move,
                                "effective_moves": effective_moves
                            }
                    except (ValueError, TypeError):
                        continue
            # Guying
            for guy in photofirst_data.get("guying", {}).values():
                trace_id = guy.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                cable_type = trace_info.get("cable_type", "").strip()
                measured_height = guy.get("_measured_height")
                mr_move = guy.get("mr_move", 0)
                effective_moves = guy.get("_effective_moves", {})
                if company and cable_type and measured_height is not None and neutral_height is not None:
                    try:
                        guy_height = float(measured_height)
                        if guy_height < neutral_height:
                            attacher_name = f"{company} {cable_type} (Down Guy)"
                            if attacher_name not in attacher_sections or guy_height < attacher_sections[attacher_name]["measured_height"]:
                                attacher_sections[attacher_name] = {
                                    "measured_height": guy_height,
                                    "mr_move": mr_move,
                                    "effective_moves": effective_moves
                                }
                    except (ValueError, TypeError):
                        continue
        # Now build the backspan_data list from the lowest section for each attacher
        for attacher_name, info in attacher_sections.items():
            measured_height = info["measured_height"]
            mr_move = info["mr_move"]
            effective_moves = info["effective_moves"]
            feet = int(measured_height) // 12
            inches = round(measured_height - (feet * 12))
            existing_height = f"{feet}'-{inches}\""
            proposed_height = ""
            total_move = float(mr_move)
            if effective_moves:
                for move in effective_moves.values():
                    try:
                        total_move += float(move)
                    except (ValueError, TypeError):
                        continue
            if abs(total_move) > 0:
                proposed_height_value = measured_height + total_move
                feet_proposed = int(proposed_height_value) // 12
                inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                proposed_height = f"{feet_proposed}'-{inches_proposed}\""
            backspan_data.append({
                'name': attacher_name,
                'existing_height': existing_height,
                'proposed_height': proposed_height,
                'raw_height': measured_height
            })
        backspan_data.sort(key=lambda x: x['raw_height'], reverse=True)
        return backspan_data, bearing

    def get_reference_attachers(self, job_data, current_node_id):
        """Find reference span attachers by finding connections where current_node_id matches either node_id_1 or node_id_2"""
        reference_info = []  # List to store reference data with bearings
        
        # Get neutral wire height
        neutral_height = self.get_neutral_wire_height(job_data, current_node_id)
        
        # Find reference connections where our current_node_id matches either node
        for conn_id, conn_data in job_data.get("connections", {}).items():
            # Check if it's a reference connection (button = "ref" and connection_type = "reference")
            is_reference = False
            
            # Check button
            if conn_data.get("button") == "ref":
                # Check connection_type
                connection_type = conn_data.get("attributes", {}).get("connection_type", {})
                if isinstance(connection_type, dict):
                    connection_type_value = next(iter(connection_type.values()), "")
                else:
                    connection_type_value = connection_type.get("button_added", "")
                
                if "reference" in str(connection_type_value).lower():
                    is_reference = True
            
            if is_reference:
                # Get the node IDs, making sure the pole is node_id_1 and the reference is node_id_2
                if conn_data.get("node_id_1") == current_node_id:
                    pole_id = current_node_id
                    ref_id = conn_data.get("node_id_2")
                else:
                    pole_id = current_node_id
                    ref_id = conn_data.get("node_id_1")
                
                # Calculate cardinal direction from pole to reference
                cardinal = self.cardinal_between_nodes(job_data, pole_id, ref_id, conn_data)
                
                # Get reference node type
                ref_node = job_data["nodes"].get(ref_id, {})
                ref_attributes = ref_node.get("attributes", {})
                node_type_data = ref_attributes.get("node_type", {})
                
                if isinstance(node_type_data, dict):
                    node_type = next(iter(node_type_data.values()), "Reference")
                else:
                    node_type = str(node_type_data) if node_type_data else "Reference"
                
                # Format the bearing text and label
                bearing = f"{cardinal}"
                label = f"Ref ({cardinal}) to {node_type.title()}"
                
                # Find the sections to get the attacher data
                sections = conn_data.get("sections", {})
                if sections:
                    # Find the midpoint section (if multiple sections exist)
                    section_ids = list(sections.keys())
                    mid_section_index = len(section_ids) // 2
                    mid_section_id = section_ids[mid_section_index]
                    mid_section = sections[mid_section_id]
                    
                    # Get the main photo from the midpoint section
                    photos = mid_section.get("photos", {})
                    main_photo_id = next((pid for pid, pdata in photos.items() if pdata.get("association") == "main"), None)
                    if main_photo_id:
                        # Get photofirst_data from the main photo
                        photo_data = job_data.get("photos", {}).get(main_photo_id, {})
                        if not photo_data:
                            continue
                        
                        photofirst_data = photo_data.get("photofirst_data", {})
                        if not photofirst_data:
                            continue
                        
                        # Process the reference span data
                        span_data = []
                        
                        # Get trace_data
                        trace_data = job_data.get("traces", {}).get("trace_data", {})
                        
                        # Process wire data
                        wire_data = photofirst_data.get("wire", {})
                        if wire_data:
                            for wire in wire_data.values():
                                trace_id = wire.get("_trace")
                                if not trace_id or trace_id not in trace_data:
                                    continue
                                
                                trace_info = trace_data[trace_id]
                                company = trace_info.get("company", "").strip()
                                cable_type = trace_info.get("cable_type", "").strip()
                                
                                # Skip if cable_type is "Primary"
                                if cable_type.lower() == "primary":
                                    continue
                                
                                measured_height = wire.get("_measured_height")
                                mr_move = wire.get("mr_move", 0)
                                effective_moves = wire.get("_effective_moves", {})
                                
                                if company and cable_type and measured_height is not None:
                                    try:
                                        measured_height = float(measured_height)
                                        attacher_name = f"{company} {cable_type}"
                                        
                                        # Format existing height (measured_height)
                                        feet = int(measured_height) // 12
                                        inches = round(measured_height - (feet * 12))
                                        existing_height = f"{feet}'-{inches}\""
                                        
                                        # Calculate proposed height using effective_moves and mr_move
                                        proposed_height = ""
                                        total_move = float(mr_move)  # Start with mr_move
                                        
                                        # Add effective moves
                                        if effective_moves:
                                            for move in effective_moves.values():
                                                try:
                                                    total_move += float(move)
                                                except (ValueError, TypeError):
                                                    continue
                                        
                                        # Calculate proposed height if there's a move
                                        if abs(total_move) > 0:
                                            proposed_height_value = measured_height + total_move
                                            feet_proposed = int(proposed_height_value) // 12
                                            inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                            proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                                        
                                        span_data.append({
                                            'name': attacher_name,
                                            'existing_height': existing_height,
                                            'proposed_height': proposed_height,
                                            'raw_height': measured_height,
                                            'is_reference': True  # Mark this as a reference span
                                        })
                                    except (ValueError, TypeError):
                                        continue
                        
                        # Process guying data
                        guying_data = photofirst_data.get("guying", {})
                        if guying_data:
                            for guy in guying_data.values():
                                trace_id = guy.get("_trace")
                                if not trace_id or trace_id not in trace_data:
                                    continue
                                
                                trace_info = trace_data[trace_id]
                                company = trace_info.get("company", "").strip()
                                cable_type = trace_info.get("cable_type", "").strip()
                                
                                measured_height = guy.get("_measured_height")
                                mr_move = guy.get("mr_move", 0)
                                effective_moves = guy.get("_effective_moves", {})
                                
                                if company and cable_type and measured_height is not None and neutral_height is not None:
                                    try:
                                        guy_height = float(measured_height)
                                        if guy_height < neutral_height:
                                            attacher_name = f"{company} {cable_type} (Down Guy)"
                                            
                                            # Format existing height
                                            feet = int(guy_height) // 12
                                            inches = round(guy_height - (feet * 12))
                                            existing_height = f"{feet}'-{inches}\""
                                            
                                            # Calculate proposed height using effective_moves and mr_move
                                            proposed_height = ""
                                            total_move = float(mr_move)  # Start with mr_move
                                            
                                            # Add effective moves
                                            if effective_moves:
                                                for move in effective_moves.values():
                                                    try:
                                                        total_move += float(move)
                                                    except (ValueError, TypeError):
                                                        continue
                                            
                                            # Calculate proposed height if there's a move
                                            if abs(total_move) > 0:
                                                proposed_height_value = guy_height + total_move
                                                feet_proposed = int(proposed_height_value) // 12
                                                inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                                proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                                            
                                            span_data.append({
                                                'name': attacher_name,
                                                'existing_height': existing_height,
                                                'proposed_height': proposed_height,
                                                'raw_height': guy_height,
                                                'is_reference': True
                                            })
                                    except (ValueError, TypeError):
                                        continue
                        
                        if span_data:  # Only add reference info if we found attachers
                            # Sort by height from highest to lowest
                            span_data.sort(key=lambda x: x['raw_height'], reverse=True)
                            reference_info.append({
                                'bearing': bearing,
                                'data': span_data
                            })
        
        return reference_info

    def get_work_type(self, job_data, node_id):
        """Get the work type from node attributes, falling back to kat_work_type if needed"""
        node_attributes = job_data.get("nodes", {}).get(node_id, {}).get("attributes", {})
        
        # First try work_type
        work_type_data = node_attributes.get("work_type", {})
        if work_type_data:
            # Get the first non-empty value from the dynamic keys
            for key, value in work_type_data.items():
                if value and value != "N/A":
                    return value
        
        # If no work_type, try kat_work_type
        kat_work_type_data = node_attributes.get("kat_work_type", {})
        if kat_work_type_data:
            # Get the first non-empty value from the dynamic keys
            for key, value in kat_work_type_data.items():
                if value and value != "N/A":
                    return value
        
        return "N/A"

    def get_responsible_party(self, job_data, node_id):
        """Get the responsible party from node attributes, falling back to KAT if needed"""
        node_attributes = job_data.get("nodes", {}).get(node_id, {}).get("attributes", {})
        
        # First try STRESS_-_MR_responsible_party
        stress_party_data = node_attributes.get("STRESS_-_MR_responsible_party", {})
        if stress_party_data:
            # Get the first non-empty value from the dynamic keys
            for key, value in stress_party_data.items():
                if value and value != "N/A":
                    return value
        
        # If no STRESS value, try KAT_-_MR_responsible_party
        kat_party_data = node_attributes.get("KAT_-_MR_responsible_party", {})
        if kat_party_data:
            # Get the first non-empty value from the dynamic keys
            for key, value in kat_party_data.items():
                if value and value != "N/A":
                    return value
        
        return "N/A"

    def compare_scids(self, scid1, scid2):
        """Compare two SCID numbers, prioritizing base numbers over suffixed ones"""
        # Convert to strings if they're numbers
        scid1 = str(scid1)
        scid2 = str(scid2)
        
        # Handle N/A values
        if scid1 == 'N/A':
            return 1  # N/A values go last
        if scid2 == 'N/A':
            return -1
        
        # Split on dots to separate base number from suffixes
        scid1_parts = scid1.split('.')
        scid2_parts = scid2.split('.')
        
        # Compare base numbers first
        try:
            # Remove leading zeros and convert to integers
            base1 = int(scid1_parts[0].lstrip('0') or '0')
            base2 = int(scid2_parts[0].lstrip('0') or '0')
            if base1 != base2:
                return base1 - base2
        except (ValueError, IndexError):
            # If base numbers can't be compared as integers, compare as strings
            if scid1_parts[0] != scid2_parts[0]:
                return -1 if scid1_parts[0] < scid2_parts[0] else 1
        
        # If base numbers are equal, the one without suffixes comes first
        if len(scid1_parts) == 1 and len(scid2_parts) > 1:
            return -1
        if len(scid1_parts) > 1 and len(scid2_parts) == 1:
            return 1
        
        # If both have suffixes, compare them
        return -1 if scid1 < scid2 else 1

    def get_pole_structure(self, job_data, node_id):
        # Get the node's attributes
        node_attributes = job_data.get("nodes", {}).get(node_id, {}).get("attributes", {})
        
        # First try to get proposed_pole_spec
        proposed_spec = None
        proposed_spec_data = node_attributes.get("proposed_pole_spec", {})
        if proposed_spec_data:
            # Get the first non-empty value from the dynamic keys
            for key, value in proposed_spec_data.items():
                if isinstance(value, dict):
                    proposed_spec = value.get("value")  # If it's in a value field
                else:
                    proposed_spec = value  # If it's direct
                if proposed_spec and proposed_spec != "N/A":
                    break
        
        if proposed_spec:
            return proposed_spec
        
        # Fall back to pole_height and pole_class
        # Get pole_height from dynamic key
        pole_height = None
        pole_height_data = node_attributes.get("pole_height", {})
        if pole_height_data:
            if "one" in pole_height_data:
                pole_height = pole_height_data.get("one")
            else:
                # Try first non-empty value from dynamic keys
                for key, value in pole_height_data.items():
                    if value and value != "N/A":
                        pole_height = value
                        break
        
        # Get pole_class from dynamic key
        pole_class = None
        pole_class_data = node_attributes.get("pole_class", {})
        if pole_class_data:
            if "one" in pole_class_data:
                pole_class = pole_class_data.get("one")
            else:
                # Try first non-empty value from dynamic keys
                for key, value in pole_class_data.items():
                    if value and value != "N/A":
                        pole_class = value
                        break
        
        if pole_height and pole_class:
            return f"{pole_height}-{pole_class}"
        
        return "N/A"

    def get_proposed_guy_value(self, job_data, node_id):
        # Find the main photo for this node
        node_info = job_data.get("nodes", {}).get(node_id, {})
        photo_ids = node_info.get("photos", {})
        main_photo_id = next((pid for pid, pdata in photo_ids.items() if pdata.get("association") == "main"), None)
        
        if main_photo_id:
            # Get the photo data and check for proposed guying
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            photofirst_data = photo_data.get("photofirst_data", {})
            guying_data = photofirst_data.get("guying", {})
            if guying_data:
                proposed_guy_count = sum(1 for guy in guying_data.values() if guy.get("proposed") is True)
                if proposed_guy_count > 0:
                    return f"YES ({proposed_guy_count})"
        
        return "No"

    def get_movement_summary(self, attacher_data, cps_only=False):
        """Generate a movement summary for all attachers that have moves, proposed wires, and guying
        Args:
            attacher_data: List of attacher data
            cps_only: If True, only include CPS Energy movements
        """
        summaries = []
        
        # First handle movements of existing attachments
        for attacher in attacher_data:
            name = attacher['name']
            existing = attacher['existing_height']
            proposed = attacher['proposed_height']
            is_proposed = attacher.get('is_proposed', False)
            is_guy = '(Guy)' in name or '(Down Guy)' in name
            
            # Skip if cps_only is True and this is not a CPS attachment
            if cps_only and not name.lower().startswith("cps energy"):
                continue
            
            # Handle proposed new attachments (including guys)
            if is_proposed:
                if is_guy:
                    summaries.append(f"Add {name} at {existing}")
                else:
                    summaries.append(f"Install proposed {name} at {existing}")
                continue
                
            # Handle movements of existing attachments
            if proposed and existing:
                try:
                    existing_parts = existing.replace('"', '').split("'")
                    proposed_parts = proposed.replace('"', '').split("'")
                    
                    existing_inches = int(existing_parts[0]) * 12 + int(existing_parts[1])
                    proposed_inches = int(proposed_parts[0]) * 12 + int(proposed_parts[1])
                    
                    # Calculate movement
                    movement = proposed_inches - existing_inches
                    
                    if movement != 0:
                        # Determine if raising or lowering
                        action = "Raise" if movement > 0 else "Lower"
                        # Get absolute movement in inches
                        inches_moved = abs(movement)
                        
                        summary = f"{action} {name} {inches_moved}\" from {existing} to {proposed}"
                        summaries.append(summary)
                except (ValueError, IndexError):
                    continue
        
        return "\n".join(summaries) if summaries else ""
    
    def get_all_movements_summary(self, main_attachers, reference_spans, backspan_data):
        """Generate comprehensive movement summary including all attachers"""
        all_attachers = []
        
        # Add main attachers
        all_attachers.extend(main_attachers)
        print(f"DEBUG: Added {len(main_attachers)} main attachers to movement summary")
        
        # Add reference span attachers
        ref_count = 0
        for ref_span in reference_spans:
            ref_attachers = ref_span.get('data', [])
            all_attachers.extend(ref_attachers)
            ref_count += len(ref_attachers)
        print(f"DEBUG: Added {ref_count} reference span attachers to movement summary")
        
        # Add backspan attachers
        all_attachers.extend(backspan_data)
        print(f"DEBUG: Added {len(backspan_data)} backspan attachers to movement summary")
        
        summary = self.get_movement_summary(all_attachers, cps_only=False)
        print(f"DEBUG: Generated movement summary with {len(summary.split(chr(10)) if summary else [])} movement lines")
        
        return summary
    
    def get_cps_movements_only(self, main_attachers, reference_spans, backspan_data):
        """Generate movement summary for CPS Energy attachments only (for Remedy Description)"""
        all_attachers = []
        
        # Add main attachers
        all_attachers.extend(main_attachers)
        
        # Add reference span attachers
        for ref_span in reference_spans:
            all_attachers.extend(ref_span.get('data', []))
        
        # Add backspan attachers
        all_attachers.extend(backspan_data)
        
        summary = self.get_movement_summary(all_attachers, cps_only=True)
        print(f"DEBUG: Generated CPS-only movement summary with {len(summary.split(chr(10)) if summary else [])} movement lines")
        
        return summary

    def _is_number(self, value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def get_midspan_proposed_heights(self, job_data, connection_id, attacher_name):
        """Get the proposed height for a specific attacher in the connection's span
        For each wire:
        1. Find the section with the lowest measured height
        2. Use that section to check for mr_move or effective_moves
        3. If there are moves (nonzero), calculate and return the proposed height
        4. If no moves, return empty string"""
        # Get the connection data
        connection_data = job_data.get("connections", {}).get(connection_id, {})
        if not connection_data:
            return ""
            
        # Get sections from the connection
        sections = connection_data.get("sections", {})
        if not sections:
            return ""
            
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        # Store the lowest height section for this attacher
        lowest_height = float('inf')
        lowest_section = None
        
        # First pass: find the section with the lowest measured height for this attacher
        for section_id, section_data in sections.items():
            photos = section_data.get("photos", {})
            main_photo_id = next((pid for pid, pdata in photos.items() if pdata.get("association") == "main"), None)
            if not main_photo_id:
                continue
                
            # Get photofirst_data
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            photofirst_data = photo_data.get("photofirst_data", {})
            
            # Process wire data
            for wire in photofirst_data.get("wire", {}).values():
                trace_id = wire.get("_trace")
                if not trace_id or trace_id not in trace_data:
                    continue
                    
                trace_info = trace_data[trace_id]
                company = trace_info.get("company", "").strip()
                cable_type = trace_info.get("cable_type", "").strip()
                
                # Skip if cable_type is "Primary"
                if cable_type.lower() == "primary":
                    continue
                
                # Construct the attacher name the same way as in the main list
                current_attacher = f"{company} {cable_type}"
                
                if current_attacher.strip() == attacher_name.strip():
                    measured_height = wire.get("_measured_height")
                    if measured_height is not None:
                        try:
                            measured_height = float(measured_height)
                            if measured_height < lowest_height:
                                lowest_height = measured_height
                                lowest_section = (section_data, wire, trace_info)
                        except (ValueError, TypeError):
                            continue
        
        # If we found a section with this attacher
        if lowest_section:
            section_data, wire, trace_info = lowest_section
            
            # Check if this is a proposed wire
            is_proposed = trace_info.get("proposed", False)
            if is_proposed:
                return self.format_height_feet_inches(lowest_height)
            
            # Check for moves
            mr_move = wire.get("mr_move", 0)
            effective_moves = wire.get("_effective_moves", {})
            
            # Only consider nonzero moves
            has_mr_move = False
            try:
                has_mr_move = abs(float(mr_move)) > 0.01
            except (ValueError, TypeError):
                has_mr_move = False
            has_effective_move = any(abs(float(mv)) > 0.01 for mv in effective_moves.values() if self._is_number(mv))
            
            if not has_mr_move and not has_effective_move:
                return ""
            
            # Calculate total move
            total_move = float(mr_move) if has_mr_move else 0.0
            if has_effective_move:
                for move in effective_moves.values():
                    try:
                        move_value = float(move)
                        # Only add if nonzero - using full effective_moves value for consistency with pole attachments
                        if abs(move_value) > 0.01:
                            total_move += move_value
                    except (ValueError, TypeError):
                        continue
            # Calculate proposed height
            proposed_height = lowest_height + total_move
            return self.format_height_feet_inches(proposed_height)
        
        return ""  # Return empty string if no section found or if there was an error

    def process_data(self, job_data, geojson_data):
        """Process job data to extract connections, nodes, and create structured DataFrame"""
        print("DEBUG: Starting process_data method...")
        
        data = []
        operation_number = 1
        
        # Create a mapping of node IDs to their properties
        node_properties = {}
        for node_id, node_data in job_data.get("nodes", {}).items():
            attributes = node_data.get("attributes", {})
            
            # Get DLOC_number - it's stored under attributes.DLOC_number with a dynamic key
            dloc_number = 'N/A'
            dloc_data = attributes.get('DLOC_number', {})
            if dloc_data:
                # Get the first value from the DLOC_number dictionary
                dloc_number = next(iter(dloc_data.values()), 'N/A')
                # Add PL prefix if it doesn't start with NT and doesn't already contain PL
                if dloc_number != 'N/A' and not dloc_number.upper().startswith('NT') and 'PL' not in dloc_number.upper():
                    dloc_number = f"PL{dloc_number}"
            
            # Get pole_tag - it's stored under attributes.pole_tag with a dynamic key
            pole_tag = 'N/A'
            pole_tag_data = attributes.get('pole_tag', {})
            if pole_tag_data:
                # Get the first value from the pole_tag dictionary and then get its tagtext
                pole_tag = next(iter(pole_tag_data.values()), {}).get('tagtext', 'N/A')
                # Add PL prefix if it doesn't start with NT and doesn't already contain PL
                if pole_tag != 'N/A' and not pole_tag.upper().startswith('NT') and 'PL' not in pole_tag.upper():
                    pole_tag = f"PL{pole_tag}"
            
            # Get SCID and store both string and numeric versions
            scid_data = attributes.get('scid', {})
            # First try auto_button, then -Imported, then any other key
            scid_value = None
            for key in ['auto_button', '-Imported']:
                if key in scid_data:
                    scid_value = scid_data[key]
                    break
            if scid_value is None and scid_data:
                # If no specific key found but scid_data is not empty, get the first value
                scid_value = next(iter(scid_data.values()), 'N/A')
            
            # Convert to string and handle empty values
            scid_value = str(scid_value) if scid_value is not None else 'N/A'
            if not scid_value.strip():
                scid_value = 'N/A'
                
            # Get node type - first try -Imported, then any other key
            node_type_data = attributes.get('node_type', {})
            node_type_value = None
            for key in ['-Imported']:
                if key in node_type_data:
                    node_type_value = node_type_data[key]
                    break
            if node_type_value is None and node_type_data:
                # If no specific key found but node_type_data is not empty, get the first value
                node_type_value = next(iter(node_type_data.values()), '')
                
            node_properties[node_id] = {
                'scid': scid_value,  # Store as string for comparison
                'scid_display': scid_value,  # Keep original string for display
                'DLOC_number': dloc_number,
                'pole_tag': pole_tag,
                'pole_spec': attributes.get('pole_spec', {}).get('-OMnHH-D1_o6_KaGMtG7', 'N/A'),
                'pole_height': attributes.get('pole_height', {}).get('one', 'N/A'),
                'pole_class': attributes.get('pole_class', {}).get('one', 'N/A'),
                'riser': attributes.get('riser', {}).get('button_added', "No"),
                'final_passing_capacity_%': '',  # Changed from N/A to empty string
                'construction_grade': attributes.get('construction_grade', ''),
                'work_type': self.get_work_type(job_data, node_id),
                'responsible_party': self.get_responsible_party(job_data, node_id),
                'node_type': node_type_value  # Store the node type value
            }
        
        print(f"DEBUG: Processed {len(node_properties)} nodes")
        
        # First pass: collect all underground connections for each pole
        pole_underground_connections = {}
        underground_connections = {}  # Initialize the dictionary for storing underground connections
        for connection_id, connection_data in job_data.get("connections", {}).items():
            connection_type = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added", "")
            if connection_type == "underground cable":
                node_id_1 = connection_data.get("node_id_1")
                if node_id_1:
                    pole_underground_connections[node_id_1] = pole_underground_connections.get(node_id_1, 0) + 1
        
        print(f"DEBUG: Found {len(pole_underground_connections)} poles with underground connections")
        
        # Process connections and store in a list for sorting
        connection_data_list = []
        for connection_id, connection_data in job_data.get("connections", {}).items():
            # Check if this is an aerial cable or underground cable with a pole
            connection_type = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added", "")
            is_aerial = connection_type == "aerial cable"
            is_underground = connection_type == "underground cable"
            
            if not (is_aerial or is_underground):
                continue
                
            node_id_1 = connection_data.get("node_id_1")
            node_id_2 = connection_data.get("node_id_2")
            
            if not (node_id_1 and node_id_2):
                continue
                
            # For underground cables, check if one of the nodes is a pole
            if is_underground:
                node1_type_dict = node_properties.get(node_id_1, {}).get('node_type', {})
                node2_type_dict = node_properties.get(node_id_2, {}).get('node_type', {})
                
                # Handle both string and dictionary node types
                def get_node_type(node_type_value):
                    if isinstance(node_type_value, dict):
                        return 'pole' if 'pole' in node_type_value.values() else ''
                    elif isinstance(node_type_value, str):
                        return 'pole' if node_type_value == 'pole' else ''
                    return ''
                
                node1_type = get_node_type(node1_type_dict)
                node2_type = get_node_type(node2_type_dict)
                
                if not (node1_type == 'pole' or node2_type == 'pole'):
                    continue
                
                # Get the pole node ID and pedestal node ID
                pole_node_id = node_id_1 if node1_type == 'pole' else node_id_2
                pedestal_node_id = node_id_2 if node1_type == 'pole' else node_id_1
                
                # Get the pole's SCID
                pole_scid = node_properties.get(pole_node_id, {}).get('scid', '')
                if not pole_scid:
                    continue
                
                # Get the pedestal's SCID
                pedestal_scid = node_properties.get(pedestal_node_id, {}).get('scid', '')
                if not pedestal_scid:
                    continue
                
                # Add to underground connections
                if pole_scid not in underground_connections:
                    underground_connections[pole_scid] = []
                underground_connections[pole_scid].append(pedestal_scid)
                
                # Set from/to node IDs for underground
                from_node_id = pole_node_id
                to_node_id = pedestal_node_id
            else:
                # For aerial cables, determine from/to based on SCID
                scid_1 = node_properties.get(node_id_1, {}).get('scid', 'N/A')
                scid_2 = node_properties.get(node_id_2, {}).get('scid', 'N/A')
                if self.compare_scids(scid_1, scid_2) <= 0:
                    from_node_id = node_id_1
                    to_node_id = node_id_2
                else:
                    from_node_id = node_id_2
                    to_node_id = node_id_1
            
            # Get pole properties
            from_pole_props = node_properties.get(from_node_id, {})
            to_pole_props = node_properties.get(to_node_id, {})
            
            # Determine pole number with fallback to pole_tag
            pole_number = from_pole_props.get('DLOC_number')
            if not pole_number or pole_number == 'N/A':
                pole_number = from_pole_props.get('pole_tag', 'N/A')
            
            # Create row for this connection
            # Get red tag status from from_node attributes
            node_attributes = job_data.get("nodes", {}).get(from_node_id, {}).get("attributes", {})
            red_tag_data = node_attributes.get("existing_red_tag?", {})
            # Check any value in the red_tag_data dictionary
            has_red_tag = any(val for val in red_tag_data.values() if val is True)

            # Get final passing capacity from from_node attributes
            node_attributes = job_data.get("nodes", {}).get(from_node_id, {}).get("attributes", {})
            final_capacity_data = node_attributes.get("final_passing_capacity_%", {})
            # Get the first non-empty value from the dictionary, or empty string if not found
            final_capacity = next((str(val) for val in final_capacity_data.values() if val), "")

            # For underground connections, get the company and bearing for the remedy description
            remedy_description = ""
            if is_underground:
                # Get the company from the connection's trace data
                trace_data = job_data.get("traces", {}).get("trace_data", {})
                for trace_id, trace_info in trace_data.items():
                    if trace_info.get("connection_id") == connection_id:
                        company = trace_info.get("company", "").strip()
                        if company:
                            # Calculate bearing from coordinates
                            from_node = job_data.get("nodes", {}).get(from_node_id, {})
                            from_photos = from_node.get("photos", {})
                            if from_photos:
                                main_photo_id = next((pid for pid, pdata in from_photos.items() if pdata.get("association") == "main"), None)
                                if main_photo_id:
                                    photo_data = job_data.get("photos", {}).get(main_photo_id, {})
                                    if photo_data and "latitude" in photo_data and "longitude" in photo_data:
                                        from_lat = photo_data["latitude"]
                                        from_lon = photo_data["longitude"]
                                        # Get the other node's coordinates
                                        to_node = job_data.get("nodes", {}).get(to_node_id, {})
                                        to_photos = to_node.get("photos", {})
                                        if to_photos:
                                            main_photo_id = next((pid for pid, pdata in to_photos.items() if pdata.get("association") == "main"), None)
                                            if main_photo_id:
                                                photo_data = job_data.get("photos", {}).get(main_photo_id, {})
                                                if photo_data and "latitude" in photo_data and "longitude" in photo_data:
                                                    to_lat = photo_data["latitude"]
                                                    to_lon = photo_data["longitude"]
                                                    # Calculate bearing
                                                    degrees, cardinal = self.calculate_bearing(from_lat, from_lon, to_lat, to_lon)
                                                    remedy_description = f"Proposed {company} to transition to UG connection to the {cardinal} ({int(degrees)}°)"
                                                    break

            row = {
                "Connection ID": connection_id,
                "Operation Number": operation_number,
                "Attachment Action": "I",
                "Pole Owner": "CPS",
                "Pole #": pole_number,
                "SCID": from_pole_props.get('scid_display', 'N/A'),
                "SCID_sort": from_pole_props.get('scid', 'N/A'),
                "Pole Structure": self.get_pole_structure(job_data, from_node_id),
                "Proposed Riser": "YES (1)" if is_underground else ("YES ({})".format(pole_underground_connections[from_node_id]) if from_node_id in pole_underground_connections else "No"),
                "Proposed Guy": self.get_proposed_guy_value(job_data, from_node_id),
                "PLA (%) with proposed attachment": final_capacity,
                "Construction Grade of Analysis": "C",
                "Height Lowest Com": "NA" if is_underground else "",
                "Height Lowest CPS Electrical": "NA" if is_underground else "",
                "One Touch Transfer": from_pole_props.get('work_type', 'N/A'),
                "Remedy Description": remedy_description if is_underground else "",
                "Responsible Party": from_pole_props.get('responsible_party', 'N/A'),
                "Existing CPSE Red Tag on Pole": "YES" if has_red_tag else "NO",
                "Pole Data Missing in GIS": "",
                "CPSE Application Comments": "",
                "Movement Summary": "",  # Will be populated in create_output_excel
                "node_id_1": from_node_id,
                "node_id_2": to_node_id,
                "From Pole Properties": from_pole_props,
                "To Pole Properties": to_pole_props
            }
            connection_data_list.append(row)
            operation_number += 1
        
        print(f"DEBUG: Processed {len(connection_data_list)} connections")
        
        # Sort the connection data by from pole's SCID
        connection_data_list.sort(key=lambda x: (
            self.compare_scids(x['From Pole Properties'].get('scid', 'N/A'), 'N/A'),
            x['From Pole Properties'].get('scid', 'N/A'),
            x['To Pole Properties'].get('scid', 'N/A')
        ))
        
        # Update operation numbers after sorting
        for i, row in enumerate(connection_data_list, 1):
            row['Operation Number'] = i
        
        print(f"DEBUG: Created DataFrame with {len(connection_data_list)} rows")
        
        # Create DataFrame from sorted data
        df = pd.DataFrame(connection_data_list)
        
        # Drop the sorting column
        if 'SCID_sort' in df.columns:
            df = df.drop('SCID_sort', axis=1)
        
        return df

    def create_output_excel(self, path, df, job_data):
        """Create a simplified Excel output with flat single sheet structure"""
        
        # Define columns for the flat single sheet
        # Connection ID, SCID, and Bearing are excluded from Excel output but kept in DataFrame for processing
        desired_columns = [
            "Operation Number", "Attachment Action", "Pole Owner", 
            "Pole #", "Pole Structure", "Proposed Riser", "Proposed Guy", 
            "PLA (%) with proposed attachment", "Construction Grade of Analysis",
            "Height Lowest Com", "Height Lowest CPS Electrical", 
            "Data Category", "Attacher Description",
            "Attachment Height - Existing", "Attachment Height - Proposed",
            "Mid-Span (same span as existing)",
            "One Touch Transfer", "Remedy Description", "Responsible Party",
            "Existing CPSE Red Tag on Pole", "Pole Data Missing in GIS", 
            "CPSE Application Comments", "Movement Summary", "From Pole", "To Pole"
        ]
        
        df_final_rows = [] 
        writer = None 

        try:
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            workbook = writer.book
            
            if df.empty:
                print("DataFrame is empty, processing job_data directly to create sample structure.")
                sample_row = {
                    "Connection ID": "SAMPLE_CONN_001",
                    "Operation Number": 1,
                    "Attachment Action": "I",
                    "Pole Owner": "CPS",
                    "Pole #": "PL12345",
                    "SCID": "12345",
                    "Pole Structure": "35-5",
                    "Proposed Riser": "No",
                    "Proposed Guy": "No",
                    "PLA (%) with proposed attachment": "",
                    "Construction Grade of Analysis": "C",
                    "Height Lowest Com": "",
                    "Height Lowest CPS Electrical": "",
                    "Data Category": "Sample_Data",
                    "Bearing": "",
                    "Attacher Description": "Sample - No actual data processed",
                    "Attachment Height - Existing": "",
                    "Attachment Height - Proposed": "",
                    "Mid-Span (same span as existing)": "",
                    "One Touch Transfer": "",
                    "Remedy Description": "",
                    "Responsible Party": "",
                    "Existing CPSE Red Tag on Pole": "NO",
                    "Pole Data Missing in GIS": "",
                    "CPSE Application Comments": "",
                    "Movement Summary": "",
                    "From Pole": "PL12345",
                    "To Pole": "PL12346"
                }
                df_final_rows.append(sample_row)
            else:
                print("Processing DataFrame with actual data...")
                
                # Process each connection in order
                for _, record in df.iterrows():
                    connection_id = record.get('Connection ID', '')
                    node_id_1 = record.get('node_id_1', '')
                    
                    # Check if this is an underground connection
                    connection_data = job_data.get("connections", {}).get(connection_id, {})
                    is_underground = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added") == "underground cable"
                    
                    # Get attacher data using enhanced methods
                    attacher_data = self.get_attachers_for_node(job_data, node_id_1)
                    
                    # Get lowest heights for this connection (only for aerial)
                    lowest_com = ""
                    lowest_cps = ""
                    if not is_underground:
                        lowest_com, lowest_cps = self.get_lowest_heights_for_connection(job_data, connection_id)
                    else:
                        lowest_com = "NA"
                        lowest_cps = "NA"
                    
                    # Get From Pole/To Pole values
                    from_pole_props = record.get("From Pole Properties", {})
                    to_pole_props = record.get("To Pole Properties", {})
                    
                    # Get From Pole value (DLOC_number or SCID)
                    from_pole_value = from_pole_props.get('DLOC_number')
                    if not from_pole_value or from_pole_value == 'N/A':
                        from_pole_value = from_pole_props.get('pole_tag', 'N/A')
                    if from_pole_value == 'N/A':
                        from_pole_value = from_pole_props.get('scid', 'N/A')
                    
                    # Get To Pole value (DLOC_number or SCID)
                    to_pole_value = to_pole_props.get('DLOC_number')
                    if not to_pole_value or to_pole_value == 'N/A':
                        to_pole_value = to_pole_props.get('pole_tag', 'N/A')
                    if to_pole_value == 'N/A':
                        to_pole_value = to_pole_props.get('scid', 'N/A')
                    
                    # For underground connections, set To Pole value to "UG"
                    if is_underground:
                        to_pole_value = "UG"
                    else:
                        # Add PL prefix if needed for To Pole value
                        if to_pole_value != 'N/A' and not to_pole_value.upper().startswith('NT') and 'PL' not in to_pole_value.upper():
                            to_pole_value = f"PL{to_pole_value}"
                    
                    # Generate movement summaries for this connection using enhanced methods
                    all_movements = self.get_all_movements_summary(
                        attacher_data['main_attachers'], 
                        attacher_data['reference_spans'], 
                        attacher_data['backspan']['data']
                    )
                    cps_movements = self.get_cps_movements_only(
                        attacher_data['main_attachers'], 
                        attacher_data['reference_spans'], 
                        attacher_data['backspan']['data']
                    )
                    
                    # Base pole data for all rows related to this connection
                    base_row_data = {
                        "Connection ID": connection_id,
                        "Operation Number": record.get("Operation Number", ""),
                        "Attachment Action": record.get("Attachment Action", "I"),
                        "Pole Owner": record.get("Pole Owner", "CPS"),
                        "Pole #": record.get("Pole #", ""),
                        "SCID": record.get("SCID", ""),
                        "Pole Structure": record.get("Pole Structure", ""),
                        "Proposed Riser": "YES (1)" if is_underground else record.get("Proposed Riser", "No"),
                        "Proposed Guy": record.get("Proposed Guy", "No"),
                        "PLA (%) with proposed attachment": record.get("PLA (%) with proposed attachment", ""),
                        "Construction Grade of Analysis": record.get("Construction Grade of Analysis", "C"),
                        "Height Lowest Com": lowest_com,
                        "Height Lowest CPS Electrical": lowest_cps,
                        "One Touch Transfer": record.get("One Touch Transfer", ""),
                        "Remedy Description": cps_movements if cps_movements else record.get("Remedy Description", ""),
                        "Responsible Party": record.get("Responsible Party", ""),
                        "Existing CPSE Red Tag on Pole": record.get("Existing CPSE Red Tag on Pole", "NO"),
                        "Pole Data Missing in GIS": record.get("Pole Data Missing in GIS", ""),
                        "CPSE Application Comments": record.get("CPSE Application Comments", ""),
                        "Movement Summary": all_movements if all_movements else record.get("Movement Summary", ""),
                        "From Pole": from_pole_value,
                        "To Pole": to_pole_value,
                    }
                    
                    # Main Attachers
                    for i, attacher in enumerate(attacher_data['main_attachers']):
                        row = base_row_data.copy()
                        row["Data Category"] = "Main_Attacher"
                        row["Bearing"] = ""
                        row["Attacher Description"] = attacher.get('name', '')
                        row["Attachment Height - Existing"] = attacher.get('existing_height', '')
                        row["Attachment Height - Proposed"] = attacher.get('proposed_height', '')
                        row["Mid-Span (same span as existing)"] = self.get_midspan_proposed_heights(job_data, connection_id, attacher.get('name', ''))
                        
                        # For the flat sheet structure, only put Movement Summary and Remedy Description in the first main attacher row
                        if i > 0:
                            row["Movement Summary"] = ""
                            row["Remedy Description"] = ""
                        
                        df_final_rows.append(row)
                    
                    # Reference Spans
                    for ref_span in attacher_data['reference_spans']:
                        # Reference span header row
                        ref_header_row = base_row_data.copy()
                        ref_header_row["Data Category"] = "Ref_Span_Header"
                        ref_header_row["Bearing"] = ref_span.get('bearing', '')
                        ref_header_row["Attacher Description"] = f"REF ({ref_span.get('bearing', '')})"
                        ref_header_row["Attachment Height - Existing"] = ""
                        ref_header_row["Attachment Height - Proposed"] = ""
                        ref_header_row["Mid-Span (same span as existing)"] = ""
                        ref_header_row["Movement Summary"] = ""  # Don't repeat in reference spans
                        ref_header_row["Remedy Description"] = ""
                        df_final_rows.append(ref_header_row)
                        
                        # Reference span attacher rows
                        for attacher in ref_span.get('data', []):
                            row = base_row_data.copy()
                            row["Data Category"] = "Ref_Span_Attacher"
                            row["Bearing"] = ref_span.get('bearing', '')
                            row["Attacher Description"] = attacher.get('name', '')
                            row["Attachment Height - Existing"] = attacher.get('existing_height', '')
                            row["Attachment Height - Proposed"] = attacher.get('proposed_height', '')
                            row["Mid-Span (same span as existing)"] = ""  # Not applicable for ref spans
                            row["Movement Summary"] = ""  # Don't repeat in reference spans
                            row["Remedy Description"] = ""
                            df_final_rows.append(row)
                    
                    # Backspan
                    backspan_info = attacher_data['backspan']
                    if backspan_info['data']:
                        # Backspan header row
                        back_header_row = base_row_data.copy()
                        back_header_row["Data Category"] = "Backspan_Header"
                        back_header_row["Bearing"] = backspan_info.get('bearing', '')
                        back_header_row["Attacher Description"] = f"Backspan ({backspan_info.get('bearing', '')})"
                        back_header_row["Attachment Height - Existing"] = ""
                        back_header_row["Attachment Height - Proposed"] = ""
                        back_header_row["Mid-Span (same span as existing)"] = ""
                        back_header_row["Movement Summary"] = ""  # Don't repeat in backspans
                        back_header_row["Remedy Description"] = ""
                        df_final_rows.append(back_header_row)
                        
                        # Backspan attacher rows
                        for attacher in backspan_info['data']:
                            row = base_row_data.copy()
                            row["Data Category"] = "Backspan_Attacher"
                            row["Bearing"] = backspan_info.get('bearing', '')
                            row["Attacher Description"] = attacher.get('name', '')
                            row["Attachment Height - Existing"] = attacher.get('existing_height', '')
                            row["Attachment Height - Proposed"] = attacher.get('proposed_height', '')
                            row["Mid-Span (same span as existing)"] = ""  # Not applicable for backspans
                            row["Movement Summary"] = ""  # Don't repeat in backspans
                            row["Remedy Description"] = ""
                            df_final_rows.append(row)
                    
                    # If no attachers/refs/backspans, ensure at least one pole-only row is written
                    if not attacher_data['main_attachers'] and not attacher_data['reference_spans'] and not (attacher_data['backspan'] and attacher_data['backspan']['data']):
                        row = base_row_data.copy()
                        row["Data Category"] = "Pole_Only"
                        row["Bearing"] = ""
                        row["Attacher Description"] = "No attachers found"
                        row["Attachment Height - Existing"] = ""
                        row["Attachment Height - Proposed"] = ""
                        row["Mid-Span (same span as existing)"] = ""
                        # Keep Movement Summary and Remedy Description for pole-only rows
                        df_final_rows.append(row)
                    
                    # First row: Add headers "From Pole" and "To Pole"
                    header_row = {col: "" for col in desired_columns}
                    header_row["Height Lowest Com"] = "From Pole"  # Column J
                    header_row["Height Lowest CPS Electrical"] = "To Pole"  # Column K
                    df_final_rows.append(header_row)
                    
                    # Second row: Add the actual pole values
                    values_row = {col: "" for col in desired_columns}
                    # Get the "From Pole" value (current pole number)
                    from_pole_value = base_row_data.get("Pole #", "")
                    # Get the "To Pole" value (destination pole)
                    to_pole_value = base_row_data.get("To Pole", "")
                    # Add the values to the second row
                    values_row["Height Lowest Com"] = from_pole_value  # Value for From Pole in Column J
                    values_row["Height Lowest CPS Electrical"] = to_pole_value  # Value for To Pole in Column K
                    df_final_rows.append(values_row)
            
            # Create final DataFrame and write to Excel
            final_df = pd.DataFrame(df_final_rows, columns=desired_columns)
            # Write data starting at the configured row (Excel is 1-based, pandas is 0-based)
            final_df.to_excel(writer, sheet_name='MakeReadyData', index=False, startrow=EXCEL_DATA_START_ROW-1)
            
            # Get the worksheet after writing the data
            worksheet = writer.sheets['MakeReadyData']
            
            # Format for the merged header cells
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Format for merged data cells
            data_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Merge each column header vertically from rows 1-3
            for idx, col_name in enumerate(desired_columns):
                # Convert index to Excel column letter (A, B, C, etc.)
                col_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
                
                # Merge cells for this column from row 1 to 3
                worksheet.merge_range(f'{col_letter}1:{col_letter}3', col_name, header_format)
            
            # Now merge cells for columns A-I for each unique pole
            # Group rows by pole (identified by Operation Number)
            operation_groups = {}
            excel_row = EXCEL_DATA_START_ROW  # Starting row in Excel (1-based)
            
            # First, group rows by Operation Number, skipping empty rows
            for i, row in enumerate(df_final_rows):
                op_num = str(row.get("Operation Number", ""))
                # Skip empty rows (they have empty Operation Number)
                if not op_num:
                    continue
                    
                if op_num not in operation_groups:
                    operation_groups[op_num] = []
                operation_groups[op_num].append((excel_row + i, row))
            
            # Now merge cells for each group in columns A-I
            for op_num, rows in operation_groups.items():
                if len(rows) > 1:  # Only merge if there are multiple rows for this pole
                    start_row = rows[0][0]
                    end_row = rows[-1][0]
                    
                    # Merge cells in columns A through I
                    for col_idx in range(9):  # A=0, B=1, ..., I=8
                        col_letter = chr(65 + col_idx)  # A, B, C, etc.
                        
                        # Get the value from the first row of this group
                        value = rows[0][1].get(desired_columns[col_idx], "")
                        
                        # Merge the cells and set the value
                        worksheet.merge_range(f'{col_letter}{start_row+1}:{col_letter}{end_row+1}', value, data_format)
            
            # Auto-fit all columns
            for idx, col in enumerate(final_df.columns):
                # Get the maximum length in this column, handle potential empty series
                max_data_len = final_df[col].astype(str).map(len).max()
                if pd.isna(max_data_len): # Handle case where column might be all NaN or empty
                    max_data_len = 0
                
                max_len = max(
                    max_data_len,  # Length of data
                    len(str(col))    # Length of column name
                ) + 2  # Add a little extra space
                worksheet.set_column(idx, idx, max_len)  # Set column width
            
            print(f"Excel file created: {path}")
            print(f"Total rows written to Excel: {len(df_final_rows)}") # Clarified log

        except Exception as e:
            print(f"Error during Excel file creation or formatting: {str(e)}")
            # Optionally re-raise or handle as needed
            # raise
        finally:
            if writer:
                try:
                    writer.close()
                    print(f"Excel writer closed for {path}.")
                except Exception as e:
                    print(f"Error closing Excel writer for {path}: {str(e)}")


    def process_files(self, job_json_path, geojson_path=None):
        """Main processing function that replaces the GUI version"""
        try:
            # Validate job JSON path
            if not os.path.exists(job_json_path):
                print(f"Error: Job JSON file not found: {job_json_path}")
                return False

            self.job_data = self.load_json(job_json_path)
            print("Job JSON file loaded successfully.")
            
            # Make GeoJSON loading optional
            geojson_data = None
            if geojson_path and os.path.exists(geojson_path):
                try:
                    geojson_data = self.load_json(geojson_path)
                    print("GeoJSON file loaded successfully.")
                except Exception as e:
                    print(f"Warning: Could not load GeoJSON file: {str(e)}")
                    print("Continuing without GeoJSON data...")
            else:
                print("No GeoJSON file provided. Processing without GeoJSON data...")

            df = self.process_data(self.job_data, geojson_data)

            if df.empty:
                print("Warning: DataFrame is empty. No data to export.")
                # Still create a log file indicating no data was processed.
                json_base = os.path.splitext(os.path.basename(job_json_path))[0]
                log_filename_empty = f"{json_base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_Processing_Log.txt"
                log_path_empty = os.path.join(self.downloads_path, log_filename_empty)
                self.logger.write_summary(log_path_empty) # Log will show 0 items processed
                print(f"Processing log for empty data written to: {log_path_empty}")
                return False

            # Generate unique output filenames using timestamp to prevent conflicts
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            json_base_name = os.path.splitext(os.path.basename(job_json_path))[0]
            
            output_excel_filename = f"{json_base_name}_Output_{timestamp}.xlsx"
            output_excel_path = os.path.join(self.downloads_path, output_excel_filename)
            
            # Versioning (if somehow a file with the exact same timestamp exists, though unlikely)
            version = 2
            temp_excel_path = output_excel_path
            while os.path.exists(temp_excel_path):
                temp_excel_filename = f"{json_base_name}_Output_{timestamp}_v{version}.xlsx"
                temp_excel_path = os.path.join(self.downloads_path, temp_excel_filename)
                version += 1
            output_excel_path = temp_excel_path # Use the versioned path if needed

            self.create_output_excel(output_excel_path, df, self.job_data)
            # Corrected log message for clarity
            excel_row_count = 0
            try:
                # A simple way to get row count without fully parsing if pandas isn't already loaded
                # For more robust validation, consider using openpyxl or similar to read row count
                if os.path.exists(output_excel_path):
                     # This is a placeholder, actual row count is in df_final_rows inside create_output_excel
                     # We'll rely on the print statement from within create_output_excel for now.
                     pass # excel_row_count will be printed from create_output_excel
            except Exception as e:
                print(f"Could not verify Excel row count: {e}")

            print(f"Successfully created output file: {output_excel_path}")
            # This log refers to the initial DataFrame size, not the final Excel row count.
            print(f"Initial DataFrame for processing contained {len(df)} connection records.") 
            
            # Write the processing log with a unique name
            log_filename = f"{json_base_name}_Log_{timestamp}.txt"
            log_path = os.path.join(self.downloads_path, log_filename)
            self.logger.write_summary(log_path)
            print(f"Processing log written to: {log_path}")
            
            return True
            
        except Exception as e:
            print(f"Error processing files: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False


def main():
    """Main function to run the file processor - for local testing"""
    # This main function is intended for local testing and development.
    # In a production environment, FileProcessor().process_files() would be called
    # by the Flask/FastAPI application.

    # Example: Create a dummy JSON file for testing if one doesn't exist
    test_json_filename = "test_job_data.json"
    if not os.path.exists(test_json_filename):
        print(f"Creating dummy '{test_json_filename}' for testing.")
        dummy_data = {
            "nodes": {
                "node1": {"attributes": {"scid": {"auto_button": "100"}}, "photos": {}},
                "node2": {"attributes": {"scid": {"auto_button": "101"}}, "photos": {}}
            },
            "connections": {
                "conn1": {"node_id_1": "node1", "node_id_2": "node2", "attributes": {"connection_type": {"button_added": "aerial cable"}}}
            },
            "traces": {}
        }
        with open(test_json_filename, 'w') as f:
            json.dump(dummy_data, f)
        job_json_path = test_json_filename
    elif os.path.exists("CPS_6457E_03.json"): # Prioritize specific test file if available
        job_json_path = "CPS_6457E_03.json"
    else: # Fallback if specific test file is not present but dummy one is
        job_json_path = test_json_filename

    print(f"--- Local Test Run ---")
    print(f"Using Job JSON: {job_json_path}")

    if not os.path.exists(job_json_path):
        print(f"Error: Job JSON file not found at {job_json_path}. Please create it or provide a valid path.")
        return

    # Create processor instance. For local testing, output_dir can be specified.
    # If None, it will use the default logic (e.g., system temp).
    # For this example, let's create an 'outputs' directory in the current working directory.
    local_output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(local_output_dir, exist_ok=True)
    print(f"Local test outputs will be saved to: {local_output_dir}")
    
    processor = FileProcessor(output_dir=local_output_dir)
    
    # Call process_files, which now handles loading JSON internally
    success = processor.process_files(job_json_path) # GeoJSON is optional

    if success:
        print("--- Local Test Run Completed Successfully ---")
    else:
        print("--- Local Test Run Failed ---")


if __name__ == "__main__":
    main()
