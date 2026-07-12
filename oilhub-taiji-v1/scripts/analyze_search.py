#!/usr/bin/env python3
"""Analyze search_files tool calls in logs."""
import json, re

LT = chr(60)  # <
GT = chr(62)  # >

with open('logs/taiji-provider.log') as f:
    for line in f:
        if 'search_files' not in line or 'Streaming response' not in line:
            continue
        try:
            d = json.loads(line.strip())
            ts = d['timestamp'][:19]
            extra = d.get('extra', {})
            names = extra.get('tool_call_names', '')
            content = extra.get('content', '')
            
            # find invoke blocks for search_files using escaped chars
            pat = LT + r'invoke name="search_files"' + GT + r'(.*?)' + LT + r'/invoke' + GT
            blocks = re.findall(pat, content, re.DOTALL)
            for b in blocks:
                param_pat = LT + r'parameter name="(\w+)"' + GT + r'(.*?)' + LT + r'/parameter' + GT
                params_raw = re.findall(param_pat, b, re.DOTALL)
                params = {}
                for k, v in params_raw:
                    params[k] = v.strip()[:300]
                print(f'{ts} search_files({names})')
                for k, v in params.items():
                    print(f'  {k}: {v}')
                print()
        except Exception as e:
            pass
