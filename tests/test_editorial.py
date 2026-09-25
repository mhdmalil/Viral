from app.services.ai.editorial.bounds import refine_bounds
from app.services.ai.editorial.engine import run_editorial
from app.services.ai.editorial.pool import assign_clusters, one_per_cluster, select_strongest, take_non_overlapping
from app.services.ai.editorial.vibes import filter_wanted_vibes
from app.services.ai.test_backend import TestAIProvider


def test_cluster_keeps_highest_score() -> None:
    rows = [
        {"id": "a", "start": 10, "end": 20, "quality": 0.7},
        {"id": "b", "start": 12, "end": 22, "quality": 0.9},
        {"id": "c", "start": 80, "end": 95, "quality": 0.8},
    ]
    clustered = assign_clusters(rows)
    picked = one_per_cluster(clustered)
    ids = {row["id"] for row in picked}
    assert ids == {"b", "c"}


def test_select_strongest_prefers_hook() -> None:
    rows = [
        {"id": "weak", "start": 10, "end": 20, "quality": 0.95, "hook_score": 0.2},
        {"id": "hook", "start": 80, "end": 95, "quality": 0.7, "hook_score": 0.95},
    ]
    picked = select_strongest(rows, 1)
    assert picked[0]["id"] == "hook"


def test_refine_bounds_snaps_to_utterance() -> None:
    transcript = {
        "segments": [
            {
                "start": 8.0,
                "end": 16.0,
                "text": "Hello there this is the hook.",
                "words": [
                    {"start": 8.0, "end": 8.4, "word": "Hello"},
                    {"start": 8.5, "end": 8.9, "word": "there"},
                    {"start": 9.0, "end": 9.3, "word": "this"},
                    {"start": 9.4, "end": 9.6, "word": "is"},
                    {"start": 9.7, "end": 10.0, "word": "the"},
                    {"start": 10.1, "end": 10.8, "word": "hook."},
                ],
            }
        ]
    }
    span = refine_bounds(9.4, 10.2, transcript, video_duration=20)
    assert span is not None
    assert span["start"] == 8.0
    assert span["end"] - span["start"] >= 8.0
    assert span["end"] >= 16.0


def test_refine_bounds_starts_on_hook_when_marked() -> None:
    transcript = {
        "segments": [
            {
                "start": 8.0,
                "end": 16.0,
                "text": "Hello there this is the hook.",
                "words": [
                    {"start": 8.0, "end": 8.4, "word": "Hello"},
                    {"start": 8.5, "end": 8.9, "word": "there"},
                    {"start": 9.0, "end": 9.3, "word": "this"},
                    {"start": 9.4, "end": 9.6, "word": "is"},
                    {"start": 9.7, "end": 10.0, "word": "the"},
                    {"start": 10.1, "end": 10.8, "word": "hook."},
                ],
            }
        ]
    }
    span = refine_bounds(8.0, 10.8, transcript, hook_at=10.1, video_duration=20)
    assert span is not None
    assert span["start"] == 10.1
    assert span["end"] - span["start"] >= 8.0
    assert span["end"] <= 20.0


def test_refine_bounds_never_under_eight_seconds() -> None:
    span = refine_bounds(1.0, 3.0, {"segments": []}, video_duration=30)
    assert span is not None
    assert span["end"] - span["start"] >= 8.0


def test_refine_bounds_grows_to_a_full_beat() -> None:
    words = []
    t = 8.0
    for i in range(40):
        token = "end." if i in {4, 22, 34} else "word"
        words.append({"start": t, "end": t + 0.3, "word": token})
        t += 0.5
    transcript = {
        "segments": [
            {
                "start": 8.0,
                "end": 28.0,
                "text": "story",
                "words": words,
            }
        ]
    }
    span = refine_bounds(8.0, 10.2, transcript, video_duration=40)
    assert span is not None
    assert span["end"] - span["start"] >= 14.5
    assert span["end"] - span["start"] <= 30.0


def test_refine_bounds_drops_when_source_shorter_than_eight() -> None:
    assert refine_bounds(0.0, 4.0, {"segments": []}, video_duration=5.0) is None


def test_editorial_keeps_distant_moments_not_first_come() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, artifacts = run_editorial(
        transcript,
        provider=TestAIProvider(),
        video_duration=400.0,
        user_max=None,
    )
    assert len(artifacts["seeds"]) >= 2
    assert len(clips) == 2
    starts = [row["start"] for row in clips]
    assert min(starts) < 30
    assert max(starts) > 200


def test_user_max_is_ceiling_not_target() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, _artifacts = run_editorial(
        transcript,
        provider=TestAIProvider(),
        video_duration=400.0,
        user_max=1,
    )
    assert len(clips) == 1


def test_user_max_does_not_invent_extra_clips() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, _artifacts = run_editorial(
        transcript,
        provider=TestAIProvider(),
        video_duration=400.0,
        user_max=15,
    )
    assert len(clips) == 2


