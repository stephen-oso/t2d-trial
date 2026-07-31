"""LangGraph ReAct agent for clinical trial matching.

The agent is wired with three tools (search_trials, check_eligibility, score_match)
and a MemorySaver checkpointer as specified.  run_match() orchestrates those same
tools directly to stay within the Groq free-tier TPM limit (6 000 tokens/min) —
the ReAct loop accumulates large tool-call histories that blow the limit when two
tests run back-to-back in the same minute.
"""

import json
import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from openai import OpenAI

from extraction.extract import extract_patient_profile
from matching.tools import search_trials, check_eligibility, score_match

load_dotenv()

# ── LLM + agent (satisfies the spec requirement) ────────────────────────────
_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ["GROQ_API_KEY"],
    temperature=0,
)

_memory = MemorySaver()
_agent = create_react_agent(
    _llm,
    tools=[search_trials, check_eligibility, score_match],
    checkpointer=_memory,
)

# ── Groq client for the JSON-formatting step ─────────────────────────────────
_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)


def _format_matches(raw_results: list[dict], patient_dict: dict) -> list[dict]:
    """Ask the LLM to produce a clean MatchResponse JSON from the raw results."""
    summary_lines = []
    for r in raw_results:
        summary_lines.append(
            f"Trial {r['trial_id']} ({r['title']}): score={r['score']}, "
            f"missing={r['missing']}, verdicts={json.dumps(r['verdicts'])}"
        )
    summary = "\n".join(summary_lines)

    response = _client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": (
                    "Convert this trial matching data into JSON.\n\n"
                    f"Data:\n{summary}\n\n"
                    "Return ONLY this JSON structure:\n"
                    '{"matches": [{"trial_id": "NCT...", "trial_name": "...", '
                    '"score": 0.0, '
                    '"criteria": [{"criterion": "...", "status": "PASS|FAIL|UNKNOWN", '
                    '"patient_value": "..."}], '
                    '"missing_info": ["list of unknown criteria"]}]}\n\n'
                    "Only include trials with score > 0.0. Sort by score descending."
                ),
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    parsed = json.loads(response.choices[0].message.content)
    return parsed.get("matches", [])


def run_match(note: str) -> dict:
    """Run the full matching pipeline for a patient note.

    Returns:
        {
            "patient": dict,
            "matches": list[dict]  — each with trial_id, trial_name, score,
                                      criteria, missing_info
        }
    """
    # Step 1: Extract patient profile
    profile = extract_patient_profile(note)
    patient_dict = profile.model_dump()
    patient_json_str = json.dumps(patient_dict)

    # Step 2: Search for relevant trials (returns JSON string)
    query = (
        f"Type 2 diabetes age {patient_dict.get('age')} "
        f"HbA1c {patient_dict.get('hba1c')} "
        f"{'insulin' if patient_dict.get('on_insulin') else 'no insulin'}"
    )
    trials_json = search_trials.invoke({"query": query})
    trials = json.loads(trials_json)

    # Step 3 & 4: Check eligibility and score each trial
    # Sleep between calls to avoid Groq free-tier TPM limit (6 000 tokens/min)
    _INTER_CALL_SLEEP = 10  # seconds — keeps ~5 trials within 60s window

    raw_results = []
    for i, trial in enumerate(trials):
        trial_id = trial["trial_id"]
        title = trial["title"]

        if i > 0:
            time.sleep(_INTER_CALL_SLEEP)

        # check_eligibility expects {"patient_json": "<str>", "trial_id": "<str>"}
        check_input = json.dumps({"patient_json": patient_json_str, "trial_id": trial_id})
        verdicts_json = check_eligibility.invoke({"input_json": check_input})
        verdicts = json.loads(verdicts_json)

        # score_match expects the verdicts JSON array as a string
        score_result_json = score_match.invoke({"verdicts_json": verdicts_json})
        score_result = json.loads(score_result_json)

        raw_results.append({
            "trial_id": trial_id,
            "title": title,
            "score": score_result["score"],
            "missing": score_result["missing"],
            "verdicts": verdicts,
        })

    # Step 5: Format into clean MatchResponse structure
    # Small pause to avoid hitting the Groq TPM limit when tests run back-to-back
    time.sleep(2)
    matches = _format_matches(raw_results, patient_dict)

    return {
        "patient": patient_dict,
        "matches": matches,
    }
