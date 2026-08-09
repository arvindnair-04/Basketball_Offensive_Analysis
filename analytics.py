from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
SHOTS_PATH = ROOT / "data" / "season_aggregates" / "SPAIN_2024-2025_shots_offense.csv"
PICKS_PATH = ROOT / "data" / "season_aggregates" / "SPAIN_2024-2025_picks_offense.csv"
GLOSSARY_PATH = ROOT / "data" / "glossary" / "metric_glossary.csv"

ZONE_CONFIG = {
    "Rim": ("rim_attempts", "rim_mades", "rim_fg_percentage", 2),
    "Short mid / paint": (
        "short_midrange_paint_attempts",
        "short_midrange_paint_mades",
        "short_midrange_paint_fg_percentage",
        2,
    ),
    "Long mid-range": (
        "long_midrange_attempts",
        "long_midrange_mades",
        "long_midrange_fg_percentage",
        2,
    ),
    "Three": ("zone_three_attempts", "zone_three_mades", "zone_three_fg_percentage", 3),
}

FIT_PRESETS = {
    "Primary creator": {
        "description": "On-ball volume, pick-and-roll creation, pull-up efficiency, and scoring load.",
        "weights": {
            "handler_volume_percentile": 0.25,
            "handler_creation_percentile": 0.35,
            "shot_volume_percentile": 0.20,
            "off_dribble_efg_percentile": 0.20,
        },
        "confidence": ["shooting_reliability", "handler_reliability"],
    },
    "Floor spacer": {
        "description": "Three-point willingness, shooting accuracy, and catch-and-shoot performance.",
        "weights": {
            "three_volume_percentile": 0.35,
            "three_accuracy_percentile": 0.35,
            "catch_shoot_efg_percentile": 0.30,
        },
        "confidence": ["shooting_reliability"],
    },
    "Rim pressure": {
        "description": "Rim frequency, finishing, free-throw pressure, and sustainable shot volume.",
        "weights": {
            "rim_rate_percentile": 0.30,
            "rim_finish_percentile": 0.30,
            "ft_rate_percentile": 0.20,
            "shot_volume_percentile": 0.20,
        },
        "confidence": ["shooting_reliability"],
    },
    "Screen-and-roll big": {
        "description": "Screening workload, points created per screen, success, and rim finishing.",
        "weights": {
            "screener_volume_percentile": 0.30,
            "screener_creation_percentile": 0.40,
            "rim_finish_percentile": 0.30,
        },
        "confidence": ["shooting_reliability", "screener_reliability"],
    },
    "Versatile scorer": {
        "description": "Efficiency, balanced shot diet, shot-making, pressure response, and volume.",
        "weights": {
            "shot_efficiency_percentile": 0.25,
            "shot_versatility_percentile": 0.20,
            "shotmaking_percentile": 0.20,
            "pressure_resilience_percentile": 0.15,
            "shot_volume_percentile": 0.20,
        },
        "confidence": ["shooting_reliability"],
    },
}


@dataclass
class DataBundle:
    shots: pd.DataFrame
    picks: pd.DataFrame
    profiles: pd.DataFrame
    glossary: pd.DataFrame
    quality: dict[str, int | float | str]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    return numerator.div(denominator.where(denominator.ne(0)))


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _add_percentile(
    frame: pd.DataFrame,
    source: str,
    output: str,
    eligible: pd.Series,
    *,
    higher_is_better: bool = True,
) -> None:
    frame[output] = np.nan
    mask = eligible.fillna(False) & frame[source].notna()
    values = frame.loc[mask, source]
    if values.empty:
        return
    ranking_values = values if higher_is_better else -values
    frame.loc[mask, output] = ranking_values.rank(method="average", pct=True)


def _sample_reliability(volume: pd.Series, appearances: pd.Series, scale: float) -> pd.Series:
    volume_component = 1 - np.exp(-pd.to_numeric(volume, errors="coerce").fillna(0) / scale)
    game_component = np.sqrt(pd.to_numeric(appearances, errors="coerce").fillna(0).clip(0, 30) / 30)
    return (100 * volume_component * game_component).clip(0, 100)


