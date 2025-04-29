import os
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import base64
import io
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'K0M3zP9SBn'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'log'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_values(csv_path, column_index):
    cmd = f"awk -F, 'NR>1 {{print ${column_index}}}' \"{csv_path}\" | sort -u"
    result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            shell=True 
        )
    return [x for x in result.stdout.splitlines() if x]

@app.route('/')
def index():
    return redirect(url_for('view_logs'))

@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'logfile' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('view_logs'))
    
    file = request.files['logfile']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('view_logs'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('File successfully uploaded')
        return redirect(url_for('view_logs'))
    else:
        return redirect(url_for('view_logs'))

@app.route('/display_logs/<filename>')
def display_logs(filename):
    log_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(log_path):
        flash('File not found')
        return redirect(url_for('index'))
    
    csv_filename = filename.replace('.log', '.csv')
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)

    if not os.path.exists(csv_path):
        try:
            subprocess.run(["./scripts/parse_logs.sh", log_path, csv_path], check=True)
        except subprocess.CalledProcessError as e:
            flash('Error processing log file')
            return redirect(url_for('view_logs'))

    months = get_unique_values(csv_path, 1)
    days = get_unique_values(csv_path, 2)
    hours = sorted(set(h.split(':')[0] for h in get_unique_values(csv_path, 3) if h))
    levels = get_unique_values(csv_path, 5)
    eventids = get_unique_values(csv_path, 7)

    with open(csv_path, 'r') as f:
        headers = f.readline().strip().split(',')
        rows = [line.strip().split(',') for line in f]

    return render_template(
        'display.html',
        headers=headers,
        rows=rows,
        filename=filename,
        csv_filename=csv_filename,
        months=months,
        days=days,
        hours=hours,
        levels=levels,
        eventids=eventids,
        selected_month='',
        selected_day='',
        selected_hour='',
        selected_level='',
        selected_eventid=''
    )

@app.route('/filter_logs/<filename>', methods=['POST'])
def filter_logs(filename):
    month = request.form.get('month', '')
    day = request.form.get('day', '')
    hour = request.form.get('hour', '')
    level = request.form.get('level', '')
    eventid = request.form.get('eventid', '')

    csv_filename = filename.replace('.log', '.csv')
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
    filtered_filename = f'filtered_{csv_filename}'
    filtered_path = os.path.join(app.config['UPLOAD_FOLDER'], filtered_filename)
    
    subprocess.run([
        "./scripts/filter_logs.sh", csv_path, filtered_path, 
        month, day, hour, level, eventid
    ], check=True, text=True, capture_output=True)

    if not os.path.exists(filtered_path):
        raise Exception("Filtered file not created")
    
    months = get_unique_values(csv_path, 1)
    days = get_unique_values(csv_path, 2)
    hours = sorted(set(h.split(':')[0] for h in get_unique_values(csv_path, 3) if h))
    levels = get_unique_values(csv_path, 5)
    eventids = get_unique_values(csv_path, 7)

    with open(filtered_path, 'r') as f:
        headers = f.readline().strip().split(',')
        rows = [line.strip().split(',') for line in f]

    return render_template(
        'display.html',
        headers=headers,
        rows=rows,
        filename=filename,
        csv_filename=filtered_filename,
        months=months,
        days=days,
        hours=hours,
        levels=levels,
        eventids=eventids,
        selected_month=month,
        selected_day=day,
        selected_hour=hour,
        selected_level=level,
        selected_eventid=eventid
    )

@app.route('/download/<csv_filename>')
def download_csv(csv_filename):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
    if not os.path.exists(csv_path):
        log_filename = csv_filename.replace('.csv', '.log')
        log_path = os.path.join(app.config['UPLOAD_FOLDER'], log_filename)
        
        if os.path.exists(log_path):
            try:
                subprocess.run(["./scripts/parse_logs.sh", log_path, csv_path], check=True)
            except subprocess.CalledProcessError as e:
                flash('Error generating CSV file')
                return redirect(url_for('view_logs'))
        else:
            flash('File not found')
            return redirect(url_for('view_logs'))
    
    return send_file(csv_path, as_attachment=True)

@app.route('/view_logs')
def view_logs():
    log_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                if f.endswith('.log')]
    return render_template('view_logs.html', log_files=log_files)

@app.route('/plots/<filename>')
def show_plots(filename):
    log_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.log', '.csv'))

    if not os.path.exists(csv_path):
        try:
            subprocess.run(["./scripts/parse_logs.sh", log_path, csv_path], check=True)
        except subprocess.CalledProcessError as e:
            flash('Error processing log file')
            return redirect(url_for('view_logs'))

    from_date = request.args.get('from_date', '')
    from_time = request.args.get('from_time', '00:00:00')
    to_date = request.args.get('to_date', '')
    to_time = request.args.get('to_time', '23:59:59')

    headers, data = read_csv_data(csv_path)
    filtered_data = filter_by_datetime(data, from_date, from_time, to_date, to_time)

    plots = {
        'line_plot': generate_line_plot_from_data(headers, filtered_data),
        'pie_chart': generate_pie_plot_from_data(headers, filtered_data),
        'bar_chart': generate_bar_plot_from_data(headers, filtered_data),
        'filename': filename,
        'from_date': from_date,
        'from_time': from_time if from_time != '00:00:00' else '',
        'to_date': to_date,
        'to_time': to_time if to_time != '23:59:59' else ''
    }
    
    return render_template('plots.html', **plots)

