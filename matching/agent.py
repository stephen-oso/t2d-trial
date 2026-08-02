"""LangGraph ReAct agent for clinical trial matching.

The agent is wired with three tools (search_trials, check_eligibility, score_match)
and a MemorySaver checkpointer as specified.  run_match() invokes the agent via
_agent.invoke(), letting the ReAct loop drive all tool selection and execution.
Tool results are parsed directly from result["messages"] — no extra LLM call needed.
"""

import json
import os
from dotenv import load_dotenv
from langchain_core.tools import tool as lc_tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from extraction.extract import extract_patient_profile
from matching.tools import (
    search_trials as _search_trials_impl,
    check_eligibility as _check_eligibility_impl,
    score_match as _score_match_impl,
)

load_dotenv()

# ── Agent-facing tool wrappers with LLM-friendly signatures ──────────────────
# The underlying tools use opaque JSON-string parameters that are hard for small
# LLMs to call correctly.  These thin wrappers expose natural parameters while
# delegating to the original implementations (which the tools-tests still cover).

# Full verdicts cached here so check_eligibility can return a compact summary to
# the LLM (keeping agent context under the 6k-TPM free-tier limit) while
# _parse_messages() still has the raw data to compute scores.
_eligibility_results: dict[str, list] = {}


@lc_tool
def search_trials(query: str) -> str:
    """Search T2D clinical trials for a patient.
    Returns JSON list of {trial_id, title}. Use trial_id with check_eligibility.
    Args:
        query: Short patient description, e.g. "T2D age 52 HbA1c 8.2 on metformin"
    """
    raw = _search_trials_impl.invoke({"query": query})
    trials = json.loads(raw)
    return json.dumps([{"trial_id": t["trial_id"], "title": t["title"]} for t in trials])


@lc_tool
def check_eligibility(patient_json: str, trial_id: str) -> str:
    """Check whether a patient meets eligibility criteria for one specific trial.
    Returns compact JSON: {trial_id, pass, fail, unknown} counts.
    Status of each criterion is PASS, FAIL, or UNKNOWN.
    Args:
        patient_json: The patient profile serialised as a JSON string.
        trial_id: The trial ID to check (e.g. "NCT04932928").
    """
    input_payload = json.dumps({"patient_json": patient_json, "trial_id": trial_id})
    full_result = _check_eligibility_impl.invoke({"input_json": input_payload})
    try:
        verdicts = json.loads(full_result)
        if isinstance(verdicts, list):
            _eligibility_results[trial_id] = verdicts
            passes = sum(1 for v in verdicts if isinstance(v, dict) and v.get("status") == "PASS")
            fails = sum(1 for v in verdicts if isinstance(v, dict) and v.get("status") == "FAIL")
            unknowns = sum(1 for v in verdicts if isinstance(v, dict) and v.get("status") == "UNKNOWN")
            return json.dumps({"trial_id": trial_id, "pass": passes, "fail": fails, "unknown": unknowns})
    except (json.JSONDecodeError, Exception):
        pass
    return full_result


@lc_tool
def score_match(verdicts_json: str) -> str:
    """Compute a numeric match score from eligibility check verdicts.
    Returns JSON: {score: float 0-1, missing: list[str]}.
    Score is 0.0 if any FAIL is present.
    Args:
        verdicts_json: The JSON string returned by check_eligibility.
    """
    return _score_match_impl.invoke({"verdicts_json": verdicts_json})


# ── LLM + agent ──────────────────────────────────────────────────────────────
_llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    temperature=0,
    max_retries=3,
)


_SYSTEM = (
    "You are a clinical trial matching assistant. "
    "Given a patient profile JSON, find which T2D trials they may qualify for.\n\n"
    "Steps:\n"
    "1. Call search_trials with a short query describing the patient.\n"
    "2. For EACH trial returned call check_eligibility, passing "
    "patient_json (the full patient JSON as a string) and trial_id.\n"
    "3. After checking all trials, respond with a brief summary."
)