def engineer_shooting(raw: pd.DataFrame) -> pd.DataFrame:
    required = {
        "player_id", "player_name", "team_name", "appearances", "attempts", "mades",
        "total_points", "two_mades", "three_mades", "three_attempts", "ft_attempts",
        "ft_mades", "efg_percentage", "three_pa_rate", "blocked_shots",
        "rim_attempt_rate", "short_midrange_paint_attempt_rate", "long_midrange_attempt_rate",
        "contested_attempts", "contested_efg_percentage",
        "uncontested_attempts", "uncontested_efg_percentage", "cns_attempts",
        "cns_efg_percentage", "od_attempts", "od_efg_percentage",
    }
    required.update(value for config in ZONE_CONFIG.values() for value in config[:3])
    _require_columns(raw, required, "Shooting data")

    frame = raw.copy()
    frame["attempts_per_game"] = safe_divide(frame["attempts"], frame["appearances"])
    frame["points_per_game"] = safe_divide(frame["total_points"], frame["appearances"])
    frame["true_shooting_pct"] = safe_divide(
        frame["total_points"], 2 * (frame["attempts"] + 0.44 * frame["ft_attempts"])
    )
    frame["ft_rate"] = safe_divide(frame["ft_attempts"], frame["attempts"])
    frame["block_rate"] = safe_divide(frame.get("blocked_shots", 0), frame["attempts"])
    frame["catch_shoot_share"] = safe_divide(frame["cns_attempts"], frame["attempts"])
    frame["off_dribble_share"] = safe_divide(frame["od_attempts"], frame["attempts"])
    frame["pressure_delta"] = frame["contested_efg_percentage"] - frame["uncontested_efg_percentage"]

    zone_attempt_columns = [config[0] for config in ZONE_CONFIG.values()]
    attempt_matrix = frame[zone_attempt_columns].fillna(0).clip(lower=0).to_numpy(dtype=float)
    attempt_totals = attempt_matrix.sum(axis=1)
    shares = np.divide(
        attempt_matrix,
        attempt_totals[:, None],
        out=np.zeros_like(attempt_matrix),
        where=attempt_totals[:, None] > 0,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        entropy = -(np.where(shares > 0, shares * np.log(shares), 0).sum(axis=1)) / np.log(len(ZONE_CONFIG))
    frame["shot_diet_entropy"] = entropy
    frame["classified_zone_share"] = safe_divide(pd.Series(attempt_totals, index=frame.index), frame["attempts"])

    prior_attempts = 30.0
    adjusted_value = pd.Series(0.0, index=frame.index)
    expected_value = pd.Series(0.0, index=frame.index)
    for zone, (attempt_col, made_col, _pct_col, point_value) in ZONE_CONFIG.items():
        attempts = pd.to_numeric(frame[attempt_col], errors="coerce").fillna(0)
        made = pd.to_numeric(frame[made_col], errors="coerce").fillna(0)
        league_rate = float(made.sum() / attempts.sum()) if attempts.sum() else np.nan
        slug = zone.lower().replace(" / ", "_").replace("-", "_").replace(" ", "_")
        frame[f"{slug}_league_fg"] = league_rate
        frame[f"{slug}_adjusted_fg"] = (made + prior_attempts * league_rate) / (attempts + prior_attempts)
        adjusted_value += attempts * frame[f"{slug}_adjusted_fg"] * point_value
        expected_value += attempts * league_rate * point_value

    classified_attempts = pd.Series(attempt_totals, index=frame.index).replace(0, np.nan)
    frame["adjusted_shot_value"] = adjusted_value / classified_attempts
    frame["expected_shot_value"] = expected_value / classified_attempts
    frame["shotmaking_over_expected"] = frame["adjusted_shot_value"] - frame["expected_shot_value"]
    frame["shooting_reliability"] = _sample_reliability(frame["attempts"], frame["appearances"], 120)

    three_rate = frame["three_pa_rate"].fillna(0)
    rim_rate = frame["rim_attempt_rate"].fillna(0)
    mid_rate = frame["short_midrange_paint_attempt_rate"].fillna(0) + frame["long_midrange_attempt_rate"].fillna(0)
    frame["shot_archetype"] = np.select(
        [
            frame["attempts"].lt(20),
            three_rate.ge(0.55) & frame["catch_shoot_share"].ge(0.55),
            three_rate.ge(0.55),
            rim_rate.ge(0.45),
            mid_rate.ge(0.50),
            rim_rate.ge(0.28) & three_rate.ge(0.32),
        ],
        [
            "Limited sample", "Catch-and-shoot spacer", "Perimeter creator",
            "Rim attacker", "Interior / mid-range", "Balanced modern",
        ],
        default="Balanced scorer",
    )

    qualified = frame["appearances"].ge(10) & frame["attempts"].ge(50)
    _add_percentile(frame, "attempts_per_game", "shot_volume_percentile", qualified)
    _add_percentile(frame, "efg_percentage", "shot_efficiency_percentile", qualified)
    _add_percentile(frame, "shotmaking_over_expected", "shotmaking_percentile", qualified)
    _add_percentile(frame, "shot_diet_entropy", "shot_versatility_percentile", qualified)
    _add_percentile(frame, "three_pa_rate", "three_volume_percentile", qualified)
    _add_percentile(frame, "rim_attempt_rate", "rim_rate_percentile", qualified)
    _add_percentile(frame, "ft_rate", "ft_rate_percentile", qualified)
    _add_percentile(
        frame, "zone_three_fg_percentage", "three_accuracy_percentile",
        qualified & frame["zone_three_attempts"].ge(25),
    )
    _add_percentile(
        frame, "rim_fg_percentage", "rim_finish_percentile",
        qualified & frame["rim_attempts"].ge(25),
    )
    _add_percentile(
        frame, "cns_efg_percentage", "catch_shoot_efg_percentile",
        qualified & frame["cns_attempts"].ge(25),
    )
    _add_percentile(
        frame, "od_efg_percentage", "off_dribble_efg_percentile",
        qualified & frame["od_attempts"].ge(25),
    )
    pressure_qualified = qualified & frame["contested_attempts"].ge(25) & frame["uncontested_attempts"].ge(15)
    _add_percentile(frame, "pressure_delta", "pressure_resilience_percentile", pressure_qualified)

    frame["spacing_score"] = 100 * (
        0.55 * frame["three_volume_percentile"] + 0.45 * frame["three_accuracy_percentile"]
    )
    frame["rim_pressure_score"] = 100 * (
        0.40 * frame["rim_rate_percentile"]
        + 0.30 * frame["rim_finish_percentile"]
        + 0.30 * frame["ft_rate_percentile"]
    )
    frame["scoring_impact_score"] = 100 * (
        0.35 * frame["shot_efficiency_percentile"]
        + 0.25 * frame["shot_volume_percentile"]
        + 0.25 * frame["shotmaking_percentile"]
        + 0.15 * frame["shooting_reliability"].div(100)
    )
    return frame


def engineer_picks(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"player_id", "player_name", "team_name", "appearances"}
    for role in ("handler", "screener"):
        required.update(
            {
                f"{role}_total_picks", f"{role}_points", f"{role}_ppp",
                f"{role}_success_rate", f"{role}_turnover_rate",
                f"{role}_assist_opportunity", f"{role}_shot_taken",
                f"{role}_pass",
            }
        )
    _require_columns(raw, required, "Pick-and-roll data")
    frame = raw.copy()

    for role in ("handler", "screener"):
        picks = frame[f"{role}_total_picks"]
        frame[f"{role}_picks_per_game"] = safe_divide(picks, frame["appearances"])
        frame[f"{role}_shot_rate"] = safe_divide(frame[f"{role}_shot_taken"], picks)
        frame[f"{role}_pass_rate"] = safe_divide(frame[f"{role}_pass"], picks)
        frame[f"{role}_assist_opportunity_rate"] = safe_divide(
            frame[f"{role}_assist_opportunity"], picks
        )
        frame[f"{role}_reliability"] = _sample_reliability(picks, frame["appearances"], 75)
        qualified = frame["appearances"].ge(10) & picks.ge(30)
        _add_percentile(frame, f"{role}_picks_per_game", f"{role}_volume_percentile", qualified)
        _add_percentile(frame, f"{role}_ppp", f"{role}_ppp_percentile", qualified)
        _add_percentile(frame, f"{role}_success_rate", f"{role}_success_percentile", qualified)
        _add_percentile(
            frame, f"{role}_turnover_rate", f"{role}_turnover_control_percentile",
            qualified, higher_is_better=False,
        )
        _add_percentile(
            frame, f"{role}_assist_opportunity_rate", f"{role}_assist_opportunity_percentile",
            qualified,
        )
        frame[f"{role}_creation_score"] = 100 * (
            0.35 * frame[f"{role}_ppp_percentile"]
            + 0.25 * frame[f"{role}_success_percentile"]
            + 0.20 * frame[f"{role}_assist_opportunity_percentile"]
            + 0.20 * frame[f"{role}_turnover_control_percentile"]
        )
        _add_percentile(
            frame, f"{role}_creation_score", f"{role}_creation_percentile",
            frame[f"{role}_creation_score"].notna(),
        )

    total_role_picks = frame["handler_total_picks"] + frame["screener_total_picks"]
    handler_share = safe_divide(frame["handler_total_picks"], total_role_picks)
    frame["pnr_role"] = np.select(
        [total_role_picks.lt(20), handler_share.ge(0.72), handler_share.le(0.28)],
        ["Low PnR sample", "Ball handler", "Screener"],
        default="Dual role",
    )
    return frame


def build_profiles(shots: pd.DataFrame, picks: pd.DataFrame) -> pd.DataFrame:
    profiles = shots.merge(picks, on="player_id", how="outer", suffixes=("", "_pnr"), validate="one_to_one")
    identity = ["league", "season", "games_played", "player_name", "team_name", "meta_team_id", "appearances", "is_traded"]
    for column in identity:
        pick_column = f"{column}_pnr"
        if pick_column in profiles:
            if column in profiles:
                profiles[column] = profiles[column].combine_first(profiles[pick_column])
            else:
                profiles[column] = profiles[pick_column]
            profiles.drop(columns=pick_column, inplace=True)
    return profiles.sort_values("player_name", kind="stable").reset_index(drop=True)


def compute_fit_scores(profiles: pd.DataFrame, preset: str) -> pd.DataFrame:
    if preset not in FIT_PRESETS:
        raise KeyError(f"Unknown fit preset: {preset}")
    result = profiles.copy()
    weights = FIT_PRESETS[preset]["weights"]
    available_weight = pd.Series(0.0, index=result.index)
    weighted_score = pd.Series(0.0, index=result.index)
    for column, weight in weights.items():
        values = pd.to_numeric(result[column], errors="coerce")
        mask = values.notna()
        weighted_score += values.fillna(0) * weight
        available_weight += mask.astype(float) * weight
    coverage = available_weight / sum(weights.values())
    raw_score = weighted_score.div(available_weight.where(available_weight.gt(0)))
    result["fit_coverage"] = coverage
    result["fit_score"] = (100 * raw_score * (0.70 + 0.30 * coverage)).where(coverage.ge(0.60))
    confidence_columns = FIT_PRESETS[preset]["confidence"]
    result["fit_confidence"] = result[confidence_columns].mean(axis=1, skipna=True)
    return result


def closest_comparisons(
    profiles: pd.DataFrame,
    player_id: int,
    *,
    limit: int = 5,
) -> pd.DataFrame:
    features = [
        "shot_volume_percentile", "shot_efficiency_percentile", "three_volume_percentile",
        "rim_rate_percentile", "shot_versatility_percentile", "handler_volume_percentile",
        "handler_creation_percentile", "screener_volume_percentile", "screener_creation_percentile",
    ]
    selected_rows = profiles.loc[profiles["player_id"].eq(player_id)]
    if selected_rows.empty:
        return pd.DataFrame()
    selected = selected_rows.iloc[0]
    records: list[dict[str, object]] = []
    for _, candidate in profiles.loc[profiles["player_id"].ne(player_id)].iterrows():
        shared = [column for column in features if pd.notna(selected[column]) and pd.notna(candidate[column])]
        if len(shared) < 4:
            continue
        distance = float(np.sqrt(np.mean([(selected[c] - candidate[c]) ** 2 for c in shared])))
        records.append(
            {
                "player_name": candidate["player_name"],
                "team_name": candidate["team_name"],
                "similarity": max(0.0, 100 * (1 - distance)),
                "shared_dimensions": len(shared),
                "shot_archetype": candidate.get("shot_archetype"),
                "pnr_role": candidate.get("pnr_role"),
            }
        )
    if not records:
        return pd.DataFrame(
            columns=[
                "player_name", "team_name", "similarity", "shared_dimensions",
                "shot_archetype", "pnr_role",
            ]
        )
    return pd.DataFrame(records).sort_values("similarity", ascending=False).head(limit)


def metric_glossary(glossary: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if glossary.empty or "column" not in glossary:
        return pd.DataFrame()
    result = glossary.loc[glossary["column"].isin(columns)].copy()
    display = [column for column in ["display_name", "definition", "unit", "dataset"] if column in result]
    return result[display].drop_duplicates("display_name")


def _quality_summary(shots: pd.DataFrame, picks: pd.DataFrame) -> dict[str, int | float | str]:
    shot_ids, pick_ids = set(shots["player_id"]), set(picks["player_id"])
    identity = shots[["player_id", "player_name"]].merge(
        picks[["player_id", "player_name"]], on="player_id", suffixes=("_shots", "_picks")
    )
    return {
        "shot_rows": len(shots),
        "pick_rows": len(picks),
        "matched_players": len(shot_ids & pick_ids),
        "shot_only_players": len(shot_ids - pick_ids),
        "pick_only_players": len(pick_ids - shot_ids),
        "teams": int(pd.concat([shots["team_name"], picks["team_name"]]).nunique()),
        "duplicate_shot_ids": int(shots["player_id"].duplicated().sum()),
        "duplicate_pick_ids": int(picks["player_id"].duplicated().sum()),
        "identity_mismatches": int((identity["player_name_shots"] != identity["player_name_picks"]).sum()),
        "scope": f"{shots['league'].iloc[0]} {shots['season'].iloc[0]}",
    }


@st.cache_data(show_spinner="Preparing scouting data…")
def _load_data_cached(shots_stamp: int, picks_stamp: int, glossary_stamp: int) -> DataBundle:
    del shots_stamp, picks_stamp, glossary_stamp
    for path in (SHOTS_PATH, PICKS_PATH, GLOSSARY_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required data file was not found: {path}")
    shots_raw = pd.read_csv(SHOTS_PATH)
    picks_raw = pd.read_csv(PICKS_PATH)
    glossary = pd.read_csv(GLOSSARY_PATH)
    shots = engineer_shooting(shots_raw)
    picks = engineer_picks(picks_raw)
    profiles = build_profiles(shots, picks)
    return DataBundle(
        shots=shots,
        picks=picks,
        profiles=profiles,
        glossary=glossary,
        quality=_quality_summary(shots_raw, picks_raw),
    )


def load_data() -> DataBundle:
    return _load_data_cached(
        SHOTS_PATH.stat().st_mtime_ns,
        PICKS_PATH.stat().st_mtime_ns,
        GLOSSARY_PATH.stat().st_mtime_ns,
    )
