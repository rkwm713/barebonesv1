# Barebones Utility Data Processor

A simplified Python utility for processing electrical pole attachment and make-ready data from JSON files into Excel reports.

## Project Overview

This project creates Excel reports for utility pole attachment analysis, processing complex nested JSON data from utility inspection systems into flat, readable Excel spreadsheets. The focus is on make-ready analysis for new attachments to existing utility poles.

## Current Status: **Phase 1 Complete** ✅

### What's Been Accomplished

#### ✅ **Task 1.1: Core Infrastructure Setup**
- **Environment**: Virtual environment with pandas, xlsxwriter installed
- **File Structure**: Single `barebones.py` file with modular class structure
- **JSON Loading**: Successfully loads `CPS_6457E_03.json` (1.3MB utility data file)
- **Helper Functions**: All essential data processing functions copied and adapted from original

#### ✅ **Task 1.2: Simplified Excel Output**
- **Single Sheet**: Flat structure instead of complex merged cells
- **No Formatting**: Removed all xlsxwriter formatting for simplicity
- **Flat Row Structure**: Each attachment/span/backspan gets its own row
- **Column Structure**: 27 columns including new "Data Category" and "Bearing" fields

### File Structure

```
barebones/
├── barebones.py              # Main processing script (1,400+ lines)
├── CPS_6457E_03.json         # Sample utility data (1.3MB)
├── CPS_6457E_03_MakeReady_Output.xlsx  # Generated output
├── .venv/                    # Virtual environment
└── README.md                 # This file
```

### Key Components Implemented

#### **FileProcessor Class**
- `__init__()`: Basic setup
- `load_json()`: JSON file loading
- `main()`: Orchestrates the entire process
- `create_output_excel()`: **COMPLETED** - Creates flat Excel structure

#### **Helper Functions (All Implemented)** ✅
- `format_height_feet_inches()`: Height formatting (e.g., "25'-6\"")
- `get_neutral_wire_height()`: Finds neutral wire for height filtering
- `get_attachers_for_node()`: **CRUCIAL** - Main attacher extraction
- `get_lowest_heights_for_connection()`: **CRUCIAL** - Span height analysis
- `get_midspan_proposed_heights()`: **CRUCIAL** - Mid-span calculations
- `get_backspan_attachers()`: Backspan data with bearings
- `get_reference_attachers()`: Reference span data with bearings
- `calculate_bearing()`: Geographic bearing calculations
- `get_work_type()`: Work type from node attributes
- `get_responsible_party()`: Responsible party extraction
- `compare_scids()`: SCID sorting logic
- `get_pole_structure()`: Pole specifications
- `get_proposed_guy_value()`: Guy wire proposals
- `get_movement_summary()`: Movement calculations for remedies
- `_is_number()`: Utility function for numeric validation

#### **Excel Output Structure**
27 columns in flat format:
```
Connection ID | Operation Number | Attachment Action | Pole Owner | Pole # | SCID | 
Pole Structure | Proposed Riser | Proposed Guy | PLA (%) | Construction Grade |
Height Lowest Com | Height Lowest CPS Electrical | Data Category | Bearing |
Attacher Description | Attachment Height - Existing | Attachment Height - Proposed |
Mid-Span (same span as existing) | One Touch Transfer | Remedy Description |
Responsible Party | Existing CPSE Red Tag | Pole Data Missing in GIS |
CPSE Application Comments | Movement Summary | From Pole | To Pole
```

### How to Run

```bash
# Navigate to project directory
cd C:/Users/Ryan/Downloads/barebones

# Activate virtual environment (if not already active)
.venv/Scripts/activate

# Run the processor
python barebones.py
```

**Expected Output:**
```
Loading Job JSON from: CPS_6457E_03.json
Job JSON loaded successfully.
Processing data...
process_data method - placeholder
Creating Excel report at: CPS_6457E_03_MakeReady_Output.xlsx
DataFrame is empty, processing job_data directly to create sample structure.
Excel file created: CPS_6457E_03_MakeReady_Output.xlsx
Total rows written: 1
Warning: No data processed. DataFrame was empty, but Excel file created with headers.
```

## What's Still Needed: **Phase 2**

### 🔄 **Critical Missing Component: `process_data()` Method**

**Current State:** Placeholder that returns empty DataFrame
```python
def process_data(self, job_data, geojson_data):
    # Placeholder - will add the full method in next step
    print("process_data method - placeholder")
    return pd.DataFrame()
```

