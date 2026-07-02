def compute_stats(problems: dict, schedule: dict, today: str, sessions: list) -> dict:
    """problems: {slug: Problem}. schedule: {"problems": {slug: sm2}, "concepts": {tag: {attempts,cleans}}}.
    Returns a dashboard-ready dict. Pure; no I/O."""
    sp = schedule.get("problems", {})
    concepts = schedule.get("concepts", {})

    def bucket(track=None):
        items = [p for p in problems.values() if track is None or getattr(p, "track", "coding") == track]
        attempted = [p for p in items if p.slug in sp]
        due = [p for p in attempted if sp[p.slug].get("due") and sp[p.slug]["due"] <= today]
        return {"total": len(items), "attempted": len(attempted), "due": len(due)}

    overall = bucket()
    by_track = {"coding": bucket("coding"), "ml": bucket("ml")}

    stages = {"new": 0, "learning": 0, "reviewing": 0}
    ratings = {}
    for p in problems.values():
        st = sp.get(p.slug)
        if not st:
            stages["new"] += 1
            continue
        reps = st.get("repetitions", 0)
        stages["learning" if reps <= 2 else "reviewing"] += 1
        lr = st.get("last_result")
        if lr:
            ratings[lr] = ratings.get(lr, 0) + 1

    concept_rows = []
    for tag, m in concepts.items():
        a, c = m.get("attempts", 0), m.get("cleans", 0)
        concept_rows.append({"tag": tag, "attempts": a, "cleans": c, "rate": (c / a) if a else 0.0})
    concept_rows.sort(key=lambda r: (r["rate"], -r["attempts"]))  # weakest (lowest clean-rate) first

    recent = sorted(sessions, key=lambda s: s.get("timestamp", ""), reverse=True)[:10]
    recent = [{"slug": s.get("slug"), "result": s.get("result"), "timestamp": s.get("timestamp")} for s in recent]

    return {"overall": overall, "by_track": by_track, "stages": stages,
            "ratings": ratings, "concepts": concept_rows, "recent": recent}
