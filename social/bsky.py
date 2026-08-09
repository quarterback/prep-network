"""
Compose Bluesky posts from the state's records — and, with credentials, post them.

    python3 -m social.bsky                 # compose and print, nothing sent
    python3 -m social.bsky --limit 5
    python3 -m social.bsky --post          # publish to @varsityapex.com

The account is real (bsky.app/profile/varsityapex.com); the state is not. That
is the demo: results flow records → site and records → feed from the same
canonical store, which is the argument the whole repository makes. Nothing
here invents a result — every post is composed from a tournament or contest
record already on disk, the same records the pages render.

Posting needs an **app password** (Bluesky Settings → Privacy & Security →
App Passwords), supplied as environment, never as an argument and never
committed:

    BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx python3 -m social.bsky --post
    BSKY_HANDLE=varsityapex.com            # optional, this is the default

The transport is two XRPC calls on the stdlib — ``createSession`` then
``createRecord`` per post — because the repository takes no dependencies for
things four lines of urllib can do. Posts go up oldest-composed-last, so the
"tonight" items end up newest in the feed.

The site side is deliberately decoupled: pages fetch the PUBLIC AppView API
from the reader's browser and fall back to a follow card. This module is only
how the account gets something to say.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.request
from itertools import zip_longest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import records_io                                  # noqa: E402
from app.shapes import TournamentFormat, TournamentStatus   # noqa: E402
from app.sports import BY_KEY                               # noqa: E402
from generators.jefferson.gen import TODAY as _CLOCK        # noqa: E402

RECORDS = ROOT / "records"
PDS = "https://bsky.social/xrpc"
DEFAULT_HANDLE = "varsityapex.com"

#: Bluesky's grapheme limit. Composed text stays under it or is cut at a word.
LIMIT = 300


def _nice(day: str) -> str:
    d = dt.date.fromisoformat(day)
    return f"{d.strftime('%A, %B')} {d.day}"


def _when(day: str | None, today: str) -> str:
    if not day:
        return "this week"
    if day == today:
        return "tonight"
    return _nice(day)


def _team(matchup, side: str) -> str:
    school = getattr(matchup, side)
    seed = getattr(matchup, f"{side}_seed")
    return f"No. {seed} {school}" if seed else (school or "TBD")


def _fit(text: str) -> str:
    if len(text) <= LIMIT:
        return text
    return text[: LIMIT - 1].rsplit(" ", 1)[0] + "…"


def compose(records_dir: pathlib.Path, today: str, limit: int) -> list[str]:
    """Postable moments from the records, most newsworthy first.

    Three kinds, in order: live brackets (what a follower opens the app for),
    results from the last few days, and fields that are set but unplayed.
    Champions crowned in the last three weeks would appear ahead of all of it;
    at the May demo clock the winter titles are months old, so that shelf is
    usually empty — the code path matters for other clocks, not this one.
    """
    tournaments = records_io.load_tournaments(records_dir)
    # One round gap back: bracket rounds are a week apart, so a shorter window
    # never contains a result and the feed becomes previews only.
    recent = (dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat()
    crowned = (dt.date.fromisoformat(today) - dt.timedelta(days=21)).isoformat()
    posts: list[str] = []

    champs, live, played, upcoming = [], [], [], []
    for t in sorted(tournaments, key=lambda t: (t.sport, t.group)):
        sport = BY_KEY[t.sport]
        if t.status is TournamentStatus.COMPLETE and t.champion \
                and t.final_date and crowned <= t.final_date <= today:
            champs.append(
                f"{t.champion} are the {t.group} {sport.name} state champions. "
                f"Final: {t.final.home_score}–{t.final.away_score} over "
                f"{t.runner_up}, {_nice(t.final_date)}.")
            continue
        if t.status is TournamentStatus.IN_PROGRESS:
            current = t.current_round()
            if current is None:
                continue
            date = min((m.date for m in current.matchups if m.date), default=None)
            head = (f"{t.group} {sport.name}: {current.name.lower()} "
                    f"{_when(date, today)}.")
            if len(current.matchups) <= 2:
                pairs = " · ".join(f"{_team(m, 'away')} at {_team(m, 'home')}"
                                   for m in current.matchups if not m.bye)
                head = f"{head} {pairs}." if pairs else head
            live.append(head)
            for r in reversed(t.rounds):
                done = [m for m in r.matchups
                        if m.status == "final" and m.winner and not m.bye
                        and m.date and recent <= m.date <= today]
                if not done:
                    continue
                m = done[0]
                loser = m.away if m.winner == m.home else m.home
                ws, ls = ((m.home_score, m.away_score) if m.winner == m.home
                          else (m.away_score, m.home_score))
                nxt = t.rounds[r.index + 1].name.lower() if r.index + 1 < len(t.rounds) else None
                tail = f" — {m.winner} on to the {nxt}" if nxt else ""
                played.append(
                    f"{t.group} {sport.name} {r.name.lower()}: {m.winner} "
                    f"{ws}, {loser} {ls}{tail}.")
                break
            continue
        if t.status is TournamentStatus.UPCOMING and t.start_date \
                and today <= t.start_date:
            start = dt.date.fromisoformat(t.start_date)
            if (start - dt.date.fromisoformat(today)).days <= 10:
                what = ("championship meet" if t.format is TournamentFormat.MEET
                        else f"{t.size}-team bracket")
                upcoming.append(
                    f"The {t.group} {sport.name} field is set — a {what}, "
                    f"opening {_nice(t.start_date)}.")

    # Weave the shelves rather than concatenating them: ten brackets are live
    # at the demo clock, so champs + live + played + upcoming capped at eight
    # is eight identical "semifinals Saturday" previews and the feed reads
    # like a scheduler, not a newsroom.
    posts = champs[:]
    for pair in zip_longest(live, played):
        posts.extend(p for p in pair if p)
    posts.extend(upcoming)
    return [_fit(p) for p in posts[:limit]]


# ────────────────────────────────────────────────────────────────── posting


def _xrpc(method: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(
        f"{PDS}/{method}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def publish(texts: list[str], handle: str, password: str) -> int:
    """Create one ``app.bsky.feed.post`` per text, oldest-composed last.

    ``createdAt`` is the real clock, not the demo clock: the record is "this
    account said this now", and a 2027 timestamp on a real network would be
    a lie about the post rather than fiction about the state.
    """
    session = _xrpc("com.atproto.server.createSession",
                    {"identifier": handle, "password": password})
    sent = 0
    for text in reversed(texts):
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        _xrpc("com.atproto.repo.createRecord",
              {"repo": session["did"], "collection": "app.bsky.feed.post",
               "record": {"$type": "app.bsky.feed.post", "text": text,
                          "createdAt": now, "langs": ["en"]}},
              token=session["accessJwt"])
        sent += 1
        time.sleep(1.0)          # a burst of instant posts reads as a bot spasm
    return sent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="social.bsky")
    ap.add_argument("--records", default=str(RECORDS))
    ap.add_argument("--today", default=_CLOCK.isoformat(),
                    help="the demo clock (default: the generator's)")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--post", action="store_true",
                    help="publish via BSKY_APP_PASSWORD (never a flag, never committed)")
    args = ap.parse_args(argv)

    posts = compose(pathlib.Path(args.records), args.today, args.limit)
    if not posts:
        print("nothing postable at this clock")
        return 0
    for i, p in enumerate(posts, 1):
        print(f"\n[{i}] ({len(p)} chars)\n{p}")

    if not args.post:
        print(f"\n{len(posts)} post(s) composed — dry run. --post publishes them.")
        return 0

    password = os.environ.get("BSKY_APP_PASSWORD")
    if not password:
        print("\nBSKY_APP_PASSWORD is not set; not posting.", file=sys.stderr)
        return 1
    handle = os.environ.get("BSKY_HANDLE", DEFAULT_HANDLE)
    sent = publish(posts, handle, password)
    print(f"\n{sent} post(s) published to @{handle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
