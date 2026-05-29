import json

# Use the CURRENT workflow (already has all previous fixes)
with open('/tmp/bduk_wf_current.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Fix Build Blog Index Update - handle missing excerpt/headline in old articles
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
  // Handle both 'excerpt' (new format) and 'lead'/'headline' (old format from Sports News workflow)
  const excerptRaw = a.excerpt || a.lead || a.headline || '';
  const excerpt = (typeof excerptRaw === 'string' ? excerptRaw : String(excerptRaw))
    .replace(/[\u{1F000}-\u{1FFFF}]/gu, '').trim();
  const titleStr = a.title || a.headline || '';
  return '    <a href="blog/' + a.slug + '.html" class="bp-card">\n' +
    '      <span class="bp-cat">' + (a.category || '') + '</span>\n' +
    '      <h3>' + titleStr + '</h3>\n' +
    '      <p class="bp-desc">' + excerpt + '</p>\n' +
    '      <div class="bp-footer"><span>' + (a.date || '') + '</span><span class="bp-read-more">閱讀全文 &rarr;</span></div>\n' +
    '    </a>';
}

const cardsHtml = articles.map(buildBpCard).join('\n');

return [{ json: { newB64, recentSha, cardsHtml } }];"""

fixed_count = 0
for node in wf['nodes']:
    if node['name'] == 'Build Blog Index Update':
        node['parameters']['jsCode'] = build_blog_index_code
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

with open('/tmp/bduk_wf7.json', 'w', encoding='utf-8') as f:
    json.dump(put_body, f, ensure_ascii=True)

print('Saved /tmp/bduk_wf7.json')
