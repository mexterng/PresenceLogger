import os
import csv
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import threading
from io import BytesIO
import zipfile

app = Flask(__name__)
lock = threading.Lock()

DATA_DIR = "./data/groups"
LOG_FILE_PATH = ".\\data\\log"


def read_group_list():
    return [file[:-4] for file in os.listdir(DATA_DIR) if file.endswith(".csv")]


def read_group_members(filename):
    path = os.path.join(DATA_DIR, filename + ".csv")
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
    return render_template("admin.html")

@app.route("/api/export-logs", methods=["GET"])
def export_logs():    
    zip_file = generate_zip(LOG_FILE_PATH)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_filename = f"logs_{timestamp}.zip"
    # send zip-file as download
    return send_file(zip_file, mimetype='application/zip', as_attachment=True, download_name=zip_filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=False)