import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = json.loads((root/'backend/handework/services/service_catalogue.json').read_text(encoding='utf-8'))
for name in ('lib/service-catalogue.ts', 'mobile/src/service-catalogue.ts'):
    text = (root/name).read_text(encoding='utf-8')
    line = next(x for x in text.splitlines() if x.startswith('export const catalogue = '))
    assert json.loads(line.removeprefix('export const catalogue = ').removesuffix(';')) == source, name
assert len(source) == 218 and len({r['category'] for r in source}) == 35
assert len({r['id'] for r in source}) == len(source)
print('Catalogue consistency passed: 218 services, 35 families')
