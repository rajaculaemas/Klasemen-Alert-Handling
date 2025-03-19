import dash
from dash import dcc, html, dash_table, Output, Input, State
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import plotly.express as px

# Konfigurasi koneksi database
DATABASE_URL = "mysql+pymysql://root:@localhost:3306/klasemen"
engine = create_engine(DATABASE_URL)

# Fungsi untuk membaca data dari database
def fetch_data_from_db():
    query = "SELECT * FROM alerts"
    df = pd.read_sql(query, engine)
    return df

# Membaca data dari database
df = fetch_data_from_db()

# Konversi kolom Alert time ke datetime dengan format yang sesuai
df['alert_time'] = pd.to_datetime(df['alert_time'], errors='coerce')
df = df.dropna(subset=['alert_time'])

# Fungsi untuk memfilter data berdasarkan bulan dan tahun
def filter_data(year, month):
    df = fetch_data_from_db()
    df['alert_time'] = pd.to_datetime(df['alert_time'], errors='coerce')
    df = df.dropna(subset=['alert_time'])


    filtered_df = df[(df['alert_time'].dt.year == int(year)) & (df['alert_time'].dt.month == int(month))]

    if filtered_df.empty:
        print(f"⚠️ Tidak ada data untuk {month}/{year}")

    # Agregasi data
    assignee_stats = filtered_df.groupby('assignee').agg(
        Alert=('alert_id', 'count'),  # Jumlah total alert
        Alert_Case=('created_case', lambda x: x.notnull().sum()),  # Jumlah alert yang menjadi case
        Alerts_PASS=('sla_detect_criteria', lambda x: ((x == 'PASS') & (filtered_df.loc[x.index, 'sla_response_criteria'] != 'PASS')).sum()),  # Hanya alert dengan sla_detect_criteria = 'PASS' dan sla_response_criteria != 'PASS'
        Alerts_Case_PASS=('sla_response_criteria', lambda x: (x == 'PASS').sum()),  # Jumlah alert dengan sla_response_criteria = 'PASS'
        Alerts_OFFSIDE=('sla_detect_criteria', lambda x: (x == 'OFFSIDE').sum()),  # Jumlah alert dengan sla_detect_criteria = 'OFFSIDE'
        Alerts_Case_OFFSIDE=('sla_response_criteria', lambda x: (x == 'OFFSIDE').sum())  # Jumlah alert dengan sla_response_criteria = 'OFFSIDE'
    ).reset_index()

    # Menghitung Total Poin
    assignee_stats['Total Poin'] = assignee_stats['Alerts_PASS'] + (assignee_stats['Alerts_Case_PASS'] * 3)
    assignee_stats['Total Poin'] -= assignee_stats['Alerts_OFFSIDE'] * 1
    assignee_stats['Total Poin'] -= assignee_stats['Alerts_Case_OFFSIDE'] * 2

    # Mengurutkan data berdasarkan Total Poin
    df_sorted = assignee_stats.sort_values(by='Total Poin', ascending=False).reset_index(drop=True)
    df_sorted.insert(0, 'Position', df_sorted.index + 1)

    return df_sorted

# Inisialisasi aplikasi Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = 'Liga SOC'
app._favicon = ("punggawa_logo.png")

