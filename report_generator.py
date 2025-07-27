import csv
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
from reportlab.lib.units import cm

HISTO_TIMES = list(range(21))  # 0 to 20 minutes
TIMESLOTS_PATH = ".\\static\\timeslots.txt"
TEMP_DIR = ".\\data\\temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def generate_report(input_csv_path):
    try:
        # --- 1. Read CSV ---
        df = pd.read_csv(input_csv_path)
        df.columns = ['person', 'code', 'session', 'lastname', 'firstname', 'status', 'timestamp']
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by='timestamp')

        # --- 2. Filter valid pairs ---
        valid_rows = []
        used = set()

        for i in range(len(df)):
            if i in used:
                continue
            row = df.iloc[i]
            if row['status'] == 'ausgetreten':
                for j in range(i + 1, len(df)):
                    candidate = df.iloc[j]
                    if j in used:
                        continue
                    if candidate['status'] == 'eingetreten':
                        delta = candidate['timestamp'] - row['timestamp']
                        if timedelta(0) < delta <= timedelta(minutes=20):
                            valid_rows.append(row)
                            valid_rows.append(candidate)
                            used.add(i)
                            used.add(j)
                            break

        df_valid = pd.DataFrame(valid_rows)
        
        # sign data if valid
        df['valid_pair'] = pd.Series(df.index.isin(df_valid.index), index=df.index).map({True: '✓', False: 'x'})

        # --- 3. Calculate statistics ---
        pairs = [(valid_rows[i], valid_rows[i + 1]) for i in range(0, len(valid_rows), 2)]
        total_seconds = sum([(b['timestamp'] - a['timestamp']).total_seconds() for a, b in pairs])
        average_seconds = total_seconds / len(pairs) if pairs else 0

        def seconds_to_hms(seconds):
            return str(timedelta(seconds=int(seconds)))

        def seconds_to_ms(seconds):
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"

        total_duration_str = seconds_to_hms(total_seconds)
        average_duration_str = seconds_to_ms(average_seconds)
        count_pairs = len(pairs)

        # --- 4. Prepare heatmap ---
        # --- Read timeslots from file ---
        timeslots = []
        with open(TIMESLOTS_PATH, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                slot_num = parts[0]
                start = parts[1]
                end = parts[2]
                timeslots.append({'slot': slot_num, 'start': start, 'end': end})

        timeslots_df = pd.DataFrame(timeslots)

        # --- Convert time strings to datetime.time objects ---
        timeslots_df['start_dt'] = pd.to_datetime(timeslots_df['start'], format='%H:%M').dt.time
        timeslots_df['end_dt'] = pd.to_datetime(timeslots_df['end'], format='%H:%M').dt.time

        # --- Filter exits only ---
        heatmap_df = df[df['status'] == 'ausgetreten'].copy()

        # Helper function to assign time slot to each timestamp
        def assign_timeslot(timestamp):
            ts_time = timestamp.time()
            for _, row in timeslots_df.iterrows():
                if row['start_dt'] <= ts_time < row['end_dt']:
                    return row['slot']
            return None

        # Assign timeslot to each timestamp
        heatmap_df['timeslot'] = heatmap_df['timestamp'].apply(assign_timeslot)
        heatmap_df['weekday'] = heatmap_df['timestamp'].dt.dayofweek

        # Use all defined timeslots
        all_slots = timeslots_df['slot'].tolist()
        
        # Create pivot table (timeslot as index, weekday as columns)
        pivot = heatmap_df.pivot_table(index='timeslot', columns='weekday', aggfunc='size', fill_value=0)
        for weekday in range(5):
            if weekday not in pivot.columns:
                pivot[weekday] = 0
        pivot = pivot[[0, 1, 2, 3, 4]]
        
        pivot = pivot.reindex(all_slots, fill_value=0)

        # Sort by slot number
        pivot = pivot.reindex(sorted(pivot.index, key=int))

        # Y-axis labels with time window (e.g. "1: 07:50-08:35")
        yticklabels = []
        for slot in pivot.index:
            start = timeslots_df[timeslots_df['slot'] == slot]['start'].values[0]
            end = timeslots_df[timeslots_df['slot'] == slot]['end'].values[0]
            yticklabels.append(f"{slot}: {start}-{end}")

        # Save heatmap
        heatmap_file = os.path.join(TEMP_DIR, "heatmap.png")
        plt.figure(figsize=(8, 5))
        sns.heatmap(pivot, annot=True, fmt='d', cmap='Blues', cbar=False,
                    xticklabels=['Mo', 'Di', 'Mi', 'Do', 'Fr'],
                    yticklabels=yticklabels)
        plt.xlabel('Wochentag')
        plt.ylabel('Schulstunde')
        plt.tight_layout()
        plt.savefig(heatmap_file)
        plt.close()

        # --- Histogram ---
        durations_min = [(b['timestamp'] - a['timestamp']).total_seconds() / 60 for a, b in pairs]

        histogram_file = os.path.join(TEMP_DIR, "histogram.png")
        plt.figure(figsize=(6, 4))
        plt.hist(durations_min, bins=HISTO_TIMES, edgecolor='black', color='skyblue')
        plt.title('Verteilung der Austrittsdauer')
        plt.xlabel('Dauer (Minuten)')
        plt.ylabel('Anzahl')
        plt.xticks(HISTO_TIMES)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(histogram_file)
        plt.close()

        # --- Create PDF ---
        pdf_file_path = os.path.join(TEMP_DIR, f"{df.iloc[0]['code']}.pdf")

        doc = SimpleDocTemplate(pdf_file_path, pagesize=A4,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=2.5 * cm,
            rightMargin=1.5 * cm
        )
        elements = []
        styles = getSampleStyleSheet()

        # filename
        firstname = df.iloc[0]['firstname']
        lastname = df.iloc[0]['lastname']
        fullname = f"{firstname} {lastname}"
        now_dt = datetime.now()
        now_str = now_dt.strftime("%d.%m.%Y %H:%M")
        file_ts = now_dt.strftime("%Y-%m-%d_%H-%M")
        filename_base = f"Auswertung_{lastname}-{firstname}_{file_ts}".replace(" ", "_").replace(":", "-")


        def add_page_elements(canvas, doc):
            canvas.saveState()
            header_text = f"Auswertung von {fullname} am {now_str}"
            canvas.setFont('Helvetica', 9)
            canvas.drawString(2 * cm, A4[1] - 1.2 * cm, header_text)
            canvas.setTitle(header_text)
            canvas.restoreState()

        def df_to_table(df):
            column_map = {
                'person': 'Lehrkraft',
                'code': 'Unterrichtsgruppe',
                'session': 'ID',
                'lastname': 'Nachname',
                'firstname': 'Vorname',
                'status': 'Status',
                'timestamp': 'Zeitstempel',
                'valid_pair': 'valide'
            }
            headers = [column_map.get(col, col) for col in df.columns]
            data = [headers] + df.astype(str).values.tolist()
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            return table

        elements.append(Paragraph("Alle Einträge (ungefiltert)", styles['Heading2']))        
        elements.append(Spacer(1, 12))
        elements.append(df_to_table(df))
        elements.append(PageBreak())

        elements.append(Paragraph("Gefilterte Ein-/Austrittspaare", styles['Heading2']))        
        elements.append(Spacer(1, 12))
        elements.append(df_to_table(df_valid))
        elements.append(PageBreak())

        elements.append(Paragraph("Statistiken", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Anzahl Ein/Austritte: {count_pairs}", styles['Normal']))
        elements.append(Paragraph(f"Durchschnittliche Dauer pro Austritt: {average_duration_str} Minuten", styles['Normal']))
        elements.append(Paragraph(f"Gesamte Zeit außerhalb: {total_duration_str} Stunden", styles['Normal']))
        elements.append(Spacer(1, 24))

        elements.append(Paragraph("Verteilung der Austrittsdauern", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Image(histogram_file, width=15 * cm, height=9 * cm))
        elements.append(Spacer(1, 24))

        elements.append(Paragraph("Heatmap der Austritte", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Image(heatmap_file, width=15 * cm, height=9 * cm))

        doc.build(elements, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
            
        return {'status': 'OK', 'pdf_path': pdf_file_path, 'filename': filename_base}

    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}