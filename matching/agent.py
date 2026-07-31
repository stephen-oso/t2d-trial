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
from langchain_groq import ChatGroq
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

@lc_tool
def search_trials(query: str) -> str:
    """Search the clinical trial database for T2D trials relevant to a patient.
    Returns a JSON list of trials with trial_id, title, and eligibility criteria.
    Args:
        query: Free-text description of the patient (e.g. "T2D age 52 HbA1c 8.2 no insulin")
    """
    return _search_trials_impl.invoke({"query": query})


@lc_tool
def check_eligibility(patient_json: str, trial_id: str) -> str:
    """Check whether a patient meets eligibility criteria for one specific trial.
    Returns a JSON list of {criterion, status, patient_value} objects.
    Status is PASS, FAIL, or UNKNOWN.
    Args:
        patient_json: The patient profile serialised as a JSON string.
        trial_id: The trial ID to check (e.g. "NCT04932928").
    """
    input_payload = json.dumps({"patient_json": patient_json, "trial_id": trial_id})
    return _check_eligibility_impl.invoke({"input_json": input_payload})


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
_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ["GROQ_API_KEY"],
    temperature=0,
    max_retries=6,  # retry on 429 rate-limit errors with exponential backoff
)

_memory = MemorySaver()
_agent = create_react_agent(
    _llm,
    tools=[search_trials, check_eligibility, score_match],
    checkpointer=_memory,
)

_SYSTEM = (
    "You are a clinical trial matching assistant. "
    "Given a patient profile JSON, find which T2D trials they may qualify for.\n\n"
    "Steps:\n"
    "1. Call search_trials with a short query describing the patient.\n"
    "2. For EACH trial returned call check_eligibility, passing "
    "patient_json (the full patient JSON as a string) and trial_id.\n"
    "3. For EACH eligibility result call score_match with the verdicts JSON string.\n"
    "4. After scoring all trials, respond with a brief summary."
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
    """Parse agent messages to extract match data from ToolMessage results.

    Extracts verdicts from check_eligibility ToolMessage outputs (keyed by
    trial_id from the AIMessage tool_call args), then computes scores locally
    using the same deterministic formula as score_match — no additional LLM
    call and no fragile correlation across tool boundaries.

    Returns a list of match dicts sorted by score descending.
    """
    # Build maps from tool_call_id
    call_info: dict[str, tuple[str, dict]] = {}  # id -> (name, args)
    call_output: dict[str, str] = {}             # id -> raw content string

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

    # --- check_eligibility: trial_id -> verdicts ---
    # The agent wrapper exposes separate (patient_json, trial_id) params so
    # we can reliably read trial_id from the tool call args.
    trial_verdicts: dict[str, list] = {}
    for call_id, (name, args) in call_info.items():
        if name == "check_eligibility" and call_id in call_output:
            tid = args.get("trial_id")
            if tid:
                try:
                    verdicts = json.loads(call_output[call_id])
                    if isinstance(verdicts, list):
                        trial_verdicts[tid] = verdicts
                except json.JSONDecodeError:
                    pass

    # --- Compute scores locally from the raw verdicts ---
    # We do NOT use the agent's score_match tool call outputs because the LLM
    # may reformat the verdicts before passing them to score_match, producing
    # incorrect scores.  The deterministic computation here is reliable.
    matches: list[dict] = []
    for trial_id, verdicts in trial_verdicts.items():
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
    profile = extract_patient_profile(note)
    patient_dict = profile.model_dump()
    patient_json_str = json.dumps(patient_dict)

    prompt = (
        f"Patient profile JSON:\n{patient_json_str}\n\n"
        "Find matching T2D clinical trials, check eligibility for each, and score each one."
    )

    config = {
        "configurable": {"thread_id": f"match-{hash(note)}"},
        "recursion_limit": 15,
    }
    result = _agent.invoke(
        {"messages": [{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": prompt}]},
        config=config,
    )

    matches = _parse_messages(result["messages"])

    return {
        "patient": patient_dict,
        "matches": matches,
    }