def test_wanted_vibes_keeps_only_ticked_kinds() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    none, _ = run_editorial(
        transcript,
        provider=TestAIProvider(),
        video_duration=400.0,
        user_max=None,
        wanted_vibes=["financial"],
    )
    assert none == []
    kept, _ = run_editorial(
        transcript,
        provider=TestAIProvider(),
        video_duration=400.0,
        user_max=None,
        wanted_vibes=["viral"],
    )
    assert len(kept) == 2


def test_mixed_vibes_match_any_ticked_kind() -> None:
    rows = [
        {"id": "mix", "vibes": ["funny", "informative"]},
        {"id": "sad", "vibe": "sad"},
        {"id": "money", "vibes": ["financial", "lifestyle"]},
    ]
    kept = filter_wanted_vibes(rows, ["funny", "financial"])
    assert {row["id"] for row in kept} == {"mix", "money"}
    assert filter_wanted_vibes(rows, []) == rows


def test_take_non_overlapping_keeps_strongest_distinct() -> None:
    rows = [{"id": str(i), "start": i * 20.0, "end": i * 20.0 + 10.0, "quality": 0.9 - i * 0.01} for i in range(20)]
    picked = take_non_overlapping(rows, 15)
    assert len(picked) == 15
    assert [row["id"] for row in picked] == [str(i) for i in range(15)]


def test_select_strongest_caps_at_max() -> None:
    rows = [{"id": str(i), "start": i * 30.0, "end": i * 30.0 + 10.0, "quality": 0.95 - i * 0.001} for i in range(30)]
    picked = select_strongest(rows, 15)
    assert len(picked) == 15
    assert picked[0]["id"] == "0"
    assert all(float(row["quality"]) >= float(rows[14]["quality"]) for row in picked)


def test_select_strongest_returns_fewer_when_few_pass() -> None:
    rows = [
        {"id": "a", "start": 0, "end": 10, "quality": 0.9},
        {"id": "b", "start": 80, "end": 90, "quality": 0.88},
    ]
    assert len(select_strongest(rows, 15)) == 2


def test_select_strongest_keeps_better_duplicate_moment() -> None:
    rows = [
        {"id": "weak", "start": 10, "end": 22, "quality": 0.8, "vibe": "awkward"},
        {"id": "strong", "start": 12, "end": 24, "quality": 0.94, "vibe": "funny"},
    ]
    picked = select_strongest(rows, 15)
    assert [row["id"] for row in picked] == ["strong"]


def test_select_strongest_keeps_close_distinct_clips() -> None:
    rows = [
        {"id": "first", "start": 10, "end": 20, "quality": 0.91, "vibe": "funny"},
        {"id": "second", "start": 22, "end": 32, "quality": 0.9, "vibe": "funny"},
    ]
    picked = select_strongest(rows, 15)
    assert {row["id"] for row in picked} == {"first", "second"}


def test_select_strongest_quality_beats_vibe_diversity() -> None:
    rows = [
        {"id": "a", "start": 0, "end": 10, "quality": 0.95, "vibe": "funny", "topic": "same"},
        {"id": "b", "start": 40, "end": 50, "quality": 0.94, "vibe": "funny", "topic": "same"},
        {"id": "c", "start": 300, "end": 310, "quality": 0.7, "vibe": "awkward", "topic": "other"},
    ]
    picked = select_strongest(rows, 2)
    assert {row["id"] for row in picked} == {"a", "b"}


class _SelectiveKeepProvider(TestAIProvider):
    def editor_json(self, system: str, payload: dict) -> dict:
        kind = str(payload.get("pass") or "")
        if kind == "discovery":
            start = float(payload.get("window_start") or 0)
            end = float(payload.get("window_end") or start + 80)
            candidates = []
            t = start
            while t + 10 <= min(end, start + 90) + 0.01:
                candidates.append(
                    {
                        "start": t,
                        "end": t + 10,
                        "score": 0.82,
                        "reason": "test beat",
                        "topic": "test",
                        "vibe": "viral",
                    }
                )
                t += 16
            return {"candidates": candidates}
        if kind == "select":
            ids = [item.get("id") for item in payload.get("cards") or [] if isinstance(item, dict)]
            return {"keep_ids": ids[:4]}
        return super().editor_json(system, payload)


def test_user_max_takes_strongest_up_to_ceiling() -> None:
    transcript = {
        "duration": 400,
        "text": "long speech later speech",
        "segments": [
            {"start": 0.0, "end": 110.0, "text": "first long speech with many standalone beats."},
            {"start": 240.0, "end": 350.0, "text": "later long speech with many standalone beats."},
        ],
    }
    clips, artifacts = run_editorial(
        transcript,
        provider=_SelectiveKeepProvider(),
        video_duration=400.0,
        user_max=10,
    )
    assert len(artifacts["seeds"]) >= 10
    assert len(clips) == 10
    assert len(clips) <= 10
    funnel = artifacts["funnel"]
    assert funnel["pass1_discovery"] == len(artifacts["seeds"])
    assert funnel["pass4_kept"] == len(artifacts["validated"])
    assert funnel["pass5_selected"] == len(artifacts["selected"])
    assert funnel["pass6_final"] == len(clips)


