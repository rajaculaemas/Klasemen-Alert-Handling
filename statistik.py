import dash
from dash import dcc, html
import plotly.express as px
from dash.dependencies import Input, Output
from utils import filter_data  # Impor dari utils.py

# Layout halaman statistik
layout = html.Div([
    html.H1("Statistik Alerts Handling", style={'textAlign': 'center'}),
    dcc.Graph(id='pie-chart'),
    dcc.Graph(id='bar-chart'),
    html.Button('Kembali ke Halaman Utama', id='btn-kembali', n_clicks=0, style={'marginTop': '20px', 'display': 'block', 'marginLeft': 'auto', 'marginRight': 'auto'})
])

# Callback untuk menampilkan pie chart dan bar chart
@app.callback(
    [Output('pie-chart', 'figure'), Output('bar-chart', 'figure')],
    [Input('url', 'pathname'), Input('year-filter', 'value'), Input('month-filter', 'value')]
)
def update_charts(pathname, selected_year, selected_month):
    if pathname != '/statistik':
        return {}, {}

    filtered_df = filter_data(selected_year, selected_month)
    total_alerts = filtered_df['Alert'].sum()
    total_pass = filtered_df['Alerts_PASS'].sum()
    total_offside = filtered_df['Alerts_OFFSIDE'].sum()

    pie_chart = px.pie(
        names=['PASS', 'OFFSIDE'],
        values=[total_pass, total_offside],
        title='Persentase PASS dan OFFSIDE'
    )

    bar_chart = px.bar(
        filtered_df,
        x='assignee',
        y='Alert',
        title='Jumlah Alert per Analis',
        labels={'assignee': 'Nama Analis', 'Alert': 'Jumlah Alert'}
    )

    return pie_chart, bar_chart