**What It Needs To Do:**
1. **Extract Connections**: Find all aerial/underground cable connections
2. **Process Node Properties**: Extract SCID, pole specs, work types, etc.
3. **Get Attachment Data**: Use helper functions to get main/reference/backspan attachers
4. **Calculate Heights**: Use `get_lowest_heights_for_connection()` for each span
5. **Generate Movement Summaries**: Calculate what needs to be moved and where
6. **Return Structured Data**: DataFrame with all connection and attachment data

### **Recent Enhancements** ✅

#### **Sub-task 1.2.7: Movement Summary & Remedy Description** ✅
- **Enhanced `get_movement_summary()`**: Now supports "(Down Guy)" detection and better error handling
- **Added `get_all_movements_summary()`**: Comprehensive movement tracking across main/reference/backspan attachers
- **Added `get_cps_movements_only()`**: CPS Energy-specific movements for Remedy Description field
- **Updated Excel Output Logic**: Movement Summary and Remedy Description properly populated in first main attacher row only (flat sheet structure)

#### **Sub-task 1.3.1: Data Extraction Logic Verification** ✅
- **Enhanced Company Matching**: `get_lowest_heights_for_connection()` now handles CPS name variations ["cps energy", "cps", "cpse"]
- **Added Equipment Processing**: Now processes both wire and equipment sections for more accurate height detection
- **Improved Filtering**: Better handling of empty company names and more robust classification logic

#### **Sub-task 1.3.2: Attachment Existing/Proposed Heights** ✅
- **CRITICAL FIX**: `get_attachers_for_node()` now properly incorporates `_effective_moves` data for consistent height calculations
- **Unified Logic**: All attachment functions (main pole, reference spans, backspans) now use both `mr_move` AND `_effective_moves`
- **Data Verified**: Confirmed `_effective_moves` exists in JSON (48 instances) and is properly processed
- **Enhanced Debugging**: Added comprehensive logging for `mr_move`, `_effective_moves`, and `total_move` calculations

### **Template Structure Ready**
The `create_output_excel()` method has a complete TODO template for processing the data when `process_data()` is implemented:

```python
# Generate movement summaries for this connection
all_movements = self.get_all_movements_summary(
    connection_data['main_attachers'], 
    connection_data['reference_spans'], 
    connection_data['backspan']['data']
)
cps_movements = self.get_cps_movements_only(
    connection_data['main_attachers'], 
    connection_data['reference_spans'], 
    connection_data['backspan']['data']
)

# Base pole data with enhanced Movement Summary and Remedy Description
base_row_data = {
    "Movement Summary": all_movements if all_movements else record.get("Movement Summary", ""),
    "Remedy Description": cps_movements if cps_movements else record.get("Remedy Description", ""),
    # ... other fields
}
```

## Dependencies

```
pandas==2.2.3
xlsxwriter==3.2.3
numpy==2.2.6
python-dateutil==2.9.0.post0
```

## Data Flow

```
CPS_6457E_03.json → process_data() → DataFrame → create_output_excel() → Excel File
      ↑                   ↑                          ↑
   (Complete)        (PLACEHOLDER)               (Complete)
```

## Key Features

- **No GUI Dependencies**: Pure command-line processing
- **Minimal Formatting**: Uses Excel defaults for simplicity
- **Flat Structure**: Each attachment gets its own row with category labels
- **Bearing Calculations**: Geographic directions for spans
- **Height Analysis**: Comprehensive height tracking (existing, proposed, mid-span)
- **Movement Summaries**: Automated calculation of required changes

## Original Source

Derived from `final_code_output (1).py` (1,985 lines) with:
- GUI components removed
- Complex Excel formatting simplified
- Flat data structure implemented
- All essential helper functions preserved

## Next Steps for AI Context

1. **Implement `process_data()`**: Copy and adapt from original file
2. **Test with Real Data**: Verify output matches expectations
3. **Add Error Handling**: Robust processing for various data conditions
4. **Optimize Performance**: Stream processing for large files
5. **Add Configuration**: Make paths and settings configurable

---

**Last Updated**: Created during Phase 1 implementation
**Status**: Ready for Phase 2 (process_data implementation)
**File Working**: ✅ JSON loads, ✅ Excel creates, ✅ All helpers ready 