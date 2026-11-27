#!/usr/bin/env python3
"""meta_kaggle_search.py - find similar past Kaggle competitions and top solutions.

Supports two data engines (pure Python standard library, zero pip dependencies):
  1. Zero-config online/cached index ("farid", default when --data-dir is omitted):
     Fetches and caches faridrashidi/kaggle-solutions (data/competitions.yml, ~1 MB,
     700+ curated competitions with writeup, GitHub code, and notebook links) under
     ~/.cache/kaggle-prior-art/. Works out of the box with no Kaggle API token.
  2. Official Meta Kaggle tables ("meta", default when --data-dir is provided):
     Reads Competitions.csv[.zip], and optionally ForumTopics.csv[.zip] (--solutions),
     CompetitionTags.csv[.zip] + Tags.csv[.zip] (tag recall), and Teams.csv[.zip]
     (historical public/private LB shake-up radar).

Usage examples:
  # Zero-config instant search (no Kaggle token or CSV download needed):
  python3 meta_kaggle_search.py --keywords essay scoring --metric qwk --solutions

  # Offline Meta Kaggle tables search:
  python3 meta_kaggle_search.py --data-dir ~/.cache/kaggle-prior-art/meta \
      --keywords brain eeg --metric kl --since-year 2020 --solutions --shakeup

  # Combine both engines and deduplicate by competition slug:
  python3 meta_kaggle_search.py --source both --data-dir meta/ --keywords tabular --metric auc
"""
import argparse
import contextlib
import csv
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
import zipfile

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FARID_RAW_URL = "https://raw.githubusercontent.com/faridrashidi/kaggle-solutions/main/data/competitions.yml"
DEFAULT_CACHE_DIR = os.path.expanduser(
    os.environ.get("KAGGLE_PRIOR_ART_CACHE", "~/.cache/kaggle-prior-art")
)
CACHE_TTL_SECONDS = 7 * 24 * 3600

COMP_COLS = {
    "id": ["Id"],
    "slug": ["Slug", "CompetitionSlug"],
    "title": ["Title"],
    "subtitle": ["Subtitle"],
    "segment": ["HostSegmentTitle", "HostSegment"],
    "forum_id": ["ForumId"],
    "metric_name": ["EvaluationAlgorithmName"],
    "metric_abbr": ["EvaluationAlgorithmAbbreviation"],
    "deadline": ["DeadlineDate", "Deadline"],
    "teams": ["TotalTeams"],
}
REQUIRED_COMP = ["slug", "title"]
TOPIC_COLS = {
    "id": ["Id"],
    "forum_id": ["ForumId"],
    "title": ["Title"],
    "score": ["Score"],
    "created": ["CreationDate"],
}
COMP_TAG_COLS = {"comp_id": ["CompetitionId"], "tag_id": ["TagId"]}
TAG_COLS = {"id": ["Id"], "name": ["Name"], "slug": ["Slug"]}
TEAM_COLS = {
    "comp_id": ["CompetitionId"],
    "pub_rank": ["PublicLeaderboardRank"],
    "priv_rank": ["PrivateLeaderboardRank"],
}

METRIC_ALIASES = {
    "qwk": ["qwk", "quadratic weighted kappa", "kappa"],
    "kappa": ["kappa", "qwk", "quadratic weighted kappa"],
    "auc": ["auc", "roc auc", "area under"],
    "pauc": ["pauc", "partial auc", "partial area under"],
    "logloss": ["logloss", "log loss", "cross entropy", "crossentropy", "brier"],
    "rmse": ["rmse", "root mean squared error", "root mean squared"],
    "rmsle": ["rmsle", "root mean squared logarithmic"],
    "mcrmse": ["mcrmse", "mean columnwise root mean squared"],
    "mae": ["mae", "mean absolute error"],
    "mape": ["mape", "mean absolute percentage", "smape"],
    "f1": ["f1", "f-score", "fbeta", "macro f1", "micro f1"],
    "dice": ["dice", "sorensen", "iou", "jaccard"],
    "iou": ["iou", "jaccard", "mean iou"],
    "map": ["map", "mean average precision", "map@"],
    "ndcg": ["ndcg", "normalized discounted cumulative gain"],
    "pearson": ["pearson", "spearman", "correlation"],
    "kl": ["kl divergence", "kullback-leibler", "kullback"],
    "wer": ["wer", "word error rate", "cer"],
    "accuracy": ["accuracy", "categorization accuracy", "multiclass loss"],
}

