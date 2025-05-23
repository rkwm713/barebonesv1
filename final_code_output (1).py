
# === Constants for Attachment and Span Labels ===
EXISTING_ATTACHMENT_HEIGHT = "Attachment Height - Existing"
MR_MOVE = "MR Move"
EFFECTIVE_MOVE = "Effective Move"
PROPOSED_ATTACHMENT_HEIGHT = "Attachment Height - Proposed"

EXISTING_SPAN_HEIGHT = "Mid-Span Existing"
SPAN_MR_MOVE = "Span MR Move"
SPAN_EFFECTIVE_MOVE = "Span Effective Move"
SPAN_PROPOSED_HEIGHT = "Mid-Span Proposed"





class FileProcessorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Processor")
        self.geometry("500x350")
        self.downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

        self.job_json_path = tk.StringVar()
        self.geojson_path = tk.StringVar()
        self.latest_output_path = None

        ttk.Label(self, text="Job JSON:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self, textvariable=self.job_json_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(self, text="Browse", command=lambda: self.browse_file("job")).grid(row=0, column=2)

        ttk.Label(self, text="GeoJSON:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self, textvariable=self.geojson_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(self, text="Browse", command=lambda: self.browse_file("geojson")).grid(row=1, column=2)

        ttk.Button(self, text="Process Files", command=self.process_files).grid(row=2, column=0, columnspan=3, pady=20)

        self.info_text = tk.Text(self, height=8, width=60)
        self.info_text.grid(row=3, column=0, columnspan=3, pady=10)

        self.open_file_button = ttk.Button(self, text="Open Output File", command=self.open_output_file)
        self.open_file_button.grid(row=4, column=0, columnspan=3, pady=10)
        self.open_file_button.grid_remove()

    def browse_file(self, file_type):
        filetypes = {
            "job": [("JSON files", "*.json")],
            "geojson": [("GeoJSON files", "*.json *.geojson")]
        }
        filename = filedialog.askopenfilename(initialdir=self.downloads_path, filetypes=filetypes[file_type])
        if filename:
            if file_type == "job":
                self.job_json_path.set(filename)
            elif file_type == "geojson":
                self.geojson_path.set(filename)

    def open_output_file(self):
        if self.latest_output_path:
            os.startfile(self.latest_output_path)

    def format_height_feet_inches(self, height_float):
        if not isinstance(height_float, (int, float)):
            return ""
        total_inches = round(height_float)
        feet = total_inches // 12
        inches = total_inches % 12
        return f"{feet}'-{inches}\""

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
                        self.info_text.insert(tk.END, f"Height parse error: {str(e)}\n")
        return heights

    def get_attachers_for_node(self, job_data, node_id):
        """Get all attachers for a node including guying and drip loops"""
        # Store main pole attachers
        main_attacher_data = []
        
        # Get neutral wire height
        neutral_height = self.get_neutral_wire_height(job_data, node_id)
        
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
            
            # Process wire section for main pole attachers
            for wire in photofirst_data.get("wire", {}).values():
                trace_id = wire.get("_trace")
                if trace_id and trace_id in trace_data:
                    trace_info = trace_data[trace_id]
                    company = trace_info.get("company", "").strip()
                    cable_type = trace_info.get("cable_type", "").strip()
                    
                    # Skip if cable_type is "Primary"
                    if cable_type.lower() == "primary":
                        continue
                        
                    measured_height = wire.get("_measured_height")
                    mr_move = wire.get("mr_move")
                    
                    # Only include wires at or below neutral height if neutral height is known
                    if (
                        measured_height is not None
                        and neutral_height is not None
                    ):
                        try:
                            if float(measured_height) > neutral_height:
                                # Above neutral – skip per new requirement
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    if company and cable_type:
                        attacher_name = f"{company} {cable_type}"
                        existing_height = ""
                        proposed_height = ""
                        raw_height = None
                        
                        if measured_height is not None:
                            try:
                                measured_height = float(measured_height)
                                raw_height = measured_height
                                feet = int(measured_height) // 12
                                inches = round(measured_height - (feet * 12))
                                existing_height = f"{feet}'-{inches}\""
                                
                                # Always calculate proposed height if mr_move exists
                                if mr_move is not None:
                                    try:
                                        mr_move = float(mr_move)
                                        proposed_height_value = measured_height + mr_move
                                        feet_proposed = int(proposed_height_value) // 12
                                        inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                        proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                                    except (ValueError, TypeError):
                                        proposed_height = ""
                            except (ValueError, TypeError):
                                existing_height = ""
                                proposed_height = ""
                                raw_height = 0
                        
                        main_attacher_data.append({
                            'name': attacher_name,
                            'existing_height': existing_height,
                            'proposed_height': proposed_height,
                            'raw_height': raw_height or 0
                        })
            
            # === New: Process equipment section for main pole attachers (at or below neutral) ===
            for equip in photofirst_data.get("equipment", {}).values():
                trace_id = equip.get("_trace")
                if trace_id and trace_id in trace_data:
                    trace_info = trace_data[trace_id]
                    company = trace_info.get("company", "").strip()
                    equipment_type = trace_info.get("equipment_type", "").strip()

                    if not company or not equipment_type:
                        continue

                    measured_height = equip.get("_measured_height")
                    mr_move = equip.get("mr_move")

                    # Only include equipment at or below neutral height if neutral height is known
                    if (
                        measured_height is not None
                        and neutral_height is not None
                    ):
                        try:
                            if float(measured_height) > neutral_height:
                                continue  # Above neutral – skip
                        except (ValueError, TypeError):
                            continue
                    else:
                        # If we don't have measured height or neutral height, skip – can't compare
                        continue

                    attacher_name = f"{company} {equipment_type}"
                    existing_height = ""
                    proposed_height = ""
                    raw_height = None

                    try:
                        measured_height = float(measured_height)
                        raw_height = measured_height
                        feet = int(measured_height) // 12
                        inches = round(measured_height - (feet * 12))
                        existing_height = f"{feet}'-{inches}\""

                        # Always calculate proposed height if mr_move exists
                        if mr_move is not None:
                            try:
                                mr_move = float(mr_move)
                                proposed_height_value = measured_height + mr_move
                                feet_proposed = int(proposed_height_value) // 12
                                inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                            except (ValueError, TypeError):
                                proposed_height = ""
                    except (ValueError, TypeError):
                        existing_height = ""
                        proposed_height = ""
                        raw_height = 0

                    main_attacher_data.append({
                        'name': attacher_name,
                        'existing_height': existing_height,
                        'proposed_height': proposed_height,
                        'raw_height': raw_height or 0
                    })
            
            # Process guying section - now including down guys below neutral
            for guy in photofirst_data.get("guying", {}).values():
                trace_id = guy.get("_trace")
                if trace_id and trace_id in trace_data:
                    trace_info = trace_data[trace_id]
                    company = trace_info.get("company", "").strip()
                    cable_type = trace_info.get("cable_type", "").strip()
                    
                    measured_height = guy.get("_measured_height")
                    mr_move = guy.get("mr_move")
                    
                    if company and cable_type:
                        # Check if this is a down guy below neutral
                        is_down_guy = False
                        if measured_height is not None and neutral_height is not None:
                            try:
                                guy_height = float(measured_height)
                                if guy_height < neutral_height:
                                    is_down_guy = True
                            except (ValueError, TypeError):
                                pass
                        
                        if is_down_guy:
                            attacher_name = f"{company} {cable_type} (Down Guy)"
                            existing_height = ""
                            proposed_height = ""
                            raw_height = None
                            
                            if measured_height is not None:
                                try:
                                    measured_height = float(measured_height)
                                    raw_height = measured_height
                                    feet = int(measured_height) // 12
                                    inches = round(measured_height - (feet * 12))
                                    existing_height = f"{feet}'-{inches}\""
                                    
                                    # Always calculate proposed height if mr_move exists
                                    if mr_move is not None:
                                        try:
                                            mr_move = float(mr_move)
                                            proposed_height_value = measured_height + mr_move
                                            feet_proposed = int(proposed_height_value) // 12
                                            inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                            proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                                        except (ValueError, TypeError):
                                            proposed_height = ""
                                except (ValueError, TypeError):
                                    existing_height = ""
                                    proposed_height = ""
                                    raw_height = 0
                            
                            main_attacher_data.append({
                                'name': attacher_name,
                                'existing_height': existing_height,
                                'proposed_height': proposed_height,
                                'raw_height': raw_height or 0
                            })
        
        # Sort by height from highest to lowest
        main_attacher_data.sort(key=lambda x: x['raw_height'], reverse=True)
        
        # Get reference spans
        reference_spans = self.get_reference_attachers(job_data, node_id)
        
        # Get backspan data
        backspan_data, backspan_bearing = self.get_backspan_attachers(job_data, node_id)
        
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
        lowest_com = float('inf')
        lowest_cps = float('inf')
        
        # Get the connection data
        connection_data = job_data.get("connections", {}).get(connection_id, {})
        if not connection_data:
            return "", ""
            
        # Get sections from the connection
        sections = connection_data.get("sections", {})
        if not sections:
            return "", ""
            
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
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
                        
                        # For CPS ENERGY electrical (Neutral or Street Light)
                        if company.lower() == "cps energy" and cable_type.lower() in ["neutral", "street light"]:
                            lowest_cps = min(lowest_cps, height)
                        # For communication attachments (non-CPS)
                        elif company.lower() != "cps energy":
                            lowest_com = min(lowest_com, height)
                    except (ValueError, TypeError):
                        continue
        
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
            
        return lowest_com_formatted, lowest_cps_formatted

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
            # Check if it's a reference connection
            connection_type = conn_data.get("attributes", {}).get("connection_type", {})
            if isinstance(connection_type, dict):
                connection_type_value = next(iter(connection_type.values()), "")
            else:
                connection_type_value = connection_type.get("button_added", "")
            
            if "reference" in str(connection_type_value).lower():
                # Check if current_node_id matches either node
                if (conn_data.get("node_id_1") == current_node_id or 
                    conn_data.get("node_id_2") == current_node_id):
                    # Calculate bearing
                    bearing = ""
                    sections = conn_data.get("sections", {})
                    if sections:
                        # Find the midpoint section (if multiple sections exist)
                        section_ids = list(sections.keys())
                        mid_section_index = len(section_ids) // 2
                        mid_section_id = section_ids[mid_section_index]
                        mid_section = sections[mid_section_id]
                        
                        # Calculate bearing using midpoint section
                        lat = mid_section.get("latitude")
                        lon = mid_section.get("longitude")
                        if lat and lon:
                            # Get the current pole coordinates
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

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate the bearing between two points
        Returns tuple of (degrees, cardinal_direction)"""
        import math
        
        # Convert to radians
        lat1 = math.radians(float(lat1))
        lon1 = math.radians(float(lon1))
        lat2 = math.radians(float(lat2))
        lon2 = math.radians(float(lon2))
        
        # Calculate bearing
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        bearing = math.degrees(math.atan2(y, x))
        
        # Convert to compass bearing (0-360)
        bearing = (bearing + 360) % 360
        
        # Convert to cardinal direction
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(bearing / 45) % 8
        cardinal = directions[index]
        
        return (bearing, cardinal)

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

    def process_data(self, job_data, geojson_data):
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
        
        # First pass: collect all underground connections for each pole
        pole_underground_connections = {}
        underground_connections = {}  # Initialize the dictionary for storing underground connections
        for connection_id, connection_data in job_data.get("connections", {}).items():
            connection_type = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added", "")
            if connection_type == "underground cable":
                node_id_1 = connection_data.get("node_id_1")
                if node_id_1:
                    pole_underground_connections[node_id_1] = pole_underground_connections.get(node_id_1, 0) + 1
        
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
                "Movement Summary": self.get_movement_summary(self.get_attachers_for_node(job_data, from_node_id)['main_attachers']),
                "node_id_1": from_node_id,
                "node_id_2": to_node_id,
                "From Pole Properties": from_pole_props,
                "To Pole Properties": to_pole_props
            }
            connection_data_list.append(row)
            operation_number += 1
        
        # Sort the connection data by from pole's SCID
        connection_data_list.sort(key=lambda x: (
            self.compare_scids(x['From Pole Properties'].get('scid', 'N/A'), 'N/A'),
            x['From Pole Properties'].get('scid', 'N/A'),
            x['To Pole Properties'].get('scid', 'N/A')
        ))
        
        # Update operation numbers after sorting
        for i, row in enumerate(connection_data_list, 1):
            row['Operation Number'] = i
        
        # Create DataFrame from sorted data
        df = pd.DataFrame(connection_data_list)
        
        # Drop the sorting column
        if 'SCID_sort' in df.columns:
            df = df.drop('SCID_sort', axis=1)
        
        return df

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
                                # Debug print for first span
                                if connection_id == list(job_data.get("connections", {}).keys())[0]:
                                    print("\n=== First Span Debug Info ===")
                                    print(f"Attacher: {attacher_name}")
                                    print(f"Measured Height: {self.format_height_feet_inches(measured_height)}")
                                    print(f"MR Move: {wire.get('mr_move', 0)}")
                                    print(f"Effective Moves: {wire.get('_effective_moves', {})}")
                                    print("===========================\n")
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
                        # Only add if nonzero
                        if abs(move_value) > 0.01:
                            # Round up half of the move
                            half_move = -(-move_value // 2) if move_value > 0 else (move_value // 2)
                            total_move += half_move
                    except (ValueError, TypeError):
                        continue
            # Calculate proposed height
            proposed_height = lowest_height + total_move
            return self.format_height_feet_inches(proposed_height)
        
        return ""  # Return empty string if no section found or if there was an error

    def process_files(self):
        self.info_text.delete(1.0, tk.END)
        try:
            # Validate job JSON path
            job_json_path = self.job_json_path.get()
            if not job_json_path:
                self.info_text.insert(tk.END, "Error: Please select a Job JSON file.\n")
                return
                
            if not os.path.exists(job_json_path):
                self.info_text.insert(tk.END, f"Error: Job JSON file not found: {job_json_path}\n")
                return

            self.job_data = self.load_json(job_json_path)  # Store as instance variable
            
            # Make GeoJSON loading optional
            geojson_data = None
            geojson_path = self.geojson_path.get()
            if geojson_path:
                if not os.path.exists(geojson_path):
                    self.info_text.insert(tk.END, f"Warning: GeoJSON file not found: {geojson_path}\n")
                    self.info_text.insert(tk.END, "Continuing without GeoJSON data...\n")
                else:
                    try:
                        geojson_data = self.load_json(geojson_path)
                        self.info_text.insert(tk.END, "GeoJSON file loaded successfully.\n")
                    except Exception as e:
                        self.info_text.insert(tk.END, f"Warning: Could not load GeoJSON file: {str(e)}\n")
                        self.info_text.insert(tk.END, "Continuing without GeoJSON data...\n")
            else:
                self.info_text.insert(tk.END, "No GeoJSON file selected. Processing without GeoJSON data...\n")

            self.info_text.insert(tk.END, "Job JSON file loaded successfully.\n")
            df = self.process_data(self.job_data, geojson_data)  # Use instance variable

            if df.empty:
                self.info_text.insert(tk.END, "Warning: DataFrame is empty. No data to export.\n")
                return

            # Generate output filename based on JSON file name
            json_base = os.path.splitext(os.path.basename(job_json_path))[0]
            output_base = f"{json_base}_Python_Output"
            output_filename = f"{output_base}.xlsx"
            output_path = os.path.join(self.downloads_path, output_filename)
            
            # Check if file exists and add versioning if needed
            version = 2
            while os.path.exists(output_path):
                output_filename = f"{output_base}_v{version}.xlsx"
                output_path = os.path.join(self.downloads_path, output_filename)
                version += 1
            
            self.create_output_excel(output_path, df, self.job_data)  # Pass job_data as parameter

            self.latest_output_path = output_path
            self.open_file_button.grid()
            self.info_text.insert(tk.END, f"Successfully created output file: {output_path}\n")
            self.info_text.insert(tk.END, f"DataFrame contains {len(df)} rows.\n")
        except Exception as e:
            self.info_text.insert(tk.END, f"Error processing files: {str(e)}\n")
            import traceback
            self.info_text.insert(tk.END, f"Traceback: {traceback.format_exc()}\n")

    def load_json(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
        
    def create_output_excel(self, path, df, job_data):
        # First sort by SCID to assign operation numbers
        df['SCID_numeric'] = df['SCID'].apply(lambda x: float('inf') if x == 'N/A' or x == '' else float(x))
        df = df.sort_values('SCID_numeric')
        df = df.drop('SCID_numeric', axis=1)
        
        # Assign operation numbers based on SCID sort
        df['Operation Number'] = range(1, len(df) + 1)
        
        # Create a list to store all rows with their attachers in the correct order
        all_rows = []
        
        # Process each connection in order of operation number
        for _, record in df.sort_values('Operation Number').iterrows():
            connection_id = record['Connection ID']
            node_id_1 = record['node_id_1']
            
            # Check if this is an underground connection
            connection_data = job_data.get("connections", {}).get(connection_id, {})
            is_underground = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added") == "underground cable"
            
            # Get attacher data
            attacher_data = self.get_attachers_for_node(job_data, node_id_1)
            
            # Get lowest heights for this connection
            lowest_com, lowest_cps = self.get_lowest_heights_for_connection(job_data, connection_id)
            
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
            
            # Store the connection info and its related data
            connection_data = {
                'record': record,
                'lowest_com': lowest_com,
                'lowest_cps': lowest_cps,
                'from_pole_value': from_pole_value,
                'to_pole_value': to_pole_value,
                'main_attachers': attacher_data['main_attachers'],
                'reference_spans': attacher_data['reference_spans'],
                'backspan': attacher_data['backspan'],
                'is_underground': is_underground
            }
            
            all_rows.append(connection_data)
        
        # Now write to Excel maintaining the order
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        wb = writer.book
        ws = wb.add_worksheet('Sheet1')

        # === Formats ===
        section_header_format = wb.add_format({
            'bold': True, 
            'align': 'center', 
            'valign': 'vcenter',
            'bg_color': '#B7DEE8', 
            'border': 1, 
            'text_wrap': True
        })
        
        sub_header_format = wb.add_format({
            'bold': True, 
            'align': 'center', 
            'valign': 'vcenter',
            'border': 1, 
            'bg_color': '#DAEEF3', 
            'text_wrap': True
        })
        
        cell_format = wb.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True, 
            'border': 1
        })
        
        underground_format = wb.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1,
            'bg_color': '#F2DCDB',  # Light red background
            'font_color': '#000000'
        })
        
        backspan_format = wb.add_format({
            'bold': True, 
            'align': 'center', 
            'valign': 'vcenter',
            'border': 1, 
            'bg_color': '#D9E1F2'
        })
        
        reference_format = wb.add_format({
            'bold': True, 
            'align': 'center', 
            'valign': 'vcenter',
            'border': 1, 
            'bg_color': '#E2EFD9'  # Light green background
        })

        # Set default row height
        ws.set_default_row(20)

        # === Columns ===
        columns = [
            "Connection ID", "Operation Number", "Attachment Action", "Pole Owner", "Pole #", "SCID", "Pole Structure",
            "Proposed Riser", "Proposed Guy", "PLA (%) with proposed attachment", "Construction Grade of Analysis",
            "Height Lowest Com", "Height Lowest CPS Electrical", "Attacher Description",
            "Attachment Height - Existing", "Attachment Height - Proposed",
            "Mid-Span (same span as existing)",
            "One Touch Transfer", "Remedy Description", "Responsible Party",
            "Existing CPSE Red Tag on Pole", "Pole Data Missing in GIS", "CPSE Application Comments",
            "Movement Summary"
        ]

        # Write headers
        self.write_excel_headers(ws, columns, section_header_format, sub_header_format)
        
        row_pos = 3  # Start after headers

        # Process each connection in the maintained order
        for connection_data in all_rows:
            start_row = row_pos
            record = connection_data['record']
            is_underground = connection_data['is_underground']
            
            # Process main attachers
            main_attachers = connection_data['main_attachers']
            
            if is_underground:
                group_start_row = row_pos
                # Ensure we have at least 3 rows total for data (before From/To Pole overlap)
                while len(main_attachers) < 3:
                    main_attachers.append({'name': '', 'existing_height': '', 'proposed_height': '', 'raw_height': 0})

                attacher_start = row_pos
                # Write main attachers for the from pole
                for i, attacher in enumerate(main_attachers):
                    current_row = row_pos + i
                    if i == 0:
                        for col_num, col_name in enumerate(columns[:11]):
                            ws.write(current_row, col_num, record.get(col_name, ""), cell_format)
                    self.write_attacher_row(ws, current_row, attacher, record['Connection ID'], job_data, cell_format)
                row_pos += len(main_attachers)
                attacher_end = row_pos - 1

                # Process reference spans for underground connections
                for ref_span in connection_data['reference_spans']:
                    bearing = ref_span.get('bearing', '')
                    ref_data = ref_span.get('data', [])
                    if ref_data:
                        header_text = f"REF ({bearing})" if bearing else "REF"
                        ws.merge_range(row_pos, 13, row_pos, 16, header_text, reference_format)
                        row_pos += 1
                        for ref_row in ref_data:
                            self.write_attacher_row(ws, row_pos, ref_row, record['Connection ID'], job_data, cell_format)
                            row_pos += 1

                # Process backspan data for underground connections
                backspan_data = connection_data['backspan']
                if backspan_data['data']:
                    bearing = backspan_data['bearing']
                    header_text = f"Backspan ({bearing})" if bearing else "Backspan"
                    ws.merge_range(row_pos, 13, row_pos, 16, header_text, backspan_format)
                    row_pos += 1
                    for bs_row in backspan_data['data']:
                        self.write_attacher_row(ws, row_pos, bs_row, record['Connection ID'], job_data, cell_format)
                        row_pos += 1

                # Calculate From Pole/To Pole positions - they will overlap with the last two rows
                header_row = row_pos - 2
                value_row = row_pos - 1

                # Merge and fill Height Lowest Com/Electrical with 'NA' for all attacher rows (not for ref/backspan or header rows)
                if header_row - 1 > attacher_start:
                    ws.merge_range(attacher_start, 11, header_row - 1, 11, "NA", cell_format)
                    ws.merge_range(attacher_start, 12, header_row - 1, 12, "NA", cell_format)
                else:
                    ws.write(attacher_start, 11, "NA", cell_format)
                    ws.write(attacher_start, 12, "NA", cell_format)

                # Write From Pole/To Pole headers and values (overlapping last two rows, like aerial)
                ws.write(header_row, 11, "From Pole", sub_header_format)
                ws.write(header_row, 12, "To Pole", sub_header_format)
                ws.write(value_row, 11, connection_data['from_pole_value'], cell_format)
                ws.write(value_row, 12, connection_data['to_pole_value'], cell_format)

                # Store the final remedy text and merge/write it after all rows for the group are written
                install_lines = []
                riser_lines = set()
                for attacher in main_attachers:
                    if attacher.get('is_proposed'):
                        company = attacher['name'].split()[0]
                        height = attacher.get('proposed_height') or attacher.get('existing_height') or ""
                        install_line = f"Install proposed {attacher['name']} at {height}" if height else f"Install proposed {attacher['name']}"
                        install_lines.append(install_line)
                        riser_lines.add(f"Install proposed {company} Riser @ {height} to UG connection" if height else f"Install proposed {company} Riser to UG connection")
                if not install_lines and main_attachers:
                    attacher = main_attachers[0]
                    company = attacher['name'].split()[0]
                    height = attacher.get('proposed_height') or attacher.get('existing_height') or ""
                    install_lines.append(f"Install proposed {attacher['name']} at {height}" if height else f"Install proposed {attacher['name']}")
                    riser_lines.add(f"Install proposed {company} Riser @ {height} to UG connection" if height else f"Install proposed {company} Riser to UG connection")
                movement_summary = self.get_movement_summary(main_attachers)
                remedy_text = "\n".join(install_lines + list(riser_lines))
                if movement_summary:
                    remedy_text += f"\n{movement_summary}"
                group_end_row = row_pos - 1
                print(f"[DEBUG] Connection {record['Connection ID']} - Writing Remedy Text to Excel:")
                print(f"Start Row: {group_start_row}, End Row: {group_end_row}")
                print(f"Remedy Text:\n{remedy_text}\n")
                ws.merge_range(group_start_row, 18, group_end_row, 18, remedy_text, cell_format)
            else:
                # Ensure we have at least 3 rows total for data (before From/To Pole overlap)
                while len(main_attachers) < 3:
                    main_attachers.append({'name': '', 'existing_height': '', 'proposed_height': '', 'raw_height': 0})

                # Write main attachers
                for i, attacher in enumerate(main_attachers):
                    current_row = row_pos + i
                    if i == 0:  # First row gets all the common data
                        for col_num, col_name in enumerate(columns[:11]):  # Now includes Construction Grade
                            ws.write(current_row, col_num, record.get(col_name, ""), cell_format)
                    
                    # Write attacher info including mid-span height
                    self.write_attacher_row(ws, current_row, attacher, record['Connection ID'], job_data, cell_format)

                row_pos += len(main_attachers)

                # Process reference spans
                for ref_span in connection_data['reference_spans']:
                    bearing = ref_span.get('bearing', '')
                    ref_data = ref_span.get('data', [])
                    
                    if ref_data:
                        # Write reference span header with bearing
                        header_text = f"REF ({bearing})" if bearing else "REF"
                        ws.merge_range(row_pos, 13, row_pos, 16, header_text, reference_format)
                        row_pos += 1

                        # Write reference span entries
                        for ref_row in ref_data:
                            self.write_attacher_row(ws, row_pos, ref_row, record['Connection ID'], job_data, cell_format)
                            row_pos += 1

                # Process backspan data
                backspan_data = connection_data['backspan']
                if backspan_data['data']:
                    # Write backspan header with bearing
                    bearing = backspan_data['bearing']
                    header_text = f"Backspan ({bearing})" if bearing else "Backspan"
                    ws.merge_range(row_pos, 13, row_pos, 16, header_text, backspan_format)
                    row_pos += 1

                    # Write backspan entries
                    for bs_row in backspan_data['data']:
                        self.write_attacher_row(ws, row_pos, bs_row, record['Connection ID'], job_data, cell_format)
                        row_pos += 1

                # Calculate From Pole/To Pole positions - they will overlap with the last two rows
                header_row = row_pos - 2
                value_row = row_pos - 1

                # Write lowest heights in the merged cells (all rows except last two)
                if header_row - 1 > start_row:
                    # If we have multiple rows to merge
                    ws.merge_range(start_row, 11, header_row - 1, 11, connection_data['lowest_com'], cell_format)  # Column L
                    ws.merge_range(start_row, 12, header_row - 1, 12, connection_data['lowest_cps'], cell_format)  # Column M
                else:
                    # If we only have one row, just write the values
                    ws.write(start_row, 11, connection_data['lowest_com'], cell_format)
                    ws.write(start_row, 12, connection_data['lowest_cps'], cell_format)

                # Write From Pole/To Pole headers and values (overlapping last two rows)
                ws.write(header_row, 11, "From Pole", sub_header_format)  # Shifted right by 1
                ws.write(header_row, 12, "To Pole", sub_header_format)  # Shifted right by 1
                ws.write(value_row, 11, connection_data['from_pole_value'], cell_format)  # Shifted right by 1
                ws.write(value_row, 12, connection_data['to_pole_value'], cell_format)  # Shifted right by 1

            # Get movement summaries
            all_movements = self.get_movement_summary(connection_data['main_attachers'])
            cps_movements = self.get_movement_summary(connection_data['main_attachers'], cps_only=True)
            
            # Merge columns A through K for the entire group
            for col in range(11):  # 0 through 10 for columns A through K
                try:
                    ws.merge_range(start_row, col, row_pos - 1, col, record[columns[col]], cell_format)
                except:
                    # If merge fails (single cell), just write the value
                    ws.write(start_row, col, record[columns[col]], cell_format)

            # Only write to column S if this is not an underground group
            if not is_underground:
                # Merge the Remedy Description column (S) and write all movements
                try:
                    ws.merge_range(start_row, 18, row_pos - 1, 18, all_movements, cell_format)
                except:
                    ws.write(start_row, 18, all_movements, cell_format)

            # Merge the CPS movements column (W) and write CPS-only movements
            try:
                ws.merge_range(start_row, 22, row_pos - 1, 22, cps_movements, cell_format)
            except:
                ws.write(start_row, 22, cps_movements, cell_format)

            # Merge remaining columns Q through V (except S which we already handled)
            for col in range(17, 23):
                if col != 18:  # Skip column S (Remedy Description) as we already handled it
                    try:
                        col_name = columns[col] if col < len(columns) else ""
                        if col_name and col != 22:  # Skip column W as we already handled it
                            value = record.get(col_name, "")
                            ws.merge_range(start_row, col, row_pos - 1, col, value, cell_format)
                    except:
                        if col != 22:  # Skip column W as we already handled it
                            ws.write(start_row, col, "", cell_format)

        writer.close()

    def write_excel_headers(self, ws, columns, section_header_format, sub_header_format):
        """Write the Excel headers with proper formatting"""
        # === Top header: merge sections ===
        ws.merge_range(0, 11, 0, 12, "Existing Mid-Span Data", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 13, 0, 16, "Make Ready Data", section_header_format)  # Shifted right by 1

        # === Row 2 headers ===
        ws.merge_range(1, 11, 2, 11, "Height Lowest Com", sub_header_format)  # Shifted right by 1
        ws.merge_range(1, 12, 2, 12, "Height Lowest CPS Electrical", sub_header_format)  # Shifted right by 1
        ws.merge_range(1, 13, 2, 13, "Attacher Description", sub_header_format)  # Shifted right by 1
        ws.merge_range(1, 14, 1, 15, "Attachment Height", sub_header_format)  # Shifted right by 1
        ws.write(2, 14, "Existing", sub_header_format)  # Shifted right by 1
        ws.write(2, 15, "Proposed", sub_header_format)  # Shifted right by 1
        ws.write(1, 16, "Mid-Span (same span as existing)", sub_header_format)  # Shifted right by 1
        ws.write(2, 16, "Proposed", sub_header_format)  # Shifted right by 1

        # === Extra header columns ===
        ws.merge_range(0, 17, 2, 17, "One Touch Transfer:\nMake Ready or Upgrade &\nSimple or Complex", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 18, 2, 18, "Remedy Description and Explanation/\nAdditional Comments/Variance Requests", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 19, 2, 19, "Responsible Party:\nAttacher or CPS", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 20, 2, 20, "Existing CPSE Red Tag on Pole", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 21, 2, 21, "Pole Data Missing in GIS\n(if yes fill out Missing Pole Data worksheet)", section_header_format)  # Shifted right by 1
        ws.merge_range(0, 22, 2, 22, "CPSE Application Comments", section_header_format)  # Shifted right by 1
            
        # === Fix: Add top-level headers for initial columns including Construction Grade ===
        for col_num, col_name in enumerate(columns[:11]):  # Now includes Construction Grade
            ws.merge_range(0, col_num, 2, col_num, col_name, section_header_format)
            
        # === Auto column width and center alignment ===
        for col_num, col_name in enumerate(columns):
            ws.set_column(col_num, col_num, max(len(col_name) + 2, 18), None)  # Set width without default format

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

    def write_attacher_row(self, ws, row_pos, attacher, connection_id, job_data, cell_format):
        """Write a row for an attacher including the proposed mid-span height"""
        # Check if this is a reference span row
        is_reference = attacher.get('is_reference', False)
        
        if is_reference:
            # For reference spans, just write the pre-calculated heights
            ws.write(row_pos, 13, attacher['name'], cell_format)  # Attacher name
            ws.write(row_pos, 14, attacher['existing_height'], cell_format)  # Column O - Existing height
            ws.write(row_pos, 15, attacher['proposed_height'], cell_format)  # Column P - Proposed height
            ws.write(row_pos, 16, "", cell_format)  # Column Q - always empty for reference spans
            return
        
        # For non-reference spans, continue with the original logic
        # Get both nodes from the connection
        connection_data = job_data.get("connections", {}).get(connection_id, {})
        node_id_1 = connection_data.get("node_id_1")
        node_id_2 = connection_data.get("node_id_2")
        
        # Get SCIDs for both poles
        scid_1 = job_data.get("nodes", {}).get(node_id_1, {}).get("attributes", {}).get("scid", {}).get("auto_button", "N/A")
        scid_2 = job_data.get("nodes", {}).get(node_id_2, {}).get("attributes", {}).get("scid", {}).get("auto_button", "N/A")
        
        # Determine which node is the FROM POLE (lower SCID)
        from_node_id = node_id_1 if self.compare_scids(scid_1, scid_2) <= 0 else node_id_2
        
        # Get the main photo for the FROM POLE
        node_info = job_data.get("nodes", {}).get(from_node_id, {})
        photo_ids = node_info.get("photos", {})
        main_photo_id = next((pid for pid, pdata in photo_ids.items() if pdata.get("association") == "main"), None)
        
        # Get trace_data
        trace_data = job_data.get("traces", {}).get("trace_data", {})
        
        # Initialize variables
        existing_height = ""
        proposed_height = ""
        is_proposed = False
        
        if main_photo_id:
            # Get the photo data
            photo_data = job_data.get("photos", {}).get(main_photo_id, {})
            photofirst_data = photo_data.get("photofirst_data", {})
            
            # Look through all sections (wire, equipment, guying)
            for category in ["wire", "equipment", "guying"]:
                for item in photofirst_data.get(category, {}).values():
                    trace_id = item.get("_trace")
                    if not trace_id or trace_id not in trace_data:
                        continue
                        
                    trace_info = trace_data[trace_id]
                    company = trace_info.get("company", "").strip()
                    cable_type = trace_info.get("cable_type", "") if category in ["wire", "guying"] else trace_info.get("equipment_type", "")
                    
                    # Skip if cable_type is "Primary"
                    if cable_type.lower() == "primary":
                        continue
                    
                    # Construct attacher name
                    current_attacher = f"{company} {cable_type}"
                    if category == "guying":
                        current_attacher += " (Guy)"
                    
                    if current_attacher.strip() == attacher['name'].strip():
                        measured_height = item.get("_measured_height")
                        mr_move = item.get("mr_move", 0)
                        
                        # Check if this is a proposed attachment
                        is_proposed = trace_info.get("proposed", False)
                        attacher['is_proposed'] = is_proposed
                        
                        if measured_height is not None:
                            try:
                                measured_height = float(measured_height)
                                mr_move = float(mr_move)
                                
                                # Format measured height
                                feet = int(measured_height) // 12
                                inches = round(measured_height - (feet * 12))
                                height_str = f"{feet}'-{inches}\""
                                
                                # For proposed attachments, use measured height as the proposed height
                                if is_proposed:
                                    proposed_height = height_str
                                    existing_height = ""
                                # For existing attachments, calculate proposed height if there's a move
                                elif abs(mr_move) > 0:
                                    existing_height = height_str
                                    proposed_height_value = measured_height + mr_move
                                    feet_proposed = int(proposed_height_value) // 12
                                    inches_proposed = round(proposed_height_value - (feet_proposed * 12))
                                    proposed_height = f"{feet_proposed}'-{inches_proposed}\""
                                else:
                                    existing_height = height_str
                                    proposed_height = ""
                            except (ValueError, TypeError):
                                continue
                        break
        
        # Write the attacher name
        ws.write(row_pos, 13, attacher['name'], cell_format)
        
        # Write heights
        ws.write(row_pos, 14, existing_height, cell_format)  # Column O - Existing height
        ws.write(row_pos, 15, proposed_height, cell_format)  # Column P - Proposed height
        
        # Get and write the mid-span proposed height
        midspan_height = self.get_midspan_proposed_heights(job_data, connection_id, attacher['name'])
        ws.write(row_pos, 16, midspan_height, cell_format)

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
            is_guy = '(Guy)' in name
            
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

    # Add new method to find neutral wire height
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

    def _is_number(self, value):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False






if __name__ == "__main__":
    app = FileProcessorGUI()
    app.mainloop()
