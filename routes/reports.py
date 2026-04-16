# routes/reports.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, make_response
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
import calendar
import re
import pyecharts.options as opts
from pyecharts.charts import Bar, Line, Pie
from weasyprint import HTML
import tempfile
import os
import time

reports = Blueprint('reports', __name__, url_prefix='/reports')

# ---------- Helper: get office reference and ID from session ----------
def get_office_ref_and_id():
    office_id = session.get('office_id')
    if not office_id:
        return None, None
    office_ref = db.collection('OFFICES').document(office_id)
    return office_ref, office_id

# ---------- Helper: get office name ----------
def get_office_name(office_id):
    if not office_id:
        return None
    doc = db.collection('OFFICES').document(office_id).get()
    return doc.get('name') if doc.exists else None

# ---------- Helper: get service name from SERVICES collection ----------
def get_service_name(service_ref):
    try:
        if hasattr(service_ref, 'id'):
            service_id = service_ref.id
        elif isinstance(service_ref, str):
            path = service_ref.lstrip('/')
            parts = path.split('/')
            service_id = parts[-1] if parts else path
        else:
            return "Unknown Service"
        
        service_doc = db.collection('SERVICES').document(service_id).get()
        if service_doc.exists:
            service_data = service_doc.to_dict()
            name = service_data.get('name') or service_data.get('serviceName') or service_data.get('displayName')
            if name:
                return name
            return service_id.replace('_', ' ').title()
        return f"Service {service_id.replace('service_', '')}"
    except Exception as e:
        print(f"Error getting service name: {e}")
        return "Unknown Service"

# ---------- Helper: get office working hours ----------
def get_office_working_hours(office_id):
    if not office_id:
        return "Not set"
    doc = db.collection('OFFICES').document(office_id).get()
    if doc.exists:
        office_data = doc.to_dict()
        open_time = office_data.get('openTime', '9:00 AM')
        close_time = office_data.get('closeTime', '5:00 PM')
        return f"{open_time} - {close_time}"
    return "Not set"

# ---------- Helper: calculate total working duration ----------
def get_office_working_duration(office_id):
    if not office_id:
        return "0 hours"
    doc = db.collection('OFFICES').document(office_id).get()
    if doc.exists:
        office_data = doc.to_dict()
        open_time_str = office_data.get('openTime', '9:00 AM')
        close_time_str = office_data.get('closeTime', '5:00 PM')
        
        try:
            from datetime import datetime as dt
            open_time = dt.strptime(open_time_str, '%I:%M %p')
            close_time = dt.strptime(close_time_str, '%I:%M %p')
            diff = close_time - open_time
            total_minutes = diff.seconds // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            if hours > 0 and minutes > 0:
                return f"{hours} hours {minutes} mins"
            elif hours > 0:
                return f"{hours} hours"
            else:
                return f"{minutes} mins"
        except:
            return "8 hours"
    return "8 hours"

# ---------- Date range helpers ----------
def get_today_range():
    tz = pytz.timezone('Asia/Colombo')
    now = datetime.now(tz)
    start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
    end = datetime(now.year, now.month, now.day, 23, 59, 59, 999999, tzinfo=tz)
    return start.astimezone(pytz.UTC), end.astimezone(pytz.UTC)

def get_week_range():
    tz = pytz.timezone('Asia/Colombo')
    today = datetime.now(tz).date()
    monday = today - timedelta(days=today.weekday())
    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz).astimezone(pytz.UTC)
        end = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=tz).astimezone(pytz.UTC)
        days.append((day.strftime('%A'), start, end))
    return days

def get_month_range():
    tz = pytz.timezone('Asia/Colombo')
    today = datetime.now(tz).date()
    dates = []
    for i in range(30):
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz).astimezone(pytz.UTC)
        end = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=tz).astimezone(pytz.UTC)
        dates.append((day.strftime('%Y-%m-%d'), start, end))
    dates.reverse()
    return dates