NOISE_SEGMENTS = {"inclass", "community"}
MEDAL_SEGMENTS = {"featured", "research", "masters"}

ORDINAL = r"\b(\d{1,4})\s*(?:st|nd|rd|th)\b"
HASH_OR_RANK = r"(?:(?:#|no\.?\s*|rank\s*)(\d{1,4})\b)"
WORD_PLACE = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
MONTH_ORDINAL_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{1,2}\s*(?:st|nd|rd|th)\b",
    re.I,
)
STAGE_ORDINAL_RE = re.compile(
    r"\b(?:\d{1,2}\s*(?:st|nd|rd|th)|first|second|third)\s+"
    r"(?:stage|level|round|order|step|phase|time|submission|attempt|try)\b",
    re.I,
)
QUESTION_OR_NOISE_RE = re.compile(
    r"\?|"
    r"^(?:when|where|how|why|what|who|any|anyone|looking\s+for|can\s+someone|help)\b|"
    r"\b(?:submission\s+error|scoring\s+error|oom\s+error|bug\s+in|sample\s+solution|"
    r"how\s+to\s+place|question\s+about)\b",
    re.I,
)
STRONG_SOLUTION_RE = re.compile(
    r"\b(?:solution|solutions|write[- ]?up|writeups|winning\s+approach|our\s+approach|"
    r"my\s+approach|gold\s+medal\s+approach)\b",
    re.I,
)
PLACE_CLAIM_RE = re.compile(
    r"(?:\b\d{1,4}\s*(?:st|nd|rd|th)|\b(?:first|second|third|fourth|fifth)|"
    r"(?:#|rank\s*|no\.?\s*)\d{1,4})\s*(?:place\s*)?"
    r"(?:solution|write[- ]?up|approach|overview|summary|notes|code)\b|"
    r"\b(?:winning|winner'?s?)\s+(?:solution|write[- ]?up|approach)\b",
    re.I,
)
PRIVATE_AFTER_RE = re.compile(
    r"\bprivate[^0-9a-z]{0,12}(?:lb[^0-9a-z]{0,12})?(?:#|rank\s*)?(\d{1,4})(?:\s*(?:st|nd|rd|th))?\b",
    re.I,
)
PRIVATE_BEFORE_RE = re.compile(
    r"(?:#|\b)(\d{1,4})\s*(?:st|nd|rd|th)?\s*(?:place\s*)?(?:on\s+|in\s+)?private\b",
    re.I,
)
GENERAL_PLACE_RE = re.compile(
    ORDINAL
    + r"|"
    + HASH_OR_RANK
    + r"|\b(first|second|third|fourth|fifth)\b"
    + r"|\btop[- ]?(\d{1,4})\b(?!\s*%)"
    + r"|\b(winner|winning)\b"
    + r"|\b(gold)\b",
    re.I,
)
SHAKEUP_SLUG_RE = re.compile(r"\b(?:up|down|jumped|shake[- ]?up)[-_ ](\d{2,4})[-_ ]places?\b", re.I)


