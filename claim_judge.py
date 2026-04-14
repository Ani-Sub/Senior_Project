"""
Takes transcript chunck and chunks and uses an LLM to:
- Extrat claims
- Judge each claim for accuracy
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Literal

import requests

Verdict = Literal["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO", "MISLEADING", "NOT_CHECKABLE"]
ClaimType = Literal["FACTUAL", "OPINION", "PREDICTION", "OTHER"]

# LLM Client

@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    model: str = "llama3:latest"
    temperature: float = 0.2
    num_predict: int = 300
    timeout_s: int = 180

    def generate_text(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        try:
            resp = requests.post(
                url,
                json = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.num_predict,
                    },
                },
                timeout = self.timeout_s,
            )
            if resp.status_code != 200:
                print("\n--- OLLAMA ERROR ---")
                print("Status:", resp.status_code)
                print(resp.text[:2000])  # show Ollama's error message
                print("--- END OLLAMA ERROR ---\n")
                resp.raise_for_status() 

            data = resp.json()
            return data.get("response", "")
        
        except requests.exceptions.ReadTimeout:
            print("\n--- OLLAMA TIMEOUT ---")
            print(f"Model: {self.model}")
            print(f"Timeout: {self.timeout_s} seconds")
            print("The model took too long to respond.")
            print("--- END OLLAMA TIMEOUT ---\n")
            return ""
    
# Helpers

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

def _extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Robust JSON extraction for LLM output.
    - Tries full JSON parse
    - Tries to find the first {...} block
    - If still fails, returns a safe default instead of crashing
    """
    if text is None:
        return {"claims": []}

    text = text.strip()
    if not text:
        # LLM returned nothing
        return {"claims": []}

    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to find a JSON object substring
    m = _JSON_OBJECT_RE.search(text)
    if m:
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Last resort: safe fallback so pipeline doesn't die
    return {"claims": []}

# Core prompts

def extract_claims(llm, chunk_text, max_claims=5):
    prompt = f"""
Return only JSON.

Transcript:
{chunk_text}

Rules:
- claim_type must be exactly one of: FACTUAL, OPINION, PREDICTION, OTHER
- Do not include any extra text outside JSON

Schema:
{{
  "claims": [
    {{
      "claim_text": "string",
      "claim_type": "FACTUAL, OPINION, PREDICTION, or OTHER",
      "is_checkable_now": true
    }}
  ]
}}
"""

    raw = llm.generate_text(prompt)

    print("\n--- EXTRACT CLAIMS RAW ---")
    print(raw[:2000])
    print("--- END EXTRACT CLAIMS RAW ---\n")

    obj = _extract_first_json_object(raw)
    claims = obj.get("claims", []) if isinstance(obj, dict) else []

    out = []
    valid_types = {"FACTUAL", "OPINION", "PREDICTION", "OTHER"}

    for c in claims:
        if not isinstance(c, dict):
            continue

        t = (c.get("claim_text") or "").strip()
        if not t:
            continue

        claim_type = str(c.get("claim_type", "OTHER")).strip().upper()
        if claim_type not in valid_types:
            claim_type = "OTHER"

        out.append(
            {
                "claim_text": t,
                "claim_type": claim_type,
                "is_checkable_now": bool(c.get("is_checkable_now", False)),
            }
        )

    return out[:max_claims]

