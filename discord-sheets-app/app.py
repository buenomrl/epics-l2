import os
import tempfile
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from services.claude_vision import extract_bosses_from_image, extract_cc_members
from services.discord_sender import build_discord_message, build_whatsapp_message, send_to_discord
from services.cp_tracker import load_cp_list, process_members, list_all_cps, add_member_to_cp_list
from services.sheets_writer import save_attendance

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_cp_list_path() -> str:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
    default = os.path.join(os.path.dirname(_app_dir), "CP List.txt")
    return os.getenv("CP_LIST_PATH", default)


# ── Boss → Discord ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/preview", methods=["POST"])
def preview():
    if "image" not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400
    file = request.files["image"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Formato inválido. Use JPG, PNG ou WebP."}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        bosses = extract_bosses_from_image(tmp_path)
        if not bosses:
            return jsonify({"error": "Nenhum boss Dead encontrado na imagem."}), 400
        discord_msg = build_discord_message(bosses)
        whatsapp_msg = build_whatsapp_message(bosses)
        return jsonify({"discord_message": discord_msg, "whatsapp_message": whatsapp_msg, "bosses": bosses})
    except Exception as e:
        msg = str(e)
        if "credit balance is too low" in msg or "Your credit balance" in msg:
            return jsonify({"error": "Sem créditos na API. Acesse console.anthropic.com para adicionar."}), 402
        return jsonify({"error": f"Erro ao processar imagem: {msg}"}), 500
    finally:
        os.unlink(tmp_path)


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Mensagem não fornecida."}), 400
    try:
        result = send_to_discord(data["message"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── CC → Planilha ─────────────────────────────────────────────────────────────

@app.route("/process-cc", methods=["POST"])
def process_cc():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    cp_list_path = get_cp_list_path()
    if not os.path.exists(cp_list_path):
        return jsonify({"error": f"CP List não encontrada em: {cp_list_path}"}), 400

    cp_map = load_cp_list(cp_list_path)
    all_cps = list_all_cps(cp_list_path)
    all_members: list[str] = []
    errors: list[str] = []

    tmp_paths = []
    for file in files:
        if not file.filename or not allowed_file(file.filename):
            continue
        ext = file.filename.rsplit(".", 1)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            file.save(tmp.name)
            tmp_paths.append((tmp.name, file.filename))

    for tmp_path, original_name in tmp_paths:
        try:
            members = extract_cc_members(tmp_path)
            all_members.extend(members)
        except Exception as e:
            msg = str(e)
            if "credit balance is too low" in msg or "Your credit balance" in msg:
                return jsonify({"error": "Sem créditos na API. Acesse console.anthropic.com para adicionar."}), 402
            errors.append(f"{original_name}: {msg}")
        finally:
            os.unlink(tmp_path)

    if not all_members and errors:
        return jsonify({"error": "Erro ao processar imagens: " + "; ".join(errors)}), 500

    attendance = process_members(all_members, cp_map)

    return jsonify({
        "attendance": attendance,
        "all_cps": all_cps,
        "errors": errors,
        "total": len(attendance),
    })


@app.route("/save-attendance", methods=["POST"])
def save_attendance_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados não fornecidos."}), 400

    boss = data.get("boss", "").strip()
    date = data.get("date", "").strip()
    attendance = data.get("attendance", [])

    if not boss or not date:
        return jsonify({"error": "Boss e data são obrigatórios."}), 400
    if not attendance:
        return jsonify({"error": "Nenhum membro para salvar."}), 400

    try:
        result = save_attendance(boss, date, attendance)

        # Add newly identified members to CP List
        cp_list_path = get_cp_list_path()
        newly_added = []
        for entry in attendance:
            if entry.get("match_type") == "not_found" and entry.get("cp") and entry.get("member"):
                added = add_member_to_cp_list(cp_list_path, entry["member"].strip(), entry["cp"].strip())
                if added:
                    newly_added.append({"member": entry["member"], "cp": entry["cp"]})

        result["newly_added_to_cp_list"] = newly_added
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
