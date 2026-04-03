/**
 * citation_crawler — Apify Actor (SDK v3 + Crawlee)
 *
 * Two operating modes:
 *   Deterministic: pass `articleUrls` → fetch each page directly, extract metadata + PDFs
 *   Crawl:        pass `startUrls`   → discover article links, then extract each
 *
 * Output per article:
 *   sourceUrl, loadedUrl, sourceDomain, loadedDomain,
 *   title, authors, journal, publishedAt, doi, abstract,
 *   wordCount, pdfUrls, retrievedAt, [html]
 */

import { Actor } from 'apify';
import { PlaywrightCrawler, log } from 'crawlee';
import { parse as parseDate } from 'chrono-node';
import { URL } from 'url';
import * as cheerio from 'cheerio';

// ---------------------------------------------------------------------------
// CONFIG
// ---------------------------------------------------------------------------
const MINIMUM_WORDS_DEFAULT = 100;

// ---------------------------------------------------------------------------
// HELPERS
// ---------------------------------------------------------------------------

/** Extract hostname without www. prefix. */
const parseDomain = (url) => {
    try {
        return new URL(url).hostname.replace(/^www\./, '');
    } catch {
        return null;
    }
};

/** Rough word count. */
const countWords = (text) => {
    if (typeof text !== 'string') return 0;
    return text.trim().split(/\s+/).filter(Boolean).length;
};

/**
 * Determine if a URL is likely an article page.
 * Clinical guidelines don't follow news URL patterns, so we're intentionally
 * inclusive — false positives are caught by the minWords gate downstream.
 */
const isLikelyArticlePage = (rawUrl) => {
    const hardExcludes = [
        '/login', '/signup', '/register', '/cart', '/checkout',
        '/search', '/tag/', '/category/', '/author/', '/feed', '/rss',
        '/sitemap', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3', '.zip',
    ];
    const positives = [
        '/article', '/content/', '/guideline', '/clinical/', '/recommendation',
        '/statement', '/report', '/journal/', '?p=', 'id=', '.html',
        '/full', '/abstract', '/doi/', '/pmc/', '/pubmed/',
        '/afp/', '/jama/', '/nejm/', '/bmj/', '/lancet/', '/annals/',
        '/uspstf', '/cdc.gov/mmwr', '/acp', '/ada', '/aha', '/acc',
    ];

    let lower;
    try {
        lower = new URL(rawUrl).href.toLowerCase();
    } catch {
        return false;
    }

    if (hardExcludes.some(x => lower.includes(x))) return false;
    if (positives.some(x => lower.includes(x))) return true;

    // Slug heuristic: 4+ hyphens in path = likely an article slug
    const path = new URL(rawUrl).pathname;
    const hyphens = (path.match(/-/g) || []).length;
    if (hyphens >= 4) return true;

    // Depth heuristic: /domain/year/section/article-slug
    const depth = path.split('/').filter(Boolean).length;
    if (depth >= 3) return true;

    return false;
};

/**
 * Collect all PDF-linked URLs on a page.
 * Matches .pdf extension, /pdf/ paths, and common publisher PDF URL patterns.
 */
const extractPdfUrls = ($, baseUrl) => {
    const pdfUrls = new Set();
    $('a[href]').each((_, el) => {
        const href = $( el).attr('href');
        if (!href) return;
        try {
            const abs = new URL(href, baseUrl).href;
            const lower = abs.toLowerCase();
            if (
                lower.endsWith('.pdf') ||
                lower.includes('/pdf/') ||
                lower.includes('/pdfs/') ||
                lower.includes('fullpdf') ||
                lower.includes('format=pdf') ||
                lower.includes('type=pdf') ||
                lower.includes('media=pdf')
            ) {
                pdfUrls.add(abs);
            }
        } catch { /* malformed URL, skip */ }
    });
    return [...pdfUrls];
};

/**
 * Extract structured article metadata using (in priority order):
 *   1. Schema.org JSON-LD (most reliable for academic publishers)
 *   2. OpenGraph / Dublin Core meta tags
 *   3. Citation meta tags (Google Scholar standard)
 *   4. DOM element selectors
 */
