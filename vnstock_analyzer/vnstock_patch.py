"""
Monkey patch for vnstock to fix pandas 3.x compatibility issues.

This patch automatically fixes the deprecated applymap() usage in vnstock
when working with pandas 3.0+, which removed applymap() in favor of map().

The patch is applied automatically when importing vnstock_analyzer and
runs silently without user-facing messages.

Technical details:
- vnstock 3.4.2 uses DataFrame.applymap() which was removed in pandas 3.0
- This patch adds applymap as an alias to map() for backward compatibility
- Safer than patching vnstock directly as it survives reinstalls
"""

import sys


def patch_vnstock_applymap():
    """
    Patch pandas DataFrame to provide applymap() as an alias to map()
    for backward compatibility with vnstock.
    
    This is safer than patching vnstock directly as it works regardless
    of vnstock's internal implementation.
    """
    try:
        import pandas as pd
        
        # Check pandas version
        pandas_version = tuple(map(int, pd.__version__.split('.')[:2]))
        
        # Only patch if pandas >= 3.0 (applymap was removed)
        if pandas_version >= (3, 0):
            # Check if applymap already exists
            if not hasattr(pd.DataFrame, 'applymap'):
                # Add applymap as an alias to map
                pd.DataFrame.applymap = pd.DataFrame.map
                # Silent patch - only log in debug mode
                # print(f"✅ Applied pandas 3.x compatibility patch: DataFrame.applymap → DataFrame.map", file=sys.stderr)
                return True
        
        return False
        
    except Exception as e:
        # Silent fail - don't spam user with warnings
        # print(f"⚠️  Warning: Could not patch pandas for vnstock compatibility: {e}", file=sys.stderr)
        return False


def apply_patches():
    """Apply all vnstock patches for pandas 3.x compatibility"""
    patch_vnstock_applymap()


# Auto-apply patches when this module is imported
apply_patches()

