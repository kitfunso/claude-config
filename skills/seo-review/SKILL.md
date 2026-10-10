---
name: seo-review
description: SEO and AEO (answer-engine) review of any website. Covers Search Console totals and trends, index coverage, AI-crawler access, duplicate hosts, share images, structured data, Bing and IndexNow, a local HTML report, then one fix PR. Use when asked to check GSC, review or improve SEO/AEO, or explain why a site gets little or less search traffic, for hippo-memory.com, phzse.com, braingymdaily.app, mure-energy.com, boring-math.com or any other site. boring-math.com's weekly calculator-page batch is /gsc-review.
---

# SEO + AEO review

One site per run. Output: one self-contained HTML report, opened in the browser, then one PR with the fixes. Production is a separate step: merging usually deploys, so merge only when the user says "ship", "merge" or "deploy" by name. A bare "go" approves the review and the PR. It does not approve production; this was learned on boring-math, 2026-10-09 and 2026-10-10.

`S=~/.claude/skills/seo-review/scripts`. The scripts reuse boring-maths' GSC OAuth token (`~/boring-maths/scripts/seo/`), which reads every property Keith owns. Set `SEO_TOOLS_DIR` if that repo moves.

## 0. Context, before any number

| Site | GSC property | Site source | Rule |
|---|---|---|---|
| boring-math.com | `sc-domain:boring-math.com` | `~/boring-maths` | weekly loop is /gsc-review |
| hippo-memory.com | `sc-domain:hippo-memory.com` | `~/hippo/website` | all wording is Keith's: report copy issues, never rewrite |
| phzse.com | `https://phzse.com/` | `~/phzse` | wellness, never medical claims |
| braingymdaily.app | `sc-domain:braingymdaily.app` | `~/brain-gym` | |
| mure-energy.com | `sc-domain:mure-energy.com` | `~/mure/frontend` | |

Other properties: `npm --prefix ~/boring-maths run -s seo:gsc-pull -- --list-sites`.

- Read the repo's `CLAUDE.md` or `AGENTS.md`. Read the site source from the freshly fetched default branch (`git -C <repo> fetch`, then `git show origin/<branch>:<path>`): on 2026-10-10 the local hippo checkout was 477 commits behind.
- **Find the last checkpoint:** `grep -ril "<host>" ~/.claude/projects/C--Users-skf-s/memory/ <repo>/docs ~/boring-maths/docs`. A cross-site review dated 2026-10-09 lives in `~/boring-maths/docs/seo-checklist-2026-10-09.html`. Read every number in this run against the last checkpoint.
- Who else is on it: `bash ~/.claude/scripts/inflight.sh <repo>`. Look only for PRs and worktrees that touch the site folder.

## 1. Search Console

```bash
npm --prefix ~/boring-maths run -s seo:gsc-pull -- --site "<property>" --label "other-sites/<name>/<YYYY-MM-DD>"
node $S/gsc.mjs daily    --site "<property>" --start <date> --end <date> [--query "<q>"] [--by week|month]
node $S/gsc.mjs queries  --site "<property>" --start <date> --end <date> --brand "<brand words>"
node $S/gsc.mjs windows  --site "<property>" --a <start>:<end> --b <start>:<end> [--min 30]
node $S/gsc.mjs sitemaps --site "<property>"
```

The pull writes 28 days of JSON under `~/boring-maths/gsc-export/` (gitignored). Its closing "Next: python scripts/gsc_analysis.py" hint only applies to boring-math. On an auth error, run the pull with `--reauth` and click the read-only consent in Chrome `ba81958c`. Keith pre-approved that click. Every mode reads final data, as the pull does. `--fresh` adds the last two or three days, which are still partial.

