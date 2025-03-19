import requests
import base64
import json
import csv
from urllib.parse import urlunparse
from datetime import datetime, timedelta
import pytz
import time
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# nonaktifkan SSL warning
requests.packages.urllib3.disable_warnings()

# Step 1: ini jgn disebar, sensitif beud njirr
HOST = "<Your Stellar Cyber IP or DNS>"
userid = "<Your Stellar Cyber username>"
refresh_token = "<Your Stellar Cyber API token>"

def getAccessToken(userid, refresh_token):
    auth = base64.b64encode(bytes(userid + ":" + refresh_token, "utf-8")).decode("utf-8")
    headers = {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    url = urlunparse(("https", HOST, "/connect/api/v1/access_token", "", "", ""))
    res = requests.post(url, headers=headers, verify=False)
    return res.json().get("access_token")

def convert_timestamp_to_datetime(timestamp):
    if isinstance(timestamp, str):
        try:
            timestamp = int(timestamp)
        except ValueError:
            return None
    if isinstance(timestamp, (int, float)):
        utc_time = datetime.fromtimestamp(timestamp / 1000, pytz.utc)
        jakarta_time = utc_time.astimezone(pytz.timezone('Asia/Jakarta'))
        return jakarta_time.strftime('%Y-%m-%d %H:%M:%S')
    return None

# Fungsi untuk menentukan start_date dan end_date otomatis berdasarkan waktu 7 pagi setiap hari
def get_start_end_dates_for_today():
    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz)

    # Tentukan waktu 24 jam yang lalu
    start_of_day = now - timedelta(days=1)

    # Waktu sekarang sebagai akhir
    end_of_day = now

    # Format dalam string yang bisa digunakan di API
    start_of_day_str = start_of_day.strftime("%Y-%m-%d %H:%M")
    end_of_day_str = end_of_day.strftime("%Y-%m-%d %H:%M")

    return start_of_day_str, end_of_day_str

# Fungsi lainnya (getAccessToken, typewriter_effect, convert_timestamp_to_datetime, dll.)

def getAlertsForCase(token, case_id):
    headers = {"Authorization": "Bearer " + token}
    url = urlunparse(("https", HOST, f"/connect/api/v1/cases/{case_id}/alerts?skip=0&limit=50", "", "", ""))
    res = requests.get(url, headers=headers, verify=False)
    
    alerts = []
    if res.status_code == 200:
        alert_data = res.json()
        if "data" in alert_data and "docs" in alert_data["data"]:
            alerts = alert_data["data"]["docs"]
    return alerts

def getCasesB(token, start_timestamp, end_timestamp, tenantid_filters=None):
    headers = {"Authorization": "Bearer " + token}
    alertsB = []

    # Konversi start_timestamp dan end_timestamp ke epoch timestamp (dalam milidetik)
    tz = pytz.timezone('Asia/Jakarta')
    start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M")

    # Localize datetime ke timezone Jakarta
    start_datetime = tz.localize(start_datetime)
    end_datetime = tz.localize(end_datetime)

    # Konversi ke epoch timestamp (dalam milidetik)
    start_epoch = int(start_datetime.timestamp() * 1000)
    end_epoch = int(end_datetime.timestamp() * 1000)

    for tenantid in tenantid_filters:
        url = urlunparse(("https", HOST, f"/connect/api/v1/cases?tenantid={tenantid}&status=Resolved&FROM~created_at={start_epoch}&TO~created_at={end_epoch}&limit=500", "", "", ""))
        
        while url:
            res = requests.get(url, headers=headers, verify=False)

            if res.status_code == 200:
                case_data = res.json()
                if "data" in case_data and "cases" in case_data["data"]:
                    cases = case_data["data"]["cases"]
                    for case in cases:
                        ticket_id = case.get('ticket_id', 'Unknown')
                        case_id = case['_id']
                        case_created_at = case.get("created_at", None)
                        if case_created_at:
                            print(f"Case ID yang di proses: {case_id} dengan ticket ID: {ticket_id}")
                            case_created_at_converted = convert_timestamp_to_datetime(case_created_at)
                            alerts = getAlertsForCase(token, case_id)  # Panggil fungsi getAlertsForCase
                            for alert in alerts:
                                alert["ticket_id"] = ticket_id
                                alert["case_created_at"] = case_created_at_converted
                                alertsB.append(alert)
                next_url = case_data.get("paging", {}).get("next", None)
                if next_url:
                    url = next_url
                else:
                    break
            else:
                print(f"Error saat tarik data dari API: {res.status_code}, Response: {res.text}")
                break
    return alertsB

