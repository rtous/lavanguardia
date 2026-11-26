"""M10: screening for "La Vanguardia-only" knowledge (cheap triage before costly regurgitation tests).

Idea: ask a model short questions whose answer exists (practically) only on lavanguardia.com. A model that answers
member items (pre-cutoff) clearly better than control items (published after its training-data cutoff) is flagged
as a CANDIDATE for the expensive M1/M9 regurgitation tests. A hit is NOT evidence of training on La Vanguardia by
itself: facts can also come from copies, and knowing facts is not reproducing wording.

Item types (all built deterministically from the Common Crawl articles in data/cc, no LLM involved):
  url_id    Given title, section and date, complete the article URL. The 7-12 digit numeric ID cannot be derived
            from the title; only an exact ID counts. (Structurally exclusive: the ID exists only in LV URLs and links.)
  byline    Given title, section and date, name the author. Generic bylines ("La Vanguardia", "Autor Genérico")
            and La Contra (only 3 interviewers) are excluded. Columnists tied to a topic inflate both sets equally.
  box_title La Contra: given the headline, give the short heading (1-6 words) of the introductory box.
  cloze     La Contra intro box / LV scoop sentences ("según ha podido saber La Vanguardia"...): one number or proper
            noun masked. The masked token must not appear elsewhere in the shown text or title. Interviewees are
            mostly non-famous people, so these details rarely exist outside La Vanguardia.
Exclusivity of cloze answers is checked AFTER the run, only for the items a model gets right (the summary lists
them), e.g. by web search or a FineWeb-2 grep. That is far cheaper than checking every item.

Two prompt styles, chosen by model: chat models get a question ("NO LO SÉ" allowed); local base models (no chat
template) get a plain page they simply continue (prompt ends right before the answer).

Usage:
  python -I src/m10_exclusive_facts.py build [--seed 0]                      -> data/m10/items.jsonl
  python -I src/m10_exclusive_facts.py run --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit [--n 60] [--abstain]
  python -I src/m10_exclusive_facts.py build-outlets                         -> appends other outlets' url_id items
  python -I src/m10_exclusive_facts.py build-qa                              -> appends La Contra Q->A items
  python -I src/m10_exclusive_facts.py summary                               -> results/m10_summary.json
"""
import argparse, glob, hashlib, json, os, random, re, sys, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))

EXP = "m10_exclusive"
ITEMS = "data/m10/items.jsonl"
MEMBER_MAX_DATE = "20231231"   # members: published by end-2023 (before every target model's data cutoff)
CONTROL_MIN_DATE = "20250901"  # controls: after the training-data cutoff of all models tested so far
GENERIC_AUTHORS = {"la vanguardia", "autor generico", "autor genérico", "redaccion", "redacción", "agencias", ""}
SCOOP = re.compile(r"(ha sabido La Vanguardia|ha podido saber|ha tenido acceso La Vanguardia|a los que ha tenido acceso"
                   r"|a la que ha tenido acceso|al que ha tenido acceso|consultad[ao]s por La Vanguardia|explican a La Vanguardia"
                   r"|confirman a La Vanguardia|en declaraciones a La Vanguardia|adelantó La Vanguardia|avanzó La Vanguardia)")
STOP_CAPS = {"La", "El", "Los", "Las", "Un", "Una", "En", "De", "Del", "Y", "Pero", "Por", "Para", "Con", "Es", "Esta", "Este",
             "Dice", "Hoy", "Ahora", "Cuando", "Como", "Si", "No", "Sí", "Se", "Su", "Sus", "Al", "Lo", "Ya", "Hace", "Vanguardia",
             "España", "Barcelona", "Catalunya", "Cataluña", "Madrid", "Europa", "Estados", "Unidos", "Dios", "Contra", "Tras"}
MONTHS = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", s))


def hdate(d):
    return f"{int(d[6:8])} de {MONTHS[int(d[4:6]) - 1]} de {d[:4]}"