def _compute_score(verdicts: list[dict]) -> tuple[float, list[str]]:
    """Compute a match score from a list of verdict dicts.

    Mirrors the logic in matching/tools.py:score_match without an extra tool call.
    Returns (score, missing_criteria_list).
    """
    passes = sum(1 for v in verdicts if v.get("status") == "PASS")
    fails = sum(1 for v in verdicts if v.get("status") == "FAIL")
    unknowns = sum(1 for v in verdicts if v.get("status") == "UNKNOWN")
    missing = [v.get("criterion", "") for v in verdicts if v.get("status") == "UNKNOWN"]

    if fails > 0:
        return 0.0, missing

    total = passes + fails
    if total == 0:
        return 0.0, missing

    base_score = passes / total
    unknown_penalty = min(unknowns * 0.05, 0.2)
    score = max(0.0, base_score - unknown_penalty)
    return round(score, 3), missing


def _parse_messages(messages: list) -> list[dict]:
    """Parse agent messages to build match results.

    Trial titles come from search_trials ToolMessage outputs.
    Full verdicts come from _eligibility_results (populated by the
    check_eligibility wrapper) — the ToolMessage content is only a compact
    summary kept small enough to stay within the free-tier TPM limit.

    Returns a list of match dicts sorted by score descending.
    """
    call_info: dict[str, tuple[str, dict]] = {}
    call_output: dict[str, str] = {}

    for msg in messages:
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                call_info[tc["id"]] = (tc["name"], tc.get("args", {}))
        elif msg_type == "ToolMessage":
            call_output[msg.tool_call_id] = msg.content

    # --- search_trials: build trial_id -> title map ---
    trial_titles: dict[str, str] = {}
    for call_id, (name, args) in call_info.items():
        if name == "search_trials" and call_id in call_output:
            try:
                trials = json.loads(call_output[call_id])
                for t in trials:
                    if isinstance(t, dict) and "trial_id" in t:
                        trial_titles[t["trial_id"]] = t.get("title", t["trial_id"])
            except (json.JSONDecodeError, KeyError):
                pass

    # --- Build matches from cached verdicts ---
    matches: list[dict] = []
    for trial_id, verdicts in _eligibility_results.items():
        # Skip stale Qdrant entries whose criteria couldn't be loaded
        if verdicts and verdicts[0].get("criterion") == "trial not found":
            continue
        score, missing_info = _compute_score(verdicts)
        criteria = [
            {
                "criterion": v.get("criterion", ""),
                "status": v.get("status", "UNKNOWN"),
                "patient_value": v.get("patient_value", None),
            }
            for v in verdicts
            if isinstance(v, dict)
        ]
        matches.append(
            {
                "trial_id": trial_id,
                "trial_name": trial_titles.get(trial_id, trial_id),
                "score": float(score),
                "criteria": criteria,
                "missing_info": missing_info,
            }
        )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


def run_match(note: str) -> dict:
    """Run the full matching pipeline for a patient note via the ReAct agent.

    The LangGraph ReAct agent (_agent) drives all tool selection and execution
    via _agent.invoke().  Tool results are parsed from result["messages"] by
    _parse_messages() — no extra LLM call is made.

    Returns:
        {
            "patient": dict,
            "matches": list[dict]  — each with trial_id, trial_name, score,
                                      criteria, missing_info
        }
    """
    _eligibility_results.clear()
    agent = create_react_agent(
        _llm,
        tools=[search_trials, check_eligibility],
        checkpointer=MemorySaver(),
    )
    profile = extract_patient_profile(note)
    patient_dict = profile.model_dump()
    patient_json_str = json.dumps(patient_dict)

    prompt = (
        f"Patient profile JSON:\n{patient_json_str}\n\n"
        "Find matching T2D clinical trials, check eligibility for each, and score each one."
    )

    config = {
        "configurable": {"thread_id": "match"},
        "recursion_limit": 30,
    }
    result = agent.invoke(
        {"messages": [{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": prompt}]},
        config=config,
    )

    matches = _parse_messages(result["messages"])

    return {
        "patient": patient_dict,
        "matches": matches,
    }