# ---------- Helper: parse wait time ----------
def parse_wait_time(wait_str):
    if not wait_str:
        return 0
    
    if isinstance(wait_str, str) and wait_str.startswith('-'):
        wait_str = wait_str[1:]
    
    match = re.search(r'(\d+)\s*min', wait_str)
    if match:
        mins = int(match.group(1))
        match_h = re.search(r'(\d+)\s*hr', wait_str)
        if match_h:
            mins += int(match_h.group(1)) * 60
        if mins > 480:
            return 0
        return mins
    match_h = re.search(r'(\d+)\s*hr', wait_str)
    if match_h:
        mins = int(match_h.group(1)) * 60
        match_m = re.search(r'(\d+)\s*min', wait_str)
        if match_m:
            mins += int(match_m.group(1))
        if mins > 480:
            return 0
        return mins
    return 0

# ---------- Core: fetch office data ----------
def fetch_office_data(office_ref, start_dt, end_dt):
    office_id = office_ref.id

    def resolve_queue_ref(queue_ref):
        if hasattr(queue_ref, 'id'):
            return queue_ref
        if isinstance(queue_ref, str):
            path = queue_ref.lstrip('/')
            return db.document(path)
        return None

    # Tokens in range
    tokens_query = db.collection('TOKENS').where('officeId', '==', office_ref).stream()
    tokens_in_range = []
    for doc in tokens_query:
        data = doc.to_dict()
        booked = data.get('bookedtime') or data.get('bookedTime')
        if not booked:
            continue
        if hasattr(booked, 'timestamp'):
            booked_dt = datetime.fromtimestamp(booked.timestamp(), pytz.UTC)
        else:
            booked_dt = booked
        if start_dt <= booked_dt <= end_dt:
            tokens_in_range.append(data)

    total_tokens = len(tokens_in_range)
    served_tokens = sum(1 for t in tokens_in_range if t.get('status') == 'served')
    waiting_tokens = sum(1 for t in tokens_in_range if t.get('status') == 'waiting')

    # Active counters
    counters = db.collection('COUNTERS').where('officeId', '==', office_ref).where('status', '==', 'active').stream()
    active_counters = sum(1 for _ in counters)

    # Queues with service names
    queues = db.collection('QUEUES').where('officeId', '==', office_ref).stream()
    queue_service_names = {}
    queue_name_mapping = {}
    
    for q_doc in queues:
        q_data = q_doc.to_dict()
        queue_id = q_doc.id
        queue_name_mapping[queue_id] = q_data.get('name', queue_id)
        service_ref = q_data.get('serviceId')
        if service_ref:
            queue_service_names[queue_id] = get_service_name(service_ref)
        else:
            queue_service_names[queue_id] = q_data.get('name', 'Unknown Queue')

    # QUEUE_ANALYTICS
    analytics_query = db.collection('QUEUE_ANALYTICS').stream()
    queue_analytics = {}
    
    for ana_doc in analytics_query:
        ana = ana_doc.to_dict()
        ts = ana.get('timestamp')
        if not ts or not hasattr(ts, 'timestamp'):
            continue
        ts_dt = datetime.fromtimestamp(ts.timestamp(), pytz.UTC)
        if not (start_dt <= ts_dt <= end_dt):
            continue
        
        queue_ref = ana.get('queueId')
        if not queue_ref:
            continue
        
        queue_id = queue_ref.id if hasattr(queue_ref, 'id') else str(queue_ref)
        service_name = ana.get('serviceName')
        if not service_name or service_name == 'Unknown':
            service_name = queue_service_names.get(queue_id, 'Unknown Queue')
        
        avg_wait_str = ana.get('avgWaitTime', '0 mins')
        avg_wait_mins = parse_wait_time(avg_wait_str)
        
        if avg_wait_mins <= 0:
            continue
            
        if queue_id not in queue_analytics:
            queue_analytics[queue_id] = {
                'service_name': service_name,
                'queue_display_name': queue_name_mapping.get(queue_id, queue_id),
                'total_wait_mins': 0,
                'count': 0,
                'wait_times': []
            }
        queue_analytics[queue_id]['total_wait_mins'] += avg_wait_mins
        queue_analytics[queue_id]['count'] += 1
        queue_analytics[queue_id]['wait_times'].append(avg_wait_mins)

    for qid in queue_analytics:
        if queue_analytics[qid]['count'] > 0:
            queue_analytics[qid]['avg_wait_mins'] = queue_analytics[qid]['total_wait_mins'] // queue_analytics[qid]['count']
        else:
            queue_analytics[qid]['avg_wait_mins'] = 0

    # Token queue counts
    token_queue_counts = defaultdict(lambda: {'served': 0, 'waiting': 0, 'wait_times': []})
    
    for token in tokens_in_range:
        queue_ref_raw = token.get('queueId')
        if not queue_ref_raw:
            continue
        queue_ref = resolve_queue_ref(queue_ref_raw)
        if not queue_ref:
            continue
        queue_id = queue_ref.id
        
        if token.get('status') == 'served':
            token_queue_counts[queue_id]['served'] += 1
        elif token.get('status') == 'waiting':
            token_queue_counts[queue_id]['waiting'] += 1

        if token.get('status') == 'served':
            served_time = token.get('servedTime') or token.get('servedtime')
            booked = token.get('bookedtime') or token.get('bookedTime')
            if served_time and booked:
                try:
                    if hasattr(served_time, 'timestamp'):
                        served_dt = datetime.fromtimestamp(served_time.timestamp(), pytz.UTC)
                    else:
                        served_dt = served_time
                    if hasattr(booked, 'timestamp'):
                        booked_dt = datetime.fromtimestamp(booked.timestamp(), pytz.UTC)
                    else:
                        booked_dt = booked
                    wait_minutes = int((served_dt - booked_dt).total_seconds() / 60)
                    if 0 <= wait_minutes <= 480:
                        token_queue_counts[queue_id]['wait_times'].append(wait_minutes)
                except:
                    pass

    # Build queue_data
    queue_data = []
    all_queue_ids = set(queue_analytics.keys()) | set(token_queue_counts.keys()) | set(queue_service_names.keys())
    
    for qid in all_queue_ids:
        service_name = queue_analytics.get(qid, {}).get('service_name')
        if not service_name or service_name == 'Unknown Queue':
            service_name = queue_service_names.get(qid, 'Unknown Queue')
        
        if qid in queue_analytics and queue_analytics[qid]['count'] > 0:
            avg_wait_mins = queue_analytics[qid]['avg_wait_mins']
            avg_wait_time_str = f"{avg_wait_mins} mins"
        else:
            wait_times = token_queue_counts.get(qid, {}).get('wait_times', [])
            avg_wait_mins = sum(wait_times) // len(wait_times) if wait_times else 0
            avg_wait_time_str = f"{avg_wait_mins} mins" if avg_wait_mins > 0 else "N/A"
        
        served = token_queue_counts.get(qid, {}).get('served', 0)
        waiting = token_queue_counts.get(qid, {}).get('waiting', 0)
        
        if served > 0 or waiting > 0 or qid in queue_analytics:
            queue_data.append({
                'queue_id': qid,
                'queue_name': queue_name_mapping.get(qid, qid),
                'service_name': service_name,
                'tokens_served': served,
                'tokens_waiting': waiting,
                'total_tokens': served + waiting,
                'avg_wait_time': avg_wait_time_str,
                'avg_wait_mins': avg_wait_mins
            })

    office_working_hours = get_office_working_hours(office_id)
    office_working_duration = get_office_working_duration(office_id)

    return {
        'total_tokens': total_tokens,
        'served': served_tokens,
        'waiting': waiting_tokens,
        'active_counters': active_counters,
        'office_working_hours': office_working_hours,
        'office_working_duration': office_working_duration,
        'queue_data': queue_data
    }

