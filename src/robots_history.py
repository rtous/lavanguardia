"""Wayback Machine history of lavanguardia.com/robots.txt: when were AI crawlers blocked?
Usage: curl CDX list -> snaps.json (see PROGRESS.md), then: python -I src/robots_history.py snaps.json GPTBot CCBot ClaudeBot
Assumes monotonic adoption (binary search); verify with spot checks."""
import gzip, json, sys, urllib.request, time, re
snaps = json.load(open(sys.argv[1]))
def txt(ts):
    for i in range(4):
        try:
            raw = urllib.request.urlopen(f"https://web.archive.org/web/{ts}id_/http://www.lavanguardia.com/robots.txt", timeout=60).read(); raw = gzip.decompress(raw) if raw[:2]==b"\x1f\x8b" else raw; return raw.decode('utf-8','replace')
        except Exception as e:
            time.sleep(5)
    return None
def has(t, bot):
    return t is not None and re.search(rf"User-agent:\s*{bot}\s*\n\s*Disallow:\s*/\s*\n", t, re.I) is not None
for bot in sys.argv[2:]:
    lo, hi = 0, len(snaps)-1
    if not has(txt(snaps[hi][0]), bot): print(bot, "not blocked in latest"); continue
    while lo < hi:
        mid = (lo+hi)//2
        if has(txt(snaps[mid][0]), bot): hi = mid
        else: lo = mid+1
    print(bot, "first blocked in snapshot", snaps[lo][0], "previous unblocked", snaps[lo-1][0] if lo else None)
