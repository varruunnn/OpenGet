# OpenGet

A simple open-source parallel download manager in Python.  
It splits large files into chunks, downloads them concurrently, and merges them afterward. Supports resume if the process is interrupted.

## Features
- Parallel downloads via HTTP Range requests (multiple threads).
- Resume support for interrupted downloads (partial files).
- Single-connection fallback for servers without Range support.
- Console progress display via `tqdm` (optional).
- Unit tests (with `pytest` and `requests-mock`) and integration tests.

## Requirements
- Python 3.7+  
- See [requirements.txt](requirements.txt) for exact versions:
