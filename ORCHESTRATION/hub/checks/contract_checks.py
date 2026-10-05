"""Independent contract checks for the Music Hub (04_VISUAL_CONTRACT.md, 06_EXPECTED_OUTCOMES.md).

Written by the orchestrator as part of the locked plan. The building agent must NOT edit this file;
if a check is wrong, raise it in LEDGER.md and the orchestrator changes it (07 change log).

Usage:  python contract_checks.py <check-id> [<check-id> ...]      exit 0 = all pass
Env:    HUB_URL (default http://127.0.0.1:8790), HUB_WORKSPACE_ROOT (default: two levels above the
        Toolshop repo, i.e. D:\\Projects), HUB_PY (default: Toolshop .venv python).
Stdlib only. ASCII literals only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]                      # code under test: master checkout OR the lane worktree
WS = Path(os.environ.get("HUB_WORKSPACE_ROOT", REPO.parent))
PARENT = WS / "Music-AI-Toolshop"           # the data the hub indexes always comes from the main checkout
URL = os.environ.get("HUB_URL", "http://127.0.0.1:8790").rstrip("/")
_VENV = [REPO / ".venv" / "Scripts" / "python.exe", PARENT / ".venv" / "Scripts" / "python.exe"]
PY = os.environ.get("HUB_PY", str(next((v for v in _VENV if v.exists()), _VENV[-1])))
CSS = REPO / "toolshop" / "hub" / "static" / "hub.css"
TOKENS_SRC = PARENT / "MAirina_Tucc" / "rimer-ui" / "src" / "index.css"
CODE_ENV = dict(os.environ, PYTHONPATH=str(REPO))   # make subprocesses import the code under test
KINDS = {"commit", "pointer_bump", "session", "handoff", "ledger_update", "listen_verdict",
         "inbox_opened", "inbox_resolved", "inbox_reopened", "changelog"}
INBOX_KINDS = {"decision", "ear_test", "sign_off", "provide_input", "run_on_signal", "review"}


class Fail(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Fail(msg)


# ---------- tiny DOM ----------
class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.text = tag, dict(attrs), parent, [], ""

    def all_text(self):
        return (self.text + " ".join(c.all_text() for c in self.children)).strip()

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


class Dom(HTMLParser):
    VOID = {"meta", "link", "br", "img", "input", "hr", "source", "col", "area", "base", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [], None)
        self.cur = self.root
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.text += data

    def sections(self, sid):
        return [n for n in self.root.walk() if n.attrs.get("data-section") == sid]

    def one(self, sid):
        s = self.sections(sid)
        need(len(s) >= 1, f"missing data-section={sid}")
        return s[0]


# ---------- http / git ----------
def get(path, base=None):
    with urllib.request.urlopen((base or URL) + path, timeout=60) as r:
        return r.status, r.read().decode("utf-8", "replace")


def post(path, body, origin, base=None):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request((base or URL) + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "Origin": origin})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout


def repos():
    out = [PARENT]
    gm = (PARENT / ".gitmodules").read_text(encoding="utf-8-sig")
    out += [PARENT / m for m in re.findall(r"^\s*path\s*=\s*(.+?)\s*$", gm, re.M)]
    return [r for r in out if (r / ".git").exists()]


def home():
    st, html = get("/")
    need(st == 200, f"GET / -> {st}")
    return Dom(html)


# ---------- checks ----------
def c_tokens():
    need(CSS.exists(), f"missing {CSS}")
    src = TOKENS_SRC.read_text(encoding="utf-8").lower()
    css = CSS.read_text(encoding="utf-8").lower()
    allowed = set(re.findall(r"#[0-9a-f]{6}\b", src))
    need(len(allowed) >= 20, "token source parse failed")
    used = set(re.findall(r"#[0-9a-f]{6}\b", css))
    for name in ["bg", "panel", "ink", "muted", "line", "accent", "accent-ink", "ok", "warn", "bad", "chip", "focus"]:
        vals_src = re.findall(r"--%s:\s*(#[0-9a-f]{6})" % re.escape(name), src)
        vals_css = re.findall(r"--%s:\s*(#[0-9a-f]{6})" % re.escape(name), css)
        need(vals_src[:2] == vals_css[:2], f"token --{name}: css {vals_css[:2]} != source {vals_src[:2]}")
    need(used <= allowed, f"hex colors outside token set: {sorted(used - allowed)}")
    need("prefers-color-scheme: dark" in css or "prefers-color-scheme:dark" in css, "no dark-mode block")


def c_s0_header():
    d = home()
    h = d.one("s0_header")
    need("Music Hub" in h.all_text(), "header title")
    links = [n.attrs.get("href") for n in h.walk() if n.tag == "a" and n.attrs.get("href", "").startswith("/")]
    need("/" in links and "/journal" in links, f"nav links {links}")
    for href in links:
        need(get(href)[0] == 200, f"nav link {href} not 200 (only existing views may be linked)")


def c_s0a_health():
    d = home()
    t = d.one("s0a_health").all_text()
    need(re.search(r"Indexed .+ \u00b7 \d+/\d+ sources", t), f"freshness copy: {t!r}")
    need("Refresh" in t, "Refresh button")


def c_s0b_degraded():
    st, body = get("/api/health")
    need(st == 200, "/api/health")
    bad = [c for c in json.loads(body)["collectors"] if c["status"] != "ok"]
    b = home().one("s0b_degraded")
    if bad:
        need("hidden" not in b.attrs and "degraded" in b.all_text(), "banner must show degraded sources")
    else:
        need("hidden" in b.attrs, "banner must be hidden when all ok")


def _open_items():
    st, body = get("/api/inbox?state=open")
    need(st == 200, "/api/inbox")
    return json.loads(body)


def c_s1_inbox():
    items = _open_items()
    d = home()
    s = d.one("s1_inbox")
    need("Waiting on you" in s.all_text(), "heading")
    cards = [n for n in s.walk() if n.attrs.get("data-section") == "s1a_item"]
    if not items:
        need("Nothing waiting on you." in s.all_text(), "empty state copy")
        return
    cnt = [n for n in s.walk() if "data-count" in n.attrs]
    need(cnt and int(cnt[0].attrs["data-count"]) == len(items), "count badge != open items")
    exp = sorted(items, key=lambda i: (-len(i.get("blocking") or []), i["created_ts"]))[:6]
    need([c.attrs.get("data-id") for c in cards] == [i["id"] for i in exp], "card order/limit wrong")


def c_s1a_item():
    for c in home().sections("s1a_item"):
        need(c.attrs.get("data-kind") in INBOX_KINDS, f"bad kind {c.attrs.get('data-kind')}")
        t = c.all_text()
        need("opened" in t and "Resolve" in t and "Snooze" in t, f"card copy: {t[:80]!r}")
        need(re.fullmatch(r"\d+", c.attrs.get("data-blocking", "")), "data-blocking")


def c_inbox_roundtrip():
    """Separate server on :8791 with a temp data dir: ask -> visible -> resolve via UI API -> agent reads it."""
    tmp = tempfile.mkdtemp(prefix="hubcheck_")
    env = dict(CODE_ENV, TOOLSHOP_DATA_DIR=tmp)
    base = "http://127.0.0.1:8791"
    srv = subprocess.Popen([PY, "-m", "toolshop.hub", "serve", "--port", "8791"], cwd=str(REPO), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(180):
            try:
                if get("/api/health", base)[0] == 200:
                    break
            except Exception:
                time.sleep(1)
        else:
            raise Fail("test server on 8791 did not come up")
        p = subprocess.run([PY, "-m", "toolshop.hub", "ask", "--title", "contract roundtrip probe",
                            "--kind", "review", "--lane", "hub", "--by", "agent:contract-check"],
                           cwd=str(REPO), env=env, capture_output=True, text=True, timeout=60)
        need(p.returncode == 0, f"ask failed: {p.stderr[-300:]}")
        iid = p.stdout.strip().splitlines()[-1].strip()
        need(iid.startswith("inb_"), f"ask did not print id: {p.stdout!r}")
        need(iid in get("/", base)[1], "asked item not on Home")
        st, _ = post(f"/api/inbox/{iid}/resolve", {"answer": "ok-from-check"}, "http://127.0.0.1:8791", base)
        need(st == 200, f"resolve -> {st}")
        p = subprocess.run([PY, "-m", "toolshop.hub", "list", "--resolved-since", "2000-01-01T00:00:00Z", "--json"],
                           cwd=str(REPO), env=env, capture_output=True, text=True, timeout=60)
        rows = json.loads(p.stdout)
        need(any(r["id"] == iid and r.get("answer") == "ok-from-check" for r in rows), "agent cannot read answer")
        lines = Path(tmp, "hub", "inbox.jsonl").read_text(encoding="utf-8").splitlines()
        need(len(lines) == 2 and '"op": "open"' in lines[0].replace('"op":"open"', '"op": "open"'),
             "inbox.jsonl must hold exactly open+resolve lines (append-only)")
    finally:
        srv.terminate()


def _rows(path="/"):
    return Dom(get(path)[1]).sections("s2c_row")


def c_s2_journal():
    rows = _rows()
    ts = [r.attrs.get("data-ts", "") for r in rows]
    need(ts == sorted(ts, reverse=True), "journal not newest-first")
    need(len(rows) <= 100, "home journal > 100 rows")
    st, body = get("/api/events?days=7&limit=100")
    need(st == 200, "/api/events")
    api = json.loads(body)
    need(len(rows) == min(100, len(api)), f"rendered {len(rows)} rows, api has {len(api)}")
    if not rows:
        need("No activity in the last 7 days." in get("/")[1], "empty copy")


def c_s2a_filters():
    d = home()
    f = d.one("s2a_filters")
    t = f.all_text()
    for s in ("All lanes", "All repos", "All kinds"):
        need(s in t, f"filter default {s}")
    need(any(n.tag == "input" and n.attrs.get("placeholder") == "Search titles" for n in f.walk()), "search input")
    lanes = sorted({r.attrs.get("data-lane") for r in _rows("/journal") if r.attrs.get("data-lane")})
    if lanes:
        sub = _rows(f"/journal?lane={lanes[0]}")
        need(sub and all(r.attrs.get("data-lane") == lanes[0] for r in sub), "lane filter leaks other lanes")


def c_s2c_row():
    for r in _rows("/journal"):
        need(r.attrs.get("data-kind") in KINDS, f"kind {r.attrs.get('data-kind')}")
        tm = [n for n in r.walk() if n.tag == "time"]
        need(tm and re.fullmatch(r"\d\d:\d\d", tm[0].all_text()), "time HH:MM")
        if r.attrs.get("data-kind") in ("pointer_bump", "ledger_update"):
            need("muted" in r.attrs.get("class", ""), "pointer/ledger rows must be .muted")


_HASH = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{7,12}(?![0-9a-fA-F])")


def _independent_receipt(text):
    """Re-implementation of 03 Receipts, kept independent from toolshop/hub/receipts.py."""
    states = []
    for h in sorted(set(_HASH.findall(text))):
        if not (re.search(r"\d", h) and re.search(r"[a-f]", h)):
            continue
        found = None
        for r in repos() + [WS / "ai_dev_meta_layer", WS]:
            if git(r, "cat-file", "-e", h + "^{commit}")[0] == 0:
                found = r
                break
        emph = re.search(r"`" + h + r"|(commit|merged|pushed|hash)\W{1,3}" + h, text, re.I)
        if found is None:
            if emph:
                states.append("missing")
            continue
        states.append("pushed" if git(found, "branch", "-r", "--contains", h)[1].strip() else "local")
    for s in ("missing", "local", "pushed"):
        if s in states:
            return s
    return "none"


def c_receipts():
    """API-level: hub receipt status == independent re-computation, on >= 5 real documents."""
    st, body = get("/api/events?kind=session&limit=100000")
    evs = json.loads(body)
    st, body = get("/api/events?kind=handoff&limit=100000")
    evs += json.loads(body)
    need(evs, "no session/handoff events")
    evs.sort(key=lambda e: e["ts_utc"], reverse=True)
    checked = 0
    for e in evs[:15]:
        need(e.get("receipt_status") in ("pushed", "local", "missing", "none"), f"status {e.get('receipt_status')}")
        link = e.get("link", "")
        if link.startswith("file:"):
            text = (WS / link[5:]).read_text(encoding="utf-8", errors="replace")
            mine = _independent_receipt(text)
            need(mine == e["receipt_status"], f"receipt mismatch on {link}: hub={e['receipt_status']} check={mine}")
            checked += 1
    need(checked >= 5, f"only {checked} receipts cross-checked")


def c_s2d_receipt():
    """Page-level: every session/handoff row carries a badge with a valid data-state matching the API."""
    rows = _rows("/journal")
    for r in rows:
        badges = [n for n in r.walk() if n.attrs.get("data-section") == "s2d_receipt"]
        if r.attrs.get("data-kind") in ("session", "handoff"):
            need(len(badges) == 1, f"row {r.attrs.get('data-id')} lacks receipt badge")
            need(badges[0].attrs.get("data-state") in ("pushed", "local", "missing", "none"), "badge data-state")
        else:
            need(not badges, f"receipt badge on non-claim row {r.attrs.get('data-id')}")


def c_origin_guard():
    st, _ = post("/api/refresh", {}, "http://evil.example")
    need(st == 403, f"foreign Origin POST -> {st}, expected 403")
    st, _ = post("/api/refresh", {}, URL)
    need(st in (200, 202), f"same-origin refresh -> {st}")


def c_no_mutation():
    before = {str(r): git(r, "status", "--porcelain")[1] for r in repos()}
    st, _ = post("/api/refresh", {}, URL)
    need(st in (200, 202), "refresh")
    after = {str(r): git(r, "status", "--porcelain")[1] for r in repos()}
    diff = [r for r in before if before[r] != after[r]]
    need(not diff, f"repo status changed during index (or a live lane wrote meanwhile - re-run): {diff}")


def c_s3_repos():
    d = Dom(get("/lanes")[1])
    rows = [n for n in d.one("s3_repos").walk() if "data-repo" in n.attrs]
    need(len(rows) >= len(repos()), "repo rows missing")
    for n in rows[:3]:
        name = n.attrs["data-repo"]
        r = PARENT if name in ("Music-AI-Toolshop", "parent") else PARENT / name
        out = git(r, "status", "--porcelain")[1].splitlines()
        mod = sum(1 for l in out if not l.startswith("??"))
        unt = sum(1 for l in out if l.startswith("??"))
        need(int(n.attrs["data-modified"]) == mod and int(n.attrs["data-untracked"]) == unt,
             f"{name}: page M{n.attrs['data-modified']}/U{n.attrs['data-untracked']} vs git M{mod}/U{unt}")


def c_s3a_marker():
    f = WS / ".workspace_archive" / "orchestration" / "ACTIVE"
    d = Dom(get("/lanes")[1])
    m = d.one("s3a_marker")
    if not f.exists():
        need("Orchestrator mode: off" in m.all_text(), "marker off copy")
        return
    n = sum(1 for l in f.read_text(encoding="utf-8").splitlines() if l.startswith("override:"))
    need(len(d.sections("s3a_override")) == n, f"override count page != file ({n})")


def c_s4b_profile():
    prof = json.loads((PARENT / "studio" / "voice_profiles" / "tale.json").read_text(encoding="utf-8"))
    d = Dom(get("/artists/tale")[1])
    card = d.one("s4b_profile")
    rows = {n.attrs["data-field"]: n.all_text() for n in card.walk() if "data-field" in n.attrs}
    need("f0_mean_hz" in rows, "f0_mean_hz row")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rows["f0_mean_hz"])]
    need(any(abs(x - prof["target"]["f0_mean_hz"]) <= 0.5 for x in nums), f"f0 mean shown {rows['f0_mean_hz']!r}")
    de = rows.get("de_esser_threshold_db", "")
    need("linear" in de and "dB" not in de, f"de-esser must read linear, not dB: {de!r}")


def c_s4c_chainmaps():
    files = sorted((PARENT / "studio" / "artists" / "tale").rglob("chain_map*.svg"))
    st, html = get("/artists/tale")
    d = Dom(html)
    figs = d.sections("s4c_map")
    need(len(figs) == len(files), f"maps on page {len(figs)} != files {len(files)}")
    need("<script" not in html.lower().split('data-section="s4c_chainmaps"', 1)[-1], "script inside chain-map area")


def c_health():
    st, body = get("/api/health")
    need(st == 200, f"/api/health -> {st}")
    j = json.loads(body)
    need("collectors" in j and "indexed_at" in j, f"health keys {sorted(j)}")


def c_host_refusal():
    p = subprocess.run([PY, "-m", "toolshop.hub", "serve", "--host", "0.0.0.0", "--port", "8799"], cwd=str(REPO), env=CODE_ENV,
                       capture_output=True, text=True, timeout=60)
    need(p.returncode != 0, "serve must refuse a non-loopback host")


def c_collectors_ok():
    st, body = get("/api/health")
    bad = [c for c in json.loads(body)["collectors"] if c["status"] != "ok"]
    need(not bad, f"collectors not ok: {[(c['name'], c['status'], c.get('error')) for c in bad]}")


def _cfg():
    return json.loads((REPO / "toolshop" / "hub" / "hub_config.json").read_text(encoding="utf-8"))


def _music(path, kws):
    head = " ".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]).lower()
    return any(k.lower() in head for k in kws)


def c_counts():
    """Independent reconciliation of indexed events against the sources (refreshes first)."""
    st, _ = post("/api/refresh", {}, URL)
    need(st in (200, 202), "refresh")
    cfg = _cfg()

    def ids(kind):
        return {e["id"] for e in json.loads(get(f"/api/events?kind={kind}&limit=1000000")[1])}

    want = set()
    for r in repos():
        out = git(r, "log", "--all", "--since=%d.days" % cfg["horizon_days"], "--format=%H")[1]
        want |= {h.strip() for h in out.splitlines() if h.strip()}
    have = {i.split(":", 1)[1] for i in ids("commit") | ids("pointer_bump")}
    need(have == want, f"commits: hub {len(have)} vs git {len(want)}; missing {sorted(want - have)[:5]} extra {sorted(have - want)[:5]}")
    pat = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{6}_.+|session_record_\d{8}_.+)\.md$")
    sess = {p.name for p in WS.glob(cfg["sessions_glob"]) if pat.match(p.name) and _music(p, cfg["music_keywords"])}
    got = {i.split(":", 1)[1] for i in ids("session")}
    need(got == sess, f"sessions: hub {len(got)} vs files {len(sess)}; diff {sorted(sess ^ got)[:5]}")
    hand = {p.name for p in WS.glob(cfg["handoffs_glob"]) if _music(p, cfg["music_keywords"])}
    got = {i.split(":", 1)[1] for i in ids("handoff")}
    need(got == hand, f"handoffs: hub {len(got)} vs files {len(hand)}; diff {sorted(hand ^ got)[:5]}")
    n = 0
    for f in (WS / cfg["audition_comments_dir"]).glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                if "ts_utc" in json.loads(line):
                    n += 1
            except ValueError:
                pass
    got = len(ids("listen_verdict"))
    need(got == n, f"listen verdicts: hub {got} vs lines {n}")


def c_file_guard():
    try:
        st, _ = get("/file?path=../../Windows/win.ini")
    except urllib.error.HTTPError as e:
        st = e.code
    need(st == 404, f"path outside workspace -> {st}, expected 404")
    need(get("/file?path=Music-AI-Toolshop/README.md")[0] == 200, "workspace file not served")


def c_s0a_pills():
    st, body = get("/api/repos")
    need(st == 200, "/api/repos")
    rs = json.loads(body)
    dirty = sum(1 for r in rs if (r.get("modified") or 0) + (r.get("untracked") or 0) > 0)
    ahead = sum((r.get("ahead") or 0) for r in rs)
    t = home().one("s0a_health").all_text()
    if dirty:
        need(f"{dirty} dirty" in t, f"dirty pill != {dirty}: {t!r}")
    else:
        need("dirty" not in t, "dirty pill shown at 0")
    if ahead:
        need(f"{ahead} unpushed" in t, f"unpushed pill != {ahead}: {t!r}")
    marker = WS / ".workspace_archive" / "orchestration" / "ACTIVE"
    ov = marker.exists() and any(l.startswith("override:") for l in marker.read_text(encoding="utf-8").splitlines())
    need(("guard overridden" in t) == bool(ov), "guard pill mismatch")


def c_skill_path():
    s = (WS / "ai_dev_meta_layer" / ".windsurf" / "skills" / "mix_svg_tree" / "SKILL.md").read_text(encoding="utf-8")
    need("artists/" in s, "mix_svg_tree SKILL.md does not mention artists/<name>/rounds/")
    need("ORCHESTRATION/<song>/" not in s, "stale ORCHESTRATION/<song>/ path still in mix_svg_tree")


def _local_date(iso):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Belgrade")).date()


def c_s2b_day():
    """Every row sits under the day header of its local (Europe/Belgrade) date; today's header starts 'Today'."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Belgrade")).date()
    d = Dom(get("/journal")[1])
    current = None
    seen = 0
    for n in d.root.walk():
        sec = n.attrs.get("data-section")
        if sec == "s2b_day":
            current = n.all_text()
        elif sec == "s2c_row":
            need(current is not None, "row before any day header")
            day = _local_date(n.attrs["data-ts"])
            label = day.strftime("%a %d %b").replace(" 0", " ")
            need(label in current, f"row {n.attrs.get('data-id')} ({label}) under header {current!r}")
            if day == today:
                need(current.startswith("Today"), f"today's header must start with 'Today': {current!r}")
            seen += 1
    need(seen > 0 or "No activity" in d.root.all_text(), "no rows and no empty state")


def c_s5_inbox_full():
    st, body = get("/api/inbox?state=all")
    need(st == 200, "/api/inbox?state=all")
    items = json.loads(body)
    opn = [i for i in items if i["state"] == "open"]
    res = [i for i in items if i["state"] == "resolved"]
    d = Dom(get("/inbox")[1])
    d.one("s5_inbox_full")
    need(len(d.sections("s1a_item")) == len(opn), f"/inbox open cards {len(d.sections('s1a_item'))} != {len(opn)}")
    rows = d.sections("s5_resolved_row")
    need(len(rows) == len(res), f"/inbox resolved rows {len(rows)} != {len(res)}")
    if not res:
        need("Nothing resolved yet." in d.root.all_text(), "empty history copy")


def c_s3b_lanes():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    rows = [n for n in Dom(get("/lanes")[1]).one("s3b_lanes").walk() if "data-lane" in n.attrs]
    need(rows, "no lane rows")
    for n in rows:
        st = n.attrs.get("data-status")
        need(st in ("active", "quiet", "dormant"), f"lane {n.attrs['data-lane']} status {st}")
        age_h = (now - datetime.fromisoformat(n.attrs["data-last-ts"].replace("Z", "+00:00"))).total_seconds() / 3600
        exp = "active" if age_h <= 48 else ("quiet" if age_h <= 14 * 24 else "dormant")
        need(st == exp, f"lane {n.attrs['data-lane']}: {st} but last event {age_h:.0f} h ago -> {exp}")


def _artist_dirs():
    return sorted(p.parent.name for p in (PARENT / "studio" / "artists").glob("*/ARTIST.md"))


def c_s4_artist_grid():
    cards = Dom(get("/artists")[1]).sections("s4_artist_card")
    need(sorted(c.attrs.get("data-artist") for c in cards) == _artist_dirs(),
         f"artist cards {[c.attrs.get('data-artist') for c in cards]} != dirs {_artist_dirs()}")


def c_s4a_songs():
    md = (PARENT / "studio" / "artists" / "tale" / "ARTIST.md").read_text(encoding="utf-8")
    table = [l for l in md.splitlines() if l.startswith("|")]
    need(len(table) >= 3 and "song" in table[0].lower(), "tale songs table not found")
    body = [l for l in table[2:] if l.strip("| -")]
    rows = Dom(get("/artists/tale")[1]).sections("s4a_song")
    need(len(rows) == len(body), f"song rows {len(rows)} != table rows {len(body)}")
    for r in rows:
        need(r.attrs.get("data-source-exists") in ("0", "1"), "data-source-exists")


def c_s4e_ledgers():
    files = sorted((PARENT / "studio" / "artists" / "tale" / "ledgers").glob("*.md"))
    rows = Dom(get("/artists/tale")[1]).sections("s4e_ledger")
    need(len(rows) == len(files), f"ledger rows {len(rows)} != files {len(files)}")


CHECKS = {k[2:]: v for k, v in globals().items() if k.startswith("c_")}


def main(argv):
    ids = argv[1:] or sorted(CHECKS)
    bad = 0
    for cid in ids:
        fn = CHECKS.get(cid)
        if fn is None:
            print(f"UNKNOWN {cid}")
            bad += 1
            continue
        try:
            fn()
            print(f"PASS {cid}")
        except Fail as e:
            print(f"FAIL {cid}: {e}")
            bad += 1
        except Exception as e:  # server down, file missing, ...
            print(f"ERROR {cid}: {type(e).__name__}: {e}")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
