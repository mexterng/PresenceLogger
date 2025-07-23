import os
import csv
from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request
from datetime import datetime
import threading
from io import BytesIO
import zipfile
from report_generator import generate_report
import shutil
import time

app = Flask(__name__)
lock = threading.Lock()

ADMIN_PSWD_PATH = ".\\data\\admin-pswd.key"
GROUPS_DIR = ".\\data\\groups"
LOG_FILE_PATH = ".\\data\\log"
ASV_PATH = ".\\data\\asv-data.csv"

REQUIRED_HEADERS_ASV = {"Klasse", "Familienname", "Rufname", "lokales Differenzierungsmerkmal"}
REQUIRED_HEADERS_GROUPCSV = {"id", "lastname", "firstname"}


def read_group_list():
    return [file[:-4] for file in os.listdir(GROUPS_DIR) if file.endswith(".csv")]


def read_group_members(filename):
    path = os.path.join(GROUPS_DIR, filename + ".csv")
    members = []
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            members.append(
                {
                    "id": row.get("id", ""),
                    "firstname": row.get("firstname", ""),
                    "lastname": row.get("lastname", ""),
                }
            )
    return members


def generate_zip(dir):
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for foldername, subfolders, filenames in os.walk(dir):
            if not filenames and not subfolders: # empty folders
                #print(f"Adding {foldername} to ZIP archive") # TODO: sse-connection
                zf.write(foldername, os.path.relpath(foldername, dir) + '/')
            for filename in filenames: # files
                file_path = os.path.join(foldername, filename)
                #print(f"Adding {file_path} to ZIP archive") # TODO: sse-connection
                zf.write(file_path, os.path.relpath(file_path, dir))
    
    memory_file.seek(0)
    return memory_file

@app.route("/")
def index():
    groups = read_group_list()
    groups.sort(key=str.lower)
    return render_template("index.html", groups=groups)


@app.route("/get_members", methods=["POST"])
def get_members():
    group = request.get_json().get("group")
    if not group:
        return jsonify({"error": "Keine Gruppe angegeben"}), 400
    try:
        members = read_group_members(group)
        return jsonify({"members": members})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/submit_action", methods=["POST"])
def submit_action():
    data = request.get_json()
    initials = data.get("initials")
    group = data.get("group")
    people = data.get("people")
    action = data.get("action")  # "eingetreten" oder "ausgetreten"

    if not (initials and group and people and action):
        return jsonify({"error": "Unvollständige Angaben", "initials": initials, "group": group, "people": people, "action":action}), 400

    with lock:
        os.makedirs(LOG_FILE_PATH, exist_ok=True)
        
        for person in people:
            person_id = person["id"]
            log_file = os.path.join(LOG_FILE_PATH, f"{person_id}.csv")
            
            # Create a new CSV file with header if it doesn't exist.
            if not os.path.exists(log_file):
                with open(log_file, "w", newline="", encoding="utf-8") as f_out:
                    csv.writer(f_out).writerow(
                        [
                            "initials",
                            "group",
                            "id",
                            "lastname",
                            "firstname",
                            "status",
                            "timestamp",
                        ]
                    )
        
        
        # Add new entry to log-file
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for person in people:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow(
                    [
                        initials,
                        group,
                        person["id"],
                        person["lastname"],
                        person["firstname"],
                        action,
                        timestamp,
                    ]
                )

    return jsonify({"status": "OK", "action": action, "people": people})