@contextlib.contextmanager
def open_table(data_dir, name):
    """Yield a text stream for NAME.csv or NAME.csv.zip in data_dir, or None if absent."""
    plain = os.path.join(data_dir, name + ".csv")
    zipped = plain + ".zip"
    if os.path.exists(plain):
        with open(plain, newline="", encoding="utf-8-sig", errors="replace") as f:
            yield f
        return
    if os.path.exists(zipped):
        with zipfile.ZipFile(zipped) as zf:
            member = next((n for n in zf.namelist() if n.lower().endswith(".csv")), None)
            if member is None:
                sys.exit(f"{zipped} contains no CSV")
            with zf.open(member) as raw_member:
                with io.TextIOWrapper(raw_member, encoding="utf-8-sig", errors="replace", newline="") as wrapper:
                    yield wrapper
        return
    yield None


def has_table(data_dir, name):
    if not data_dir:
        return False
    plain = os.path.join(data_dir, name + ".csv")
    return os.path.exists(plain) or os.path.exists(plain + ".zip")


def resolve(header, spec, required, table):
    lower = {h.lstrip("\ufeff").strip().lower(): h for h in header}
    cols = {}
    for key, candidates in spec.items():
        cols[key] = next((lower[c.lower()] for c in candidates if c.lower() in lower), None)
    missing = [k for k in required if cols[k] is None]
    if missing:
        sys.exit(f"{table}: cannot find columns for {missing}. Columns present: {header}")
    return cols


def year_of(s):
    m = re.search(r"(19|20)\d{2}", str(s or ""))
    return int(m.group(0)) if m else None


def to_int(s):
    if s is None:
        return 0
    cleaned = str(s).replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return 0


def clean_for_place(title):
    t = MONTH_ORDINAL_RE.sub(" ", title.lower())
    t = STAGE_ORDINAL_RE.sub(" ", t)
    return t


def place_of(title):
    """Return the finishing place claimed in a thread title, preferring private LB."""
    t = clean_for_place(title)
    if "private" in t:
        m = PRIVATE_AFTER_RE.search(t) or PRIVATE_BEFORE_RE.search(t)
        if m:
            return int(m.group(1))
    m = GENERAL_PLACE_RE.search(t)
    if not m:
        return None
    if m.group(1):
        return int(m.group(1))
    if m.group(2):
        return int(m.group(2))
    if m.group(3):
        return WORD_PLACE[m.group(3).lower()]
    if m.group(4):
        return int(m.group(4))
    if m.group(5):
        return 1
    return 10  # "gold" without an explicit rank


def is_solution_thread(title):
    if not title:
        return False
    stripped = title.strip()
    if QUESTION_OR_NOISE_RE.search(stripped):
        return False
    if PLACE_CLAIM_RE.search(stripped):
        return True
    t = clean_for_place(stripped)
    if not STRONG_SOLUTION_RE.search(t):
        return False
    return place_of(stripped) is not None or bool(
        re.search(r"\b(?:top\s*\d+\s*%|gold|silver|bronze|medal|write[- ]?up|solution)\b", t, re.I)
    )


def tokenize(text):
    norm = re.sub(r"[^a-z0-9+]+", " ", (text or "").lower()).strip()
    return norm, set(norm.split())


def match_keywords(text, keywords):
    norm_text, tokens = tokenize(text)
    matched = []
    for kw in keywords:
        k = kw.lower().strip()
        if not k:
            continue
        k_norm = re.sub(r"[^a-z0-9+]+", " ", k).strip()
        if " " in k_norm:
            if k_norm in norm_text:
                matched.append(kw)
        elif len(k_norm) <= 4:
            if k_norm in tokens or (len(k_norm) >= 3 and (k_norm + "s") in tokens):
                matched.append(kw)
        else:
            if k_norm in norm_text:
                matched.append(kw)
    return matched


def match_metric(metric_text, metric_query):
    if not metric_query:
        return False
    norm_metric, tokens = tokenize(metric_text)
    if not norm_metric:
        return False
    q = metric_query.lower().strip()
    candidates = METRIC_ALIASES.get(q, [q])
    for cand in candidates:
        c_norm = re.sub(r"[^a-z0-9+@]+", " ", cand.lower()).strip()
        if not c_norm:
            continue
        if " " in c_norm or "@" in c_norm:
            if c_norm in metric_text.lower() or c_norm in norm_metric:
                return True
        elif len(c_norm) <= 3:
            if c_norm in tokens:
                return True
        else:
            if c_norm in norm_metric:
                return True
    return False


def classify_match(has_kws, kw_hits, has_metric, metric_hit):
    if has_kws and has_metric:
        if kw_hits and metric_hit:
            return "domain+metric"
        return "domain_only" if kw_hits else "metric_only"
    return "domain_only" if kw_hits else "metric_only"


def compute_score(kw_hits, metric_hit, teams, segment):
    seg_l = (segment or "").strip().lower()
    seg_bonus = 0.5 if seg_l in MEDAL_SEGMENTS else 0.0
    return 2 * len(kw_hits) + (3 if metric_hit else 0) + min(teams, 5000) / 5000 + seg_bonus


def load_meta_tags(data_dir):
    """Return {comp_id: [tag_name, ...]} if CompetitionTags and Tags exist, else {}."""
    if not (has_table(data_dir, "CompetitionTags") and has_table(data_dir, "Tags")):
        return {}
    tag_names = {}
    with open_table(data_dir, "Tags") as f:
        if f is None:
            return {}
        reader = csv.DictReader(f)
        cols = resolve(reader.fieldnames or [], TAG_COLS, ["id", "name"], "Tags.csv")
        for row in reader:
            tid = row.get(cols["id"])
            name = row.get(cols["name"]) or (row.get(cols["slug"]) if cols["slug"] else "")
            if tid and name:
                tag_names[tid] = name.strip()
    comp_tags = {}
    with open_table(data_dir, "CompetitionTags") as f:
        if f is None:
            return {}
        reader = csv.DictReader(f)
        cols = resolve(reader.fieldnames or [], COMP_TAG_COLS, ["comp_id", "tag_id"], "CompetitionTags.csv")
        for row in reader:
            cid = row.get(cols["comp_id"])
            tname = tag_names.get(row.get(cols["tag_id"]))
            if cid and tname:
                comp_tags.setdefault(cid, []).append(tname)
    return comp_tags


def search_meta_competitions(data_dir, keywords, metric, since_year, include_inclass, min_teams, limit):
    with open_table(data_dir, "Competitions") as f:
        if f is None:
            sys.exit(f"Competitions.csv(.zip) not found in {data_dir}")
        comp_tags = load_meta_tags(data_dir)
        reader = csv.DictReader(f)
        cols = resolve(reader.fieldnames or [], COMP_COLS, REQUIRED_COMP, "Competitions.csv")
        hits = []
        for row in reader:
            g = lambda k: (row.get(cols[k]) or "") if cols[k] else ""
            segment = g("segment")
            if not include_inclass and segment.strip().lower() in NOISE_SEGMENTS:
                continue
            teams = to_int(g("teams"))
            if min_teams and teams < min_teams:
                continue
            year = year_of(g("deadline"))
            if since_year and (year is None or year < since_year):
                continue
            cid = g("id")
            tags = comp_tags.get(cid, [])
            searchable = " ".join([g("title"), g("subtitle"), g("slug"), " ".join(tags)])
            kw_hits = match_keywords(searchable, keywords)
            metric_text = f"{g('metric_name')} {g('metric_abbr')}"
            metric_hit = match_metric(metric_text, metric)
            if keywords and not kw_hits and not metric_hit:
                continue
            if metric and not keywords and not metric_hit:
                continue
            score = compute_score(kw_hits, metric_hit, teams, segment)
            slug = g("slug")
            item = {
                "id": cid,
                "slug": slug,
                "title": g("title"),
                "subtitle": g("subtitle"),
                "segment": segment,
                "metric": g("metric_name") or g("metric_abbr"),
                "deadline_year": year,
                "teams": teams,
                "forum_id": g("forum_id"),
                "matched_keywords": kw_hits,
                "metric_match": metric_hit,
                "match_type": classify_match(bool(keywords), kw_hits, bool(metric), metric_hit),
                "relevance": round(score, 3),
                "source": "meta-kaggle",
                "url": f"https://www.kaggle.com/competitions/{slug}",
            }
            if tags:
                item["tags"] = tags
            hits.append(item)
    hits.sort(key=lambda h: (-h["relevance"], -(h["deadline_year"] or 0)))
    return hits[:limit]


