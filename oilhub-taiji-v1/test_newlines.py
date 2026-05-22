#!/usr/bin/env python3
"""Test double-encoding hypothesis."""
import json

# Simulate the double-encoded scenario from logs
raw_args = '{"code":"importjson\\nfromhermes_tools"}'
print("Raw args:", repr(raw_args))

# First decode: parse as JSON string
decoded_once = json.loads(raw_args)
print("After first decode:", repr(decoded_once))

# Check if there are still \n that need decoding
if '\\n' in decoded_once:
    print("Still has literal \\n, needs another decode or replace")
    # Replace literal \n with actual newlines
    fixed = decoded_once.replace('\\n', '\n')
    print("After replace:", repr(fixed))
else:
    print("No literal \\n found, content is clean")
