"""Minimal HTTP server for previewing questionnaire UI."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["PYTHONUTF8"] = "1"

from flask import Flask, render_template, request, jsonify, send_file
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = "preview-only"

from questionnaire_schema import QUESTIONNAIRES, QUESTIONNAIRE_ORDER

QUESTIONNAIRE_DATA_DIR = Path("data/questionnaires")
QUESTIONNAIRE_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _q_path(club_slug, member_slug, q_id):
    d = QUESTIONNAIRE_DATA_DIR / club_slug / member_slug
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{q_id}.json"


def _q_statuses(club_slug, member_slug):
    statuses = {}
    for q_id in QUESTIONNAIRE_ORDER:
        p = _q_path(club_slug, member_slug, q_id)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            has_content = False
            all_filled = True
            for section_data in data.get("data", {}).values():
                if isinstance(section_data, list):
                    for item in section_data:
                        for v in item.values():
                            if v:
                                has_content = True
                            else:
                                all_filled = False
                elif isinstance(section_data, dict):
                    for v in section_data.values():
                        if v:
                            has_content = True
                        else:
                            all_filled = False
            if has_content and all_filled:
                statuses[q_id] = "completed"
            elif has_content:
                statuses[q_id] = "partial"
        else:
            statuses[q_id] = "empty"
    return statuses


def _get_clubs():
    clubs_dir = Path("data/clubs")
    if not clubs_dir.exists():
        return []
    return [(d.name, d.name.replace("-", " ").title()) for d in sorted(clubs_dir.iterdir()) if d.is_dir()]


@app.route("/")
def index():
    return '<a href="/questionnaires">Vai ai Questionari</a>'


@app.route("/questionnaires")
def questionnaire_index():
    club = request.args.get("club", "")
    member = request.args.get("member", "")
    statuses = _q_statuses(club, member) if club and member else {}
    return render_template(
        "questionnaire_index.html",
        questionnaires=QUESTIONNAIRES,
        order=QUESTIONNAIRE_ORDER,
        clubs=_get_clubs(),
        current_club=club,
        member_name=member.replace("-", " ").title() if member else "",
        member_role=request.args.get("role", "board"),
        statuses=statuses,
        year=datetime.now().year,
    )


@app.route("/questionnaire/<club_slug>/<member_slug>/<q_id>")
def questionnaire_form(club_slug, member_slug, q_id):
    if q_id not in QUESTIONNAIRES:
        return "Questionario non trovato", 404
    q = QUESTIONNAIRES[q_id]
    role = request.args.get("role", "board")
    display_name = request.args.get("display_name", member_slug.replace("-", " ").title())
    p = _q_path(club_slug, member_slug, q_id)
    saved = {}
    if p.exists():
        saved = json.loads(p.read_text(encoding="utf-8")).get("data", {})
    idx = QUESTIONNAIRE_ORDER.index(q_id)
    prev_id = QUESTIONNAIRE_ORDER[idx - 1] if idx > 0 else None
    next_id = QUESTIONNAIRE_ORDER[idx + 1] if idx < len(QUESTIONNAIRE_ORDER) - 1 else None
    return render_template(
        "questionnaire_form.html",
        questionnaire=q,
        q_id=q_id,
        club_slug=club_slug,
        member_slug=member_slug,
        role=role,
        display_name=display_name,
        saved=saved,
        saved_json=json.dumps(saved, ensure_ascii=False),
        prev_id=prev_id,
        prev_title=QUESTIONNAIRES[prev_id]["title"] if prev_id else "",
        next_id=next_id,
        next_title=QUESTIONNAIRES[next_id]["title"] if next_id else "",
    )


@app.route("/api/questionnaire/<club_slug>/<member_slug>/<q_id>", methods=["POST"])
def api_save(club_slug, member_slug, q_id):
    if q_id not in QUESTIONNAIRES:
        return jsonify({"error": "Unknown"}), 404
    body = request.get_json()
    p = _q_path(club_slug, member_slug, q_id)
    record = {
        "club": club_slug,
        "member": member_slug,
        "questionnaire": q_id,
        "role": body.get("role", "board"),
        "display_name": body.get("display_name", member_slug),
        "data": body.get("data", {}),
        "updated_at": datetime.now().isoformat(),
    }
    p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"success": True})


@app.route("/funnel")
def funnel_page():
    return send_file("funnel_rooting_future.html")


@app.route("/free-swot")
def free_swot_page():
    return render_template("free_swot.html")


@app.route("/api/free-swot", methods=["POST"])
def api_free_swot():
    """Fallback senza AI — formatta input."""
    body = request.get_json()
    s = body.get("strengths", "")
    w = body.get("weaknesses", "")
    o = body.get("opportunities", "")
    t = body.get("threats", "")

    def bullets(text):
        if not text:
            return ""
        items = [x.strip() for x in text.replace("\n", ",").split(",") if x.strip()]
        return "".join(f"<div>• {i}</div>" for i in items)

    return jsonify({
        "success": True,
        "strengths": bullets(s),
        "weaknesses": bullets(w),
        "opportunities": bullets(o),
        "threats": bullets(t),
        "summary": f"Analisi SWOT per {body.get('club', 'Club')} ({body.get('category', '')}, {body.get('region', '')}). Per un piano strategico completo con 6 agenti AI, prova il servizio gratuito.",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
