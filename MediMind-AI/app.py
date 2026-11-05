import json
import os
import re
import time
from collections import defaultdict, deque
from threading import Lock

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from groq import Groq

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-demo-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 24 * 1024
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_INPUT_CHARS = 5000
_request_times = defaultdict(deque)
_rate_lock = Lock()

SYSTEM_PROMPT = """You are MediMind AI, an educational symptom-information and triage assistant.
You do not diagnose, replace clinicians, or claim certainty. Be cautious and empathetic.
Assess urgency based on symptoms, not merely the condition name. If severe breathing difficulty,
possible heart-attack chest pain, stroke signs (face droop, arm weakness, speech difficulty),
unconsciousness, severe uncontrolled bleeding, or severe allergic reaction are reported,
immediately recommend emergency services before routine questions. In Pakistan, mention Rescue
1122 where applicable; elsewhere say local emergency number. Never advise driving oneself in a
possible emergency. Give only low-risk first-aid guidance. Do not prescribe medication regimens,
antibiotics, or prescription drugs. Do not invent confidence percentages or medical citations.
Ask a few concise follow-up questions if important information is missing. If uncertain, say so.
Return ONLY valid JSON with these keys:
{
 "status":"assessment" or "follow_up",
 "emergency_level":"Level 1" or "Level 2" or "Level 3" or "Level 4",
 "urgency_title":"short title",
 "summary":"brief summary",
 "possible_conditions":[{"name":"...","explanation":"...","supporting_symptoms":["..."],"uncertainties":["..."]}],
 "warning_signs":["..."],
 "first_aid":["..."],
 "care_recommendation":"...",
 "follow_up_questions":["..."],
 "disclaimer":"This is not a confirmed diagnosis."
}
For a clear emergency, use Level 1 and make emergency directions the first first_aid item and care_recommendation.
Keep output concise, avoid false reassurance. For follow-up, still provide a cautious urgency estimate.
"""

EMERGENCY_PATTERNS = [
    (re.compile(r"\b(can't breathe|cannot breathe|difficulty breathing|severe shortness of breath|gasping for air|not breathing)\b", re.I), "severe breathing difficulty"),
    (re.compile(r"\b(chest pain|pressure in (my )?chest|crushing chest)\b", re.I), "chest pain that may be serious"),
    (re.compile(r"\b(face droop|face is drooping|one side.*weak|arm weakness|slurred speech|can't speak|cannot speak|stroke symptoms)\b", re.I), "possible stroke signs"),
    (re.compile(r"\b(unconscious|not waking up|passed out and won't wake|unresponsive)\b", re.I), "unconsciousness or unresponsiveness"),
    (re.compile(r"\b(uncontrolled bleeding|bleeding won't stop|severe bleeding)\b", re.I), "severe uncontrolled bleeding"),
    (re.compile(r"\b(anaphylaxis|throat (is )?swelling|tongue (is )?swelling|severe allergic reaction)\b", re.I), "possible severe allergic reaction"),
]

def emergency_flags(text):
    return [label for pattern, label in EMERGENCY_PATTERNS if pattern.search(text or "")]

def safe_emergency_override(data, flags):
    if not flags:
        return data
    data = data if isinstance(data, dict) else {}
    data["status"] = "assessment"
    data["emergency_level"] = "Level 1"
    data["urgency_title"] = "Emergency help may be needed now"
    data["summary"] = (str(data.get("summary", "")).strip() + " Reported warning sign(s): " + ", ".join(flags) + ".").strip()
    data["care_recommendation"] = "Call your local emergency number now. In Pakistan, call Rescue 1122 where available. Do not drive yourself. Do not delay emergency care to continue this chat."
    data["first_aid"] = [
        "Call your local emergency number now (Rescue 1122 in Pakistan where available). Do not drive yourself.",
        "Follow the emergency dispatcher's instructions and have someone stay with the person if safe.",
        "If the person is unconscious or cannot swallow safely, do not give food, drink, or pills."
    ]
    data["warning_signs"] = list(dict.fromkeys(flags + list(data.get("warning_signs", []))))
    data["possible_conditions"] = data.get("possible_conditions", []) if isinstance(data.get("possible_conditions", []), list) else []
    data["follow_up_questions"] = []
    data["disclaimer"] = "This is not a confirmed diagnosis. Emergency warning signs require professional assessment."
    return data

