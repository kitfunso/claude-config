// Submits every sitemap URL of a site to IndexNow (Bing, Yandex, Seznam, Naver) once its key file is live.
// Run after a deploy that adds or changes pages, not on a schedule: repeat posts of unchanged URLs read as spam.
import { UA, buildPayload, flags, sitemapUrls } from './lib.mjs'

const f = flags()
if (!f.site || !/^[a-zA-Z0-9-]{8,128}$/.test(f.key ?? '')) {
  console.error('usage: indexnow.mjs --site https://host --key <key> [--dry-run]')
  process.exit(2)
}
const { origin, host } = new URL(f.site)
const read = async url => {
  const res = await fetch(url, { headers: { 'User-Agent': UA } })
  return res.ok ? res.text() : ''
}

if ((await read(`${origin}/${f.key}.txt`)).trim() !== f.key) {
  console.error(`ERROR: ${origin}/${f.key}.txt does not serve the key; deploy the key file first`)
  process.exit(1)
}
const { urls } = await sitemapUrls(origin, await read(`${origin}/robots.txt`))
const payload = buildPayload(host, f.key, urls)
if (f['dry-run']) {
  console.log(`dry run: would submit ${payload.urlList.length} URLs, first ${payload.urlList[0]}`)
  process.exit(0)
}
const res = await fetch('https://api.indexnow.org/indexnow', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
  body: JSON.stringify(payload),
})
console.log(`IndexNow ${res.status} for ${payload.urlList.length} URLs ${await res.text()}`.trim())
if (res.status !== 200 && res.status !== 202) process.exitCode = 1
