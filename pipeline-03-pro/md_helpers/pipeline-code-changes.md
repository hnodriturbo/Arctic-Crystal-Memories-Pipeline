# Pipeline Python Code Changes & Utils Files Changes

## Table of Contents
`dateOfChange & timeOfChange` - `file_utils` <!-- each table of contents should be clickable like a chapter -->

### What Was Done

#### **file_utils.py**
```python
""" 
Here will be explanation of the change and the full function 
(if part of function was changed, copy it all here explaining the change 
in the commenting top block here above the new version of the function) 
"""

def get_input_dir() -> Path:
    """Return the pipeline input directory, creating it if needed."""
    raw = os.getenv("INPUT_DIR", "./input")
    path = (PIPELINE_DIR / raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
```
- This specific function was changed to use the environmental `INPUT_DIR` and fall back to the relative ./input folder