def load_articles():
    arts = {}
    for p in sorted(glob.glob("data/cc/*.jsonl")):
        for l in open(p, encoding="utf-8"):
            d = json.loads(l)
            d.setdefault("pub_date", d.get("pub_date_from_url") or "")
            d.setdefault("section", d["url"].split("/")[3])
            d.setdefault("id", d["url"].split("/")[5] if d["url"].count("/") > 5 else "")
            if d["pub_date"] <= MEMBER_MAX_DATE:
                d["set"] = "member"
            elif d["pub_date"] >= CONTROL_MIN_DATE:
                d["set"] = "control"
            else:
                continue
            arts.setdefault(d["url"], {**d, "src_file": os.path.basename(p)})
    return list(arts.values())


def _item(a, typ, answer, **kw):
    it = {"type": typ, "set": a["set"], "url": a["url"], "article_id": a["id"], "section": a["section"],
          "pub_date": a["pub_date"], "title": a["title"], "author": a.get("author"), "src_file": a["src_file"],
          "warc_record_sha256": a.get("warc_record_sha256"), "answer": answer, **kw}
    it["item_id"] = hashlib.sha256(json.dumps([typ, a["url"], answer], ensure_ascii=False).encode()).hexdigest()[:12]
    return it


def mask_candidates(sent, forbidden, strict=False):
    """Numbers and proper nouns (not sentence-initial), absent from the rest of the shown text/title."""
    # a whole run of capitalised words is masked together ("Carles Puigdemont", "Tribunal Constitucional"), so that the
    # other half of a name cannot give the answer away
    cap = r"[A-ZÁÉÍÓÚÑÇ][\wáéíóúñçàèòïü'-]{2,}"
    toks = list(re.finditer(rf"\b(\d[\d\.,]*\d|\d|{cap}(?:\s+(?:de\s+|del\s+|i\s+)?{cap})*)\b", sent))
    out = []
    for m in toks:
        w = m.group(0)
        if m.start() == 0 or w.split()[0] in STOP_CAPS or (w.isdigit() and len(w) == 4 and w.startswith(("19", "20"))):
            continue  # skip sentence-initial words, stop words and bare years (too guessable)
        if strict and not w[0].isdigit() and re.search(r"[\.\?!…:¡¿«\"“(\-–—]\s*$", sent[:m.start()]):
            continue  # strict (Q->A items): a capital after sentence punctuation is not a proper noun
        if any(t in forbidden for t in norm(w).split()) or len(w) < 4 and not w[0].isdigit():
            continue
        rest = sent[:m.start()] + sent[m.end():]
        if any(t in norm(rest).split() for t in norm(w).split()):
            continue
        out.append(m)
    return out