Reading rules. Each one corrected a wrong read on a real site:
- **Take site totals from `daily`** (its `total` line) or `queries`. Google aggregates dates and queries by property, which counts each search once. Page rows count each URL separately, so one search that shows two of your URLs counts twice. On hippo, each `#section` jump link on the home page is its own page row. Query rows miss anonymised queries: on boring-math they summed to 7 clicks against 36. Older checkpoints quote the pull's page-row `Totals:` line, so compare like with like.
- **Split brand from non-brand with `queries`**, and drop our own `site:` checks before any trend read. On hippo those checks were 30 of 299 impressions (10 September to 7 October). For a product site, non-brand reach is the real read.
- **Run `windows` before calling a slide a ranking loss.** It compares the same pages in two windows. On a small site, lower `--min` to 1 to 5. Fewer impressions at an unchanged position means demand or the results page changed. Position slips on the same pages mean ranking.
- **Run `daily --query` before chasing an "opportunity" query.** A spike over two or three days with no clicks is a burst, not demand. Example: "age calculator of dog" had 2,037 of its 2,153 impressions on 1 to 3 October.
- Two back-to-back 28-day windows share 21 days, so call a trend between them directional. Check Google's ranking-update history for overlaps: https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history. An overlap is timing, not proof of cause.
- Queries Google answers inline (percentages, "X% off Y") get no clicks at any position, so don't invest in them.

**When there is no traffic to explain** (flat and tiny, as on phzse and hippo), skip the slide hunt. Instead read four things:
- brand against non-brand queries;
- index coverage (section 2);
- trust signals on content pages: sources cited, true dates, a named author;
- links from other sites.

## 2. Index coverage

```bash
node $S/gsc.mjs inspect --site "<property>" [--url https://<host>] [--limit 200]
node $S/gsc.mjs inspect --site "<property>" --urls https://www.<host>/,https://www.<host>/page/
```

It inspects every sitemap URL, or the list given to `--urls` (use it on the twin host's copies: hippo's /benchmarks/ was indexed only on www). It prints the counts by coverage state, the pages that are not indexed with their last crawl, and the pages where Google picked another URL as the canonical. On both test sites this carried the main finding: 7 of 14 hippo pages and 4 of 16 phzse pages were not indexed. Read the states this way:
- **"Discovered" or "unknown to Google"**: Google has not crawled the page. Request indexing, and add internal links to it.
- **"Crawled - currently not indexed"**: Google read the page and declined it. That is a content or trust problem, so fix the page first, then request indexing. Indexing requests worked on phzse's phase guides (2026-09-07).

## 3. Crawl and answer-engine audit

```bash
node $S/aeo-audit.mjs --url https://<host> [--sample 40] [--json <file>]
```

It reports:
- robots.txt rules for each search bot and each training bot, plus any other agents robots.txt names.
- The twin host (www or apex) and plain `http`: each must redirect to the main host, never answer 200.
- Every sitemap URL, and a spoofed user-agent probe of the homepage.
- An even sample of pages, checked for: status (sitemap URLs must answer 200, not redirect), canonical, noindex, title, description, og:image loading as an image, twitter:card, and one h1.
- Two hand-typed-date signs: one share image on most pages, and one `lastmod` or `dateModified` date on most dated pages.
- JSON-LD types and author types, and links to other sites per page.

How to read it:
- **A twin host that answers 200 is a duplicate site.** Google indexed hippo's /benchmarks/ only on the www copy. Fix it with a 301 at the host or CDN.
- **Search bots decide whether answer engines can cite the site.** OpenAI: a site that blocks OAI-SearchBot "will not be shown in ChatGPT search answers". Anthropic: blocking Claude-SearchBot "may reduce your site's visibility". Blocking GPTBot, ClaudeBot or Google-Extended only stops training; Google-Extended "does not impact a site's inclusion in Google Search". Vendor docs were read 2026-10-10. Keep the search bots open, and leave the training bots to the owner.
- A probe 403 means a WAF rule on that user agent. A 200 does not prove the real bot gets in, because CDNs verify bots by IP.
- **Hand-typed dates** in `lastmod` or `dateModified` are not the real edit dates. Generate them from content changes, such as git history. phzse's guides changed in August and September but still said 2026-03-30.

