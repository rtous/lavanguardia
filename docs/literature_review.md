# Literature & case-law review (first pass, 2026-11-24)

## 1. Relevant litigation (what courts have accepted as evidence)

| Case | Jurisdiction | Relevance |
|---|---|---|
| **GEMA v. OpenAI**, LG München I, 42 O 14139/24, judgment 11 Nov 2025 | Germany (EU) | **Closest precedent for us.** Plaintiff showed ChatGPT reproduced 9 song lyrics on simple prompts. Court held that **memorization in the model is a reproduction** (§16 UrhG). Storage as distributed probabilities didn't matter. The TDM exception (Art. 4 DSM Directive) did **not** cover it. Outputs were reproduction plus communication to the public. Evidence method: simple prompts → near-verbatim output. First instance; appeal likely. |
| **NYT v. Microsoft & OpenAI** (S.D.N.Y., consolidated with Daily News etc.) | US | Complaint Exhibit J: ~100 examples of GPT-4 reproducing NYT articles near-verbatim from article openings. OpenAI argued the prompts were "manipulated". Core claims survived (Mar 2025). Discovery: 2026 order to produce ~88M output logs from before the regurgitation filter. Lesson: **prompt design will be attacked**, so keep prompts minimal and pre-registered. |
| **Bartz v. Anthropic** (N.D. Cal.) | US | Training was ruled fair use (Alsup, Jun 2025), but acquiring pirated books was not. $1.5B settlement approved Jul 2026. Output claims preserved. Lesson: **provenance of the training copy matters** (Common Crawl/robots.txt angle). |
| **Kadrey v. Meta** (N.D. Cal.) | US | Fair use for Meta because plaintiffs failed to show market harm. Lesson: a US-style fair-use defense depends on market harm. In the EU the question is the TDM opt-out instead. |
| **Getty v. Stability AI** (UK High Court, 2025) | UK | Watermarks reproduced in outputs were used as evidence of training on Getty images. Analogue for us: unique "fingerprints" in articles. |
| **Folha de S.Paulo v. OpenAI** (Brazil, 2025) | Brazil | A newspaper suit that reportedly ended in a licensing deal. |
| **Prisa–OpenAI license** (2024) | Spain | Shows a market for licensing Spanish press content exists. Useful for damages and market harm. |
| **AMI v. Meta** (Madrid, €550M, 2023) | Spain | GDPR and unfair competition, **not AI**. Shows Spanish publishers litigate collectively. |

Legal hook in the EU/Spain: Art. 4 DSM Directive / art. 67 TRLPI (Spain) TDM exception applies **unless the rightsholder
opted out in a machine-readable way**. La Vanguardia's **robots.txt today blocks GPTBot, ClaudeBot, CCBot, Bytespider**,
and it publishes an `llms.txt` with a legal section. **We need the date the opt-out started** (Wayback Machine
history of robots.txt). Crawling after that date would fall outside the TDM exception.

## 2. Technical methods for detecting training data

| Method | Access needed | Idea | Judge-friendliness |
|---|---|---|---|
| **Verbatim continuation / regurgitation** (NYT Exhibit J; Carlini et al. 2021/2023; Nasr et al. 2023) | Black-box | Give the first N words of an article and ask the model to continue. Measure overlap (longest common substring, ROUGE-L, n-gram match). | ★★★★★ Side-by-side text is self-explanatory |
| **Extraction from production LLMs** (Ahmed, Cooper, Koyejo, Liang, arXiv 2601.02671, Jan 2026) | Black-box (+jailbreak/Best-of-N) | Two-phase prompting extracted near-entire books from Claude 3.7, GPT-4.1, Gemini 2.5, Grok 3 | ★★★★ but jailbreaks invite "manipulation" objections |
| **RECAP** (arXiv 2510.25941) | Black-box | Agentic feedback loop to extract copyrighted text | ★★★ |
| **DE-COP** (Duarte et al., ICML 2024, arXiv 2402.09910) | Black-box | Multiple choice: the verbatim passage vs. 3 paraphrases. Models pick the verbatim one far above the 25% chance rate on seen texts | ★★★★ "It recognizes our exact wording". Has a clean control |
| **Min-K% Prob / Min-K%++** (Shi et al., ICLR 2024; arXiv 2404.02936) | Logprobs | Seen text has fewer very-low-probability tokens | ★★ Needs logprobs (only some APIs or open-weight models) |
| **Dataset inference** (Maini et al., NeurIPS 2024, arXiv 2406.06443) | Logprobs | Aggregates many MIA signals over ~1000 docs into a statistical test with a p-value. Built for **"did you train on my dataset"** | ★★★ Gives a p-value, but needs a well-matched held-out set |
| **Copyright traps / canaries** (Meeus et al., ICML 2024, arXiv 2402.09363) | Requires publishing | Insert unique fictitious sequences into future articles and detect them later | ★★★★★ for the *future*, but useless for past training |
| **Knowledge / "cloze" probes** (name cloze, Chang et al. 2023 "Speak, Memory") | Black-box | Mask a unique detail (quote, name, number) only that article contained, and ask the model to fill it | ★★★★ Good for exclusive content such as interviews and scoops |
| **Style/attribution probes** | Black-box | Ask "which newspaper published: <passage>". Model names La Vanguardia, with date and author | ★★★ Supporting evidence only |
| **RAG/retrieval tests** | Black-box product | With browsing ON, ask about a paywalled article and check whether it reproduces body text and cites lavanguardia.com | ★★★★ Separate claim (current use) |

Known pitfalls (Duan et al. 2024 "Do MIAs work on LLMs?"; Maini et al.): membership inference looks good when
members and non-members differ in **distribution or date**. Controls must be matched on topic, length, section and language,
differing only in the "could have been seen" variable. Using articles from just after the cutoff (same sections and authors)
is the standard fix, and it is still imperfect because topics drift over time.

## 3. Data-availability findings (2026-11-24)
- **Common Crawl contains lavanguardia.com articles**. Spot check: CC-MAIN-2019-09 and CC-MAIN-2023-14 have
  `/internacional/...` article URLs, including archive pieces from 2001–2007. Common Crawl (and C4, RefinedWeb, FineWeb, etc.)
  is in the documented training mix of GPT-3, LLaMA, and others. This gives (a) a **legal source of article text** before
  the licensed corpus arrives, and (b) an independent fact for the judge: the articles sit in the standard training corpus.
- **robots.txt history (Wayback Machine, 3,156 distinct versions 2003–2026):**
  - Until 2024-04-25 no AI crawler is mentioned at all.
  - From **2024-04-25**, GPTBot, Amazonbot, anthropic-ai and Claude-Web are blocked **only from `/peliculas-series/` and `/libros/`**.
    News articles stayed open to them.
  - From **2026-03-17** (between snapshots 20260305213253 and 20260317001452), full `Disallow: /` applies to GPTBot,
    ClaudeBot, CCBot and Bytespider.
  - A 2022 article page captured by Common Crawl (2023) had no TDM-reservation meta or headers, only `robots: index, follow`.
  - **Legal implication (to discuss with counsel):** before March 2026 there was no machine-readable opt-out covering
    news articles. AI firms will argue the EU TDM exception (Art. 4 DSM / art. 67 TRLPI) covered training on them. Counter-arguments:
    (1) GEMA: memorization goes beyond TDM. (2) Terms of use may count as a reservation (cf. Hamburg *Kneschke v. LAION*, 2024).
    (3) Crawling after 2026-03-17 is clearly unreserved-for-AI. **This makes the memorization methods (M1–M3) more important
    than mere proof of crawling.**