# ---------- API: Daily report ----------
@reports.route('/api/daily')
def api_daily():
    office_ref, office_id = get_office_ref_and_id()
    if not office_ref:
        return jsonify({'error': 'No office assigned'}), 403
    start, end = get_today_range()
    data = fetch_office_data(office_ref, start, end)

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(['Served', 'Waiting', 'Active Counters'])
    bar.add_yaxis('Count', [data['served'], data['waiting'], data['active_counters']])
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="Daily Overview"),
        yaxis_opts=opts.AxisOpts(name="Count"),
        xaxis_opts=opts.AxisOpts(name="Metrics")
    )
    chart_html = bar.render_embed()

    if data['queue_data']:
        pie_data = [(qd['service_name'], qd['tokens_served']) for qd in data['queue_data'] if qd['tokens_served'] > 0]
        if pie_data:
            pie = Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
            pie.add("", pie_data, radius=["40%", "70%"])
            pie.set_global_opts(title_opts=opts.TitleOpts(title="Served Tokens by Service"))
            pie.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
            pie_chart = pie.render_embed()
        else:
            pie_chart = "<p>No served tokens data available</p>"
    else:
        pie_chart = "<p>No queue data available</p>"

    return jsonify({
        'success': True,
        'data': data,
        'chart_html': chart_html,
        'pie_chart': pie_chart
    })

