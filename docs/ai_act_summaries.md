# AI Act training-content summaries (Art. 53(1)(d)): what developers declare (checked 2026-11-27)

Template: European Commission AI Office, 24 July 2025. Section 2.3 asks for crawler names, collection period and a list of
the top 10% of crawled domain names by content size (5% / 1,000 domains for SMEs). Copies of every document read are in
`data/ai_act_summaries/` (gitignored; `SHA256SUMS`, `RETRIEVED_UTC`), with the site's `robots.txt` of the same day.
Text was searched for "lavanguardia", "vanguardia", "Godó", "Common Crawl", "FineWeb".

| Model (provider) | EU placement | Datasets named | Crawler | Collection period | Domain list | Names LV? |
|---|---|---|---|---|---|---|
| GPT-5.2 (OpenAI) | 11 Dec 2025 | **"text from Common Crawl"** | GPTBot | ~2018 – Aug 2025 | categories only | No |
| GPT-5.5 (OpenAI) | 23 Apr 2026 | **"text from Common Crawl"** | GPTBot | ~2018 – Dec 2025 | categories only | No |
| GPT-6 Astra (OpenAI) | 3 Sep 2026 | **"text from Common Crawl"** | GPTBot | ~Mar 2013 – May 2026 | categories only | No |
| Mistral Large 3 (Mistral) | 2 Dec 2025 | **"Common Crawl"** | not named | up to Jul 2025 | categories only | No |
| DeepSeek-V4 (DeepSeek) | 24 Apr 2026 | **"text from Common Crawl and Stack Exchange"** | not named | not given | no section | No |
| Gemini 3 Pro (Google; aial.ie archive copy, Google URL 404) | Nov 2025 | sectors only | "Google's common crawlers" | knowledge cutoff Jan 2025 | categories only | No |
| Gemma 4 (Google) | Apr 2026 | sectors only (same wording as Gemini 3 Pro) | same | knowledge cutoff Jan 2025 | categories only | No |
| Grok 4.5 / 4.6 (xAI) | 14 Jul / 12 Aug 2026 | "publicly available sources" | xAI Web Crawler | Jan 2024 – Jun 2026 | categories only | No |
| Muse Spark (Meta; aial.ie archive copy) | 4 Aug 2026 | — | refers to Meta's crawler page | up to Jun 2026 | refers to crawler page | No |
| Apertus (Swiss AI) | 2 Sep 2025 | FineWeb family, CC 2013 – CC-MAIN-2024-10, opt-out filtered retrospectively | — | — | — | No (but FineWeb-2 holds 310k LV pages: measured) |
| Apertus v1.5 (Swiss AI) | 2026 | Common Crawl derivatives + custom crawl | custom | 01–04/2026 (own crawl) | — | No |
| Claude models (Anthropic) | — | summaries listed on trust.anthropic.com/resources (Opus 4.7–5.5, Sonnet 5/5.5, Haiku 5.5, Mythos/Fable) but **not retrievable without the portal**; system cards: ClaudeBot, honours robots.txt; "publicly available information from online sources" | ClaudeBot | not read | not read | not read |

Not found: Llama (Meta), Qwen (Alibaba), Salamandra/ALIA (BSC), gpt-oss, older Claude models (aial.ie lists them as missing).

## Findings
1. **No summary names La Vanguardia, or any specific domain**, although the template asks for the top 10% of domains.
   Independent trackers report the same for nearly all summaries (aial.ie; ActuIA, Sep 2026).
2. **OpenAI (GPT-5.2, 5.5, 6 Astra), Mistral (Large 3) and DeepSeek (V4) declare training on Common Crawl text.** We
   measured LV full text in every Common Crawl capture sampled 2019 – March 2026. Combined, this is a documentary link
   (developer's own statement + public, checkable dataset), not proof that LV pages survived their filters.
3. **Collection periods vs LV's opt-out (17 Mar 2026; robots.txt today blocks GPTBot, ClaudeBot, YouBot, Bytespider,
   CCBot).**
   - OpenAI's GPTBot was allowed on news pages until 17 Mar 2026 (2024–26 it was blocked only from film/books);
     GPT-6 Astra's collection runs to May 2026, i.e. past the opt-out (GPTBot blocked then, but earlier copies remain).
   - Anthropic: ClaudeBot was never named before 17 Mar 2026 (the 2024 rule named `anthropic-ai` and `Claude-Web`).
   - **xAI (Jan 2024 – Jun 2026) and Meta (up to Jun 2026): their crawlers are not named in LV's robots.txt even
     today**, and there is no `Google-Extended` rule, no TDMRep file (`/.well-known/tdmrep.json` 404) and no TDM header
     or meta tag on the home page. For these developers LV has no machine-readable reservation at all.
4. The Gemini 3 Pro and Gemma 4 summaries describe the data in the same words, with the same cutoff: consistent with
   a shared data pipeline (relevant to how far a result on Gemma carries to Gemini).

Sources: aial.ie/research/gpai-training-transparency (list of summaries); provider URLs in the PDFs' metadata above:
cdn.openai.com/pdf/…/gpt-5-5-eu-ai-act-public-summary-of-training-content.pdf, gpt-5-2-…, gpt-6-astra-…;
legal.mistral.ai/documents/Mistral Large 3 - Public Summary of Training Content.docx.pdf;
cdn.deepseek.com/policies/DeepSeek_Template_for_the_Public_Summary_of_Training_Content_for_GeneralPurpose_AI_model.pdf;
storage.googleapis.com/transparencyreport/report-downloads/pdf-report-nn_2026-7-31_2026-7-31_en_v1.pdf (Gemma 4);
aial.ie/research/gpai-training-transparency/archive/Gemini_2026_07_21.pdf, …/Muse_Spark_2026_07_21.pdf;
media.x.ai/v1/website/public-summary-of-training-content-for-grok-4.5_8jul2026.docx-fc25014a.pdf (+ 4.6 update);
huggingface.co/swiss-ai/Apertus-70B-2509 (Apertus_EU_Public_Summary.pdf); github.com/swiss-ai/apertus-legal (v1.5).