def attach_meta_solutions(data_dir, comps, per_comp):
    with open_table(data_dir, "ForumTopics") as f:
        if f is None:
            sys.exit(f"ForumTopics.csv(.zip) not found in {data_dir} (needed for --solutions)")
        by_forum = {c["forum_id"]: c for c in comps if c.get("forum_id")}
        for c in comps:
            c.setdefault("solution_threads", [])
        reader = csv.DictReader(f)
        cols = resolve(reader.fieldnames or [], TOPIC_COLS, ["id", "forum_id", "title"], "ForumTopics.csv")
        for row in reader:
            comp = by_forum.get(row.get(cols["forum_id"]))
            if comp is None:
                continue
            title = row.get(cols["title"]) or ""
            if not is_solution_thread(title):
                continue
            comp["solution_threads"].append({
                "title": title,
                "place": place_of(title),
                "kind": "discussion",
                "votes": to_int(row.get(cols["score"])) if cols["score"] else None,
                "url": f"https://www.kaggle.com/competitions/{comp['slug']}/discussion/{row[cols['id']]}",
            })
    for c in comps:
        c["solution_threads"].sort(
            key=lambda s: (s["place"] is None, s["place"] or 0, -(s.get("votes") or 0))
        )
        c["solution_threads"] = c["solution_threads"][:per_comp]
    return comps


def attach_meta_shakeup(data_dir, comps):
    """Compute historical shake-up risk from Teams.csv if available."""
    if not has_table(data_dir, "Teams"):
        return comps
    by_id = {c["id"]: c for c in comps if c.get("id")}
    if not by_id:
        return comps
    deltas = {cid: [] for cid in by_id}
    with open_table(data_dir, "Teams") as f:
        if f is None:
            return comps
        reader = csv.DictReader(f)
        cols = resolve(reader.fieldnames or [], TEAM_COLS, ["comp_id", "pub_rank", "priv_rank"], "Teams.csv")
        for row in reader:
            cid = row.get(cols["comp_id"])
            if cid not in deltas:
                continue
            priv = to_int(row.get(cols["priv_rank"]))
            pub = to_int(row.get(cols["pub_rank"]))
            if 1 <= priv <= 50 and pub >= 1:
                deltas[cid].append(abs(pub - priv))
    for cid, comp in by_id.items():
        jumps = deltas.get(cid) or []
        if len(jumps) < 5:
            continue
        med_jump = statistics.median(jumps)
        denom = max(comp.get("teams") or 0, max(jumps), 50)
        ratio = round(med_jump / denom, 3)
        risk = "high" if (ratio >= 0.08 or med_jump >= 100) else ("moderate" if (ratio >= 0.025 or med_jump >= 25) else "low")
        comp["shakeup"] = {
            "risk": risk,
            "private_top50_median_rank_delta": round(med_jump, 1),
            "normalized_jump": ratio,
        }
    return comps


