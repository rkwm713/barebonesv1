# Project Roadmap

## High-Level Goals
- [ ] Ensure reliable Excel report generation and download.
- [ ] Improve overall application stability and error handling.
- [ ] Refactor file and path management for consistency.

## Key Features
- **Excel Report Generation:**
  - [x] Centralize output path logic in `FileProcessor`.
  - [x] Implement unique (timestamped) filenames for Excel and log files in `FileProcessor`.
  - [x] Add `try...finally` block to `create_output_excel` for robust writer closing.
  - [x] Remove debug prints from `format_height_feet_inches`.
  - [x] Correct logic in `format_height_feet_inches` to prevent "X' 12"" results (initial attempt).
  - [x] Implemented more robust correction in `format_height_feet_inches` with explicit integer conversion and inch rollover safeguard.
  - [x] Update `main()` in `barebones.py` for better local testing.
  - [x] Implement accurate reference span identification and "Ref (...)" block generation in `barebones.py` as per playbook.
  - [x] Conditionally populate "Mid-Span (same span as existing)" column in `create_output_excel` based on whether the main pole attacher is new or has moved.
  - [x] Fix "refs" sheet data population in `barebones.py`, including fresh `attacher_data` fetching, refined "002.A" logic, and correct column mapping for `Ref_Span_Attacher` rows.
  - [ ] Further enhance error handling within `create_output_excel` for cell merging and formatting.
- **File Serving (Flask & FastAPI):**
  - [x] Update Flask app (`app.py`) to correctly initialize `FileProcessor` with output directory.
  - [x] Update FastAPI app (`backend/app.py`) to correctly initialize `FileProcessor` with output directory.
  - [x] Update Flask app (`app.py`) to locate and serve uniquely named files from `FileProcessor`.
  - [x] Update FastAPI app (`backend/app.py`) to locate and serve uniquely named files from `FileProcessor` (including correct prefix search).
  - [x] Add `Content-Length` header to download responses in Flask app.
  - [x] Add `Content-Length` header to download responses in FastAPI app.
- **Logging & Monitoring:**
  - [x] Clarify log messages in `FileProcessor` regarding DataFrame size vs. Excel row count.
  - [ ] Implement comprehensive logging for file operations (creation, access, deletion).
- **Developer Experience / Testing:**
  - [x] Create local testing setup instructions (`userInstructions/local_testing_setup.md`).
  - [ ] Add checksum validation for downloaded files (optional, for client-side verification).

## Completion Criteria
- User can consistently download non-corrupted Excel reports.
- Application logs clearly indicate the status of file generation and any errors.
- Codebase is cleaner and easier to maintain regarding file operations.

## Progress Tracker
- **Phase 1: Critical Path & File Handling Fixes (Completed)**
  - Centralized path management.
  - Unique file naming.
  - Robust Excel writer closing.
  - Updated app initializations for `FileProcessor`.
  - Corrected file retrieval logic in apps.
  - Added Content-Length to downloads.
- **Phase 2: Excel Generation & Download Robustness (Ongoing)**
- **Phase 3: Logging and Advanced Integrity Checks (Pending)**

## Completed Tasks
- Refactored `FileProcessor.__init__` for consistent output directory determination.
- Modified `FileProcessor.process_files` to use timestamped unique filenames for Excel and log outputs.
- Updated `FileProcessor.create_output_excel` to use a `try...finally` block, ensuring `ExcelWriter` is closed.
- Removed debug `print` statements from `FileProcessor.format_height_feet_inches`.
- Corrected logic in `FileProcessor.format_height_feet_inches` to prevent "X' 12"" height formatting errors (initial attempt and subsequent robust fix).
- Improved `main` function in `barebones.py` for local testing.
- Updated Flask app (`app.py`) `process_file` to correctly instantiate `FileProcessor` and find unique output files.
- Updated FastAPI app (`backend/app.py`) `process_file_sync` to correctly instantiate `FileProcessor` and find unique output files, including adjusting the search prefix for processor-generated files.
- Added `Content-Length` header to download responses in `app.py`.
- Added `Content-Length` header to download responses in `backend/app.py`.
- Implemented new logic in `barebones.py` for identifying and processing reference spans, including new helper functions (`get_scid_from_node_data`, `is_reference_connection`) and an overhaul of `get_reference_attachers`. Updated `create_output_excel` for correct reference span header text.
- Updated `FileProcessor.create_output_excel` to conditionally populate the "Mid-Span (same span as existing)" column for main pole attachers only if the pole attacher is new or has moved.
- Created `userInstructions/local_testing_setup.md` with detailed steps for setting up and running the application locally.
- Corrected "refs" sheet data population in `barebones.py`: ensured fresh `attacher_data` for each pole, refined "002.A" pole handling, and adjusted data mapping for columns P & Q for `Ref_Span_Attacher` rows.