class _CaptureProvider(TestAIProvider):
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def editor_json(self, system: str, payload: dict) -> dict:
        self.payloads.append(payload)
        return super().editor_json(system, payload)


def test_discovery_payload_omits_clip_count_max() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    provider = _CaptureProvider()
    _clips, _artifacts = run_editorial(
        transcript,
        provider=provider,
        video_duration=400.0,
        user_max=15,
    )
    discovery = [row for row in provider.payloads if row.get("pass") == "discovery"]
    assert discovery
    assert all("clip_count_max" not in row for row in discovery)


def test_discovery_pack_expands_sparse_windows() -> None:
    from app.services.ai.editorial.engine import discovery_pack

    segments = [
        {"start": 330.0, "end": 340.0, "text": "setup before the quiet beat."},
        {"start": 400.0, "end": 404.0, "text": "wow"},
        {"start": 460.0, "end": 470.0, "text": "payoff after the quiet beat."},
    ]
    window = {
        "window_start": 400.0,
        "window_end": 404.0,
        "text": "wow",
        "segments": [segments[1]],
    }
    packed = discovery_pack(segments, window)
    assert packed["context_expanded"] is True
    assert packed["window_start"] == 400.0
    assert packed["window_end"] == 404.0
    assert packed["local_chars"] == 3
    assert "setup before" in packed["context_transcript"]
    assert "payoff after" in packed["context_transcript"]


def test_sparse_window_still_discovers_with_context() -> None:
    transcript = {
        "duration": 800,
        "text": "loud opening. wow. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 20.0, "text": "loud opening story that stands alone with plenty of words for the first window."},
            {"start": 400.0, "end": 404.0, "text": "wow"},
            {"start": 600.0, "end": 620.0, "text": "later payoff story that also stands alone with plenty of words."},
        ],
    }
    provider = _CaptureProvider()
    clips, artifacts = run_editorial(
        transcript,
        provider=provider,
        video_duration=800.0,
        user_max=15,
    )
    sparse = [row for row in provider.payloads if row.get("pass") == "discovery" and row.get("context_expanded")]
    assert sparse
    assert all(row.get("window_start") is not None and row.get("window_end") is not None for row in sparse)
    windows_log = artifacts["pass1_windows"]
    assert any(row["context_expanded"] and row["seeds"] >= 1 for row in windows_log)
    assert len(clips) >= 1


class _MidScoreKeepProvider(TestAIProvider):
    def editor_json(self, system: str, payload: dict) -> dict:
        if payload.get("pass") == "validate":
            results = []
            for item in payload.get("items") or []:
                if not isinstance(item, dict):
                    continue
                results.append(
                    {
                        "id": item.get("id"),
                        "verdict": "keep",
                        "quality": 0.55,
                        "reason": "usable moment",
                    }
                )
            return {"results": results}
        return super().editor_json(system, payload)


def test_pass4_keeps_scores_below_075() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, artifacts = run_editorial(
        transcript,
        provider=_MidScoreKeepProvider(),
        video_duration=400.0,
        user_max=15,
    )
    assert artifacts["pass4_rejected"] == []
    assert len(artifacts["validated"]) == 2
    assert all(float(row["quality"]) == 0.55 for row in artifacts["validated"])
    assert len(clips) == 2


class _RejectOnlyInvalidProvider(TestAIProvider):
    def editor_json(self, system: str, payload: dict) -> dict:
        if payload.get("pass") == "validate":
            results = []
            for item in payload.get("items") or []:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "")
                if item_id.startswith("d0_"):
                    results.append(
                        {
                            "id": item_id,
                            "verdict": "reject",
                            "quality": 0.2,
                            "reason": "dead air fragment",
                        }
                    )
                else:
                    results.append(
                        {
                            "id": item_id,
                            "verdict": "keep",
                            "quality": 0.65,
                            "reason": "usable",
                        }
                    )
            return {"results": results}
        return super().editor_json(system, payload)


def test_pass4_rejects_only_invalid() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, artifacts = run_editorial(
        transcript,
        provider=_RejectOnlyInvalidProvider(),
        video_duration=400.0,
        user_max=None,
    )
    rejected_ids = {row["id"] for row in artifacts["pass4_rejected"]}
    assert any(rid.startswith("d0_") for rid in rejected_ids)
    assert len(clips) == 1
    assert float(artifacts["validated"][0]["quality"]) == 0.65

