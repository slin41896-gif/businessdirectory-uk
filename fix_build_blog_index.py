import json

with open('/tmp/bduk_wf2.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Fix Select Keyword node
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

# Fix Build Blog Index Update - handle missing excerpt in old articles
build_blog_index_code = r"""const raw = $input.first().json;
const recentSha = raw.sha;
const current = JSON.parse(Buffer.from(raw.content.replace(/\n/g, ''), 'base64').toString('utf8'));

const fields = $('Fill Template').first().json.fields;
const newEntry = {
  slug:     fields.SLUG,
  title:    fields.TITLE,
  category: fields.CATEGORY,
  date:     fields.DATE,
  excerpt:  (fields.LEAD || '').replace(/[\u{1F000}-\u{1FFFF}]/gu, '').trim().substring(0, 100),
  imageUrl: fields.BANNER_IMAGE_URL || ''
};

const articles = [newEntry, ...current.articles].slice(0, 3);
const newJson = JSON.stringify({ articles }, null, 2);
const newB64 = Buffer.from(newJson).toString('base64');

function buildBpCard(a) {
  // Handle both 'excerpt' (new format) and 'lead'/'headline' (old format)
  const excerptStr = a.excerpt || a.lead || a.headline || '';
  const excerpt = excerptStr.replace(/[\u{1F000}-\u{1FFFF}]/gu, '').trim();
  return '    <a href="blog/' + a.slug + '.html" class="bp-card">\n' +
    '      <span class="bp-cat">' + (a.category || '') + '</span>\n' +
    '      <h3>' + (a.title || a.headline || '') + '</h3>\n' +
    '      <p class="bp-desc">' + excerpt + '</p>\n' +
    '      <div class="bp-footer"><span>' + (a.date || '') + '</span><span class="bp-read-more">閱讀全文 &rarr;</span></div>\n' +
    '    </a>';
}

const cardsHtml = articles.map(buildBpCard).join('\n');

return [{ json: { newB64, recentSha, cardsHtml } }];"""

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
    elif node['name'] == 'Build Blog Index Update':
        node['parameters']['jsCode'] = build_blog_index_code
        fixed_count += 1
        print(f"Fixed: {node['name']}")

print(f"Total fixed: {fixed_count}")

# Also re-apply Fill Template fix (early + late)
fill_template_original_code = None
for node in wf['nodes']:
    if node['name'] == 'Fill Template':
        fill_template_original_code = node['parameters']['jsCode']
        break

if fill_template_original_code:
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

    late_bduk_fields = """// === BDUK late computed fields (after bodyImageUrl) ===
// BODY_IMAGE_URL - ensure it's set from computed bodyImageUrl
if (!fields.BODY_IMAGE_URL) fields.BODY_IMAGE_URL = bodyImageUrl || '';
// === end late BDUK fields ===

"""

    early_insert_before = "fields.DATE_MODIFIED = fields.DATE_MODIFIED || fields.DATE;"
    late_insert_after = "const bodyImageUrl = uploadOut.BODY_IMAGE_URL || '';"

    # Check if Fill Template already has these markers (from previous fix)
    if '=== BDUK-specific computed fields' in fill_template_original_code:
        print('Fill Template already has BDUK fields (from previous fix), skipping')
    elif early_insert_before in fill_template_original_code:
        new_code = fill_template_original_code.replace(early_insert_before, early_bduk_fields + early_insert_before)
        if late_insert_after in new_code:
            new_code = new_code.replace(late_insert_after, late_insert_after + '\n' + late_bduk_fields)
        for node in wf['nodes']:
            if node['name'] == 'Fill Template':
                node['parameters']['jsCode'] = new_code
                print('Fixed: Fill Template node (re-applied)')
                break
    else:
        print('WARNING: Fill Template early insert point not found')

put_body = {
    'name': wf['name'],
    'nodes': wf['nodes'],
    'connections': wf['connections'],
    'settings': wf.get('settings', {}),
    'staticData': wf.get('staticData', None)
}

with open('/tmp/bduk_wf7.json', 'w', encoding='utf-8') as f:
    json.dump(put_body, f, ensure_ascii=True)

print('Saved /tmp/bduk_wf7.json')