Then by hand:
- **Bing coverage**, which feeds ChatGPT search and Copilot. Bing Webmaster Tools is the reliable count when the site is verified there. Otherwise run `site:<host>` in Chrome `ba81958c`: scripted reads hit a challenge page (both test runs, 2026-10-10). If Bing is far short of the sitemap, set up IndexNow (section 5).
- **Cloudflare zones** (`reference_cloudflare_zones.md`): `dash.cloudflare.com/<account>/<zone>/ai/metrics` (AI Crawl Control), in Chrome `ba81958c`. The wrangler OAuth token cannot read bot settings. Check the AI bot policies, then set "Most crawled paths" to 4xx. Ignore `/.env`, `/.git`, `/wp-*`, `/actuator` and other admin probes: those are exploit scanners that use crawler names. A path ending in `/null` is a crawler artefact when the page HTML has no "null" in it (hippo, 2026-10-10). The other 404s are the leads. Redirect rules for twin hosts live in the zone's Rules, because Pages `_redirects` cannot redirect a whole domain.
- **A build gate for share images**, if the audit found broken ones: use the repo's own gate if it has one (phzse: `scripts/check-og-image.mjs` in `npm run verify`). Otherwise add one, like boring-maths' `scripts/seo/check-og-images.mjs`. On boring-math, 110 of 181 pages had pointed at a 404.
- **Skip:** `llms.txt` work (Google's AI-features doc says no special file is needed), and FAQ schema for Google (the FAQ rich result stopped on 2026-05-07).

## 4. Report

Write one self-contained HTML file and open it in the browser. It goes in `<repo>/docs/seo-aeo-<YYYY-MM-DD>.html` when a PR will carry it, else in `~/Documents/seo-reviews/<YYYY-MM-DD>/<host>.html`: an untracked file in a checkout that parallel sessions share can be swept into their commits. Reports never go to claude.ai.
- The first paragraph is the answer, in three sentences at most.
- Then come the numbers, each beside the command that regenerates it, against the last checkpoint.
- Then the defects with counts, and the fixes ranked.
- Then what was left alone and why: the 60-day rule, locked copy, authority-bound pages.
- End with the next check dates.

The chat gets three to five sentences and the path.

## 5. Fix, as a PR

- Branch from a freshly fetched default branch, and open one PR. Fix each defect at its root, and add a build gate for each defect class.
- When every defect lives outside the repo (a CDN rule, indexing requests), skip the PR and say so. hippo, 2026-10-10: the www twin needed a Cloudflare rule and nothing in the site was broken.
- Run the repo's own gates: build, tests, lint and format. A format check may cover only `src/`, so run prettier on new files elsewhere by hand.
- Cadence (adopted 2026-10-09): publish new pages one or two a week. Leave a shipped page alone for 60 days. Read GSC four and eight weeks after a change. On boring-math, title edits without links did not move rank.
- Indexing requests (GSC > URL Inspection > Request indexing, in Chrome) go after the fixed pages are live, never before. The quota is roughly 10 to 12 URLs a day (phzse, 2026-09-07), so request the pages that matter most first.
- **IndexNow setup:**
  - Make a key with `node -e "console.log(require('crypto').randomBytes(16).toString('hex'))"`.
  - Put `<key>.txt` at the site root (`public/` or `static/`), holding exactly the key with no newline.
  - Once it is deployed, run `node $S/indexnow.mjs --site https://<host> --key <key> [--dry-run]`.
  - Wire it into the deploy script: hippo's `website/scripts/indexnow.mjs` existed but `npm run deploy` never called it.

## 6. Ship, only on "ship", "merge" or "deploy"

- Confirm the PR's checks are green and the PR is still mergeable. Squash-merge, then `git fetch` before fast-forwarding the local branch: without the fetch, the fast-forward runs against a stale ref.
- Wait for the deploy to serve a changed file. Then verify each fix on the real domain. A win on a `pages.dev` preview did not carry over to boring-math's live host.
- IndexNow: the first POST after a new key can return 403 `SiteVerificationNotCompleted` even when the key file is right. Retry after five minutes. On boring-math (2026-10-10) the first POST got 403 and the retry got 200 for 229 URLs.
- Writeback: add a checkpoint to the site's memory file (numbers, PR, live proof, next check dates) and update its MEMORY.md line. `hippo remember` anything new.

Finish by listing each stage as done, partial or skipped, with the check that closed it.