@app.route("/edit")
def edit():
    id = request.args.get("id")

    if not id:
        return "Fehlender Parameter (id)", 400

    today = datetime.now().date()
    entries = []
    
    log_file = os.path.join(LOG_FILE_PATH, f"{id}.csv")
    
    if os.path.exists(log_file):
        with lock:
            with open(log_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row_date = datetime.fromisoformat(row["timestamp"]).date()
                        if row_date == today:
                            entries.append(row)
                    except ValueError:
                        continue  # ignore rows with invalid timestamps
        entries.reverse()
    return render_template(
        "edit.html", title="Einträge des heutigen Tages von", entries=entries, id=id
    )


@app.route("/edit-all")
def edit_all():
    id = request.args.get("id")

    if not id:
        return "Fehlender Parameter (id)", 400

    entries = []
    
    log_file = os.path.join(LOG_FILE_PATH, f"{id}.csv")
    
    if os.path.exists(log_file):
        with lock:
            with open(log_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        entries.append(row)
                    except ValueError:
                        continue  # ignore rows with invalid timestamps
        entries.reverse()
    return render_template(
        "edit.html",
        title="Alle Einträge von",
        entries=entries,
        id=id,
        show_edit_all_link=False,
    )


# ---------- Eintrag löschen ----------
@app.route("/api/delete_entry", methods=["POST"])
def delete_entry():
    target = request.get_json()
    person_id = target.get("id")

    if not person_id:
        return jsonify({"error": "Ungültige ID"}), 400

    log_file = os.path.join(LOG_FILE_PATH, f"{person_id}.csv")
    
    if not os.path.exists(log_file):
        return jsonify({"error": f"Keine Einträge zu {person_id} gefunden."}), 404

    removed = False
    with lock:
        with open(log_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fld = reader.fieldnames

        # keep all rows except the one that matches *totally*
        new_rows = []
        for row in rows:
            if (
                row["initials"] == target["initials"]
                and row["group"] == target["group"]
                and row["lastname"] == target["lastname"]
                and row["firstname"] == target["firstname"]
                and row["status"] == target["status"]
                and row["timestamp"] == target["timestamp"]
            ):
                removed = True
                continue
            new_rows.append(row)

        if removed:
            with open(log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fld)
                writer.writeheader()
                writer.writerows(new_rows)

    return jsonify({"removed": removed})


# ---------- Eintrag aktualisieren ----------
@app.route("/api/update_entry", methods=["POST"])
def update_entry():
    data = request.get_json()
    orig = data["original"]
    new = data["updated"]
    person_id = orig.get("id")
    
    if not person_id:
        return jsonify({"error": "Ungültige ID"}), 400

    log_file = os.path.join(LOG_FILE_PATH, f"{person_id}.csv")

    if not os.path.exists(log_file):
        return jsonify({"error": "Keine Einträge gefunden"}), 404
    
    updated = False
    with lock:
        with open(log_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fld = reader.fieldnames

        for row in rows:
            if (
                row["initials"] == orig["initials"]
                and row["group"] == orig["group"]
                and row["lastname"] == orig["lastname"]
                and row["firstname"] == orig["firstname"]
                and row["status"] == orig["status"]
                and row["timestamp"] == orig["timestamp"]
            ):
                row["status"] = new["status"]
                row["timestamp"] = new["timestamp"]
                updated = True
                break

        rows.sort(key=lambda x: x["timestamp"])

        if updated:
            with open(log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fld)
                writer.writeheader()
                writer.writerows(rows)

    return jsonify({"updated": updated})

@app.route("/admin")
def admin():
    def check_auth(username, password):
        if username == 'admin':
            try:
                with open(ADMIN_PSWD_PATH, 'r') as f:
                    stored_password = f.read().strip()
                return password == stored_password
            except FileNotFoundError:
                return False
        return False

    def authenticate():
        return Response(
            'Authentication required.', 401,
            {'WWW-Authenticate': 'Basic realm="Admin Bereich"'}
        )
        
    auth = request.authorization
    if auth:
        print(auth.username, auth.password)
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    return render_template("admin.html")

@app.route("/api/export-logs", methods=["GET"])
def export_logs():    
    zip_file = generate_zip(LOG_FILE_PATH)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_filename = f"logs_{timestamp}.zip"
    # send zip-file as download
    return send_file(zip_file, mimetype='application/zip', as_attachment=True, download_name=zip_filename)

@app.route("/api/export-groups", methods=["GET"])
def export_groups():    
    zip_file = generate_zip(GROUPS_DIR)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_filename = f"groups_{timestamp}.zip"
    # send zip-file as download
    return send_file(zip_file, mimetype='application/zip', as_attachment=True, download_name=zip_filename)

@app.route("/api/export-asv", methods=["GET"])
def export_asv():
    error_message = jsonify({"error": "Die ASV-Datei existiert nicht. Vermutlich wurden Gruppen direkt importiert."}), 404
    if request.args.get("status-check") == "true":
        if not os.path.exists(ASV_PATH):
            return error_message
        return jsonify({"ok": True})
    
    if not os.path.exists(ASV_PATH):
        return error_message

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"asv-data_{timestamp}.csv"
    return send_file(ASV_PATH, as_attachment=True, download_name=filename)

@app.route("/api/delete-log", methods=["POST"])
def delete_log():   
    confirm = request.json.get('confirm')
    if confirm == True:
        try:
            for filename in os.listdir(LOG_FILE_PATH):
                file_path = os.path.join(LOG_FILE_PATH, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            return "Log-Dateien wurden gelöscht.", 200
        except Exception as e:
            return f"Fehler beim Löschen der Log-Dateien: {str(e)}", 500

    return "Bestätigung fehlgeschlagen. Log-Dateien wurden NICHT gelöscht.", 400

@app.route("/api/import-asv", methods=["POST"])
def import_asv():
    if 'confirm' not in request.form or request.form['confirm'] != 'true':
        return jsonify({"error": "Bestätigung fehlgeschlagen. ASV-Datei wurde NICHT importiert."}), 400
    
    if 'file' not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen."}), 400
            
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Keine Datei ausgewählt."}), 400
        
    file.save(ASV_PATH)
    return jsonify({"message": "ASV-Datei erfolgreich importiert."}), 200

@app.route("/api/generate-groups", methods=["POST"])
def generate_group():
    ### helper ###
    def cls_to_filename(cls_str: str) -> str:
        # Convert class name to filename in format '00a_IT_1.csv'
        cls_str = cls_str.strip()
        if cls_str and cls_str[0].isdigit() and not cls_str.startswith('1'):
            cls_str = '0' + cls_str
        return f"{cls_str}.csv"

    def ensure_file_with_header(path: str) -> None:
        # Create a new CSV file with header if it doesn't exist
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f_out:
                csv.writer(f_out).writerow(["id", "lastname", "firstname"])
    ### helper ###
    
    confirm = request.json.get('confirm')
    if confirm == True:
        os.makedirs(GROUPS_DIR, exist_ok=True)
        try:
            with open(ASV_PATH, newline="", encoding="utf-8-sig") as f_in:
                reader = csv.DictReader(f_in, delimiter=";")
                
                missing = REQUIRED_HEADERS_ASV - set(reader.fieldnames or [])
                if missing:
                    raise RuntimeError(f"Fehlende Spalten: {', '.join(missing)} in ASV-Datei")
                
                # delete old groups
                for filename in os.listdir(GROUPS_DIR):
                    file_path = os.path.join(GROUPS_DIR, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # add new groups
                for row in reader:
                    filename = cls_to_filename(row["Klasse"])
                    filepath = os.path.join(GROUPS_DIR, filename)
                    ensure_file_with_header(filepath)

                    with open(filepath, "a", newline="", encoding="utf-8") as f_out:
                        csv.writer(f_out, delimiter=",").writerow([
                            row["lokales Differenzierungsmerkmal"],
                            row["Familienname"],
                            row["Rufname"]
                        ])
            return "Gruppen wurden erfolgreich aktualisiert.", 200
        except ValueError as ve:
            return str(ve), 400
        except RuntimeError as re:
            return str(re), 400

    return "Bestätigung fehlgeschlagen. Gruppen wurden NICHT aktualisiert.", 400

@app.route("/api/import-groups", methods=["POST"])
def import_groups():
    if 'confirm' not in request.form or request.form['confirm'] != 'true':
        return jsonify({"error": "Bestätigung fehlgeschlagen. ASV-Datei wurde NICHT importiert."}), 400
    
    if 'files' not in request.files:
        return jsonify({"error": "Keine Dateien hochgeladen."}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "Keine Dateien ausgewählt."}), 40

    # Header-validation
    for file in files:
        if not file.filename.endswith('.csv'):
            return jsonify({"error": f"Ungültiges Dateiformat: {file.filename}"}), 400

        try:
            content = file.stream.read().decode("utf-8").splitlines()
            reader = csv.reader(content)
            headers = next(reader)
            header_set = set(h.strip() for h in headers)

            if not REQUIRED_HEADERS_GROUPCSV.issubset(header_set):
                return jsonify({
                    "error": f"Datei '{file.filename}' fehlt mindestens ein Pflicht-Header. "
                             f"Erwartet: {REQUIRED_HEADERS_GROUPCSV}, gefunden: {header_set}"
                }), 400

            file.stream.seek(0)  # Reset für das Speichern
        except Exception as e:
            return jsonify({"error": f"Fehler beim Verarbeiten von {file.filename}: {str(e)}"}), 400

    # delete old groups
    for filename in os.listdir(GROUPS_DIR):
        file_path = os.path.join(GROUPS_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    # delete ASV-file to avoid inconsistencies between the ASV-file and the group-data. 
    os.remove(ASV_PATH)
    
    # add new groups
    for file in files:
        filepath = os.path.join(GROUPS_DIR, file.filename)
        file.save(filepath)

    return jsonify({"message": f"{len(files)} Gruppen-Dateien erfolgreich importiert."}), 200

@app.route("/export", methods=["GET"])
def export():
    pass

@app.route("/api/exportPDF-group", methods=["GET"])
def exportPDF_group():
    pass

@app.route("/api/exportPDF-person", methods=["GET"])
def exportPDF_person():
    person_id = request.args.get('id')
    if not person_id:
        return "Missing 'id' parameter", 400

    csv_path = os.path.join(LOG_FILE_PATH, person_id + ".csv")
    if not os.path.exists(csv_path):
        return f"CSV file for id {person_id} not found", 404

    try:
        pdf_response = generate_report(csv_path)
        if not pdf_response["status"] == "OK":
            return "PDF creation failed", 500

        pdf_path = pdf_response["pdf_path"]
        filename = pdf_response.get("filename", "report")
        temp_dir = os.path.dirname(pdf_path)  # <--- dynamic extraction

        @after_this_request
        def cleanup_temp_dir(response):
            delayed_cleanup(temp_dir)  # temp_dir = os.path.dirname(pdf_path)
            return response

        return send_file(pdf_path, as_attachment=True, download_name=f"{filename}.pdf")

    except Exception as e:
        return f"Error during PDF creation: {str(e)}", 500

def delayed_cleanup(path, delay=1):
    def remove():
        time.sleep(delay)
        try:
            shutil.rmtree(path)
        except Exception as e:
            print(f"[Cleanup Warning] Could not remove temp dir: {e}")
    threading.Thread(target=remove).start()
    
@app.route("/api/exportCSV-group", methods=["GET"])
def exportCSV_group():
    pass

@app.route("/api/exportCSV-person", methods=["GET"])
def exportCSV_person():
    person_id = request.args.get('id')
    if not person_id:
        return "Missing 'id' parameter", 400

    csv_path = os.path.join(LOG_FILE_PATH, person_id + ".csv")
    
    if not os.path.exists(csv_path):
        return f"CSV file for id {person_id} not found", 404

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"log-data_{person_id}_{timestamp}.csv"
    return send_file(csv_path, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=False)