def build(seed):
    rnd = random.Random(seed)
    arts = load_articles()
    items = []
    for a in arts:
        lacontra = a["section"] == "lacontra"
        ident = a["id"] if a["id"].isdigit() else ""
        if ident and not lacontra:
            items.append(_item(a, "url_id", ident, url_prefix=f"https://www.lavanguardia.com/{a['section']}/{a['pub_date']}/"))
        auth = re.sub(r"(?<=[a-záéíóúñçàèòïü])[A-ZÁÉÍÓÚ][a-záéíóúñ]+$", "", (a.get("author") or "").strip())  # "GarcíaMadrid"
        leak = any(t in norm(a["title"]).split() for t in norm(auth).split()[1:])  # "…, por Pedro Nueno"
        if not lacontra and not leak and norm(auth) not in {norm(x) for x in GENERIC_AUTHORS} and len(auth.split()) >= 2:
            items.append(_item(a, "byline", auth))
        lines = [x.strip() for x in a["text"].split("\n") if x.strip()]
        if lacontra and len(lines) > 2 and 1 <= len(lines[0].split()) <= 6 and not lines[0].endswith((".", "?", ":")) \
                and norm(lines[0]) not in norm(a["title"]):
            items.append(_item(a, "box_title", lines[0]))
            # cloze on the intro box (the paragraph right after the box heading)
            intro = lines[1]
            sents = re.split(r"(?<=[\.\?!])\s+", intro)
            forb = set(norm(a["title"] + " " + lines[0] + " " + auth).split())
            for si, s in enumerate(sents[:4]):
                c = mask_candidates(s, forb)
                if c and len(s.split()) >= 8:
                    m = rnd.choice(c)
                    items.append(_item(a, "cloze", m.group(0), subtype="lacontra_intro", box=lines[0],
                                       context=intro[:intro.find(s)] + s[:m.start()] + "____" + s[m.end():],
                                       prefix=intro[:intro.find(s)] + s[:m.start()]))
                    break
        if not lacontra:
            for mm in SCOOP.finditer(a["text"]):
                start = max(a["text"].rfind(". ", 0, mm.start()), a["text"].rfind("\n", 0, mm.start())) + 1
                end = min([x for x in (a["text"].find(". ", mm.end()), a["text"].find("\n", mm.end())) if x > 0] or [len(a["text"])])
                s = a["text"][start:end + 1].strip()
                c = mask_candidates(s, set(norm(a["title"] + " " + auth).split()))
                if c and len(s.split()) >= 10:
                    m = rnd.choice(c)
                    items.append(_item(a, "cloze", m.group(0), subtype="scoop", context=s[:m.start()] + "____" + s[m.end():],
                                       prefix=s[:m.start()]))
                    break
    os.makedirs(os.path.dirname(ITEMS), exist_ok=True)
    rnd.shuffle(items)
    with open(ITEMS, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    c = Counter((it["type"], it.get("subtype", ""), it["set"]) for it in items)
    for k in sorted(c):
        print(k, c[k])
    print("items:", len(items), "sha256:", hashlib.sha256(open(ITEMS, "rb").read()).hexdigest())


def build_outlets():
    """Append url_id items for other newspapers (same-period control, see src/m10_outlet_ids.py). Appended, not
    reshuffled, so the La Vanguardia items selected by `run --n` stay the same for models already tested."""
    have = {json.loads(l)["item_id"] for l in open(ITEMS, encoding="utf-8")}
    new = []
    for p in sorted(glob.glob("data/m10/outlet_*.jsonl")):
        if p.endswith("_ids.jsonl"):
            continue
        for a in map(json.loads, open(p, encoding="utf-8")):
            a["set"] = "member" if a["pub_date"] <= MEMBER_MAX_DATE else "control" if a["pub_date"] >= CONTROL_MIN_DATE else None
            if not a["set"]:
                continue
            a["src_file"] = os.path.basename(p)
            it = _item(a, "url_id", a["id"], subtype=a["outlet"], outlet_name=a["outlet_name"], url_prefix=a["url_prefix"],
                       url_rest_hint=a["url_rest_hint"])
            if it["item_id"] not in have:
                new.append(it)
    random.Random(0).shuffle(new)
    with open(ITEMS, "a", encoding="utf-8") as f:
        for it in new:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(Counter((it["subtype"], it["set"]) for it in new), "appended:", len(new))


def qa_pairs(text):
    """La Contra body: line 0 = box heading, line 1 = intro, then interviewer lines (short, often questions) each
    followed by the interviewee's answer."""
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    pairs = []
    for i in range(2, len(lines) - 1):
        q, ans = lines[i], lines[i + 1]
        if len(q.split()) <= 25 and len(ans.split()) >= 12 and (q.endswith("?") or len(q.split()) <= 12):
            pairs.append((i, q, ans))
    return lines, pairs


def build_qa(seed=0):
    """Append 'qa' items (La Contra): given headline, date, box heading, intro and one interviewer question, what did the
    interviewee answer? The answer must contain a specific fact (number or proper-noun span) that appears nowhere in
    what the model is shown. One item per interview. Appended, so earlier items keep their order."""
    rnd = random.Random(seed)
    have = {json.loads(l)["item_id"] for l in open(ITEMS, encoding="utf-8")}
    new = []
    for a in load_articles():
        if a["section"] != "lacontra":
            continue
        lines, pairs = qa_pairs(a["text"])
        if len(lines) < 4 or not (1 <= len(lines[0].split()) <= 6):
            continue
        box, intro = lines[0], lines[1]
        cands = []
        for i, q, ans in pairs:
            shown = norm(" ".join([a["title"], box, intro, q, a.get("author") or ""])).split()
            facts = mask_candidates(ans, set(shown), strict=True)
            facts = [m for m in facts if not any(t in shown for t in norm(m.group(0)).split())]
            if facts:
                cands.append((i, q, ans, facts))
        if not cands:
            continue
        i, q, ans, facts = rnd.choice(cands)
        f = rnd.choice(facts).group(0)
        it = _item(a, "qa", f, subtype="lacontra", box=box, intro=intro, question=q, true_answer=ans,
                   prev="\n".join(lines[2:i]))
        if it["item_id"] not in have:
            new.append(it)
            have.add(it["item_id"])
    rnd.shuffle(new)
    with open(ITEMS, "a", encoding="utf-8") as fo:
        for it in new:
            fo.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(Counter(it["set"] for it in new), "qa items appended")


# ---------------------------------------------------------------- prompts
# Default (triage): ask for a best guess, so recall is maximal; the control set measures what guessing alone achieves.
# --abstain allows "NO LO SÉ" instead (more conservative wording, fewer hits).
NOSE = "Si no estás seguro, da igualmente tu mejor respuesta, sin explicaciones."
NOSE_ABSTAIN = "Si no lo sabes con seguridad, responde exactamente NO LO SÉ."


def chat_prompt(it, abstain=False):
    NOSE_ = NOSE_ABSTAIN if abstain else NOSE
    when = f"publicado el {hdate(it['pub_date'])}"
    if it["type"] == "url_id":
        paper = it.get("outlet_name", "La Vanguardia")
        rest = it.get("url_rest_hint", "el identificador numérico")
        return (f"¿Cuál es la URL exacta del artículo de {paper} «{it['title']}», {when} en la sección «{it['section']}»? "
                f"Empieza por {it['url_prefix']} y sigue con {rest}. Responde solo con la URL completa. {NOSE_}")
    if it["type"] == "qa":
        return (f"En la entrevista de La Contra de La Vanguardia titulada «{it['title']}» ({when}), con el recuadro "
                f"«{it['box']}» y esta presentación: «{it['intro']}»\n\nEl periodista pregunta: «{it['question']}»\n"
                f"¿Qué respondió exactamente el entrevistado? Reproduce su respuesta tal como se publicó, con sus datos "
                f"concretos (nombres, cifras, lugares). {NOSE_}")
    if it["type"] == "byline":
        return (f"¿Quién firmó el artículo de La Vanguardia «{it['title']}», {when} en la sección «{it['section']}»? "
                f"Responde solo con el nombre y apellidos del autor. {NOSE_}")
    if it["type"] == "box_title":
        return (f"En la entrevista de La Contra de La Vanguardia titulada «{it['title']}» ({when}), el texto de presentación "
                f"del entrevistado va encabezado por un breve titular de 1 a 6 palabras. ¿Cuál era ese titular? "
                f"Responde solo con el titular. {NOSE_}")
    where = (f"la entrevista de La Contra de La Vanguardia «{it['title']}» ({when}), en el texto de presentación"
             if it["subtype"] == "lacontra_intro" else f"el artículo de La Vanguardia «{it['title']}» ({when})")
    return (f"En {where}, se lee: «{it['context']}»\n¿Qué palabra, nombre o cifra exacta falta en el hueco ____? "
            f"Responde solo con ella. {NOSE_}")


def raw_prompt(it):
    head = f"{it.get('outlet_name', 'La Vanguardia')} · {it['section']} · {hdate(it['pub_date'])}\n{it['title']}\n"
    if it["type"] == "url_id":
        return head + f"Enlace permanente: {it['url_prefix']}"
    if it["type"] == "byline":
        return head + "Autor:"
    if it["type"] == "qa":
        return (f"La Vanguardia · La Contra · {hdate(it['pub_date'])}\n{it['title']}\n\n{it['box']}\n{it['intro']}\n"
                f"{it['question']}\n")
    if it["type"] == "box_title":
        return f"La Vanguardia · La Contra · {hdate(it['pub_date'])}\n{it['title']}\n\n"
    if it["subtype"] == "lacontra_intro":
        return f"La Vanguardia · La Contra · {hdate(it['pub_date'])}\n{it['title']}\n\n{it['box']}\n{it['prefix']}"
    return head + "\n[...] " + it["prefix"]


# ---------------------------------------------------------------- scoring
def score(it, gen, raw):
    g = gen.strip()
    dontknow = bool(re.search(r"no lo s[ée]|no (lo )?conozco|no tengo (acceso|informaci)|no dispongo|no puedo", g, re.I))
    if it["type"] == "url_id":
        ids = re.findall(r"\d{6,}", g if raw else g.replace(it["url_prefix"], " "))
        if raw:  # first token of the continuation: "<ID>/slug" (LV) or "slug-<ID>" (El Periódico)
            ids = re.findall(r"\d{6,}", (g.split() or [""])[0])
        hit = it["answer"] in ids
        near = any(abs(int(x) - int(it["answer"])) <= 1000 and len(x) == len(it["answer"]) for x in ids)
        return {"hit": hit, "near_id_1000": near and not hit, "dontknow": dontknow and not ids, "pred": ids[:3]}
    if it["type"] == "qa":
        out = g.split("\n")[0] if raw else g  # base models: the answer paragraph only
        ans = norm(it["answer"]).split()
        pred = norm(out).split()
        hit = any(pred[i:i + len(ans)] == ans for i in range(len(pred)))
        # soft score: share of the true answer's content words (>=6 letters, not in what was shown) that the model produced
        shown = set(norm(" ".join([it["title"], it["box"], it["intro"], it["question"]])).split())
        content = {t for t in norm(it["true_answer"]).split() if len(t) >= 6 and t not in shown}
        ov = len(content & set(pred)) / len(content) if content else None
        a_, b_ = pred, norm(it["true_answer"]).split()
        lcs = SequenceMatcher(None, a_, b_, autojunk=False).find_longest_match(0, len(a_), 0, len(b_)).size
        return {"hit": hit, "content_overlap": round(ov, 3) if ov is not None else None, "lcs_words": lcs,
                "dontknow": dontknow and not hit, "pred": out[:120]}
    if it["type"] == "byline":
        line = g.split("\n")[0] if raw else g
        a = norm(it["answer"]).split()
        pl = norm(line).split()
        # first name AND every surname must appear ("Martínez" alone is not a hit for "Alberto Martínez")
        hit = all(t in pl for t in a if t not in ("de", "del", "la", "i", "y"))
        return {"hit": hit, "dontknow": dontknow, "pred": line[:80]}
    if it["type"] == "box_title":
        line = (g.split("\n")[0] if raw else g).strip(" «»\"“”'*")
        r = SequenceMatcher(None, norm(line), norm(it["answer"])).ratio()
        return {"hit": norm(line) == norm(it["answer"]), "ratio": round(r, 3), "fuzzy_hit": r >= 0.8,
                "dontknow": dontknow, "pred": line[:80]}
    ans = norm(it["answer"]).split()
    pred = norm(g).split()[:max(3, len(ans) + 2)] if raw else norm(g).split()
    hit = any(pred[i:i + len(ans)] == ans for i in range(len(pred)))
    return {"hit": hit, "dontknow": dontknow and not hit, "pred": g[:80]}


def is_raw(model):
    """Local base models (no chat template) are continued as plain text."""
    return "/" in model and not re.search(r"instruct|chat|-it\b|-it-", model, re.I)


def run(model, n, types, workers, abstain=False):
    from probe import ask
    items = [json.loads(l) for l in open(ITEMS, encoding="utf-8")]
    raw = is_raw(model)
    out = f"results/m10_exclusive_{model.split('/')[-1]}{'_abstain' if abstain else ''}.jsonl"
    # resume: items with an API error (e.g. quota) are retried; the failed attempt stays in the evidence log
    done = {r["item_id"] for r in map(json.loads, open(out)) if not r.get("api_error")} if os.path.exists(out) else set()
    per = defaultdict(int)
    todo = []
    for it in items:  # items file is already shuffled: take the first n per (type, subtype, set)
        k = (it["type"], it.get("subtype", ""), it["set"])
        if types and it["type"] not in types or per[k] >= n:
            continue
        per[k] += 1
        if it["item_id"] not in done:
            todo.append(it)
    print(f"{model}: {len(todo)} items to run (raw={raw})", flush=True)

    def one(it):
        prompt = raw_prompt(it) if raw else chat_prompt(it, abstain)
        mt = (120 if it["type"] == "qa" else 24) if raw else (300 if it["type"] == "qa" else 80)
        text, rec = ask(EXP, model, prompt, max_tokens=mt, raw=raw,
                        meta={"item_id": it["item_id"], "type": it["type"], "set": it["set"], "url": it["url"]})
        s = score(it, text, raw)
        return {"item_id": it["item_id"], "type": it["type"], "subtype": it.get("subtype", ""), "set": it["set"],
                "url": it["url"], "answer": it["answer"], "model": model, "model_reported": rec["model_reported"],
                "style": "raw" if raw else ("chat-abstain" if abstain else "chat-guess"), "prompt": prompt, "gen": text, "evidence_sha256": rec["sha256"],
                "api_error": rec["stop_reason"] == "api_error", **s}

    import concurrent.futures as cf
    w = 1 if "/" in model else workers
    with open(out, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(w) as ex:
        for i, r in enumerate(ex.map(one, todo)):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if r["hit"]:
                print(f"  HIT [{r['set']}] {r['type']}: {r['answer']!r} <- {r['gen'][:80]!r}", flush=True)
            if i % 50 == 49:
                print(f"  {i + 1}/{len(todo)}", flush=True)


def fisher_greater(a, b, c, d):
    from scipy.stats import fisher_exact
    return fisher_exact([[a, b], [c, d]], alternative="greater")[1]


def _ord(d):
    import datetime as dt
    return dt.date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal()


def id_to_date_fn():
    """LV's 7-8 digit article IDs (used from late 2020) grow with time (~3,000/day). Interpolating over the real
    (ID, date) pairs of our corpus converts any predicted ID into the date it corresponds to; |that date - true date|
    is a judge-friendly error ("the model's number points to a day N days away"). Older 11-12 digit IDs are skipped."""
    import datetime as dt
    import numpy as np
    tables = {"": [(int(a["id"]), _ord(a["pub_date"])) for a in load_articles() if a["id"].isdigit() and len(a["id"]) in (7, 8)]}
    for p in glob.glob("data/m10/outlet_*_ids.jsonl"):  # other outlets: (ID, date) pairs from the Common Crawl index
        name = os.path.basename(p)[len("outlet_"):-len("_ids.jsonl")]
        tables[name] = [(int(r["id"]), _ord(r["pub_date"])) for r in map(json.loads, open(p)) if r["pub_date"] >= "2015"]
    fit = {}
    for k, pts in tables.items():
        pts = sorted(set(pts))
        fit[k] = (np.array([q[0] for q in pts]), np.maximum.accumulate(np.array([q[1] for q in pts])))

    def err_days(pred, true, pub_date, outlet=""):
        if outlet == "" and len(true) not in (7, 8) or not pred:
            return None
        ids, days = fit[outlet]
        x = int(pred)
        if not ids[0] <= x <= ids[-1]:
            return 9999  # outside the range of real IDs (e.g. post-cutoff controls extrapolated wrongly)
        return abs(float(np.interp(x, ids, days)) - _ord(pub_date))
    return err_days


def summary():
    import statistics
    err_days = id_to_date_fn()
    res = {}
    for p in sorted(glob.glob("results/m10_exclusive_*.jsonl")):
        rows = [json.loads(l) for l in open(p)]
        rows = list({r["item_id"]: r for r in rows if not r.get("api_error")}.values())  # one row per item
        items = {it["item_id"]: it for it in map(json.loads, open(ITEMS, encoding="utf-8"))}
        for r in rows:  # re-score from the stored raw output, so scorer fixes apply to earlier runs
            r.update(score(items[r["item_id"]], r["gen"], r["style"] == "raw"))
        model = os.path.basename(p)[len("m10_exclusive_"):-len(".jsonl")]
        by = defaultdict(lambda: {"member": [0, 0, 0, 0], "control": [0, 0, 0, 0]})  # hits, n, dontknow, near-id
        hits = []
        for r in rows:
            r.setdefault("near_id_1000", False)
            keys = [f"{r['type']}{'/' + r['subtype'] if r['subtype'] else ''}"]
            if not (r["type"] == "url_id" and r["subtype"]):  # other outlets are a separate control, not pooled
                keys.append("ALL")
            for k in keys:
                by[k][r["set"]][0] += r["hit"]
                by[k][r["set"]][1] += 1
                by[k][r["set"]][2] += r.get("dontknow", False)
                by[k][r["set"]][3] += r.get("near_id_1000", False)
            if r["hit"]:
                hits.append({k: r[k] for k in ("set", "type", "subtype", "answer", "gen", "url", "item_id")})
        tab = {}
        for k, v in sorted(by.items()):
            (hm, nm, dm, zm), (hc, nc, dc, zc) = v["member"], v["control"]
            tab[k] = {"member": f"{hm}/{nm}", "control": f"{hc}/{nc}",
                      "rate_member": round(hm / nm, 3) if nm else None, "rate_control": round(hc / nc, 3) if nc else None,
                      "dontknow_member": dm, "dontknow_control": dc, "near_id_member": zm, "near_id_control": zc,
                      "p_fisher_member_gt_control": round(fisher_greater(hm, nm - hm, hc, nc - hc), 4) if nm and nc else None}
        dates = {}
        for outlet in sorted({r["subtype"] for r in rows if r["type"] == "url_id"}):
            idx = {}
            for st in ("member", "control"):
                e = [err_days(r["pred"][0] if r["pred"] else None, r["answer"], items[r["item_id"]]["pub_date"], outlet)
                     for r in rows if r["type"] == "url_id" and r["subtype"] == outlet and r["set"] == st]
                e = [x for x in e if x is not None]
                if e:
                    idx[st] = {"n": len(e), "median_err_days": round(statistics.median(e), 1),
                               "within_1_day": sum(x <= 1 for x in e), "within_7_days": sum(x <= 7 for x in e),
                               "within_30_days": sum(x <= 30 for x in e)}
            if "member" in idx and "control" in idx:
                m_, c_ = idx["member"], idx["control"]
                idx["p_fisher_within_7d"] = float("%.2e" % fisher_greater(m_["within_7_days"], m_["n"] - m_["within_7_days"],
                                                                         c_["within_7_days"], c_["n"] - c_["within_7_days"]))
            dates[outlet or "lavanguardia"] = idx
        idx = dates.get("lavanguardia", {})
        tab["url_id_date_error"] = dates
        flag = tab.get("ALL", {}).get("p_fisher_member_gt_control")
        res[model] = {"style": rows[0]["style"] if rows else None, "table": tab,
                      "flag_candidate": bool(flag is not None and flag < 0.05 or idx.get("p_fisher_within_7d", 1) < 0.05),
                      "hits_to_verify_exclusivity": [h for h in hits if h["set"] == "member" and h["type"] in ("cloze", "box_title")],
                      "all_hits": hits}
        print(f"\n== {model} ({res[model]['style']})  candidate={res[model]['flag_candidate']}")
        for o, v in dates.items():
            print(f"  url_id as date [{o}]: " + "  ".join(f"{st}: median {v[st]['median_err_days']}d, <=7d {v[st]['within_7_days']}/{v[st]['n']}"
                                                      for st in ("member", "control") if st in v) + f"  p={v.get('p_fisher_within_7d')}")
        for k, v in tab.items():
            if k == "url_id_date_error":
                continue
            print(f"  {k:24s} member {v['member']:>8s}  control {v['control']:>8s}  p={v['p_fisher_member_gt_control']}"
                  f"  (no-sé {v['dontknow_member']}/{v['dontknow_control']})")
    json.dump(res, open("results/m10_summary.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "build-outlets", "build-qa", "run", "summary"])
    ap.add_argument("--model")
    ap.add_argument("--n", type=int, default=60, help="max items per (type, subtype, set)")
    ap.add_argument("--types", nargs="*", default=[])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--abstain", action="store_true", help='allow "NO LO SÉ" (chat models)')
    a = ap.parse_args()
    {"build": lambda: build(a.seed), "build-outlets": build_outlets, "build-qa": lambda: build_qa(a.seed), "run": lambda: run(a.model, a.n, a.types, a.workers, a.abstain), "summary": summary}[a.cmd]()