def validate_assessment(data):
    if not isinstance(data, dict):
        raise ValueError("The AI response was not a JSON object.")
    required = ["status", "emergency_level", "urgency_title", "summary", "possible_conditions",
                "warning_signs", "first_aid", "care_recommendation", "follow_up_questions", "disclaimer"]
    if any(k not in data for k in required):
        raise ValueError("The AI response is incomplete.")
    if data["emergency_level"] not in {"Level 1", "Level 2", "Level 3", "Level 4"}:
        raise ValueError("The AI returned an invalid urgency level.")
    for key in ("possible_conditions", "warning_signs", "first_aid", "follow_up_questions"):
        if not isinstance(data[key], list):
            raise ValueError("The AI returned an invalid response format.")
    if not all(isinstance(x, str) for key in ("warning_signs", "first_aid", "follow_up_questions") for x in data[key]):
        raise ValueError("The AI returned invalid list items.")
    clean_conditions = []
    for item in data["possible_conditions"][:6]:
        if not isinstance(item, dict):
            continue
        clean_conditions.append({
            "name": str(item.get("name", "Possible explanation"))[:160],
            "explanation": str(item.get("explanation", ""))[:1000],
            "supporting_symptoms": [str(x)[:200] for x in item.get("supporting_symptoms", [])[:8] if isinstance(x, str)],
            "uncertainties": [str(x)[:200] for x in item.get("uncertainties", [])[:8] if isinstance(x, str)]
        })
    data["possible_conditions"] = clean_conditions
    for key in ("urgency_title", "summary", "care_recommendation", "disclaimer"):
        data[key] = str(data[key])[:2000]
    data["warning_signs"] = [x[:500] for x in data["warning_signs"][:12]]
    data["first_aid"] = [x[:500] for x in data["first_aid"][:12]]
    data["follow_up_questions"] = [x[:500] for x in data["follow_up_questions"][:8]]
    return data

def rate_limited(client_key):
    now = time.time()
    with _rate_lock:
        q = _request_times[client_key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= 8:
            return True
        q.append(now)
        return False

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def api_status():
    return jsonify({"configured": bool(os.getenv("GROQ_API_KEY")), "model": MODEL})

@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Please submit a valid symptom form."}), 400
    symptoms = payload.get("symptoms", "")
    if not isinstance(symptoms, str) or not symptoms.strip():
        return jsonify({"error": "Enter your symptoms before starting an assessment."}), 400
    if len(symptoms) > MAX_INPUT_CHARS:
        return jsonify({"error": f"Please keep the symptom description under {MAX_INPUT_CHARS} characters."}), 413
    client_key = request.remote_addr or "local"
    if rate_limited(client_key):
        return jsonify({"error": "Too many requests. Please wait a minute and try again."}), 429

    context_fields = []
    for key, label in (("age_group", "Age group"), ("duration", "Duration"), ("severity", "Severity"), ("additional_info", "Additional information")):
        value = payload.get(key, "")
        if isinstance(value, str) and value.strip():
            context_fields.append(f"{label}: {value.strip()[:500]}")
    user_text = "Reported symptoms: " + symptoms.strip() + "\n" + "\n".join(context_fields)
    flags = emergency_flags(user_text)

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        response = {"error": "Groq API key is not configured. Copy .env.example to .env and add your key. If this is an emergency, contact local emergency services now (Rescue 1122 in Pakistan where available)."}
        if flags:
            response["emergency"] = {"level": "Level 1", "flags": flags, "instruction": "Call local emergency services now. In Pakistan, Rescue 1122 may be available. Do not drive yourself."}
        return jsonify(response), 503

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = session.get("history", [])
    if isinstance(history, list):
        for item in history[-6:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
                messages.append({"role": item["role"], "content": item["content"][:5000]})
    messages.append({"role": "user", "content": user_text})
    try:
        client = Groq(api_key=api_key, timeout=25.0, max_retries=1)
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1600,
            response_format={"type": "json_object"}
        )
        raw = completion.choices[0].message.content or ""
        data = validate_assessment(json.loads(raw))
        data = safe_emergency_override(data, flags)
        history = (history if isinstance(history, list) else [])[-6:]
        history.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": json.dumps(data)}])
        session["history"] = history[-8:]
        return jsonify(data)
    except json.JSONDecodeError:
        message = "The AI returned an unreadable response. Please try again. If symptoms feel severe, seek urgent medical help."
        status = 502
    except ValueError as exc:
        message = str(exc) + " Please try again."
        status = 502
    except Exception as exc:
        error_name = type(exc).__name__
        if "Authentication" in error_name:
            message, status = "Groq rejected the API key. Check GROQ_API_KEY in your .env file.", 401
        elif "RateLimit" in error_name:
            message, status = "Groq rate limit reached. Wait a little and try again.", 429
        elif "Timeout" in error_name or "Connection" in error_name:
            message, status = "Could not reach Groq right now. Check your internet connection and try again.", 502
        else:
            message, status = "The AI service failed. Check your model name and API settings, then try again.", 502
    response = {"error": message}
    if flags:
        response["emergency"] = {"level": "Level 1", "flags": flags, "instruction": "Call local emergency services now. In Pakistan, Rescue 1122 may be available. Do not drive yourself."}
    return jsonify(response), status

@app.post("/api/clear")
def clear_session():
    session.pop("history", None)
    return jsonify({"ok": True, "message": "Current in-browser conversation context cleared."})

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request is too large. Please shorten the symptom description."}), 413

if __name__ == "__main__":
    # Local-only development server. Do not expose this server publicly.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