# ---------- API: Weekly report ----------
@reports.route('/api/weekly')
def api_weekly():
    office_ref, office_id = get_office_ref_and_id()
    if not office_ref:
        return jsonify({'error': 'No office assigned'}), 403
    week_days = get_week_range()
    days = []
    served_list = []
    waiting_list = []
    active_counters_list = []
    working_hours_list = []
    queue_summary = defaultdict(lambda: {'served': 0, 'waiting': 0, 'avg_wait_mins': 0, 'count': 0})

    for day_name, start, end in week_days:
        data = fetch_office_data(office_ref, start, end)
        days.append(day_name)
        served_list.append(data['served'])
        waiting_list.append(data['waiting'])
        active_counters_list.append(data['active_counters'])
        working_hours_list.append(data['office_working_duration'])
        
        for qd in data.get('queue_data', []):
            qid = qd['queue_id']
            queue_summary[qid]['served'] += qd['tokens_served']
            queue_summary[qid]['waiting'] += qd['tokens_waiting']
            queue_summary[qid]['avg_wait_mins'] += qd['avg_wait_mins']
            queue_summary[qid]['count'] += 1
            queue_summary[qid]['service_name'] = qd['service_name']

    for qid in queue_summary:
        if queue_summary[qid]['count'] > 0:
            queue_summary[qid]['avg_wait_mins'] //= queue_summary[qid]['count']
            queue_summary[qid]['avg_wait_time'] = f"{queue_summary[qid]['avg_wait_mins']} mins" if queue_summary[qid]['avg_wait_mins'] > 0 else "N/A"
        del queue_summary[qid]['count']

    line = Line(init_opts=opts.InitOpts(width="100%", height="400px"))
    line.add_xaxis(days)
    line.add_yaxis('Served', served_list, linestyle_opts=opts.LineStyleOpts(width=2))
    line.add_yaxis('Waiting', waiting_list, linestyle_opts=opts.LineStyleOpts(width=2))
    line.set_global_opts(title_opts=opts.TitleOpts(title="Weekly Trend"))
    chart_html = line.render_embed()

    return jsonify({
        'success': True,
        'labels': days,
        'served': served_list,
        'waiting': waiting_list,
        'active_counters': active_counters_list,
        'working_hours': working_hours_list,
        'queue_summary': list(queue_summary.values()),
        'chart_html': chart_html
    })

# ---------- API: Monthly report ----------
@reports.route('/api/monthly')
def api_monthly():
    office_ref, office_id = get_office_ref_and_id()
    if not office_ref:
        return jsonify({'error': 'No office assigned'}), 403
    month_dates = get_month_range()
    dates = []
    served_list = []
    waiting_list = []
    active_counters_list = []
    working_hours_list = []
    queue_summary = defaultdict(lambda: {'served': 0, 'waiting': 0, 'avg_wait_mins': 0, 'count': 0})

    for date_str, start, end in month_dates:
        data = fetch_office_data(office_ref, start, end)
        dates.append(date_str)
        served_list.append(data['served'])
        waiting_list.append(data['waiting'])
        active_counters_list.append(data['active_counters'])
        working_hours_list.append(data['office_working_duration'])
        
        for qd in data.get('queue_data', []):
            qid = qd['queue_id']
            queue_summary[qid]['served'] += qd['tokens_served']
            queue_summary[qid]['waiting'] += qd['tokens_waiting']
            queue_summary[qid]['avg_wait_mins'] += qd['avg_wait_mins']
            queue_summary[qid]['count'] += 1
            queue_summary[qid]['service_name'] = qd['service_name']

    for qid in queue_summary:
        if queue_summary[qid]['count'] > 0:
            queue_summary[qid]['avg_wait_mins'] //= queue_summary[qid]['count']
            queue_summary[qid]['avg_wait_time'] = f"{queue_summary[qid]['avg_wait_mins']} mins" if queue_summary[qid]['avg_wait_mins'] > 0 else "N/A"
        del queue_summary[qid]['count']

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(dates)
    bar.add_yaxis('Served', served_list)
    bar.add_yaxis('Waiting', waiting_list)
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="Monthly Report"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45))
    )
    chart_html = bar.render_embed()

    return jsonify({
        'success': True,
        'labels': dates,
        'served': served_list,
        'waiting': waiting_list,
        'active_counters': active_counters_list,
        'working_hours': working_hours_list,
        'queue_summary': list(queue_summary.values()),
        'chart_html': chart_html
    })

