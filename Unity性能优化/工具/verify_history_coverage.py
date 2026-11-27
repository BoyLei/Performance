#!/usr/bin/env python3
"""Compare only the finite saved snapshot; never asserts full history coverage."""
import json
import re
from pathlib import Path
root = Path(__file__).resolve().parents[2]
vault = root / 'Unity性能优化'
raw = json.loads((root / '云端交接/历史会话返回原文.json').read_text())
index = (vault / '历史问题索引.md').read_text()
blocks = dict(re.findall(r'^### Q(\d{3})\n(.*?)(?=^### Q\d{3}\n|\Z)', index, re.M | re.S))
messages = [item['text'] for conversation in raw for turn in reversed(conversation['turns'])
            for item in turn['items'] if item['type'] == 'userMessage']
def normalize(text):
    return re.sub(r'\s+', ' ', text.replace('## My request:', '')).strip()
assert len(messages) == len(blocks) == 136
for n, message in enumerate(messages, 1):
    quoted = '\n'.join(line[2:] if line.startswith('> ') else ''
                       for line in blocks[f'{n:03}'].splitlines() if line.startswith('>'))
    assert normalize(message) == normalize(quoted), f'Q{n:03} transcription mismatch'
ledger = (vault / '历史原问覆盖与缺口.md').read_text()
ids = re.findall(r'^\|\[\[历史问题索引#Q(\d{3})\|', ledger, re.M)
assert ids == [f'{n:03}' for n in range(1, 137)], 'coverage ledger missing/duplicate/out-of-order question'
print('136/136 saved user messages match index; 136 ledger rows present. Finite snapshot only.')
