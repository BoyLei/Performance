#!/usr/bin/env python3
"""Static checks only. Run with Python 3 + PyYAML, from any directory.
No Obsidian/plugin execution; no file writes. Historical originals are read-only.
"""
from pathlib import Path
import collections
import json
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
VAULT = ROOT / 'Unity性能优化'
errors = []
counts = collections.Counter()

def require(ok, message):
    if not ok:
        errors.append(message)

def body_and_blocks(text):
    """Remove frontmatter and fenced code, preserving ordinary Markdown headings."""
    text = re.sub(r'\A---\n.*?\n---\n', '', text, count=1, flags=re.S)
    body, blocks = [], []
    fence = None
    block = []
    info = ''
    for line in text.splitlines():
        m = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
        if fence is None and m:
            fence, info = m[1], m[2].strip()
            block = []
        elif fence and re.fullmatch(r'\s*' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*', line):
            blocks.append((info, '\n'.join(block)))
            fence = None
        elif fence:
            block.append(line)
        else:
            body.append(line)
    return '\n'.join(body), blocks, fence is None

all_md = list(ROOT.rglob('*.md'))
all_md = [p for p in all_md if '.git' not in p.parts and '.obsidian' not in p.parts]
by_stem = collections.defaultdict(list)
for p in all_md:
    by_stem[p.stem].append(p)
headings = {}
for p in all_md:
    body, _, _ = body_and_blocks(p.read_text())
    headings[p] = set(re.findall(r'^#{1,6}\s+(.+?)\s*#*$', body, re.M))

def resolve(target, source):
    target = target.removesuffix('.md')
    if not target:
        return source
    if '/' in target:
        direct = ROOT / (target + '.md')
        local = source.parent / (target + '.md')
        return direct if direct.is_file() else local if local.is_file() else None
    candidates = by_stem.get(target, [])
    require(len(candidates) <= 1, f'{source.name}: ambiguous wikilink {target}')
    return candidates[0] if len(candidates) == 1 else None

edges = collections.defaultdict(set)
tasks = []
for p in sorted(VAULT.glob('*.md')):
    text = p.read_text()
    counts['content_documents'] += 1
    fm = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    require(fm is not None, f'{p.name}: missing YAML')
    if fm:
        try:
            meta = yaml.safe_load(fm[1])
            require(isinstance(meta, dict), f'{p.name}: YAML must be a mapping')
            require(meta.get('title') == p.stem, f'{p.name}: title differs')
            require(meta.get('learning_status') == 'pending', f'{p.name}: learning_status not pending')
            require(meta.get('discussion_status') in {'mixed','discussed','supplemental','not-found'}, f'{p.name}: bad discussion_status')
            require(isinstance(meta.get('tags'), list), f'{p.name}: tags not a list')
        except yaml.YAMLError as e:
            errors.append(f'{p.name}: YAML {e}')
    body, blocks, closed = body_and_blocks(text)
    require(closed, f'{p.name}: unclosed fence')
    require(len(re.findall(r'^# ', body, re.M)) == 1, f'{p.name}: expected one H1')
    for raw in re.findall(r'\[\[([^\]]+)\]\]', text):
        dest = raw.split('|', 1)[0]
        target, sep, anchor = dest.partition('#')
        q = resolve(target, p)
        counts['wikilinks'] += 1
        require(q is not None, f'{p.name}: missing target {target}')
        if q:
            edges[p].add(q)
            if sep:
                require(anchor in headings[q], f'{p.name}: missing heading {dest}')
    for line in body.splitlines():
        m = re.match(r'^( *)- \[([^\]])\] (.+)$', line)
        if not m:
            continue
        counts['source_tasks'] += 1
        require(p.stem in {'学习任务脑图','未讨论与待核实路线'}, f'{p.name}: duplicate task source')
        require(m[2] == ' ', f'{p.name}: task already checked/custom status')
        require(len(re.findall(r'#discussion/(?:discussed|not-found|review-required)\b', m[3])) == 1, f'{p.name}: discussion tag count')
        require(len(re.findall(r'#priority/P[0-3]\b', m[3])) == 1, f'{p.name}: priority tag count')
        require('#unity-task' in m[3], f'{p.name}: missing task tag')
        require(len(m[1]) % 4 == 0, f'{p.name}: task indent must be 4-space levels')
        tasks.append((p, m[3]))
    if p.stem in {'学习任务脑图','知识体系脑图'}:
        previous = -1
        for line in body.splitlines():
            m = re.match(r'^( *)- ', line)
            if m:
                level = len(m[1])
                require(level % 4 == 0, f'{p.name}: invalid list indentation')
                require(previous == -1 or level <= previous + 4, f'{p.name}: skipped hierarchy level')
                previous = level
            elif line.strip():
                previous = -1
    for kind, block in blocks:
        if kind == 'mermaid':
            counts['mermaid_blocks'] += 1
        elif kind == 'tasks':
            counts['tasks_queries'] += 1
            lines = block.splitlines()
            require(lines[0] in {'not done','done'}, f'{p.name}: missing query status')
            require('path includes Unity性能优化/' in lines, f'{p.name}: query scope missing')
            for line in lines[1:]:
                require(bool(re.fullmatch(r'(path includes Unity性能优化/|tag includes #[\w/-]+|group by filename)', line)), f'{p.name}: unsupported query clause {line}')
            filters = [line.removeprefix('tag includes ') for line in lines if line.startswith('tag includes ')]

# Resolve query expectation after collecting all source tasks.
query_counts = []
for kind, block in body_and_blocks((VAULT/'任务总览.md').read_text())[1]:
    if kind == 'tasks':
        filters = [line.removeprefix('tag includes ') for line in block.splitlines() if line.startswith('tag includes ')]
        matched = 0 if block.splitlines()[0] == 'done' else sum(all(tag in task for tag in filters) for _, task in tasks)
        query_counts.append(matched)
require(len(tasks) == len(set(task for _, task in tasks)), 'duplicate task descriptions')

index = (VAULT/'历史问题索引.md').read_text()
ids = re.findall(r'^### Q(\d{3})$', index, re.M)
require(ids == [f'{i:03d}' for i in range(1,137)], 'Q001–Q136 not complete/ordered/unique')
require(len(re.findall(r'^原文：\[\[云端交接/历史会话原文/', index, re.M)) == 136, 'missing question source links')
raws = sorted((ROOT/'云端交接/历史会话原文').glob('*.md'))
require(len(raws) == 36, 'expected 36 history files')
require(sum(len(re.findall(r'^### 用户$', p.read_text(), re.M)) for p in raws) == 136, 'history user count changed')
# Every primary module must be reachable from home and link back to the question index.
home = VAULT/'00 知识库首页.md'
idx = VAULT/'历史问题索引.md'
for p in sorted(VAULT.glob('[0-9][0-9] *.md')):
    if p != home:
        require(p in edges[home], f'{p.name}: not linked from home')
        require(idx in edges[p], f'{p.name}: missing source backlink')
for p in VAULT.glob('*.md'):
    require(any(p in dests for dests in edges.values()), f'{p.name}: orphan document')
# Semantic review inventory: make omissions/stale heading anchors visible.
# This verifies ledger coverage only; it cannot judge whether prose is true.
audit_path = VAULT / '知识点逐项核验.md'
relations_path = VAULT / '知识关联核验.md'
if audit_path.exists() and relations_path.exists():
    technical = [p for p in VAULT.glob('*.md')
                 if (re.match(r'^\d{2} ', p.name) and not p.name.startswith('00'))
                 or p.stem in {'建筑ID与连续数组索引','无Loading副本与预加载卡顿',
                               'GPU Mask与铺地火焰','场景UI分辨率与RT带宽',
                               'GPU Driven与虚拟化技术','UGUI架构与事件顺序','架构线程与代码实践'}]
    expected = {p.stem + '#' + h for p in technical
                for h in re.findall(r'^## (.+)$', body_and_blocks(p.read_text())[0], re.M)
                if h != '关联'}
    audit = audit_path.read_text()
    reviewed = re.findall(r'^\|K\d{3}\|\[\[([^\]]+)\]\]\|', audit, re.M)
    require(set(reviewed) == expected, 'knowledge audit missing/stale H2 entries')
    require(len(reviewed) == len(set(reviewed)), 'knowledge audit repeats a section')
    relations = relations_path.read_text()
    pairs = re.findall(r'^\|R\d{3}\|\[\[([^\]]+)\]\] → \[\[([^\]]+)\]\]\|', relations, re.M)
    actual_pairs = set()
    for p in technical:
        if re.match(r'^\d{2} ', p.name):
            meta = yaml.safe_load(p.read_text().split('---')[1])
            actual_pairs.update((p.stem, link[2:-2]) for link in meta.get('related', []))
    require(set(pairs) == actual_pairs and len(pairs) == len(actual_pairs), 'related relation audit mismatch')
    require(len(re.findall(r'^\|D\d{2}\|', relations, re.M)) == counts['mermaid_blocks'], 'diagram semantic audit coverage mismatch')
    counts['reviewed_technical_sections'] = len(reviewed)
    counts['reviewed_related_edges'] = len(pairs)

# Explicit user protection: all tracked changes must stay within the knowledge base.
changed = subprocess.check_output(['git','diff','--name-only','-z','490076d','--'], cwd=ROOT, text=True).split('\0')
untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'], cwd=ROOT, text=True).split('\0')
require(all(path.startswith('Unity性能优化/') for path in changed + untracked if path), 'changes outside knowledge base')
counts['history_files'] = len(raws)
counts['indexed_user_messages'] = len(ids)
print(json.dumps({'counts': dict(counts), 'query_expected_counts': query_counts,
                  'errors': errors, 'runtime_checks': 'NOT RUN: Obsidian, Tasks, mind-map, Unity'}, ensure_ascii=False, indent=2))
sys.exit(bool(errors))