@reports.route('/download/<report_type>')
def download_pdf(report_type):
    office_ref, office_id = get_office_ref_and_id()
    if not office_ref:
        return "Unauthorized", 403

    now_str = datetime.now(pytz.timezone('Asia/Colombo')).strftime('%Y-%m-%d %I:%M %p')
    office_name = get_office_name(office_id) or "Your Office"
    
    try:
        if report_type == 'daily':
            start, end = get_today_range()
            data = fetch_office_data(office_ref, start, end)
            title = "Daily Performance Report"
            
            # Generate bar chart
            bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
            bar.add_xaxis(['Served', 'Waiting', 'Active Counters'])
            bar.add_yaxis('Count', [data['served'], data['waiting'], data['active_counters']])
            bar.set_global_opts(
                title_opts=opts.TitleOpts(title="Daily Overview"),
                yaxis_opts=opts.AxisOpts(name="Count"),
                xaxis_opts=opts.AxisOpts(name="Metrics")
            )
            bar_chart_html = bar.render_embed()
            
            # Generate pie chart
            pie_chart_html = None
            if data['queue_data']:
                pie_data = [(qd['service_name'], qd['tokens_served']) for qd in data['queue_data'] if qd['tokens_served'] > 0]
                if pie_data:
                    pie = Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
                    pie.add("", pie_data, radius=["40%", "70%"])
                    pie.set_global_opts(title_opts=opts.TitleOpts(title="Served Tokens by Service"))
                    pie.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
                    pie_chart_html = pie.render_embed()
            
            html_content = render_template('pdf_report.html',
                title=title,
                office_name=office_name,
                generated_on=now_str,
                report_type='daily',
                data=data,
                queue_data=data.get('queue_data', []),
                bar_chart_html=bar_chart_html,
                pie_chart_html=pie_chart_html
            )
        
        elif report_type == 'weekly':
            week_days = get_week_range()
            rows = []
            days = []
            served_list = []
            waiting_list = []
            queue_summary_dict = {}
            
            for day_name, start, end in week_days:
                d = fetch_office_data(office_ref, start, end)
                days.append(day_name)
                served_list.append(d['served'])
                waiting_list.append(d['waiting'])
                rows.append({
                    'day': day_name, 
                    'served': d['served'], 
                    'waiting': d['waiting'],
                    'active': d['active_counters'], 
                    'working_hours': d['office_working_duration']
                })
                
                # Aggregate queue data
                for qd in d.get('queue_data', []):
                    if qd['service_name'] not in queue_summary_dict:
                        queue_summary_dict[qd['service_name']] = {
                            'service_name': qd['service_name'],
                            'served': 0,
                            'waiting': 0,
                            'avg_mins': 0,
                            'count': 0
                        }
                    queue_summary_dict[qd['service_name']]['served'] += qd['tokens_served']
                    queue_summary_dict[qd['service_name']]['waiting'] += qd['tokens_waiting']
                    queue_summary_dict[qd['service_name']]['avg_mins'] += qd['avg_wait_mins']
                    queue_summary_dict[qd['service_name']]['count'] += 1
            
            # Calculate averages
            queue_summary = []
            for q in queue_summary_dict.values():
                avg_mins = q['avg_mins'] // q['count'] if q['count'] > 0 else 0
                queue_summary.append({
                    'service_name': q['service_name'],
                    'served': q['served'],
                    'waiting': q['waiting'],
                    'avg_wait_time': f"{avg_mins} mins" if avg_mins > 0 else "N/A"
                })
            
            title = "Weekly Performance Report"
            total_served = sum(served_list)
            total_waiting = sum(waiting_list)
            avg_daily_served = total_served // 7 if served_list else 0
            
            # Generate line chart
            line = Line(init_opts=opts.InitOpts(width="100%", height="400px"))
            line.add_xaxis(days)
            line.add_yaxis('Served', served_list, linestyle_opts=opts.LineStyleOpts(width=2))
            line.add_yaxis('Waiting', waiting_list, linestyle_opts=opts.LineStyleOpts(width=2))
            line.set_global_opts(title_opts=opts.TitleOpts(title="Weekly Trend"))
            chart_html = line.render_embed()
            
            html_content = render_template('pdf_report.html',
                title=title,
                office_name=office_name,
                generated_on=now_str,
                report_type='weekly',
                rows=rows,
                total_served=total_served,
                total_waiting=total_waiting,
                avg_daily_served=avg_daily_served,
                chart_html=chart_html,
                queue_summary=queue_summary
            )
        
        elif report_type == 'monthly':
            month_dates = get_month_range()
            rows = []
            served_list = []
            waiting_list = []
            queue_summary_dict = {}
            
            for date_str, start, end in month_dates:
                d = fetch_office_data(office_ref, start, end)
                served_list.append(d['served'])
                waiting_list.append(d['waiting'])
                rows.append({
                    'date': date_str, 
                    'served': d['served'], 
                    'waiting': d['waiting'],
                    'active': d['active_counters'], 
                    'working_hours': d['office_working_duration']
                })
                
                # Aggregate queue data
                for qd in d.get('queue_data', []):
                    if qd['service_name'] not in queue_summary_dict:
                        queue_summary_dict[qd['service_name']] = {
                            'service_name': qd['service_name'],
                            'served': 0,
                            'waiting': 0,
                            'avg_mins': 0,
                            'count': 0
                        }
                    queue_summary_dict[qd['service_name']]['served'] += qd['tokens_served']
                    queue_summary_dict[qd['service_name']]['waiting'] += qd['tokens_waiting']
                    queue_summary_dict[qd['service_name']]['avg_mins'] += qd['avg_wait_mins']
                    queue_summary_dict[qd['service_name']]['count'] += 1
            
            # Calculate averages
            queue_summary = []
            for q in queue_summary_dict.values():
                avg_mins = q['avg_mins'] // q['count'] if q['count'] > 0 else 0
                queue_summary.append({
                    'service_name': q['service_name'],
                    'served': q['served'],
                    'waiting': q['waiting'],
                    'avg_wait_time': f"{avg_mins} mins" if avg_mins > 0 else "N/A"
                })
            
            title = "Monthly Performance Report"
            total_served = sum(served_list)
            total_waiting = sum(waiting_list)
            avg_daily_served = total_served // len(served_list) if served_list else 0
            
            # Generate bar chart (last 15 days for readability)
            bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
            bar.add_xaxis([row['date'] for row in rows[-15:]])
            bar.add_yaxis('Served', served_list[-15:])
            bar.add_yaxis('Waiting', waiting_list[-15:])
            bar.set_global_opts(
                title_opts=opts.TitleOpts(title="Monthly Report (Last 15 Days)"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45))
            )
            chart_html = bar.render_embed()
            
            html_content = render_template('pdf_report.html',
                title=title,
                office_name=office_name,
                generated_on=now_str,
                report_type='monthly',
                rows=rows,
                total_served=total_served,
                total_waiting=total_waiting,
                avg_daily_served=avg_daily_served,
                chart_html=chart_html,
                queue_summary=queue_summary
            )
        
        else:
            return "Invalid report type", 400
        
        # Generate PDF
        from weasyprint import HTML
        pdf = HTML(string=html_content).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={report_type}_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        return response
    
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500


# ---------- Main reports page ----------
@reports.route('/')
def reports_page():
    if 'user' not in session:
        return redirect(url_for('login.index'))

    office_id = session.get('office_id')
    office_name = get_office_name(office_id) if office_id else None

    return render_template('reports.html',
                           office_name=office_name,
                           office_id=office_id,
                           user_name=session.get('name', 'User'))