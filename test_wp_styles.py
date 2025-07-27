#!/usr/bin/env python3
"""
Test script to check WordPress CSS embedding issues
"""

# Simple test HTML with embedded CSS
test_html = '''<style>
.test-container {
    background-color: #f0f0f0;
    padding: 20px;
    border: 2px solid #333;
    color: #333;
}
.test-title {
    color: #e74c3c;
    font-size: 24px;
    font-weight: bold;
}
</style>
<div class="test-container">
    <h2 class="test-title">Test Title</h2>
    <p>This is a test paragraph with embedded CSS styling.</p>
</div>'''

print("=== TEST HTML FOR WORDPRESS ===")
print(test_html)
print(f"\nHTML Length: {len(test_html)}")
print(f"Contains <style>: {'<style>' in test_html}")
print(f"Contains CSS classes: {test_html.count('test-container')} instances")

# Potential WordPress-safe alternative using inline styles
safe_html = '''<div style="background-color: #f0f0f0; padding: 20px; border: 2px solid #333; color: #333;">
    <h2 style="color: #e74c3c; font-size: 24px; font-weight: bold;">Test Title</h2>
    <p>This is a test paragraph with inline styling that WordPress should accept.</p>
</div>'''

print("\n\n=== WORDPRESS-SAFE ALTERNATIVE (INLINE STYLES) ===")
print(safe_html)
print(f"\nSafe HTML Length: {len(safe_html)}")
print(f"Contains style attributes: {safe_html.count('style=')}")
