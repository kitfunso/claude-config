import os from 'node:os'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

// boring-maths holds the one GSC OAuth token for every property Keith owns, so reuse its auth instead of a second login.
const TOOLS = process.env.SEO_TOOLS_DIR ?? path.join(os.homedir(), 'boring-maths', 'scripts', 'seo')
const load = name => import(pathToFileURL(path.join(TOOLS, name)).href)
export const { getAccessToken } = await load('gsc-auth.mjs')
export const { sitemapLocs, buildPayload } = await load('indexnow-core.mjs')

export const UA = 'Mozilla/5.0 (compatible; seo-review/1.0)'

export function flags(argv = process.argv.slice(2)) {
  const out = { _: [] }
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) out._.push(argv[i])
    else if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) out[argv[i].slice(2)] = true
    else out[argv[i].slice(2)] = argv[++i]
  }
  return out
}

export async function pool(items, n, fn) {
  const out = new Array(items.length)
  let next = 0
  const worker = async () => {
    while (next < items.length) {
      const i = next++
      out[i] = await fn(items[i])
    }
  }
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, worker))
  return out
}

// Sitemaps named in robots.txt, else the two usual roots; an index is followed two levels down.
export async function sitemapUrls(origin, robotsTxt = '') {
  const named = [...robotsTxt.matchAll(/^\s*sitemap:\s*(\S+)/gim)].map(m => m[1])
  const roots = named.length > 0 ? named : [`${origin}/sitemap-index.xml`, `${origin}/sitemap.xml`]
  const seen = new Set()
  const lastmod = new Map()
  const sitemaps = []
  const visit = async (url, depth) => {
    if (seen.has(url) || depth > 2) return
    seen.add(url)
    const res = await fetch(url, { headers: { 'User-Agent': UA } })
    if (!res.ok) return
    const xml = await res.text()
    sitemaps.push(url)
    if (/<sitemapindex/i.test(xml)) {
      for (const loc of sitemapLocs(xml)) await visit(loc, depth + 1)
      return
    }
    for (const [, block] of xml.matchAll(/<url>([\s\S]*?)<\/url>/g)) {
      const loc = block.match(/<loc>\s*([^<\s]+)\s*<\/loc>/)?.[1]
      if (loc) lastmod.set(loc, block.match(/<lastmod>\s*([^<\s]+)\s*<\/lastmod>/)?.[1])
    }
  }
  for (const root of roots) {
    await visit(root, 0)
    if (lastmod.size > 0 && named.length === 0) break
  }
  return { sitemaps, urls: [...lastmod.keys()], lastmod }
}

// The value most entries share, so a date typed once by hand shows up as one value on most pages.
export function mode(values) {
  const counts = new Map()
  for (const v of values) if (v) counts.set(v, (counts.get(v) ?? 0) + 1)
  const [value, n] = [...counts].sort((a, b) => b[1] - a[1])[0] ?? [undefined, 0]
  return { value, n }
}