def judge_claim(llm, claim_text: str, evidence_snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    evidence_snippets: [{id, source, data, text}, ...]
    If evidence_snippets is empty, the LLM should typically return NOT_ENOUGH_INFO
    unless it's clearly opinion/prediction (NOT_CHECKABLE
    """
    evidence_block = ""
    for e in evidence_snippets:
        evidence_block += (
            f"[{e.get('id')}] source={e.get('source')} date={e.get('date')}\n"
            f"{e.get('text','')}\n\n"  
        )

    prompt = f"""
You are judging whether a claim is accurate based ONLY on provided evidence snippets.

Allowed verdicts:
- SUPPORTED: evidence clearly supports the claim
- REFUTED: evidence clearly contradicts the claim
- MISLEADING: claim is partially true but missing context / overly broad
- NOT_ENOUGH_INFO: insufficient evidence provided to verify
- NOT_CHECKABLE: prediction/opinion or otherwise not fact-checkable right now

Rules:
- Use ONLY the evidence below. If evidence is empty or irrelevant, use NOT_ENOUGH_INFO.
- Provide evidence_ids that you actually used (e.g., ["E1","E3"]).
- Output MUST be valid JSON only.
- confidence_score must be an integer from 1 to 10 (1 = very uncertain, 10 = very confident)

Claim:
\"\"\"{claim_text}\"\"\"

Evidence snippets (may be empty):
\"\"\"{evidence_block.strip()}\"\"\"

Return JSON in this schema:
{{
  "verdict": "SUPPORTED|REFUTED|MISLEADING|NOT_ENOUGH_INFO|NOT_CHECKABLE",
  "confidence": 0.0,
  "confidence_score": 1,
  "rationale": "1-3 sentences",
  "evidence_ids": ["E1","E2"]
}}
"""
    raw = llm.generate_text(prompt)
    obj = _extract_first_json_object(raw)

    verdict: str = obj.get("verdict", "NOT_ENOUGH_INFO")
    conf = obj.get("confidence", 0.5)
    confidence_score = obj.get("confidence_score")
    rationale = obj.get("rationale", "")
    evidence_ids = obj.get("evidence_ids", [])

    # Normalize a bit
    if verdict not in {"SUPPORTED", "REFUTED", "MISLEADING", "NOT_ENOUGH_INFO", "NOT_CHECKABLE"}:
        verdict = "NOT_ENOUGH_INFO"
    try:
        conf = float(conf)
    except Exception:
        conf = 0.5
    conf = max(0.0, min(1.0, conf))

    # Normalize confidence_score
    try:
        confidence_score = int(confidence_score)
    except Exception:
        confidence_score = int(round(conf * 10))

    confidence_score = max(1, min(10, confidence_score))

    if not isinstance(evidence_ids, list):
        evidence_ids = []

    return {
        "verdict": verdict,
        "confidence": conf,
        "confidence_score": confidence_score,
        "rationale": str(rationale).strip(),
        "evidence_ids": evidence_ids,
    }

# Evidence retrieval (MVP stub)

def retrieve_evidence_stub(claim_text: str) -> List[Dict[str, Any]]:
    """
    MVP: returns no evidence. This will force NOT_ENOUGH_INFO most of the time,
    which is *correct* behavior when you haven't implemented retrieval yet.
    """
    return []

def _sec_to_mmss(seconds: float) -> str:
    s = int(round(seconds))
    mm = s // 60
    ss = s % 60
    return f"{mm:02d}:{ss:02d}"

# Main processing

def analyze_chunks(
    llm,
    video_id: str,
    chunks_v2: List[Dict[str, Any]],
    retrieve_evidence: Callable[[str], List[Dict[str, Any]]] = retrieve_evidence_stub,
    max_claims_per_chunk: int = 5,
) -> Dict[str, Any]:
    results = {
        "video_id": video_id,
        "claims_analysis": [],
    }

    for ch in chunks_v2:
        start = float(ch.get("start", 0.0))
        end = float(ch.get("end", start))
        text = (ch.get("text") or "").strip()
        if not text:
            continue

        chunk_entry: Dict[str, Any] = {
            "chunk": {
                "start": start,
                "end": end,
                "start_mmss": _sec_to_mmss(start),
                "end_mmss": _sec_to_mmss(end),
            },
            "text": text,
            "claims": [],
        }

        claims = extract_claims(llm, text, max_claims=max_claims_per_chunk)

        for c in claims:
            claim_text = c["claim_text"]
            evidence = retrieve_evidence(claim_text)

            # If the extractor already says not cheackable now, short-circut politely:
            if not c.get("is_checkable_now", False) and c.get("claim_type") in {"PREDICTION", "OPINION"}:
                judgment = {
                    "verdict": "NOT_CHECKABLE",
                    "confidence": 0.9,
                    "rationale": "This is a prediction/opinion, not a present-tense factual claim that can be verified with evidence.",
                    "evidence_ids": [],
                }
            else:
                judgment = judge_claim(llm, claim_text, evidence)

            chunk_entry["claims"].append(
                {
                    "claim_text": claim_text,
                    "claim_type": c.get("claim_type", "OTHER"),
                    "is_checkable_now": c.get("is_checkable_now", False),
                    "judgment": judgment,
                }
            )

        results["claims_analysis"].append(chunk_entry)

    return results