def fetch_farid_yaml(cache_dir=DEFAULT_CACHE_DIR, refresh=False, url=FARID_RAW_URL):
    """Return raw YAML string of faridrashidi/kaggle-solutions, using a 7-day local cache."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "farid_competitions.yml")
    if not refresh and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < CACHE_TTL_SECONDS:
            with open(cache_path, encoding="utf-8", errors="replace") as f:
                return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": "kaggle-prior-art-skill"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8", errors="replace") as f:
                return f.read()
        sys.exit(
            f"Cannot fetch online index ({e}) and no local cache at {cache_path}. "
            f"Pass --data-dir with Meta Kaggle CSVs or check network access."
        )


def _unquote(val):
    v = val.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1]
    return v.replace('\\"', '"').strip()


def parse_farid_yaml(yaml_text):
    """Zero-dependency parser for faridrashidi/kaggle-solutions data/competitions.yml."""
    comps = []
    cur_comp = None
    cur_sol = None
    in_solutions = False

    for raw_line in yaml_text.splitlines():
        line = raw_line.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("competitions:"):
            continue
        m_comp_start = re.match(r"^  -\s+([a-zA-Z_]+):\s*(.*)$", line)
        if m_comp_start:
            if cur_comp is not None:
                if cur_sol is not None:
                    cur_comp["solutions"].append(cur_sol)
                    cur_sol = None
                comps.append(cur_comp)
            cur_comp = {"solutions": []}
            in_solutions = False
            cur_comp[m_comp_start.group(1)] = _unquote(m_comp_start.group(2))
            continue
        if cur_comp is None:
            continue
        m_comp_field = re.match(r"^    ([a-zA-Z_]+):\s*(.*)$", line)
        if m_comp_field:
            key, val = m_comp_field.group(1), m_comp_field.group(2)
            if key == "solutions":
                in_solutions = True
            else:
                in_solutions = False
                cur_comp[key] = _unquote(val)
            continue
        if in_solutions:
            m_sol_start = re.match(r"^      -\s+([a-zA-Z_]+):\s*(.*)$", line)
            if m_sol_start:
                if cur_sol is not None:
                    cur_comp["solutions"].append(cur_sol)
                cur_sol = {m_sol_start.group(1): _unquote(m_sol_start.group(2))}
                continue
            m_sol_field = re.match(r"^        ([a-zA-Z_]+):\s*(.*)$", line)
            if m_sol_field and cur_sol is not None:
                cur_sol[m_sol_field.group(1)] = _unquote(m_sol_field.group(2))
                continue

    if cur_comp is not None:
        if cur_sol is not None:
            cur_comp["solutions"].append(cur_sol)
        comps.append(cur_comp)
    return comps


def slug_from_kaggle_url(url):
    m = re.search(r"kaggle\.com/(?:c|competitions)/([^/\s?#]+)", url or "", re.I)
    return m.group(1) if m else (url or "").rstrip("/").split("/")[-1]


def ordinal_str(n):
    if not n:
        return "Top"
    n = int(n)
    suffix = "th" if 11 <= (n % 100) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def title_from_solution_url(url, place, kind):
    tail = (url or "").rstrip("/").split("/")[-1]
    if tail and not tail.isdigit() and "github.com" not in (url or "").lower():
        readable = re.sub(r"[-_]+", " ", tail).strip()
        if len(readable) > 3:
            return readable
    prefix = f"{ordinal_str(place)} place" if place else "Top"
    if kind == "code":
        label = "code repository" if "github.com" in (url or "").lower() else "solution & code"
    elif kind == "kernel":
        label = "notebook"
    else:
        label = "solution writeup"
    return f"{prefix} {label}"


def search_farid_competitions(
    yaml_text, keywords, metric, since_year, include_inclass, min_teams, limit, with_solutions, per_comp
):
    records = parse_farid_yaml(yaml_text)
    hits = []
    for rec in records:
        segment = rec.get("kind", "")
        if not include_inclass and segment.strip().lower() in NOISE_SEGMENTS:
            continue
        teams = to_int(rec.get("team"))
        if min_teams and teams < min_teams:
            continue
        year = year_of(rec.get("year"))
        if since_year and (year is None or year < since_year):
            continue
        link = rec.get("link", "")
        slug = slug_from_kaggle_url(link)
        sol_slug_hints = " ".join(
            (s.get("link") or "").rstrip("/").split("/")[-1].replace("-", " ")
            for s in rec.get("solutions", [])
        )
        searchable = " ".join([rec.get("title", ""), rec.get("desc", ""), slug, segment, sol_slug_hints])
        kw_hits = match_keywords(searchable, keywords)
        metric_str = rec.get("metric", "")
        metric_hit = match_metric(metric_str, metric)
        if keywords and not kw_hits and not metric_hit:
            continue
        if metric and not keywords and not metric_hit:
            continue
        score = compute_score(kw_hits, metric_hit, teams, segment)
        sols = rec.get("solutions", [])
        if sols:
            score += min(len(sols), 10) * 0.05  # slight tie-breaker for rich writeup coverage

        item = {
            "slug": slug,
            "title": rec.get("title", ""),
            "subtitle": rec.get("desc", ""),
            "segment": segment,
            "metric": metric_str,
            "deadline_year": year,
            "teams": teams,
            "prize": rec.get("prize", ""),
            "done": rec.get("done", "").lower() == "true",
            "matched_keywords": kw_hits,
            "metric_match": metric_hit,
            "match_type": classify_match(bool(keywords), kw_hits, bool(metric), metric_hit),
            "relevance": round(score, 3),
            "source": "kaggle-solutions-index",
            "url": f"https://www.kaggle.com/competitions/{slug}" if slug else link,
        }

        shake_jumps = []
        for s in sols:
            m_sh = SHAKEUP_SLUG_RE.search(s.get("link") or "")
            if m_sh:
                shake_jumps.append(int(m_sh.group(1)))
        if shake_jumps:
            max_jump = max(shake_jumps)
            item["shakeup"] = {
                "risk": "high" if max_jump >= 200 else "moderate",
                "writeup_claimed_jump": max_jump,
            }

        if with_solutions:
            threads = []
            code_repos = []
            for s in sols:
                s_link = s.get("link", "")
                if not s_link:
                    continue
                s_kind = (s.get("kind") or "description").lower()
                p = to_int(s.get("rank")) or place_of(s_link)
                threads.append({
                    "title": title_from_solution_url(s_link, p, s_kind),
                    "place": p if (p and p > 0) else None,
                    "kind": s_kind,
                    "votes": None,
                    "url": s_link,
                })
                if "github.com/" in s_link.lower():
                    code_repos.append(s_link)
            threads.sort(key=lambda x: (x["place"] is None, x["place"] or 0, x["kind"] != "description"))
            item["solution_threads"] = threads[:per_comp]
            if code_repos:
                item["github_repos"] = sorted(set(code_repos))
        hits.append(item)

    hits.sort(key=lambda h: (-h["relevance"], -(h["deadline_year"] or 0)))
    return hits[:limit]


def merge_competitions(meta_comps, farid_comps, limit, per_comp):
    by_slug = {}
    for c in meta_comps:
        by_slug[c["slug"].lower()] = dict(c)
    for fc in farid_comps:
        key = fc["slug"].lower()
        if key not in by_slug:
            by_slug[key] = dict(fc)
            continue
        existing = by_slug[key]
        existing["source"] = "meta-kaggle+index"
        existing["relevance"] = max(existing["relevance"], fc["relevance"])
        if not existing.get("metric") and fc.get("metric"):
            existing["metric"] = fc["metric"]
        if fc.get("prize"):
            existing["prize"] = fc["prize"]
        if "shakeup" not in existing and "shakeup" in fc:
            existing["shakeup"] = fc["shakeup"]
        if fc.get("github_repos"):
            existing["github_repos"] = sorted(set(existing.get("github_repos", []) + fc["github_repos"]))
        if "solution_threads" in existing or "solution_threads" in fc:
            seen_urls = {t["url"].rstrip("/").lower() for t in existing.get("solution_threads", [])}
            merged_threads = list(existing.get("solution_threads", []))
            for t in fc.get("solution_threads", []):
                norm_u = t["url"].rstrip("/").lower()
                if norm_u not in seen_urls:
                    merged_threads.append(t)
                    seen_urls.add(norm_u)
            merged_threads.sort(
                key=lambda s: (s["place"] is None, s["place"] or 0, -(s.get("votes") or 0))
            )
            existing["solution_threads"] = merged_threads[:per_comp]
    merged = list(by_slug.values())
    merged.sort(key=lambda h: (-h["relevance"], -(h["deadline_year"] or 0)))
    return merged[:limit]


def summarize_strategy(comps, keywords, metric):
    if not (keywords and metric):
        return "single_axis"
    joint = sum(1 for c in comps if c.get("match_type") == "domain+metric")
    return "direct" if joint >= 2 else "orthogonal_split"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=["auto", "farid", "meta", "both"], default="auto",
                   help="data source: 'farid' (zero-config online/cached index), 'meta' (Meta Kaggle CSVs), or 'both'")
    p.add_argument("--data-dir", help="folder holding Meta Kaggle CSV[.zip] files (Competitions, ForumTopics, etc.)")
    p.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="cache folder for online index")
    p.add_argument("--refresh-cache", action="store_true", help="re-download online index even if cache is fresh")
    p.add_argument("--keywords", nargs="*", default=[], help="words matched against title, subtitle, slug, and tags")
    p.add_argument("--metric", help="metric name or alias, e.g. qwk, auc, logloss, rmse, map, dice, kl")
    p.add_argument("--since-year", type=int, help="only competitions whose deadline/year is in or after this year")
    p.add_argument("--min-teams", type=int, default=0, help="minimum number of participating teams")
    p.add_argument("--include-inclass", action="store_true", help="keep InClass and Community classroom competitions")
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--solutions", action="store_true", help="attach top solution writeups/code links")
    p.add_argument("--shakeup", action="store_true", help="attach historical shake-up risk (uses Teams.csv if present)")
    p.add_argument("--per-comp", type=int, default=10, help="max solution threads per competition")
    a = p.parse_args(argv)
    if not a.keywords and not a.metric:
        p.error("give --keywords and/or --metric")

    source = a.source
    if source == "auto":
        source = "meta" if a.data_dir else "farid"

    meta_comps, farid_comps = [], []
    if source in ("meta", "both"):
        data_dir = a.data_dir or os.path.join(a.cache_dir, "meta")
        meta_comps = search_meta_competitions(
            data_dir, a.keywords, a.metric, a.since_year, a.include_inclass, a.min_teams, a.limit
        )
        if a.solutions and meta_comps:
            meta_comps = attach_meta_solutions(data_dir, meta_comps, a.per_comp)
        if (a.shakeup or a.solutions) and meta_comps:
            meta_comps = attach_meta_shakeup(data_dir, meta_comps)

    if source in ("farid", "both"):
        yaml_text = fetch_farid_yaml(cache_dir=a.cache_dir, refresh=a.refresh_cache)
        farid_comps = search_farid_competitions(
            yaml_text, a.keywords, a.metric, a.since_year, a.include_inclass,
            a.min_teams, a.limit, a.solutions, a.per_comp
        )

    if source == "both":
        comps = merge_competitions(meta_comps, farid_comps, a.limit, a.per_comp)
    elif source == "meta":
        comps = meta_comps
    else:
        comps = farid_comps

    for c in comps:
        c.pop("forum_id", None)
        c.pop("id", None)

    out = {
        "query": {
            "source": source,
            "keywords": a.keywords,
            "metric": a.metric,
            "since_year": a.since_year,
            "min_teams": a.min_teams,
        },
        "search_strategy": summarize_strategy(comps, a.keywords, a.metric),
        "count": len(comps),
        "competitions": comps,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
