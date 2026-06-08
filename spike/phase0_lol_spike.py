#!/usr/bin/env python3
"""Phase 0 spike — proves the end-to-end LoL pipeline, with no dependencies.

Chain: getSchedule -> getEventDetails -> window feed (reconstruction) ->
frame N vs N-1 diff engine -> normalized events (KILL/TOWER/DRAGON/BARON/INHIB).

Usage: python3 spike/phase0_lol_spike.py [matchId]
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

API = "https://esports-api.lolesports.com/persisted/gw"
FEED = "https://feed.lolesports.com/livestats/v1"
KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"  # known public key (lolesports.com)


# --------------------------------------------------------------------------- I/O
def _get(url, headers=None):
    """Return (status, bytes). Does not decode: the feed returns an empty 204."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def api(path, **params):
    params.setdefault("hl", "en-US")
    _, body = _get(f"{API}/{path}?{urllib.parse.urlencode(params)}", {"x-api-key": KEY})
    return json.loads(body)


def window(game_id, starting_time=None):
    url = f"{FEED}/window/{game_id}"
    if starting_time:
        url += "?startingTime=" + urllib.parse.quote(starting_time)
    try:
        status, body = _get(url)
    except urllib.error.HTTPError as e:
        return {"_error": e.code}
    if status == 204 or not body.strip():  # before the 1st frame OR after the last
        return {"_empty": True}
    return json.loads(body)


# ----------------------------------------------------------------------- time
def parse_ts(ts):
    ts = ts.replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            pass
    raise ValueError(ts)


def round10(dt):  # the feed requires a startingTime that is a multiple of 10 s
    return dt.replace(second=(dt.second // 10) * 10, microsecond=0)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def team(f, side, key, default=0):
    return f.get(side + "Team", {}).get(key, default)


# -------------------------------------------------------------- 1. pick a match
def candidate_matches(forced_id=None):
    """Completed matches, most recent first (not all are covered by the feed:
    the LPL, for example, has no livestats)."""
    if forced_id:
        return [(forced_id, None, "forced")]
    sched = api("getSchedule")["data"]["schedule"]["events"]
    out = []
    for ev in reversed(sched):
        if ev.get("type") == "match" and ev.get("state") == "completed":
            m = ev["match"]
            names = " vs ".join(t["code"] for t in m["teams"])
            out.append((m["id"], ev, f"{ev['league']['name']} — {names}"))
    return out


# ----------------------------------------------- 2-3. rebuild the frames
def reconstruct(game_id, start_iso):
    """Replay the game in 10 s slices.

    The `window?startingTime=T` feed only returns a window of ~10 s, so we
    advance the cursor by 10 s on each call. We keep 1 frame per slice (10 s
    resolution, enough for score + events). 204 = pre-game (before the start)
    or post-game (after the end)."""
    frames, meta = {}, None
    cursor = round10(parse_ts(start_iso)) - timedelta(minutes=5)  # margin before
    started, misses, pre = False, 0, 0
    pregame_max, ingame_max = 45, 320  # ~45 min of searching, ~50 min of play
    for _ in range(pregame_max + ingame_max):
        w = window(game_id, iso(cursor))
        if "_error" in w or "_empty" in w:
            if not started:  # still in pre-game: searching for the start
                pre += 1
                if pre > pregame_max:  # no feed for this game -> give up
                    break
                cursor += timedelta(seconds=60)
                continue
            misses += 1  # gap after the start
            if misses >= 3:  # 3 empty slices in a row = end of the game
                break
            cursor += timedelta(seconds=10)
            continue
        misses, started = 0, True
        meta = meta or w.get("gameMetadata")
        last = w["frames"][-1]  # 1 frame / slice (10 s resolution)
        frames[last["rfc460Timestamp"]] = last
        if last.get("gameState") == "finished":
            break
        cursor = round10(parse_ts(last["rfc460Timestamp"])) + timedelta(seconds=10)
    return frames, meta


# -------------------------------------------------- 4. diff engine -> events
def derive_events(frames):
    ordered = [frames[k] for k in sorted(frames)]
    events, prev = [], None
    for f in ordered:
        if prev is None:
            prev = f
            continue
        ts = f["rfc460Timestamp"]
        score = f"{team(f, 'blue', 'totalKills')}-{team(f, 'red', 'totalKills')}"
        for side in ("blue", "red"):
            dk = team(f, side, "totalKills") - team(prev, side, "totalKills")
            if dk > 0:
                events.append((ts, "KILL", side, f"x{dk}  (score {score})"))
            dt_ = team(f, side, "towers") - team(prev, side, "towers")
            if dt_ > 0:
                events.append((ts, "TOWER", side, f"x{dt_}"))
            db = team(f, side, "barons") - team(prev, side, "barons")
            if db > 0:
                events.append((ts, "BARON", side, f"x{db}"))
            di = team(f, side, "inhibitors") - team(prev, side, "inhibitors")
            if di > 0:
                events.append((ts, "INHIBITOR", side, f"x{di}"))
            pd, cd = team(prev, side, "dragons", []), team(f, side, "dragons", [])
            if isinstance(cd, list) and len(cd) > len(pd or []):
                for d in cd[len(pd or []) :]:
                    events.append((ts, "DRAGON", side, d))
        prev = f
    return events, ordered


# --------------------------------------------------------------------- 5. output
def main():
    forced = sys.argv[1] if len(sys.argv) > 1 else None
    frames = meta = game_id = label = None
    for match_id, ev, lbl in candidate_matches(forced)[:10]:
        detail = api("getEventDetails", id=match_id)["data"]["event"]
        games = detail["match"]["games"]
        g1 = next((g for g in games if g.get("state") == "completed"), games[0])
        start_iso = (ev["startTime"] if ev else detail.get("startTime")) or detail.get("startTime")
        fr, md = reconstruct(g1["id"], start_iso)
        if fr:
            frames, meta, game_id, label = fr, md, g1["id"], lbl
            print(f"== MATCH {match_id}  [{label}]")
            print(f"== GAME {g1['number']} -> id {game_id}  ({len(games)} games)\n")
            break
        print(f".. skip {lbl} (no feed)")
    if not frames:
        raise SystemExit("No recent match with a feed found.")

    # --- draft / picks ---
    if meta:
        print(f"-- DRAFT (patch {meta.get('patchVersion', '?')}) --")
        for side in ("blue", "red"):
            md = meta.get(f"{side}TeamMetadata", {})
            picks = ", ".join(
                f"{p.get('role', '?')}:{p.get('championId', '?')}"
                for p in md.get("participantMetadata", [])
            )
            print(f"  {side:>4} : {picks}")
        print()

    # --- derived events ---
    events, ordered = derive_events(frames)
    t0 = parse_ts(ordered[0]["rfc460Timestamp"])
    print(f"-- {len(ordered)} frames reconstructed | {len(events)} events derived --")
    for ts, typ, side, info in events:
        clock = parse_ts(ts) - t0
        mm, ss = divmod(int(clock.total_seconds()), 60)
        print(f"  {mm:02d}:{ss:02d}  {side:>4}  {typ:<9} {info}")

    # --- final score ---
    last = ordered[-1]
    print(
        f"\n-- FINAL --  kills {team(last, 'blue', 'totalKills')}-{team(last, 'red', 'totalKills')}"
        f" | towers {team(last, 'blue', 'towers')}-{team(last, 'red', 'towers')}"
        f" | gold {team(last, 'blue', 'totalGold')}-{team(last, 'red', 'totalGold')}"
    )
    print("\nOK — pipeline proven end to end.")


if __name__ == "__main__":
    main()
