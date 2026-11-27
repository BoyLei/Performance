"""Checks for this vault's table and four-space outline conventions, not a full Markdown parser."""
import re


def wikilink_destination(raw):
    """Obsidian table aliases escape the separator before Markdown table parsing."""
    return raw.replace(r'\|', '|').split('|', 1)[0]


def table_cells(line):
    """Split only pipes preceded by an even number of backslashes (including zero)."""
    cuts = []
    slashes = 0
    for i, char in enumerate(line):
        if char == '|' and slashes % 2 == 0:
            cuts.append(i)
        slashes = slashes + 1 if char == '\\' else 0
    cells = [line[a + 1:b].strip() for a, b in zip(cuts, cuts[1:])]
    return cells


def table_errors(body):
    """Tables in this vault have leading/trailing pipes and a separator row."""
    lines = body.splitlines()
    errors = []
    i = 0
    while i + 1 < len(lines):
        header = lines[i].strip()
        separator = lines[i + 1].strip()
        cells = table_cells(separator)
        if not (header.startswith('|') and cells and
                all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells)):
            i += 1
            continue
        width = len(table_cells(header))
        if len(cells) != width:
            errors.append(f'table row {i + 2}: separator column count differs')
        j = i + 2
        while j < len(lines) and lines[j].strip().startswith('|'):
            row = lines[j].strip()
            if len(table_cells(row)) != width:
                errors.append(f'table row {j + 1}: column count differs from {width}')
            for raw in re.findall(r'\[\[([^\]]+)\]\]', row):
                if re.search(r'(?<!\\)\|', raw):
                    errors.append(f'table row {j + 1}: unescaped wikilink alias separator')
            j += 1
        i = j
    return errors


def hierarchy_errors(body):
    """Keep Copilot's root check, with the existing four-space outline convention."""
    errors = []
    previous = -1
    for number, line in enumerate(body.splitlines(), 1):
        m = re.match(r'^( *)- ', line)
        if m:
            level = len(m[1])
            if level % 4:
                errors.append(f'line {number}: invalid list indentation')
            if not (level == 0 if previous == -1 else level <= previous + 4):
                errors.append(f'line {number}: skipped hierarchy level')
            previous = level
        elif line.strip():
            previous = -1
    return errors
