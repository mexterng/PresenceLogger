import os
import csv
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import threading

app = Flask(__name__)
lock = threading.Lock()

DATA_DIR = './data/groups'
OUTPUT_FILE = './data/output.csv'

def read_group_list():
    return [file[:-4] for file in os.listdir(DATA_DIR) if file.endswith('.csv')]

def read_group_members(filename):
    path = os.path.join(DATA_DIR, filename+'.csv')
    members = []
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            members.append({
                'id': row.get('id', ''),
                'firstname': row.get('firstname', ''),
                'lastname': row.get('lastname', '')
            })
    return members

@app.route('/')
def id():
    groups = read_group_list()
    return render_template('index.html', groups=groups)

@app.route('/get_members', methods=['POST'])
def get_members():
    group = request.get_json().get('group')
    if not group:
        return jsonify({'error': 'Keine Gruppe angegeben'}), 400
    try:
        print(f"Anfrage für Mitglieder der Gruppe: {group}")
        members = read_group_members(group)
        return jsonify({'members': members})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit_action', methods=['POST'])
def submit_action():
    data = request.get_json()
    initials = data.get('initials')
    group = data.get('group')
    people = data.get('people')
    action = data.get('action')  # "eingetreten" oder "ausgetreten"

    if not (initials and group and people and action):
        return jsonify({'error': 'Unvollständige Angaben'}), 400

    with lock:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

        with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for person in people:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([initials, group, person['id'], person['lastname'], person['firstname'], action, timestamp])

    return jsonify({'status': 'OK', 'action': action, 'people': people})

@app.route("/edit")
def edit():
    id = request.args.get("id")

    if not id:
        return "Fehlender Parameter", 400

    today = datetime.now().date()
    entries = []
    with lock:
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["id"] == id:
                    try:
                        row_date = datetime.fromisoformat(row["timestamp"]).date()
                        if row_date == today:
                            entries.append(row)
                    except ValueError:
                        continue  # ignore rows with invalid timestamps
    entries.reverse()
    return render_template("edit.html", title="Einträge des heutigen Tages von",entries=entries, id=id)

@app.route("/edit-all")
def edit_all():
    id = request.args.get("id")
    
    if not id:
        return "Fehlender Parameter", 400

    entries = []
    with lock:
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["id"] == id:
                    try:
                        entries.append(row)
                    except ValueError:
                        continue  # ignore rows with invalid timestamps
    entries.reverse()
    return render_template("edit.html", title="Alle Einträge von", entries=entries, id=id, show_edit_all_link=False)

# ---------- Eintrag löschen ----------
@app.route("/api/delete_entry", methods=["POST"])
def delete_entry():
    target = request.get_json()

    removed = False
    with lock:
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fld = reader.fieldnames

        # keep all rows except the one that matches *totally*
        new_rows = []
        for row in rows:
            if (row["initials"] == target["initials"] and
                row["group"]   == target["group"]   and
                row["lastname"] == target["lastname"] and
                row["firstname"]  == target["firstname"]  and
                row["status"]   == target["status"]   and
                row["timestamp"]== target["timestamp"]):
                removed = True
                continue
            new_rows.append(row)

        if removed:
            with open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as f:
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

    updated = False
    with lock:
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows   = list(reader)
            fld    = reader.fieldnames

        for row in rows:
            if (row["initials"] == orig["initials"] and
                row["group"]   == orig["group"]   and
                row["lastname"] == orig["lastname"] and
                row["firstname"]  == orig["firstname"]  and
                row["status"]  == orig["status"]   and
                row["timestamp"] == orig["timestamp"]):
                row["status"]    = new["status"]
                row["timestamp"] = new["timestamp"]
                updated = True
                break
        
        rows.sort(key=lambda x: x["timestamp"])

        if updated:
            with open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fld)
                writer.writeheader()
                writer.writerows(rows)

    return jsonify({"updated": updated})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=False)