# Fungsi lainnya (merge_alerts, save_to_database, run_daily_data_pull, dll.)

#ambil case A, alert actually males ganti variabel aja
def getCasesA(token, status_filter=None, tenantid_filters=None, start_of_day_str=None, end_of_day_str=None):
    headers = {"Authorization": "Bearer " + token, 'content-type': 'application/json'}
    tz = pytz.timezone('Asia/Jakarta')

    start_of_day = datetime.strptime(start_of_day_str, "%Y-%m-%d %H:%M") if start_of_day_str else datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = datetime.strptime(end_of_day_str, "%Y-%m-%d %H:%M") if end_of_day_str else datetime.now(tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    start_of_day_str = start_of_day.astimezone(tz).isoformat()
    end_of_day_str = end_of_day.astimezone(tz).isoformat()

    query = {
        "size": 10000,
        "query": {
            "bool": {
                "must": []
            }
        }
    }

    if status_filter:
        query["query"]["bool"]["must"].append({"match": {"event_status": status_filter}})
    if tenantid_filters:
        query["query"]["bool"]["must"].append({"terms": {"tenantid": tenantid_filters}})  # Modify here for multiple tenantids
    query["query"]["bool"]["must"].append({
        "range": {
            "timestamp": {
                "gte": start_of_day_str,
                "lte": end_of_day_str,
                "format": "strict_date_time"
            }
        }
    })

    url = urlunparse(("https", HOST, "/connect/api/data/aella-ser-*/_search", "", "", ""))
    res = requests.get(url, headers=headers, json=query, verify=False)

    if res.status_code != 200:
        print("respon API stellar error busset")
        return []

    data = res.json()

    if 'hits' in data and 'hits' in data['hits']:
        total_hits = data['hits']['total']['value']
        filtered_cases = []
        for alert in data['hits']['hits']:
            xdr_event = alert["_source"].get("xdr_event", {})
            display_name = xdr_event.get("display_name", "")

            if display_name == "Connector Authentication Failure":
                continue

            closed_time = None
            for action in alert["_source"].get("user_action", {}).get("history", []):
                if action["action"] == "Status changed to Closed" and closed_time is None:
                    closed_time = convert_timestamp_to_datetime(action.get("action_time"))

            _id = alert["_id"]
            alert_time = convert_timestamp_to_datetime(alert["_source"].get("stellar", {}).get("alert_time", None)) or convert_timestamp_to_datetime(alert["_source"].get("alert_time", None))
            severity = alert["_source"].get("severity", "")
            event_status = alert["_source"].get("event_status", "")
            
            if event_status == "New":
                print(f"Alert dengan status '{event_status}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
            if event_status == "In Progress":
                print(f"Alert dengan status '{event_status}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
            if event_status == "Ignored":
                print(f"Alert dengan status '{event_status}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
            if event_status == "":
                print(f"Alert dengan status '{event_status}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
                
            alert_type = alert["_source"].get("xdr_event", {}).get("display_name", "")
            assignee = alert["_source"].get("user_action", {}).get("last_user", "")
            tenant_name = alert["_source"].get("tenant_name", "")
            
            if tenant_name == "Punggawa":
                print(f"Data dari tenant '{tenant_name}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
            if tenant_name == "Root Tenant":
                print(f"Data dari tenant '{tenant_name}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya 
            if tenant_name == "":
                print(f"Data dari tenant '{tenant_name}' dikecualikan dan tidak dimasukkan ke database.")
                continue  # Lewatkan data ini dan lanjut ke case berikutnya
                
            
            comments = alert["_source"].get("comments", [])
            comment = comments[0].get("comment", "") if comments else ""
            filtered_cases.append({
                "_id": _id,
                "alert_time": alert_time,
                "severity": severity,
                "event_status": event_status,
                "alert_type": alert_type,
                "closed_time": closed_time,
                "assignee": assignee,
                "alert_time": alert_time,
                "tenant_name": tenant_name,
                "comments": comments,
            })

        return filtered_cases
    return []

# Fungsi untuk mengambil case B
def getCasesB(token, start_timestamp, end_timestamp, tenantid_filters=None):
    headers = {"Authorization": "Bearer " + token}
    alertsB = []

    # Konversi start_timestamp dan end_timestamp ke epoch timestamp (dalam milidetik)
    tz = pytz.timezone('Asia/Jakarta')
    start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M")

    # Localize datetime ke timezone Jakarta
    start_datetime = tz.localize(start_datetime)
    end_datetime = tz.localize(end_datetime)

    # Konversi ke epoch timestamp (dalam milidetik)
    start_epoch = int(start_datetime.timestamp() * 1000)
    end_epoch = int(end_datetime.timestamp() * 1000)

    for tenantid in tenantid_filters:
        url = urlunparse(("https", HOST, f"/connect/api/v1/cases?tenantid={tenantid}&status=Resolved&FROM~created_at={start_epoch}&TO~created_at={end_epoch}&limit=100", "", "", ""))
        
        while url:
            res = requests.get(url, headers=headers, verify=False)

            if res.status_code == 200:
                case_data = res.json()
                if "data" in case_data and "cases" in case_data["data"]:
                    cases = case_data["data"]["cases"]
                    for case in cases:
                        ticket_id = case.get('ticket_id', 'Unknown')
                        case_id = case['_id']
                        case_created_at = case.get("created_at", None)
                        if case_created_at:
                            print(f"Case ID yang di proses: {case_id} dengan ticket ID: {ticket_id}")
                            case_created_at_converted = convert_timestamp_to_datetime(case_created_at)
                            alerts = getAlertsForCase(token, case_id)
                            for alert in alerts:
                                alert["ticket_id"] = ticket_id
                                alert["case_created_at"] = case_created_at_converted
                                alertsB.append(alert)
                next_url = case_data.get("paging", {}).get("next", None)
                if next_url:
                    url = next_url
                else:
                    break
            else:
                print(f"Error saat tarik data dari API: {res.status_code}, Response: {res.text}")
                break
    return alertsB

# Fungsi untuk menggabungkan alerts dari A dan B
def merge_alerts(alertsA, alertsB):
    alertsA_dict = {alertA["_id"]: alertA for alertA in alertsA}
    
    for alertB in alertsB:
        ticket_id = alertB.get("ticket_id", "Unknown")
        case_created_at = alertB.get("case_created_at", None)
        
        # Konversi epoch timestamp ke waktu biasa GMT+7 jika ada
        if case_created_at:
            case_created_at = convert_timestamp_to_datetime(case_created_at)
        
        if alertB["_id"] in alertsA_dict:
            alertsA_dict[alertB["_id"]].update(alertB)
            alertsA_dict[alertB["_id"]]["ticket_id"] = ticket_id
            if case_created_at:
                alertsA_dict[alertB["_id"]]["case_created_at"] = case_created_at
        else:
            alertB["ticket_id"] = ticket_id
            if case_created_at:
                alertB["case_created_at"] = case_created_at
            alertsA_dict[alertB["_id"]] = alertB
    
    return list(alertsA_dict.values())

# Database Configuration with SQLAlchemy
DATABASE_URL = "mysql+pymysql://root:socps52025@localhost:3306/klasemen"

# Create engine and connection
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define model for Alert table
class Alert(Base):
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(255), unique=False)
    ticket_id = Column(String(255), unique=False)  # Untuk memastikan kombinasi unik
    alert_time = Column(DateTime)
    severity = Column(String(50))
    event_status = Column(String(50))
    alert_type=Column(String(255))
    closed_time = Column(DateTime)
    created_case = Column(DateTime)  # Kolom untuk created_case
    assignee = Column(String(255))
    comment = Column(String(1500))
    tenant_name = Column(String(255))
    sla_detect = Column(Float)
    sla_response = Column(Float)  # Kolom untuk sla_response
    sla_detect_criteria = Column(String(50))
    sla_response_criteria = Column(String(50))  # Kolom untuk sla_response_criteria

    __table_args__ = (
        UniqueConstraint('alert_id', 'ticket_id', name='uix_alert_ticket_id'),
    )


# Create all tables in the database (if not already created)
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Fungsi untuk menyimpan data ke database
# Fungsi untuk menyimpan data ke database
def save_to_database(alerts, start_date, start_time, end_date, end_time):
    if not alerts:
        print("No data to save.")
        return

    for alert in alerts:
        comments = alert.get("comments", [])
        comment = comments[0].get("comment", "") if comments else ""

        alert_time_str = alert.get("alert_time")
        closed_time_str = alert.get("closed_time")
        case_created_at_str = alert.get("case_created_at", None)

        alert_time = datetime.strptime(alert_time_str, "%Y-%m-%d %H:%M:%S") if alert_time_str else None
        closed_time = datetime.strptime(closed_time_str, "%Y-%m-%d %H:%M:%S") if closed_time_str else None
        case_created_at = datetime.strptime(case_created_at_str, "%Y-%m-%d %H:%M:%S") if case_created_at_str else None

        sla_detect = (closed_time - alert_time).total_seconds() / 60 if (alert_time and closed_time) else None
        sla_response = (case_created_at - alert_time).total_seconds() / 60 if (case_created_at and alert_time) else None
        sla_detect_criteria = "PASS" if (sla_detect and sla_detect <= 120) else "OFFSIDE"
        sla_response_criteria = "PASS" if (sla_response and sla_response <= 120) else ("OFFSIDE" if sla_response else "")

        # Cek apakah data dengan _id yang sama sudah ada di database
        existing_alert = session.query(Alert).filter(
            Alert.alert_id == alert["_id"],
            Alert.ticket_id == alert.get("ticket_id", "Unknown")
        ).first()

        if not existing_alert:
            # Jika data tidak ada, buat data baru
            new_alert = Alert(
                alert_id=alert["_id"],
                alert_time=alert_time,
                severity=alert.get("severity", "Unknown"),
                event_status=alert.get("event_status", "Unknown"),
                alert_type=alert.get("alert_type", "Unknown"),
                ticket_id=alert.get("ticket_id", "Unknown"),
                closed_time=closed_time,
                created_case=case_created_at,  # Kolom untuk "Created Case"
                assignee=alert.get("assignee", "Unknown"),
                comment=comment,
                tenant_name=alert.get("tenant_name", "Unknown"),
                sla_detect=sla_detect,
                sla_response=sla_response,
                sla_detect_criteria=sla_detect_criteria,
                sla_response_criteria=sla_response_criteria
            )
            session.add(new_alert)
        else:
            # Jika data sudah ada, update field-field yang relevan
            print(f"Alert ID {alert['_id']} dengan Ticket ID {alert.get('ticket_id')} sudah ada. Update data yang sudah ada.")
            existing_alert.alert_time = alert_time
            existing_alert.severity = alert.get("severity", "Unknown")
            existing_alert.event_status = alert.get("event_status", "Unknown")
            existing_alert.alert_type = alert.get("alert_type", "Unknown")
            existing_alert.closed_time = closed_time
            existing_alert.created_case = case_created_at
            existing_alert.assignee = alert.get("assignee", "Unknown")
            existing_alert.comment = comment
            existing_alert.tenant_name = alert.get("tenant_name", "Unknown")
            existing_alert.sla_detect = sla_detect
            existing_alert.sla_response = sla_response
            existing_alert.sla_detect_criteria = sla_detect_criteria
            existing_alert.sla_response_criteria = sla_response_criteria

        # Commit ke database
        try:
            session.commit()
            print(f"Data berhasil disimpan atau diupdate ke database: {start_date} hingga {end_date}")
        except Exception as e:
            session.rollback()
            print(f"Error saat menyimpan atau mengupdate ke database: {str(e)}")
        finally:
            session.close()

# Fungsi utama untuk menjalankan penarikan data setiap hari pada jam 7 pagi GMT+7
def run_daily_data_pull():
    while True:
        token = getAccessToken(userid, refresh_token)
        start_date, end_date = get_start_end_dates_for_today()

        print(f"Menarik data untuk periode {start_date} hingga {end_date}")
        tenantid_filters = ["0ec12994ecde4b399df8191f6d69964d", "dae431cb3d084881aba7ab17715ecd18"]
        status_filter = "Closed"
        # Panggil getCasesB dengan format yang benar
        alertsA = getCasesA(token, start_of_day_str=start_date, end_of_day_str=end_date)
        alertsB = getCasesB(token, start_timestamp=start_date, end_timestamp=end_date, tenantid_filters=tenantid_filters)

        merged_alerts = merge_alerts(alertsA, alertsB)
        save_to_database(merged_alerts, start_date, "07:00", end_date, "07:00")

        # Hitung waktu untuk tidur hingga 1 jam ke depan
        # Mendapatkan waktu sekarang
        now = datetime.now()
        next_run_time = now + timedelta(minutes=30)
        sleep_time = (next_run_time - now).total_seconds()
        print(f"Menunggu hingga 30 menit ke depan ({sleep_time} detik)!! JANGAN DI CLOSE YA GAISSS NANTI GA UPDATE KLASEMEN!!!!")
        time.sleep(sleep_time)

# Jalankan penarikan data otomatis setiap 30 menit
run_daily_data_pull()