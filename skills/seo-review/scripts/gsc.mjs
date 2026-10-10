// Search Console reads beyond the 28-day pull: true totals, query split, same-page windows, index state, sitemaps.
import { flags, getAccessToken, pool, sitemapUrls } from './lib.mjs'

const API = 'https://searchconsole.googleapis.com/webmasters/v3'
const INSPECT = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
const USAGE = `usage: gsc.mjs <mode> --site <property> [--fresh]
  daily     --start <date> --end <date> [--query "<q>"] [--by day|week|month]
  queries   --start <date> --end <date> [--brand "name,other name"]
  windows   --a <start>:<end> --b <start>:<end> [--min 30]
  inspect   [--url https://host | --urls <url>,<url>] [--limit 200]
  sitemaps
--fresh adds the last two or three days, still partial (dataState=all); the default, final, matches the pull.`

const f = flags()
const MODES = { daily, queries, windows, inspect, sitemaps }
if (!f.site || !MODES[f._[0]]) {
  console.error(USAGE)
  process.exit(2)
}
const auth = { Authorization: `Bearer ${await getAccessToken({})}` }

async function post(url, body) {
  const res = await fetch(url, { method: 'POST', headers: { ...auth, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`${url} ${res.status} ${await res.text()}`)
  return res.json()
}
const site = `${API}/sites/${encodeURIComponent(f.site)}`
// SHORTCUT: one page of 25,000 rows; paginate with startRow for a bigger site.
const query = async body => (await post(`${site}/searchAnalytics/query`, { rowLimit: 25000, dataState: f.fresh ? 'all' : 'final', ...body })).rows ?? []
const fmt = r => `${String(r.clicks).padStart(4)}c ${String(r.impressions).padStart(7)}i pos ${r.position.toFixed(1).padStart(5)}`
const show = url => url.replace(/^https?:\/\//, '')
const sum = rows => rows.reduce((s, r) => ({ clicks: s.clicks + r.clicks, impressions: s.impressions + r.impressions }), { clicks: 0, impressions: 0 })

function bucket(date, by) {
  if (by === 'all' || by === 'month') return by === 'all' ? 'all' : date.slice(0, 7)
  if (by !== 'week') return date
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7))
  return `week of ${d.toISOString().slice(0, 10)}`
}

function rollup(rows, by) {
  const out = new Map()
  for (const r of rows) {
    const k = bucket(r.keys[0], by)
    const s = out.get(k) ?? { clicks: 0, impressions: 0, weighted: 0 }
    out.set(k, { clicks: s.clicks + r.clicks, impressions: s.impressions + r.impressions, weighted: s.weighted + r.position * r.impressions })
  }
  for (const s of out.values()) s.position = s.impressions ? s.weighted / s.impressions : 0
  return out
}

// Dates are aggregated by property, so these totals count each search once and keep anonymised queries.
async function daily() {
  const base = { startDate: f.start, endDate: f.end, dimensions: ['date'] }
  const filter = { dimensionFilterGroups: [{ filters: [{ dimension: 'query', operator: 'equals', expression: f.query }] }] }
  const [rows, q] = await Promise.all([query(base), f.query ? query({ ...base, ...filter }) : []])
  const series = rollup(rows, f.by ?? 'day')
  const qs = rollup(q, f.by ?? 'day')
  for (const [k, r] of series) console.log(k, `site ${fmt(r)}`, f.query ? `| query ${qs.has(k) ? fmt(qs.get(k)) : '-'}` : '')
  const all = rollup(rows, 'all').get('all')
  if (all) console.log(`total, each search counted once: ${all.clicks} clicks, ${all.impressions} impressions, position ${all.position.toFixed(1)}`)
}

async function queries() {
  const brand = String(f.brand ?? '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean)
  const base = { startDate: f.start, endDate: f.end }
  const [total, rows] = await Promise.all([query({ ...base, dimensions: ['date'] }), query({ ...base, dimensions: ['query'] })])
  const kind = q => (q.startsWith('site:') ? 'own site: checks (drop from trend reads)' : brand.some(b => q.includes(b)) ? 'brand' : 'non-brand')
  const groups = {}
  for (const r of rows) (groups[kind(r.keys[0].toLowerCase())] ??= []).push(r)
  const t = sum(total)
  const named = sum(rows)
  console.log(`all searches: ${t.clicks} clicks, ${t.impressions} impressions; named queries cover ${named.clicks} clicks, ${named.impressions} impressions (the rest is anonymised)`)
  for (const [k, rs] of Object.entries(groups)) console.log(`  ${k}: ${rs.length} queries, ${sum(rs).clicks} clicks, ${sum(rs).impressions} impressions`)
  const top = (groups['non-brand'] ?? []).sort((a, b) => b.impressions - a.impressions).slice(0, 15)
  console.log(`top non-brand queries${brand.length ? '' : ' (no --brand given, so brand searches are in here)'}:`)
  for (const r of top) console.log(`  ${r.keys[0].slice(0, 56).padEnd(56)} ${fmt(r)}`)
}

async function pages(win) {
  const [startDate, endDate] = String(win).split(':')
  return new Map((await query({ startDate, endDate, dimensions: ['page'] })).map(r => [r.keys[0], r]))
}

// Same pages in both windows, so a shift in which pages get shown cannot pass for a rank change.
async function windows() {
  const min = Number(f.min ?? 30)
  const [a, b] = await Promise.all([pages(f.a), pages(f.b)])
  const rows = [...a.keys()]
    .filter(k => b.has(k) && a.get(k).impressions >= min && b.get(k).impressions >= min)
    .map(k => ({ k, ap: a.get(k).position, bp: b.get(k).position, ai: a.get(k).impressions, bi: b.get(k).impressions }))
    .map(r => ({ ...r, d: r.bp - r.ap, w: Math.min(r.ai, r.bi) }))
  const wSum = rows.reduce((s, r) => s + r.w, 0)
  const mean = rows.reduce((s, r) => s + r.d * r.w, 0) / (wSum || 1)
  console.log('window A', f.a, sum([...a.values()]), `pages ${a.size} (page rows: impressions overcount when two of your pages show for one search)`)
  console.log('window B', f.b, sum([...b.values()]), `pages ${b.size}`)
  console.log(`pages in both (${min}+ impressions each): ${rows.length}; weighted mean position change ${mean.toFixed(1)} (positive = worse)`)
  if (rows.length < 5) console.log(`  under 5 pages qualify: rerun with a lower --min (e.g. --min ${Math.max(1, Math.floor(min / 5))})`)
  console.log(`worse by 2+: ${rows.filter(r => r.d > 2).length}, better by 2+: ${rows.filter(r => r.d < -2).length}, shown in A only: ${[...a.keys()].filter(k => !b.has(k)).length}`)
  const line = r => `  ${show(r.k).padEnd(60)} ${r.ap.toFixed(1)} -> ${r.bp.toFixed(1)}  impr ${r.ai} -> ${r.bi}`
  const drops = rows.filter(r => r.d > 0).sort((x, y) => y.d * y.w - x.d * x.w).slice(0, 10)
  const gains = rows.filter(r => r.d < 0).sort((x, y) => x.d * x.w - y.d * y.w).slice(0, 5)
  console.log('biggest weighted drops:\n' + (drops.map(line).join('\n') || '  none'))
  console.log('biggest weighted gains:\n' + (gains.map(line).join('\n') || '  none'))
}

async function inspect() {
  const origin = f.url ? new URL(f.url).origin : f.site.startsWith('sc-domain:') ? `https://${f.site.slice(10)}` : new URL(f.site).origin
  const robots = f.urls ? '' : await fetch(`${origin}/robots.txt`).then(r => (r.ok ? r.text() : ''))
  const { urls } = f.urls ? { urls: String(f.urls).split(',') } : await sitemapUrls(origin, robots)
  const list = urls.slice(0, Number(f.limit ?? 200))
  const results = await pool(list, 4, async url => {
    const idx = (await post(INSPECT, { inspectionUrl: url, siteUrl: f.site })).inspectionResult?.indexStatusResult ?? {}
    return { url, indexed: idx.verdict === 'PASS', state: idx.coverageState ?? idx.verdict ?? 'unknown', crawled: idx.lastCrawlTime ?? 'never', google: idx.googleCanonical }
  })
  const states = {}
  for (const r of results) states[r.state] = (states[r.state] ?? 0) + 1
  console.log(`${origin}: inspected ${list.length} of ${urls.length} ${f.urls ? 'given' : 'sitemap'} URLs; indexed ${results.filter(r => r.indexed).length}`)
  for (const [s, n] of Object.entries(states).sort((x, y) => y[1] - x[1])) console.log(`  ${s}: ${n}`)
  const out = results.filter(r => !r.indexed)
  if (out.length) console.log('not indexed:\n' + out.map(r => `  ${show(r.url).padEnd(60)} ${r.state}, last crawl ${r.crawled}`).join('\n'))
  const moved = results.filter(r => r.google && r.google !== r.url)
  if (moved.length) console.log('Google chose another URL as the canonical:\n' + moved.map(r => `  ${show(r.url)} -> ${show(r.google)}`).join('\n'))
}

async function sitemaps() {
  const res = await fetch(`${site}/sitemaps`, { headers: auth })
  if (!res.ok) throw new Error(`sitemaps ${res.status} ${await res.text()}`)
  const { sitemap = [] } = await res.json()
  if (sitemap.length === 0) console.log('no sitemap submitted for this property')
  for (const s of sitemap) {
    const counts = (s.contents ?? []).map(c => `${c.type} ${c.submitted}`).join(', ')
    console.log(`${s.path} | submitted ${s.lastSubmitted ?? '-'} | last read ${s.lastDownloaded ?? 'never'} | errors ${s.errors ?? 0} warnings ${s.warnings ?? 0} | ${counts}`)
  }
}

await MODES[f._[0]]()
