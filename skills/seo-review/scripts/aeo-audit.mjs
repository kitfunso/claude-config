// Live crawl and answer-engine audit of one site: robots rules per bot, host twins, sitemap, a page sample.
import fs from 'node:fs'
import { UA, flags, mode, pool, sitemapUrls } from './lib.mjs'

const f = flags()
if (!f.url) {
  console.error('usage: aeo-audit.mjs --url https://host [--sample 40] [--json out.json]')
  process.exit(2)
}
const origin = new URL(f.url).origin
const bareHost = new URL(origin).host.replace(/^www\./, '')
// Search bots decide whether a site can be cited; training bots are the owner's call (vendor docs read 2026-10-10).
const BOTS = {
  search: ['Googlebot', 'Bingbot', 'OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot', 'Perplexity-User', 'Claude-SearchBot', 'Claude-User'],
  training: ['GPTBot', 'ClaudeBot', 'Google-Extended', 'Applebot-Extended', 'CCBot', 'meta-externalagent'],
}
const get = (url, ua = UA) => fetch(url, { redirect: 'manual', headers: { 'User-Agent': ua } })

function robotsGroups(txt) {
  const groups = []
  let cur
  let inAgents = false
  for (const raw of txt.split(/\r?\n/)) {
    const m = raw.replace(/#.*/, '').match(/^\s*([\w-]+)\s*:\s*(.*?)\s*$/)
    if (!m) continue
    const key = m[1].toLowerCase()
    if (key === 'user-agent') {
      if (!inAgents) groups.push((cur = { agents: [], disallow: [], allow: [] }))
      cur.agents.push(m[2].toLowerCase())
      inAgents = true
      continue
    }
    inAgents = false
    if (cur && (key === 'disallow' || key === 'allow')) cur[key].push(m[2])
  }
  return groups
}

function robotsVerdict(groups, bot) {
  const named = groups.find(g => g.agents.includes(bot.toLowerCase()))
  const g = named ?? groups.find(x => x.agents.includes('*'))
  if (!g) return 'open (no rule)'
  const via = named ? 'named' : '*'
  if (g.disallow.includes('/') && !g.allow.includes('/')) return `BLOCKED (${via})`
  const paths = g.disallow.filter(Boolean)
  return paths.length > 0 ? `open except ${paths.slice(0, 3).join(' ')} (${via})` : `open (${via})`
}

const attrs = tag =>
  Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m => [m[1].toLowerCase(), m[2] ?? m[3] ?? m[4]]))
const tags = (html, name) => [...html.matchAll(new RegExp(`<${name}\\b[^>]*>`, 'gi'))].map(m => attrs(m[0]))
const meta = (html, key) => tags(html, 'meta').find(a => (a.property ?? a.name)?.toLowerCase() === key)?.content

function jsonLd(html) {
  const out = { types: new Set(), authors: new Set(), dateModified: undefined, bad: 0 }
  const walk = n => {
    if (Array.isArray(n)) return n.forEach(walk)
    if (!n || typeof n !== 'object') return
    ;[].concat(n['@type'] ?? []).forEach(t => out.types.add(t))
    ;[].concat(n.author ?? []).forEach(a => out.authors.add(a?.['@type'] ?? (a?.['@id'] ? '@id reference' : typeof a === 'string' ? 'plain name' : 'no @type')))
    out.dateModified ??= n.dateModified
    if (n['@graph']) walk(n['@graph'])
  }
  for (const m of html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)) {
    try {
      walk(JSON.parse(m[1]))
    } catch {
      out.bad++
    }
  }
  return { ...out, types: [...out.types], authors: [...out.authors] }
}

