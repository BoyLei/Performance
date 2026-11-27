#!/usr/bin/env python3
"""Verify navigation coverage, original-content preservation and JSON Canvas integrity."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / 'Unity性能优化'
m = json.loads((V/'工具/知识结构.json').read_text())
notes = {p.stem:p for p in V.rglob('*.md')}
assert len(notes) == len(list(V.rglob('*.md'))), 'duplicate note names'
assert set(notes) == set(m['paths']), 'catalogue missing/stale notes'
for name, path in m['paths'].items():
    assert notes[name] == V/path, name
assert sorted(x for d in m['domains'] for x in d['modules']) == sorted(m['modules'])
assert len(m['modules']) == 10 and len(m['specials']) == 7
assert set(m['primary']) == set(m['specials'])
assert all(x in m['modules'] for x in m['primary'].values())
assert set(m['special_related']) == set(m['specials'])
assert all(x in m['modules'] for xs in m['special_related'].values() for x in xs)
# Remove only the generated navigation block, then require original technical text byte-for-byte.
for name in m['modules'] + m['specials']:
    before = subprocess.check_output(['git','show',f"{m['baseline']}:Unity性能优化/{name}.md"],cwd=ROOT).decode()
    after = re.sub(r'%% navigation-start %%\n.*?%% navigation-end %%\n\n','',notes[name].read_text(),flags=re.S)
    assert before == after, f'technical content changed: {name}'
# Source tasks, historical questions and citations are moved without content edits.
for name in ['学习任务脑图','任务总览','未讨论与待核实路线','优化方向补充与学习路线',
             '历史问题索引','历史原问覆盖与缺口','逐份原文核对记录','历史检索与整理说明',
             '参考资料与版本边界','技术核验来源','知识点逐项核验','知识关联核验','因果与执行流程']:
    before = subprocess.check_output(['git','show',f"{m['baseline']}:Unity性能优化/{name}.md"],cwd=ROOT).decode()
    assert before == notes[name].read_text(), f'preserved note changed: {name}'
expected = {n+'#'+h for n,hs in m['sections'].items() for h in hs}
outline = notes['知识体系脑图'].read_text()
actual = re.findall(r'^\s+- \[\[([^\]|]+#[^\]|]+)\|',outline,re.M)
assert len(expected) == len(actual) == 99 and set(actual) == expected, 'outline misses/repeats section'
canvases = list((V/'图谱').glob('*.canvas'))
assert len(canvases) == 13, 'expected overview + ten modules + specials + relations'
links_checked = 0
for p in canvases:
    c = json.loads(p.read_text())
    nodes = c['nodes']; edges = c['edges']; ids = [x['id'] for x in nodes+edges]
    assert len(ids) == len(set(ids)), p.name
    assert all(re.fullmatch('[0-9a-f]{16}',x) for x in ids), p.name
    by_id = {x['id']:x for x in nodes}
    for n in nodes:
        assert n['type'] in {'text','file','link','group'}
        if 'color' in n:
            assert re.fullmatch(r'[1-6]|#[0-9a-fA-F]{6}', n['color'])
        assert all(isinstance(n[k],int) for k in ['x','y','width','height'])
        assert n['width'] > 0 and n['height'] > 0
        if n['type'] == 'text':
            assert '\\n' not in n['text'], p.name
            for dest in re.findall(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]',n['text']):
                target,_,anchor = dest.partition('#')
                if target.endswith('.canvas'):
                    assert (V/'图谱'/target).is_file(), (p.name,target)
                else:
                    assert target in notes, (p.name,target)
                    if anchor:
                        assert re.search(r'^#{1,6} '+re.escape(anchor)+r'$',notes[target].read_text(),re.M),dest
                links_checked += 1
    # Containers may contain cards; ordinary content cards must not overlap.
    for i,a in enumerate(nodes):
        for b in nodes[i+1:]:
            if a['type'] == 'group' or b['type'] == 'group':
                continue
            assert (a['x']+a['width'] <= b['x'] or b['x']+b['width'] <= a['x'] or
                    a['y']+a['height'] <= b['y'] or b['y']+b['height'] <= a['y']), (p.name,a['id'],b['id'])
    if p.stem == '学习总览':
        groups = [n for n in nodes if n['type'] == 'group']
        assert len(groups) == 4
        for d in m['domains']:
            g = next(n for n in groups if n['label'] == d['name'])
            for name in d['modules']:
                n = next(n for n in nodes if n.get('text','').startswith('## [[' + name + ']]'))
                assert g['x'] <= n['x'] and n['x']+n['width'] <= g['x']+g['width']
                assert g['y'] <= n['y'] and n['y']+n['height'] <= g['y']+g['height']
    for e in edges:
        assert e['fromNode'] in by_id and e['toNode'] in by_id, p.name
        assert e['fromSide'] in {'top','right','bottom','left'}
        assert e['toSide'] in {'top','right','bottom','left'}
        assert e['fromEnd'] == 'none'
        assert e['toEnd'] == ('arrow' if p.stem=='模块依赖图' else 'none')
        assert re.fullmatch(r'[1-6]|#[0-9a-fA-F]{6}', e['color'])
    if p.stem == '模块依赖图':
        assert sorted(e['label'].split()[0] for e in edges) == sorted(r['id'] for r in m['relations'])
        text = notes['模块依赖与关联'].read_text()
        for r in m['relations']:
            e = next(e for e in edges if e['label'] == r['id'])
            assert '[[' + r['source'] + ']]' in by_id[e['fromNode']]['text']
            assert '[[' + r['target'] + ']]' in by_id[e['toNode']]['text']
            assert r['meaning'] in by_id[e['fromNode']]['text']
            assert f"|{r['id']}|[[{r['source']}]] → [[{r['target']}]]|{r['type']}|{r['meaning']}|" in text
    for name in m['modules']:
        if p.stem == name+' 导图':
            found = {s for n in nodes for s in re.findall(r'\[\[([^\]|]+#[^\]|]+)\|',n.get('text',''))}
            assert found == {name+'#'+h for h in m['sections'][name]},p.name
print(json.dumps(dict(notes=len(notes),modules=10,specials=7,technical_sections=99,
    canvases=len(canvases),canvas_links=links_checked,typed_relations=12,
    preservation='17 technical notes and 13 task/source/flow notes unchanged after navigation removal',
    errors=[]),ensure_ascii=False,indent=2))
