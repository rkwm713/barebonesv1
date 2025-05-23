# Barebones Processing Engine - Technical Documentation

This document provides a comprehensive technical explanation of the `barebones.py` processing engine, which transforms utility pole inspection JSON data into structured Excel reports.

## Overview

The `barebones.py` module contains the core data processing logic for the MakeReady Report Generator. It processes complex nested JSON data from utility field inspections and generates standardized Excel reports for pole attachment analysis.

## Table of Contents

1. [Data Structure Overview](#data-structure-overview)
2. [Core Classes](#core-classes)
3. [Processing Pipeline](#processing-pipeline)
4. [Key Algorithms](#key-algorithms)
5. [Height Calculations](#height-calculations)
6. [Movement Analysis](#movement-analysis)
7. [Excel Generation](#excel-generation)
8. [Error Handling & Logging](#error-handling--logging)

## Data Structure Overview

### Input JSON Structure

The input JSON contains hierarchical utility pole inspection data:

```json
{
  "nodes": {
    "node_id": {
      "attributes": {
        "scid": {"key": "value"},
        "pole_height": {"key": "height"},
        "work_type": {"key": "type"}
      },
      "photos": {
        "photo_id": {
          "association": "main",
          "photofirst_data": {
            "wire": {...},
            "equipment": {...},
            "guying": {...}
          }
        }
      }
    }
  },
  "connections": {
    "connection_id": {
      "node_id_1": "node_id",
      "node_id_2": "node_id", 
      "sections": {...}
    }
  },
  "traces": {
    "trace_data": {
      "trace_id": {
        "company": "company_name",
        "cable_type": "wire_type",
        "equipment_type": "equipment_type"
      }
    }
  }
}
```

### Output Data Structure

The processing generates a structured DataFrame with columns for Excel output:

```python
columns = [
    "Operation Number", "Attachment Action", "Pole Owner",
    "Pole #", "SCID", "Pole Structure", "Proposed Riser", "Proposed Guy",
    "PLA (%)", "Construction Grade", "Height Lowest Com", "Height Lowest CPS Electrical",
    "Data Category", "Bearing", "Attacher Description",
    "Attachment Height - Existing", "Attachment Height - Proposed",
    "Mid-Span (same span as existing)", "One Touch Transfer", "Remedy Description",
    "Responsible Party", "Existing CPSE Red Tag", "Pole Data Missing in GIS",
    "CPSE Application Comments", "Movement Summary", "From Pole", "To Pole"
]
```

## Core Classes

### FileProcessor Class

The main orchestration class that manages the entire processing pipeline.

```python
class FileProcessor:
    def __init__(self):
        self.downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.job_data = None
        self.logger = ProcessingLogger()
```

**Key Responsibilities:**
- File I/O operations (JSON loading, Excel generation)
- Orchestrating the data processing pipeline
- Coordinating between helper functions
- Managing output file generation

### ProcessingLogger Class

Comprehensive logging system for tracking processing statistics and debugging.

```python
class ProcessingLogger:
    def __init__(self):
        self.node_logs = []                    # Detailed logs per node
        self.skip_reasons = defaultdict(int)   # Categorized skip reasons
        self.statistics = {                    # Processing statistics
            'total_nodes': 0,
            'nodes_with_neutral': 0,
            'nodes_without_neutral': 0,
            'total_items': defaultdict(int),
            'items_processed': defaultdict(int),
            'items_skipped': defaultdict(int)
        }
```

**Functionality:**
- **Node-level tracking**: Detailed logs for each utility pole processed
- **Item categorization**: Tracks wire, equipment, and guying items separately
- **Skip reason analysis**: Categorizes why items were excluded from processing
- **Statistics generation**: Comprehensive metrics for process analysis

## Processing Pipeline

### 1. Data Loading Phase

```python
def load_json(self, path):
    """Load and validate JSON file structure"""
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)
```

**Validation Steps:**
- File existence and readability
- JSON structure validation
- Required sections verification (nodes, connections, traces)

### 2. Node Properties Extraction

```python
def process_data(self, job_data, geojson_data):
    """Extract node properties and create mapping"""
    node_properties = {}
    for node_id, node_data in job_data.get("nodes", {}).items():
        # Extract SCID, DLOC_number, pole specifications, etc.
```

**Extracted Properties:**
- **SCID**: Unique pole identifier with fallback logic
- **DLOC_number**: Location identifier with PL prefix handling
- **Pole specifications**: Height, class, structure type
- **Work classifications**: Work type, responsible party
- **Administrative data**: Red tag status, construction grade

### 3. Connection Processing

```python
# Process aerial and underground connections
for connection_id, connection_data in job_data.get("connections", {}).items():
    connection_type = connection_data.get("attributes", {}).get("connection_type", {}).get("button_added", "")
    is_aerial = connection_type == "aerial cable"
    is_underground = connection_type == "underground cable"
```

**Connection Types:**
- **Aerial cables**: Overhead wire connections between poles
- **Underground cables**: Below-ground connections to pedestals/vaults

### 4. Attachment Analysis

The most complex phase involving detailed analysis of pole attachments.

## Key Algorithms

### 1. Neutral Wire Detection Algorithm

```python
def get_neutral_wire_height(self, job_data, node_id):
    """Find the height of the neutral wire for a given node"""
```

**Purpose**: The neutral wire serves as a reference point for filtering attachments. Only attachments below the neutral wire are typically considered for make-ready analysis.

**Algorithm Steps:**
1. **Photo Identification**: Find the main photo for the node
2. **Data Extraction**: Get photofirst_data from the main photo
3. **Wire Filtering**: Search through wire section for neutral wire
4. **Company Matching**: Filter for "CPS Energy" company
5. **Type Matching**: Filter for "neutral" cable_type
6. **Height Extraction**: Return measured_height value

**Implementation Logic:**
```python
for wire in photofirst_data.get("wire", {}).values():
    trace_id = wire.get("_trace")
    if trace_id and trace_id in trace_data:
        trace_info = trace_data[trace_id]
        company = trace_info.get("company", "").strip()
        cable_type = trace_info.get("cable_type", "").strip()
        
        if company.lower() == "cps energy" and cable_type.lower() == "neutral":
            measured_height = wire.get("_measured_height")
            if measured_height is not None:
                return float(measured_height)
```

**Edge Cases:**
- **No neutral wire found**: Returns None, disables height filtering
- **Multiple neutral wires**: Returns the first valid one found
- **Invalid height data**: Continues searching for valid data

### 2. Height Formatting Algorithm

```python
def format_height_feet_inches(self, total_in):
    """Convert total inches to utility standard format"""
```

**Purpose**: Converts numeric height values (in inches) to utility industry standard format (e.g., "25'-6\"").

**Mathematical Formula:**
```python
_feet_div, _rem_div = divmod(total_in, 12)  # Divide by 12 inches per foot
_feet_int = int(_feet_div)                  # Integer feet
_inches_round = round(_rem_div)             # Rounded inches

# Handle 12-inch edge case
if _inches_round == 12:
    feet += 1
    inches = 0
else:
    feet = _feet_int
    inches = _inches_round

return f"{feet}'-{inches}\""
```

**Edge Case Handling:**
- **12-inch remainder**: Converts to additional foot (e.g., 24.99" → "25'-0\"" not "24'-12\"")
- **Negative values**: Handled gracefully with error checking
- **Non-numeric input**: Returns empty string with debug logging

### 3. Bearing Calculation Algorithm

```python
def bearing_degrees(self, lat1, lon1, lat2, lon2):
    """Calculate great-circle bearing between two points"""
```

**Purpose**: Calculates the geographic direction from one pole to another using spherical trigonometry.

**Mathematical Implementation:**
```python
φ1, φ2 = math.radians(float(lat1)), math.radians(float(lat2))
Δλ = math.radians(float(lon2) - float(lon1))

x = math.sin(Δλ) * math.cos(φ2)
y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)

θ = math.degrees(math.atan2(x, y))
return (θ + 360) % 360  # Normalize to 0-360°
```

**Cardinal Direction Conversion:**
```python
def to_cardinal(self, deg, points=16):
    """Convert bearing to cardinal direction"""
    names = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
             "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    step = 360 / points
    index = int((deg + step/2) // step) % points
    return names[index]
```

### 4. Attachment Processing Algorithm

```python
def get_attachers_for_node(self, job_data, node_id):
    """Process all attachments for a utility pole"""
```

**Purpose**: Identifies and categorizes all attachments (wires, equipment, guying) on a utility pole.

**Processing Flow:**

#### Step 1: Initialize Processing
```python
main_attacher_data = []
neutral_height = self.get_neutral_wire_height(job_data, node_id)
self.logger.log_node_start(node_id, scid, neutral_height)
```

#### Step 2: Category Processing
For each category (wire, equipment, guying):

```python
for category in ["wire", "equipment", "guying"]:
    for item_key, item_value in photofirst_data.get(category, {}).items():
        # Validation and processing logic
```

#### Step 3: Trace Data Validation
```python
trace_id = item_value.get("_trace")
if not trace_id or trace_id not in trace_data:
    self.logger.log_item_skipped(category, f"Item {item_key}", "Trace not found")
    continue
```

#### Step 4: Type and Company Extraction
```python
trace_info = trace_data[trace_id]
company = trace_info.get("company", "").strip()

if category == "wire":
    item_type_str = trace_info.get("cable_type", "").strip()
elif category == "equipment":
    item_type_str = trace_info.get("equipment_type", "").strip()
elif category == "guying":
    item_type_str = trace_info.get("cable_type", "").strip()
```

#### Step 5: Filtering Logic

**Primary Wire Filtering:**
```python
if item_type_str.lower() == "primary":  # Skip primary power lines
    self.logger.log_item_skipped(category, f"{company} {item_type_str}", "Primary wire (skipped)")
    continue
```

**Neutral Height Filtering:**
```python
if neutral_height is not None:
    if measured_height_val > neutral_height:
        self.logger.log_item_skipped(category, attacher_name, f"Above neutral height ({neutral_height}\")")
        continue
```

**Down Guy Detection:**
```python
if category == "guying" and measured_height_val is not None and neutral_height is not None:
    if measured_height_val < neutral_height:
        is_down_guy = True
        attacher_name = f"{company} {item_type_str} (Down Guy)"
```

#### Step 6: Movement Calculation
```python
mr_move_str = item_value.get("mr_move", "0")
effective_moves = item_value.get("_effective_moves", {})

total_move_inches = 0.0
total_move_inches = float(mr_move_str if mr_move_str is not None else 0.0)

if isinstance(effective_moves, dict):
    for move_val_str in effective_moves.values():
        total_move_inches += float(move_val_str if move_val_str is not None else 0.0)
```

## Height Calculations

### 1. Existing Height Processing

Existing heights are extracted from the `_measured_height` field in the photofirst_data:

```python
measured_height_str = item_value.get("_measured_height")
measured_height_val = float(measured_height_str)
existing_height_fmt = self.format_height_feet_inches(measured_height_val)
```

### 2. Proposed Height Calculation

Proposed heights are calculated by adding movement data to existing heights:

```python
# Start with mr_move
total_move_inches = float(mr_move_str if mr_move_str is not None else 0.0)

# Add effective_moves
if isinstance(effective_moves, dict):
    for move_val_str in effective_moves.values():
        total_move_inches += float(move_val_str if move_val_str is not None else 0.0)

# Calculate proposed height if there's a significant move
if abs(total_move_inches) > 0.01:
    proposed_height_val = measured_height_val + total_move_inches
    proposed_height_fmt = self.format_height_feet_inches(proposed_height_val)
```

### 3. Mid-Span Height Analysis

```python
def get_midspan_proposed_heights(self, job_data, connection_id, attacher_name):
    """Calculate proposed height for span connections"""
```

**Algorithm:**
1. **Find Lowest Section**: Identify the span section with the lowest measured height for the attacher
2. **Movement Detection**: Check for non-zero mr_move or effective_moves
3. **Proposed Calculation**: Only calculate if movements exist
4. **Return Logic**: Return empty string if no movements, formatted height if movements exist

## Movement Analysis

### 1. Movement Summary Generation

```python
def get_movement_summary(self, attacher_data, cps_only=False):
    """Generate movement summary for remediation planning"""
```

**Movement Types Detected:**

#### New Installations
```python
if is_proposed:
    if is_guy:
        summaries.append(f"Add {name} at {existing}")
    else:
        summaries.append(f"Install proposed {name} at {existing}")
```

#### Height Adjustments
```python
if proposed and existing:
    existing_inches = int(existing_parts[0]) * 12 + int(existing_parts[1])
    proposed_inches = int(proposed_parts[0]) * 12 + int(proposed_parts[1])
    movement = proposed_inches - existing_inches
    
    if movement != 0:
        action = "Raise" if movement > 0 else "Lower"
        inches_moved = abs(movement)
        summary = f"{action} {name} {inches_moved}\" from {existing} to {proposed}"
```

### 2. CPS-Only Movement Filtering

```python
def get_cps_movements_only(self, main_attachers, reference_spans, backspan_data):
    """Generate movement summary for CPS Energy attachments only"""
    
    # Filter logic
    if cps_only and not name.lower().startswith("cps energy"):
        continue  # Skip non-CPS attachments
```

**Purpose**: Creates separate movement summaries for CPS Energy attachments, used in the "Remedy Description" field.

## Excel Generation

### 1. Report Structure

The Excel output follows a specific hierarchical structure:

```python
desired_columns = [
    "Operation Number", "Attachment Action", "Pole Owner", 
    "Pole #", "Pole Structure", "Proposed Riser", "Proposed Guy", 
    "PLA (%)", "Construction Grade", "Height Lowest Com", 
    "Height Lowest CPS Electrical", "Data Category", "Attacher Description",
    "Attachment Height - Existing", "Attachment Height - Proposed",
    "Mid-Span (same span as existing)", "One Touch Transfer", 
    "Remedy Description", "Responsible Party", "Existing CPSE Red Tag",
    "Pole Data Missing in GIS", "CPSE Application Comments", 
    "Movement Summary", "From Pole", "To Pole"
]
```

### 2. Data Categorization

Each row is categorized for proper organization:

- **Main_Attacher**: Primary pole attachments
- **Ref_Span_Header**: Reference span section headers  
- **Ref_Span_Attacher**: Reference span attachment details
- **Backspan_Header**: Backspan section headers
- **Backspan_Attacher**: Backspan attachment details
- **Pole_Only**: Poles without attachments

### 3. Cell Merging Logic

```python
# Merge cells for each group in columns A-I
for op_num, rows in operation_groups.items():
    if len(rows) > 1:  # Only merge if multiple rows for this pole
        start_row = rows[0][0]
        end_row = rows[-1][0]
        
        for col_idx in range(9):  # A=0, B=1, ..., I=8
            col_letter = chr(65 + col_idx)
            value = rows[0][1].get(desired_columns[col_idx], "")
            worksheet.merge_range(f'{col_letter}{start_row+1}:{col_letter}{end_row+1}', value, data_format)
```

### 4. Header Structure

```python
# Three-row header with merged cells
for idx, col_name in enumerate(desired_columns):
    col_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
    worksheet.merge_range(f'{col_letter}1:{col_letter}3', col_name, header_format)
```

## Error Handling & Logging

### 1. Comprehensive Logging System

The ProcessingLogger tracks multiple metrics:

```python
def log_item_processed(self, category, item_info):
    """Log successfully processed item"""
    self.statistics['total_items'][category] += 1
    self.statistics['items_processed'][category] += 1

def log_item_skipped(self, category, item_info, reason):
    """Log skipped item with reason"""
    self.statistics['total_items'][category] += 1
    self.statistics['items_skipped'][category] += 1
    self.skip_reasons[reason] += 1
```

### 2. Skip Reason Categories

Common reasons for excluding items:

- **"Not a dictionary"**: Invalid data structure
- **"No trace ID"**: Missing trace reference
- **"Trace not found in trace_data"**: Invalid trace reference
- **"Primary wire (skipped)"**: Primary power lines excluded
- **"Above neutral height"**: Height filtering exclusion
- **"Missing company or type"**: Incomplete attachment data
- **"Invalid measured height"**: Non-numeric height data
- **"No measured height"**: Missing height measurement

### 3. Statistics Generation

```python
def write_summary(self, filename):
    """Generate comprehensive processing report"""
    # Node statistics, item breakdown, skip reason analysis
    # Performance metrics, detailed logs for debugging
```

**Report Sections:**
- **Node Statistics**: Total nodes, neutral wire detection rates
- **Item Statistics**: Breakdown by category (wire/equipment/guying)
- **Processing Results**: Success vs. skip rates with percentages
- **Skip Reason Analysis**: Detailed breakdown of exclusion reasons
- **Detailed Logs**: Sample node logs for debugging

### 4. Debug Output

Extensive debug logging throughout the processing pipeline:

```python
print(f"DEBUG: Node {node_id} - Processing category: {category}")
print(f"DEBUG: Main attacher {attacher_name} - mr_move: {mr_move_str}, effective_moves: {effective_moves}")
print(f"DEBUG: Connection {connection_id} - Lowest Com: {lowest_com_formatted}, Lowest CPS: {lowest_cps_formatted}")
```

## Performance Considerations

### 1. Memory Management

- **Streaming JSON Processing**: Large files processed without loading entirely into memory
- **Efficient Data Structures**: Use of dictionaries and lists for fast lookups
- **Garbage Collection**: Explicit cleanup of temporary variables

### 2. Algorithm Efficiency

- **Single-Pass Processing**: Most operations require only one pass through the data
- **Cached Calculations**: Height formatting and bearing calculations cached where possible
- **Early Termination**: Skip processing when required data is missing

### 3. Scalability Features

- **Configurable Constants**: Easy adjustment of processing parameters
- **Modular Design**: Independent processing functions for easy testing/modification
- **Logging Integration**: Comprehensive tracking for performance analysis

---

**Document Version**: 2.0.0  
**Last Updated**: January 2025  
**Technical Review**: Complete
