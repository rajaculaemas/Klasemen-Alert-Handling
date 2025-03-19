import pandas as pd
from sqlalchemy import create_engine

# Konfigurasi koneksi database
DATABASE_URL = "mysql+pymysql://root:socps52025@localhost:3306/klasemen"
engine = create_engine(DATABASE_URL)

# Fungsi untuk membaca data dari database
def fetch_data_from_db():
    query = "SELECT * FROM alerts"
    df = pd.read_sql(query, engine)
    return df

# Fungsi untuk memfilter data berdasarkan bulan dan tahun
def filter_data(year, month):
    df = fetch_data_from_db()
    df['alert_time'] = pd.to_datetime(df['alert_time'], errors='coerce')
    df = df.dropna(subset=['alert_time'])

    df['Points'] = 0
    df.loc[df['sla_detect_criteria'] == 'PASS', 'Points'] += 1
    df.loc[df['sla_response_criteria'] == 'PASS', 'Points'] += 2
    df.loc[df['sla_detect_criteria'] == 'OFFSIDE', 'Points'] -= 1
    df.loc[df['sla_response_criteria'] == 'OFFSIDE', 'Points'] -= 1

    filtered_df = df[(df['alert_time'].dt.year == int(year)) & (df['alert_time'].dt.month == int(month))]

    if filtered_df.empty:
        print(f"⚠️ Tidak ada data untuk {month}/{year}")

    assignee_stats = filtered_df.groupby('assignee').agg(
        Alert=('alert_id', 'count'),
        Alert_Case=('created_case', lambda x: x.notnull().sum()),
        Alerts_PASS=('sla_detect_criteria', lambda x: (x == 'PASS').sum()),
        Alerts_Case_PASS=('sla_response_criteria', lambda x: (x == 'PASS').sum()),
        Alerts_OFFSIDE=('sla_detect_criteria', lambda x: (x == 'OFFSIDE').sum()),
        Alerts_Case_OFFSIDE=('sla_response_criteria', lambda x: (x == 'OFFSIDE').sum())
    ).reset_index()

    assignee_stats['Total Poin'] = assignee_stats['Alerts_PASS'] + (assignee_stats['Alerts_Case_PASS'] * 2)
    assignee_stats['Total Poin'] -= assignee_stats['Alerts_OFFSIDE']
    assignee_stats['Total Poin'] -= assignee_stats['Alerts_Case_OFFSIDE'] * 2

    df_sorted = assignee_stats.sort_values(by='Total Poin', ascending=False).reset_index(drop=True)
    df_sorted.insert(0, 'Position', df_sorted.index + 1)

    return df_sorted