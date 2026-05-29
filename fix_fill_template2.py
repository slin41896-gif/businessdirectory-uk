import json

with open('/tmp/bduk_wf2.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Find Fill Template node and patch it correctly
for node in wf['nodes']:
    if node['name'] == 'Fill Template':
        original_code = node['parameters']['jsCode']

        # Early computed fields (before bodyImageUrl declaration)
        early_bduk_fields = """
// === BDUK-specific computed fields (early - no dependency on bodyImageUrl) ===
// GTM_ID - BDUK GTM container
if (!fields.GTM_ID) fields.GTM_ID = 'GTM-KHMKPNV9';

// DATE_DISPLAY - human-readable date from DATE field
if (!fields.DATE_DISPLAY) {
  try {
    const d = new Date(fields.DATE || new Date());
    fields.DATE_DISPLAY = d.toLocaleDateString('zh-HK', { year: 'numeric', month: 'long', day: 'numeric' });
  } catch(e) {
    fields.DATE_DISPLAY = fields.DATE || '';
  }
}

// READ_TIME - from READ_MIN field
if (!fields.READ_TIME) {
  const mins = parseInt(fields.READ_MIN || '5', 10);
  fields.READ_TIME = (isNaN(mins) ? 5 : mins) + ' 分鐘';
}

// CONTENT - map from BODY (BDUK template uses CONTENT where Spheretap uses BODY directly)
if (!fields.CONTENT) fields.CONTENT = fields.BODY || '';

// EVENT_SLUG - should already be in article JSON, but fallback to SLUG
if (!fields.EVENT_SLUG) fields.EVENT_SLUG = fields.SLUG || '';
// === end early BDUK-specific fields ===

"""

        # Late computed fields (after bodyImageUrl is declared)
        late_bduk_fields = """// === BDUK late computed fields (after bodyImageUrl) ===
// BODY_IMAGE_URL - ensure it's set from computed bodyImageUrl
if (!fields.BODY_IMAGE_URL) fields.BODY_IMAGE_URL = bodyImageUrl || '';
// === end late BDUK fields ===

"""

        # Insertion points
        early_insert_before = "fields.DATE_MODIFIED = fields.DATE_MODIFIED || fields.DATE;"
        # After bodyImageUrl is declared: "const bodyImageUrl = uploadOut.BODY_IMAGE_URL || '';"
        late_insert_after = "const bodyImageUrl = uploadOut.BODY_IMAGE_URL || '';"

        if early_insert_before in original_code:
            new_code = original_code.replace(early_insert_before, early_bduk_fields + early_insert_before)
        else:
            print('WARNING: early insertion point not found')
            new_code = original_code

        if late_insert_after in new_code:
            new_code = new_code.replace(late_insert_after, late_insert_after + '\n' + late_bduk_fields)
        else:
            print('WARNING: late insertion point not found')

        node['parameters']['jsCode'] = new_code
        print('Fixed: Fill Template node - corrected BDUK computed field positions')
        break

# Also need to update the "Select Keyword" and "Mark Keyword Used" nodes
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

for node in wf['nodes']:
    if node['name'] == 'Select Keyword':
        node['parameters']['jsCode'] = select_kw_code
        print('Fixed: Select Keyword node')
    elif node['name'] == 'Mark Keyword Used':
        node['parameters']['jsCode'] = mark_kw_code
        print('Fixed: Mark Keyword Used node')

put_body = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': wf.get('settings', {}),
    'staticData': wf.get('staticData', None)
}

with open('/tmp/bduk_wf6.json', 'w', encoding='utf-8') as f:
    json.dump(put_body, f, ensure_ascii=True)

print('Saved /tmp/bduk_wf6.json')