async function checkPage(url) {
  const res = await get(url)
  if (res.status >= 300 && res.status < 400) return { url, status: res.status, location: res.headers.get('location') }
  if (!res.ok) return { url, status: res.status }
  const html = await res.text()
  const canonical = tags(html, 'link').find(a => a.rel?.toLowerCase() === 'canonical')?.href
  const og = meta(html, 'og:image')
  const hosts = tags(html, 'a').map(a => a.href?.match(/^https?:\/\/([^/?#:]+)/i)?.[1]?.toLowerCase().replace(/^www\./, ''))
  return {
    url,
    status: res.status,
    title: (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? '').trim(),
    description: meta(html, 'description') ?? '',
    canonical: canonical && new URL(canonical, url).href,
    noindex: /noindex/i.test(`${meta(html, 'robots') ?? ''} ${res.headers.get('x-robots-tag') ?? ''}`),
    ogImage: og && new URL(og, url).href,
    twitterCard: meta(html, 'twitter:card'),
    ld: jsonLd(html),
    h1: (html.match(/<h1\b/gi) ?? []).length,
    outbound: hosts.filter(h => h && h !== bareHost).length,
  }
}

async function checkImage(url) {
  let res = await fetch(url, { method: 'HEAD', headers: { 'User-Agent': UA } })
  if (res.status === 403 || res.status === 405) res = await fetch(url, { headers: { 'User-Agent': UA } })
  return { status: res.status, type: res.headers.get('content-type') ?? '' }
}

// A twin host or plain http that answers 200 serves duplicate pages; Google may index the twin over the canonical.
async function checkTwin(base) {
  try {
    const res = await get(`${base}/`)
    return { base, status: res.status, location: res.headers.get('location') ?? '' }
  } catch (err) {
    return { base, status: 'no answer', location: err.cause?.code ?? err.message }
  }
}

const spread = (list, n) => (list.length <= n ? list : Array.from({ length: n }, (_, i) => list[Math.floor((i * list.length) / n)]))
const path = u => u.replace(origin, '') || '/'
// Counts only entries that carry a value, so seven guides sharing one date still show on a 16-page site.
const most = (values, min) => {
  const present = values.filter(Boolean)
  const m = mode(present)
  return m.n >= min && m.n > present.length / 2 ? [`${m.value} on ${m.n} of ${present.length}`] : []
}

const robotsRes = await get(`${origin}/robots.txt`)
const robotsTxt = robotsRes.ok ? await robotsRes.text() : ''
const groups = robotsGroups(robotsTxt)
const { sitemaps, urls, lastmod } = await sitemapUrls(origin, robotsTxt)
const llms = (await get(`${origin}/llms.txt`)).status
const twinHost = origin.includes('://www.') ? origin.replace('://www.', '://') : origin.replace('://', '://www.')
const twins = await pool([twinHost, origin.replace(/^https:/, 'http:')], 2, checkTwin)
const probeBots = ['OAI-SearchBot', 'PerplexityBot', 'Claude-SearchBot', 'GPTBot', 'ClaudeBot']
const probe = await pool(['default', ...probeBots], 6, async bot =>
  [bot, (await get(`${origin}/`, bot === 'default' ? UA : `Mozilla/5.0 (compatible; ${bot}/1.0)`)).status])

const sample = [...new Set([`${origin}/`, ...spread(urls, Number(f.sample ?? 40))])]
const pages = await pool(sample, 6, checkPage)
const imageUrls = [...new Set(pages.map(p => p.ogImage).filter(Boolean))]
const images = new Map(imageUrls.map((u, i) => [u, i]))
const imageResults = await pool(imageUrls, 6, checkImage)
const imageOk = u => imageResults[images.get(u)].status === 200 && imageResults[images.get(u)].type.startsWith('image/')
const live = pages.filter(p => p.status === 200)
const inSitemap = new Set(urls)

const issues = {
  'twin host or http answers 200 (duplicate site)': twins.filter(t => t.status === 200).map(t => t.base),
  'twin host redirects somewhere else': twins.filter(t => t.status >= 300 && t.status < 400 && !t.location.startsWith(origin)).map(t => `${t.base} -> ${t.location}`),
  'sitemap URL not 200': pages.filter(p => inSitemap.has(p.url) && p.status !== 200).map(p => `${path(p.url)} ${p.status}${p.location ? ` -> ${p.location}` : ''}`),
  'noindex on a sampled page': live.filter(p => p.noindex).map(p => path(p.url)),
  'canonical missing': live.filter(p => !p.canonical).map(p => path(p.url)),
  'canonical is another URL': live.filter(p => p.canonical && p.canonical !== p.url).map(p => `${path(p.url)} -> ${p.canonical}`),
  'title missing': live.filter(p => !p.title).map(p => path(p.url)),
  'description missing': live.filter(p => !p.description).map(p => path(p.url)),
  'og:image missing': live.filter(p => !p.ogImage).map(p => path(p.url)),
  'og:image does not load as an image': live.filter(p => p.ogImage && !imageOk(p.ogImage)).map(p => `${path(p.url)} -> ${p.ogImage} ${imageResults[images.get(p.ogImage)].status}`),
  'one og:image on most pages': live.length >= 4 ? most(live.map(p => p.ogImage), Math.floor(live.length / 2) + 1) : [],
  'twitter:card missing': live.filter(p => !p.twitterCard).map(p => path(p.url)),
  'no JSON-LD': live.filter(p => p.ld.types.length === 0 && p.ld.bad === 0).map(p => path(p.url)),
  'JSON-LD that does not parse': live.filter(p => p.ld.bad > 0).map(p => path(p.url)),
  'one JSON-LD dateModified on most dated pages (typed by hand?)': most(live.map(p => p.ld.dateModified), 3),
  'one sitemap lastmod on most dated URLs (typed by hand?)': most([...lastmod.values()], 5),
  'h1 count is not 1': live.filter(p => p.h1 !== 1).map(p => `${path(p.url)} (${p.h1})`),
}
const count = list => Object.entries(list.reduce((a, x) => ((a[x] = (a[x] ?? 0) + 1), a), {})).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k} ${n}`).join(', ') || 'none'
const outbound = live.map(p => p.outbound).sort((a, b) => a - b)
const known = new Set([...BOTS.search, ...BOTS.training, '*'].map(b => b.toLowerCase()))
const otherAgents = [...new Set(groups.flatMap(g => g.agents))].filter(a => !known.has(a))

console.log(`${origin}: robots.txt ${robotsRes.status}, ${sitemaps.length} sitemap file(s), ${urls.length} URLs, llms.txt ${llms}`)
console.log(`host twins: ${twins.map(t => `${t.base} ${t.status}${t.location ? ` -> ${t.location}` : ''}`).join(', ')}`)
for (const [kind, bots] of Object.entries(BOTS)) {
  console.log(`robots, ${kind} bots:`)
  for (const bot of bots) console.log(`  ${bot.padEnd(19)} ${robotsVerdict(groups, bot)}`)
}
if (otherAgents.length) console.log(`other agents named in robots.txt: ${otherAgents.join(', ')}`)
console.log(`homepage by spoofed user agent (a 403 means a UA rule; a 200 does not prove the real bot gets in): ${probe.map(([b, s]) => `${b} ${s}`).join(', ')}`)
console.log(`sample: ${sample.length} pages (${live.length} answered 200), ${imageUrls.length} distinct og:image URLs`)
for (const [name, hits] of Object.entries(issues)) {
  console.log(`  ${hits.length === 0 ? 'ok  ' : 'FAIL'} ${name}: ${hits.length}${hits.length ? `  e.g. ${hits.slice(0, 3).join(' | ')}` : ''}`)
}
console.log(`JSON-LD types: ${count(live.flatMap(p => p.ld.types))}`)
console.log(`JSON-LD author types: ${count(live.flatMap(p => p.ld.authors))}`)
console.log(`links to other sites per page: median ${outbound[Math.floor(outbound.length / 2)] ?? 0}, pages with none ${outbound.filter(n => n === 0).length} of ${live.length}`)

if (typeof f.json === 'string') {
  const robots = Object.fromEntries(Object.values(BOTS).flat().map(b => [b, robotsVerdict(groups, b)]))
  const report = { origin, at: new Date().toISOString(), robotsStatus: robotsRes.status, robots, otherAgents, twins, sitemaps, urlCount: urls.length, llms, probe, pages, issues }
  fs.writeFileSync(f.json, JSON.stringify(report, null, 2))
  console.log(`wrote ${f.json}`)
}
