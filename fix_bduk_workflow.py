import json

with open('/tmp/bduk_wf2.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

select_kw_code = r"""const raw = $input.first().json;
const sha = raw.sha;
const content = raw.content.replace(/\n/g, '');
const keywordsData = JSON.parse(Buffer.from(content, 'base64').toString('utf8'));

// Support both { keywords: [...] } and plain array formats
const kwList = Array.isArray(keywordsData) ? keywordsData : keywordsData.keywords;
const available = kwList.filter(k => k.status === 'available');
if (available.length === 0) throw new Error('No available keywords - run Keyword Refresh workflow first.');

const selected = available[0];
return [{ json: { ...selected, keywordsData: kwList, keywordsSha: sha } }];"""

mark_kw_code = r"""const kw = $('Select Keyword').first().json;
const slug = $('Fill Template').first().json.slug;
const title = $('Inject Card').first().json.title;

const kwList = kw.keywordsData; // plain array
const sha = kw.keywordsSha;

const updatedKeywords = kwList.map(k => {
  if (k.id === kw.id) {
    return { ...k, status: 'used', slug, used_date: new Date().toISOString().split('T')[0] };
  }
  return k;
});

// Keep plain array format to match keywords.json structure
const content = Buffer.from(JSON.stringify(updatedKeywords, null, 2)).toString('base64');

return [{ json: { content, sha, slug, title } }];"""

fixed_count = 0
for node in wf['nodes']:
    if node['name'] == 'Select Keyword':
        node['parameters']['jsCode'] = select_kw_code
        fixed_count += 1
        print(f"Fixed: {node['name']}")
    elif node['name'] == 'Mark Keyword Used':
        node['parameters']['jsCode'] = mark_kw_code
        fixed_count += 1
        print(f"Fixed: {node['name']}")

print(f"Total fixed: {fixed_count}")

put_body = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': wf.get('settings', {}),
    'staticData': wf.get('staticData', None)
}

with open('/tmp/bduk_wf4.json', 'w', encoding='utf-8') as f:
    json.dump(put_body, f, ensure_ascii=True)

print('Saved /tmp/bduk_wf4.json')