def filter_by_datetime(data, from_date, from_time, to_date, to_time):
    if not any([from_date, from_time, to_date, to_time]):
        return data

    filtered = []
    for row in data:
        if len(row) < 4:
            continue

        try:
            month, day, time, year = row[0], row[1], row[2], row[3]
            row_dt = datetime.strptime(f"{month} {day} {year} {time}", "%b %d %Y %H:%M:%S")
        except ValueError:
            continue

        if from_date:
            try:
                from_dt_str = f"{from_date} {from_time}" if from_time else f"{from_date} 00:00:00"
                from_dt = datetime.strptime(from_dt_str, "%Y-%m-%d %H:%M:%S")
                if row_dt < from_dt:
                    continue
            except ValueError:
                continue

        if to_date:
            try:
                to_dt_str = f"{to_date} {to_time}" if to_time else f"{to_date} 23:59:59"
                to_dt = datetime.strptime(to_dt_str, "%Y-%m-%d %H:%M:%S")
                if row_dt > to_dt:
                    continue
            except ValueError:
                continue

        filtered.append(row)

    return filtered

def read_csv_data(csv_path):
    with open(csv_path, 'r') as f:
        headers = f.readline().strip().split(',')
        data = [line.strip().split(',') for line in f]
    return headers, data

def generate_line_plot_from_data(headers, data):
    time_counts = {}
    for row in data:
        if len(row) >= 4:
            time_slot = f"{row[0]}-{row[1]}-{row[3]} {row[2].split(':')[0]}"
            time_counts[time_slot] = time_counts.get(time_slot, 0) + 1
    
    times = sorted(time_counts.keys())
    counts = [time_counts[t] for t in times]

    plt.figure(figsize=(10, 5))
    plt.plot(times, counts, marker='o', linestyle='-', color='skyblue')
    plt.title('Events Over Time')
    plt.xlabel('Time (Month-Day-Year Hour)')
    plt.ylabel('Number of Entries')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plot_to_base64()

def generate_pie_plot_from_data(headers, data):
    counts = {}
    for row in data:
        if len(row) >= 5:
            level = row[4].lower()
            counts[level] = counts.get(level, 0) + 1

    if not counts:
        counts = {'notice': 0, 'error': 0}

    plt.figure(figsize=(6, 6))
    plt.pie(counts.values(), labels=counts.keys(), autopct='%1.1f%%')
    plt.title('Level Distribution')
    return plot_to_base64()

def generate_bar_plot_from_data(headers, data):
    codes = {}
    for row in data:
        if len(row) >= 7:
            code = row[6]
            codes[code] = codes.get(code, 0) + 1

    if not codes:
        codes = {'No Data': 0}

    x = list(codes.keys())
    y = list(codes.values())

    plt.figure(figsize=(14, 7))
    bars = plt.bar(x, y, color='skyblue')
    plt.title('Event Code Distribution')
    plt.xlabel('Event Code')
    plt.ylabel('Frequency')
    
    max_y = max(y) if y and max(y) > 0 else 1
    plt.ylim(bottom=0, top=max_y * 1.5)

    for bar in bars:
        height = bar.get_height()
        if not np.isnan(height):
            plt.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5),
                        textcoords="offset points",
                        ha='center', va='bottom')

    plt.tight_layout()
    return plot_to_base64()

def plot_to_base64():
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode('utf-8')

@app.route('/download_plot/<plot_type>/<filename>')
def download_plot(plot_type, filename):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.log', '.csv'))
    headers, data = read_csv_data(csv_path)
    
    from_date = request.args.get('from_date', '')
    from_time = request.args.get('from_time', '00:00:00')
    to_date = request.args.get('to_date', '')
    to_time = request.args.get('to_time', '23:59:59')
    
    filtered_data = filter_by_datetime(data, from_date, from_time, to_date, to_time)

    if plot_type == 'line':
        plot = generate_line_plot_from_data(headers, filtered_data)
    elif plot_type == 'pie':
        plot = generate_pie_plot_from_data(headers, filtered_data)
    elif plot_type == 'bar':
        plot = generate_bar_plot_from_data(headers, filtered_data)
    else:
        return "Invalid Plot Type", 400
    
    img_data = base64.b64decode(plot)
    return send_file(io.BytesIO(img_data),
                     mimetype='image/png',
                     as_attachment=True,
                     download_name=f"{plot_type}_plot.png")