const extractMetadata = ($, html, pageUrl) => {
    // ── Schema.org JSON-LD ───────────────────────────────────────────────────
    let schemaTitle, schemaDate, schemaDoi, schemaAuthors = [], schemaJournal;
    $('script[type="application/ld+json"]').each((_, el) => {
        try {
            const raw = $(el).html();
            const data = JSON.parse(raw);
            const nodes = Array.isArray(data) ? data : [data];
            for (const node of nodes) {
                if (!node['@type']?.match?.(/Article|ScholarlyArticle|MedicalGuideline|Report/i)) continue;
                schemaTitle    = schemaTitle    || node.headline || node.name;
                schemaDate     = schemaDate     || node.datePublished;
                schemaDoi      = schemaDoi      || node.identifier?.value || node.sameAs;
                schemaJournal  = schemaJournal  || node.publisher?.name || node.isPartOf?.name;
                if (node.author) {
                    const authorList = Array.isArray(node.author) ? node.author : [node.author];
                    schemaAuthors = authorList.map(a => a.name ?? a).filter(Boolean);
                }
            }
        } catch { /* malformed JSON-LD */ }
    });

    // ── Meta tags ────────────────────────────────────────────────────────────
    const metaGet = (selector) => $(selector).attr('content') ?? null;

    const ogTitle       = metaGet('meta[property="og:title"]');
    const ogDescription = metaGet('meta[property="og:description"]');
    const metaDesc      = metaGet('meta[name="description"]');

    const rawDate =
        schemaDate ||
        metaGet('meta[property="article:published_time"]') ||
        metaGet('meta[name="citation_date"]') ||
        metaGet('meta[name="DC.date"]') ||
        metaGet('meta[name="date"]') ||
        $('time[datetime]').first().attr('datetime') ||
        $('[class*="publish"],[class*="date"],[class*="Date"],[class*="posted"]').first().text().trim() ||
        null;

    // DOI — try multiple extraction points
    const doiCandidates = [
        schemaDoi,
        metaGet('meta[name="citation_doi"]'),
        metaGet('meta[name="DC.Identifier.DOI"]'),
        metaGet('meta[name="dc.identifier"]'),
        $('a[href*="doi.org"]').first().attr('href')?.match(/10\.\d{4,}[^\s"<>]*/)?.[0],
        pageUrl.match(/10\.\d{4,}[^\s"<>]*/)?.[0],
    ];
    const doi = doiCandidates.find(v => v && v.startsWith('10.')) ?? null;

    // Title (priority: schema → og → citation meta → h1 → title tag)
    const citationTitle = metaGet('meta[name="citation_title"]');
    const title =
        schemaTitle || ogTitle || citationTitle ||
        $('h1').first().text().trim() ||
        $('title').text().replace(/\s*[|–\-].*$/, '').trim() ||
        null;

    // Authors
    const citationAuthors = [];
    $('meta[name="citation_author"]').each((_, el) => {
        const v = $(el).attr('content');
        if (v) citationAuthors.push(v);
    });
    const authors =
        schemaAuthors.length ? schemaAuthors :
        citationAuthors.length ? citationAuthors :
        null;

    // Journal
    const journal =
        schemaJournal ||
        metaGet('meta[name="citation_journal_title"]') ||
        metaGet('meta[name="DC.Source"]') ||
        null;

    // Abstract
    const abstract =
        ogDescription || metaDesc ||
        metaGet('meta[name="citation_abstract"]') ||
        $('[class*="abstract"],[id*="abstract"]').first().text().trim().substring(0, 1200) ||
        null;

    // Body text (for word count; cap at 2000 words to keep output small)
    const bodyEl = $('article, main, [role="main"], .content, #content, .body').first();
    const bodyRaw = (bodyEl.length ? bodyEl : $('body')).text().replace(/\s+/g, ' ').trim();
    const bodyText = bodyRaw.split(' ').slice(0, 2000).join(' ');

    // Parse date
    let publishedAt = null;
    if (rawDate) {
        try {
            const parsed = parseDate(rawDate);
            if (parsed?.[0]?.date()) {
                publishedAt = parsed[0].date().toISOString();
            }
        } catch { /* unparseable date */ }
    }

    return { title, publishedAt, doi, authors, journal, abstract, bodyText };
};

// ---------------------------------------------------------------------------
// MAIN
// ---------------------------------------------------------------------------
await Actor.main(async () => {
    const input = await Actor.getInput() ?? {};

    const {
        startUrls       = [],
        articleUrls     = [],
        maxPagesPerDomain = 100,
        maxConcurrency  = 5,
        maxRequestRetries = 3,
        minWords        = MINIMUM_WORDS_DEFAULT,
        dateFrom        = null,
        onlyInside      = true,
        onlyNew         = false,
        saveHtml        = false,
        proxy           = {},
    } = input;

    const dateFromMs = dateFrom ? new Date(dateFrom).getTime() : null;

    // State dataset for deduplication across runs
    const stateDataset = await Actor.openDataset('citation-crawler-state');
    const seenUrls = new Set();
    if (onlyNew) {
        const { itemCount } = await stateDataset.getInfo();
        if (itemCount > 0) {
            const { items } = await stateDataset.getData({ limit: 500000 });
            items.forEach(item => seenUrls.add(item.url));
            log.info(`Dedup state: ${seenUrls.size} previously seen URLs loaded`);
        }
    }

    const requestQueue = await Actor.openRequestQueue();
    const domainEnqueueCount = {};

    // Enqueue crawl-mode start pages
    for (const req of startUrls) {
        await requestQueue.addRequest({
            url: req.url,
            userData: { label: 'FRONT-PAGE' },
        });
    }

    // Enqueue deterministic article URLs directly
    for (const req of articleUrls) {
        await requestQueue.addRequest({
            url: req.url,
            userData: { label: 'ARTICLE', sourceDomain: parseDomain(req.url) },
        });
    }

    // Proxy config
    const proxyConfiguration = proxy?.useApifyProxy
        ? await Actor.createProxyConfiguration({
            groups: proxy.apifyProxyGroups?.length > 0 ? proxy.apifyProxyGroups : undefined,
          })
        : undefined;

    const crawler = new PlaywrightCrawler({
        requestQueue,
        maxConcurrency,
        maxRequestRetries,
        proxyConfiguration,

        async requestHandler({ request, page }) {
            // Wait for JS to render (timeout gracefully — some pages never go fully idle)
            await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
            const loadedUrl = page.url();
            const html      = await page.content();
            const $         = cheerio.load(html);

            // CAPTCHA guard
            if ($('title').text().includes('Attention Required!')) {
                throw new Error(`CAPTCHA detected at: ${request.url}`);
            }

            // ── FRONT-PAGE: discover article links ───────────────────────────
            if (request.userData.label === 'FRONT-PAGE') {
                const loadedDomain = parseDomain(loadedUrl);
                const allLinks     = [];

                $('a[href]').each((_, el) => {
                    const href = $(el).attr('href');
                    if (!href) return;
                    try {
                        allLinks.push(new URL(href, loadedUrl).href);
                    } catch { /* skip malformed */ }
                });

                let links = allLinks;

                // Same-domain filter
                if (onlyInside) {
                    links = links.filter(l => parseDomain(l) === loadedDomain);
                }

                // Dedup filter
                if (onlyNew) {
                    links = links.filter(l => !seenUrls.has(l));
                }

                // Article URL heuristic filter
                const articleLinks = links.filter(isLikelyArticlePage);

                // Per-domain cap
                const capSoFar = domainEnqueueCount[loadedDomain] ?? 0;
                let added = 0;
                for (const url of articleLinks) {
                    if (capSoFar + added >= maxPagesPerDomain) break;
                    await requestQueue.addRequest({
                        url,
                        userData: { label: 'ARTICLE', sourceDomain: loadedDomain },
                    });
                    added++;
                }
                domainEnqueueCount[loadedDomain] = capSoFar + added;

                log.info(
                    `FRONT-PAGE ${loadedUrl}: ${allLinks.length} links → ${articleLinks.length} article candidates → ${added} enqueued`
                );
            }

            // ── ARTICLE: extract metadata + PDF links ────────────────────────
            if (request.userData.label === 'ARTICLE') {
                const sourceDomain = request.userData.sourceDomain ?? parseDomain(request.url);

                const { title, publishedAt, doi, authors, journal, abstract, bodyText }
                    = extractMetadata($, html, loadedUrl);

                const pdfUrls  = extractPdfUrls($, loadedUrl);
                const wordCount = countWords(bodyText);

                // Optional date gate (default: disabled — clinical guidelines are evergreen)
                if (dateFromMs && publishedAt) {
                    const pubMs = new Date(publishedAt).getTime();
                    if (!isNaN(pubMs) && pubMs < dateFromMs) {
                        log.info(`SKIP (pre-dateFrom ${dateFrom}): ${loadedUrl}`);
                        return;
                    }
                }

                // Skip near-empty pages that also have no PDFs
                if (wordCount < minWords && pdfUrls.length === 0) {
                    log.info(`SKIP (${wordCount} words, no PDFs): ${loadedUrl}`);
                    return;
                }

                // Record to state dataset for dedup on future runs
                await stateDataset.pushData({ url: request.url });
                seenUrls.add(request.url);

                const result = {
                    sourceUrl:    request.url,
                    loadedUrl,
                    sourceDomain,
                    loadedDomain: parseDomain(loadedUrl),
                    title:        title ?? null,
                    authors:      authors ?? null,
                    journal:      journal ?? null,
                    publishedAt:  publishedAt ?? null,
                    doi:          doi ?? null,
                    abstract:     abstract ?? null,
                    wordCount,
                    pdfUrls,
                    retrievedAt:  new Date().toISOString(),
                    ...(saveHtml ? { html } : {}),
                };

                log.info(
                    `ARTICLE: "${title ?? '(no title)'}" | PDFs: ${pdfUrls.length} | DOI: ${doi ?? 'none'}`
                );
                await Actor.pushData(result);
            }
        },

        failedRequestHandler({ request, error }) {
            log.error(`Failed (${request.retryCount} retries): ${request.url} — ${error.message}`);
        },
    });

    await crawler.run();

    const { itemCount: outCount } = await (await Actor.openDataset()).getInfo();
    log.info(`Finished. ${outCount} articles saved to dataset.`);
});