# Layout halaman utama
layout_halaman_utama = html.Div([

    html.Title('Liga SOC'),
    
    # Logo
    html.Img(src='/assets/punggawalogo.jpg', style={'position': 'absolute', 'top': '10px', 'left': '10px', 'width': '260px'}),

    # Judul
    html.H1("Klasemen Alerts Handling", style={'textAlign': 'center'}),

    # Filter Bulan dan Tahun
    html.Div([
        dcc.Dropdown(
            id='year-filter',
            options=[{'label': str(year), 'value': str(year)} for year in range(2024, 2035)],
            value='2025',  # Tidak di-set langsung, akan diisi dari Store
            clearable=False,
            style={'width': '100px', 'display': 'inline-block', 'marginRight': '5px'}
            ),
        dcc.Dropdown(
            id='month-filter',
            options=[
            {'label': 'Januari', 'value': '1'},
            {'label': 'Februari', 'value': '2'},
            {'label': 'Maret', 'value': '3'},
            {'label': 'April', 'value': '4'},
            {'label': 'Mei', 'value': '5'},
            {'label': 'Juni', 'value': '6'},
            {'label': 'Juli', 'value': '7'},
            {'label': 'Agustus', 'value': '8'},
            {'label': 'September', 'value': '9'},
            {'label': 'Oktober', 'value': '10'},
            {'label': 'November', 'value': '11'},
            {'label': 'Desember', 'value': '12'}
            ],
            value='3',  # Tidak di-set langsung, akan diisi dari Store
            clearable=False,
            style={'width': '150px', 'display': 'inline-block'}
)

    ], style={'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'marginBottom': '20px', 'gap': '10px'}),

            #dcc interval auto refresh page 
            dcc.Interval(
            id='interval-component',
            interval=60000,  # Setiap 60.000 ms = 60 detik (1 menit)
            n_intervals=0
),

    # Tabel Klasemen
    dash_table.DataTable(
        id='leaderboard-table',
        columns=[
            {'name': 'Position', 'id': 'Position', 'type': 'numeric'},
            {'name': 'Nama Analis', 'id': 'assignee', 'type': 'text'},
            {'name': 'Alerts', 'id': 'Alert', 'type': 'numeric'},
            {'name': 'Alerts (Case)', 'id': 'Alert_Case', 'type': 'numeric'},
            {'name': 'Alerts PASS', 'id': 'Alerts_PASS', 'type': 'numeric'},
            {'name': 'Alerts (Case) PASS', 'id': 'Alerts_Case_PASS', 'type': 'numeric'},
            {'name': 'Alerts OFFSIDE', 'id': 'Alerts_OFFSIDE', 'type': 'numeric'},
            {'name': 'Alerts (Case) OFFSIDE', 'id': 'Alerts_Case_OFFSIDE', 'type': 'numeric'},
            {'name': 'Total Poin', 'id': 'Total Poin', 'type': 'numeric'}
        ],
        data=filter_data(2025, 1).to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        style_header={
            'backgroundColor': 'lightgrey',
            'fontWeight': 'bold',
            'borderBottom': '2px solid black',
            'position': 'sticky',
            'top': 0,              # Posisi tetap di atas saat scroll
            'zIndex': 1            # Agar header tetap di atas konten
        },
        style_data_conditional=[
            {
                'if': {'column_id': col},
                'cursor': 'pointer'
            } for col in ['Alert', 'Alert_Case', 'Alerts_PASS', 'Alerts_Case_PASS', 'Alerts_OFFSIDE', 'Alerts_Case_OFFSIDE']
        ],
        sort_action="native"
    ),

    # Running text (Notes)
    html.Div(
        "Klik value tabel untuk melihat daftar alert | Data diperbarui setiap 15 menit",
        style={
            'marginTop': '10px',
            'fontStyle': 'italic',
            'textAlign': 'center',
            'color': 'black',
            'animation': 'scrollText 10s linear infinite',  # Animasi running text
            'whiteSpace': 'nowrap',  # Mencegah teks berjalan ke baris baru
        }
    ),

        html.Div(
        "SLA Maksimal 2 jam (MSIG, TVRI) | 1 alert = 1 poin | 1 alert jadi case = 3 poin",
        style={
            'marginTop': '10px',
            'fontStyle': 'italic',
            'textAlign': 'center',
            'color': 'black',
            'animation': 'scrollText 10s linear infinite',  # Animasi running text
            'whiteSpace': 'nowrap',  # Mencegah teks berjalan ke baris baru
        }
    ),

        html.Div(
        "Handling > 2 jam = OFFSIDE |1 alert OFFSIDE = -1 poin | 1 alert jadi case OFFSIDE = -2 poin",
        style={
            'marginTop': '10px',
            'fontStyle': 'italic',
            'textAlign': 'center',
            'color': 'black',
            'animation': 'scrollText 10s linear infinite',  # Animasi running text
            'whiteSpace': 'nowrap',  # Mencegah teks berjalan ke baris baru
        }
    ),
    
    # Tombol untuk menuju ke halaman kedua
    dcc.Link(
        html.Button('click me', style={'marginBottom': '15px', 'backgroundColor': 'grey', 'color': 'white', 'padding': '10px'}),
        href='/chart'),

    # Modal untuk menampilkan detail data
    html.Div(id='modal', style={'display': 'none', 'position': 'fixed', 'top': '0', 'left': '0', 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0, 0, 0, 0.5)', 'zIndex': '1000'}, children=[
        html.Div([
            html.Div([
                html.H3('Detail Data', style={'textAlign': 'center'}),
                dash_table.DataTable(
                    id='detail-table',
                    columns=[
                        {'name': 'No', 'id': 'No', 'type': 'numeric'},  # Kolom nomor
                        {'name': 'Alert ID', 'id': 'alert_id', 'type': 'numeric'},
                        {'name': 'Alert Time', 'id': 'alert_time', 'type': 'datetime'},
                        {'name': 'Alert Type', 'id': 'alert_type', 'type': 'text'},
                        {'name': 'Severity', 'id': 'severity', 'type': 'text'},
                        {'name': 'Alert Status', 'id': 'event_status', 'type': 'text'},
                        {'name': 'Ticket ID', 'id': 'ticket_id', 'type': 'numeric'},
                        {'name': 'Closed Time', 'id': 'closed_time', 'type': 'datetime'},
                        {'name': 'Created Case', 'id': 'created_case', 'type': 'text'},
                        {'name': 'Assignee', 'id': 'assignee', 'type': 'text'},
                        {'name': 'Comment', 'id': 'comment', 'type': 'text'},
                        {'name': 'Tenant Name', 'id': 'tenant_name', 'type': 'text'},
                        {'name': 'SLA Detect', 'id': 'sla_detect', 'type': 'text'},
                        {'name': 'SLA Response', 'id': 'sla_response', 'type': 'text'},
                        {'name': 'SLA Detect Criteria', 'id': 'sla_detect_criteria', 'type': 'text'},
                        {'name': 'SLA Response Criteria', 'id': 'sla_response_criteria', 'type': 'text'}
                    ],
                    style_table={
                        'overflowX': 'auto',
                        'maxHeight': '400px',  # Batasi ketinggian tabel
                        'overflowY': 'auto'  # Aktifkan scroll vertikal
                    },
                    style_cell={'textAlign': 'center'},
                    style_header={
                        'backgroundColor': 'lightgrey',
                        'fontWeight': 'bold',
                        'borderBottom': '2px solid black',
                        'position': 'sticky',
                        'top': 0,              # Posisi tetap di atas saat scroll
                        'zIndex': 1            # Agar header tetap di atas konten
                    },
                    style_data_conditional=[
                    {
                        'if': {'column_id': 'No'},
                        'position': 'sticky',
                        'left': 1,
                        'top' : 0,
                        'backgroundColor': 'white',  # Pastikan latar belakang tetap putih agar tidak tertimpa warna tabel
                        'zIndex': 0  # Pastikan tetap terlihat di atas kolom lainnya
                    }
    ]
),

                html.Button('Tutup', id='close-modal', style={'marginTop': '10px', 'display': 'block', 'marginLeft': 'auto', 'marginRight': 'auto'})
            ], style={'backgroundColor': 'lightgrey', 'padding': '20px', 'borderRadius': '10px', 'maxWidth': '90%', 'maxHeight': '90%', 'overflowY': 'auto', 'margin': '20px auto'})
        ], style={'position': 'relative', 'top': '50%', 'transform': 'translateY(-50%)'})
    ]),

    # dcc.Store untuk menyimpan state filter
    dcc.Store(id='filter-store', data={'year': '2025', 'month': '1'})
])

# Layout halaman analisis alert
layout_analisis_alert = html.Div([

    html.Title('Liga SOC'),
    
    # Judul
    html.H1("Summary Alerts Handling", style={'textAlign': 'center' , 'fontSize': '28px', 'marginBottom': '30px'}),
    
    # Logo
    html.Img(src='/assets/punggawalogo.jpg', style={'position': 'absolute', 'top': '10px', 'left': '10px', 'width': '260px'}),

    # Filter Bulan dan Tahun untuk halaman analisis alert
    html.Div([
        dcc.Dropdown(
            id='year-filter-chart',
            options=[{'label': str(year), 'value': str(year)} for year in range(2024, 2035)],
            value='2025',
            clearable=False,
            style={'width': '100px', 'display': 'inline-block','marginBottom': '1px', 'marginRight': '5px'}
        ),
        dcc.Dropdown(
            id='month-filter-chart',
            options=[
                {'label': 'Januari', 'value': '1'},
                {'label': 'Februari', 'value': '2'},
                {'label': 'Maret', 'value': '3'},
                {'label': 'April', 'value': '4'},
                {'label': 'Mei', 'value': '5'},
                {'label': 'Juni', 'value': '6'},
                {'label': 'Juli', 'value': '7'},
                {'label': 'Agustus', 'value': '8'},
                {'label': 'September', 'value': '9'},
                {'label': 'Oktober', 'value': '10'},
                {'label': 'November', 'value': '11'},
                {'label': 'Desember', 'value': '12'}
            ],
            value='3',
            clearable=False,
            style={'width': '150px', 'display': 'inline-block', 'marginBottom': '1px'}
        )
    ], style={'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'marginBottom': '1px', 'gap': '10px'}),
    
    # Tombol untuk kembali ke halaman utama
    dcc.Link(
        html.Button('Back', style={'marginBottom': '5px', 'backgroundColor': 'grey', 'color': 'white', 'padding': '8px'}),
        href='/'
    ),

    # Pie Chart dan Keterangan di samping pie chart
    html.Div([
        # Pie Chart
        dcc.Graph(id='pie-chart'),

        # Keterangan di samping pie chart
        html.Div(id='pie-chart-info', style={
            'padding': '20px',
            'textAlign': 'left',
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'left',
            'alignItems': 'flex-start'
        }),

    ], style={'display': 'flex', 'justifyContent': 'left', 'marginBottom': '1px', 'alignItems': 'center', 'gap': '20px'}),  # Untuk meletakkan pie chart dan keterangan berdampingan

    # Menambahkan Bar Chart
    html.Div([
        # Bar Chart
        dcc.Graph(id='bar-chart'),
    ], style={'marginTop': '1px'})
])

# Layout utama aplikasi
app.layout = html.Div([
    html.Title('Liga SOC'),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Mencegah pemanggilan awal untuk menghindari siklus
@app.callback(
    Output('filter-store', 'data'),
    [Input('year-filter', 'value'), Input('month-filter', 'value')],
    prevent_initial_call=True
)
def save_filter_state(selected_year, selected_month):
    return {'year': selected_year, 'month': selected_month}

def update_table(selected_year, selected_month, n_intervals):
    return filter_data(selected_year, selected_month).to_dict('records')

# Callback untuk menangani klik pada sel tabel dan menampilkan modal
@app.callback(
    [Output('modal', 'style'), Output('detail-table', 'data')],
    [Input('leaderboard-table', 'active_cell'), Input('close-modal', 'n_clicks')],
    [State('leaderboard-table', 'data'), State('modal', 'style'),
     State('year-filter', 'value'), State('month-filter', 'value')]
)

def handle_cell_click(active_cell, n_clicks, table_data, modal_style, selected_year, selected_month):
    ctx = dash.callback_context

    if not ctx.triggered:
        return {'display': 'none'}, []

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'leaderboard-table' and active_cell:
        row = active_cell['row']
        col = active_cell['column_id']

        if col in ['Alert', 'Alert_Case', 'Alerts_PASS', 'Alerts_Case_PASS', 'Alerts_OFFSIDE', 'Alerts_Case_OFFSIDE']:
            assignee = table_data[row]['assignee']
            
            # Filter data based on year and month first
            filtered_df = df[(df['assignee'] == assignee) & 
                             (df['alert_time'].dt.year == int(selected_year)) & 
                             (df['alert_time'].dt.month == int(selected_month))]

            if col == 'Alert':
                filtered_df = filtered_df[filtered_df['alert_id'].notnull()]
            elif col == 'Alert_Case':
                filtered_df = filtered_df[filtered_df['created_case'].notnull()]
            elif col == 'Alerts_PASS':
                filtered_df = filtered_df[filtered_df['sla_detect_criteria'] == 'PASS']
            elif col == 'Alerts_Case_PASS':
                filtered_df = filtered_df[filtered_df['sla_response_criteria'] == 'PASS']
            elif col == 'Alerts_OFFSIDE':
                filtered_df = filtered_df[filtered_df['sla_detect_criteria'] == 'OFFSIDE']
            elif col == 'Alerts_Case_OFFSIDE':
                filtered_df = filtered_df[filtered_df['sla_response_criteria'] == 'OFFSIDE']

            # Menambahkan kolom nomor (index)
            filtered_df = filtered_df.reset_index(drop=True).reset_index()
            filtered_df['index'] += 1  # Mulai dari 1, bukan 0
            filtered_df.rename(columns={'index': 'No'}, inplace=True)

            return {'display': 'block'}, filtered_df.to_dict('records')

    return {'display': 'none'}, []

# Callback untuk mengubah halaman berdasarkan URL
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/chart':
        return layout_analisis_alert
    else:
        return layout_halaman_utama

# Callback untuk update tabel di halaman utama
# Callback untuk update tabel di halaman utama
@app.callback(
    Output('leaderboard-table', 'data'),
    [Input('year-filter', 'value'), Input('month-filter', 'value')]
)

def update_table(selected_year, selected_month):
    return filter_data(selected_year, selected_month).to_dict('records')

# Callback untuk pie chart di halaman analisis alert
@app.callback(
    [Output('pie-chart', 'figure'), Output('pie-chart-info', 'children')],
    [Input('year-filter-chart', 'value'), Input('month-filter-chart', 'value')]
)
def update_pie_chart(selected_year, selected_month):
    # Filter data berdasarkan tahun dan bulan
    filtered_df = df[(df['alert_time'].dt.year == int(selected_year)) & (df['alert_time'].dt.month == int(selected_month))]
    
    # Hitung jumlah alert, PASS, OFFSIDE, dan case
    total_alert = len(filtered_df)
    total_pass = len(filtered_df[filtered_df['sla_detect_criteria'] == 'PASS'])
    total_offside = len(filtered_df[filtered_df['sla_detect_criteria'] == 'OFFSIDE'])
    total_case = filtered_df['created_case'].notnull().sum()

    # Buat pie chart
    pie_data = filtered_df['sla_detect_criteria'].value_counts().reset_index()
    pie_data.columns = ['sla_detect_criteria', 'count']
    # Membuat Pie Chart dengan garis pembatas
    pass_percentage = (total_pass / total_alert) * 100 if total_alert > 0 else 0
    title_text = f"<b>SLA Achievement = {pass_percentage:.1f}%</b>"
    fig = px.pie(pie_data, values='count', names='sla_detect_criteria', title=title_text)

    # Menambahkan pengaturan ukuran pie chart
    fig.update_layout(
        height=400,  # Menentukan tinggi chart
        width=400,   # Menentukan lebar chart
    )

    # Buat keterangan di samping pie chart
    keterangan = html.Div([
        html.Div([
            html.P(html.B(f"Total Alert: {total_alert}")),
            html.P(html.Strong(f"Total PASS: {total_pass}")),
            html.P(html.B(f"Total OFFSIDE: {total_offside}")),
            html.P(html.B(f"Total Case: {total_case}"))
        ], style={'padding': '20px', 'textAlign': 'left', 'marginBottom': '1px' })
    ], style={
        'display': 'flex',  # Menyusun elemen-elemen dalam satu baris (bersebelahan)
        'flexDirection': 'row',  # Susun elemen secara horisontal
        'alignItems': 'center',  # Menyelaraskan elemen secara vertikal
        'justifyContent': 'center',  # Menyelaraskan elemen secara horizontal
        'width': '100%',  # Menggunakan lebar penuh agar pie chart dan keterangan terletak berdampingan
        'marginBottom': '1px'
    })

    # Kembalikan fig dan keterangan
    return fig, keterangan

# Callback untuk bar chart di halaman analisis alert
@app.callback(
    Output('bar-chart', 'figure'),
    [Input('year-filter-chart', 'value'), Input('month-filter-chart', 'value')]
)
def update_bar_chart(selected_year, selected_month):
    filtered_df = df[(df['alert_time'].dt.year == int(selected_year)) & (df['alert_time'].dt.month == int(selected_month))]
    bar_data = filtered_df['assignee'].value_counts().reset_index()
    bar_data.columns = ['assignee', 'count']
    bar_data = bar_data.sort_values('count', ascending=False)
    title_text2 = f"<b>Jumlah Alert per Analis</b>"
    fig = px.bar(bar_data, x='assignee', y='count', title=title_text2)
    return fig

# Gaskeun
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)