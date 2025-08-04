import dash
from dash import html, dcc
import plotly.express as px
from mylibrary import *
from myconfig import *

dash.register_page(__name__)


def serve_layout(ci=None, **other_unknown_query_strings):
    cutoff = (pd.Timestamp.now() - pd.Timedelta(hours=stats_delta_hours)).tz_localize('UTC').tz_convert('Europe/Berlin')
    ci_data = get_availability_data_of_ci(file_name, ci)
    ci_data = ci_data[ci_data['times']>=cutoff]
    number_of_values = len(ci_data['values'])
    mean_availability = np.mean(ci_data['values'].values)
    first_timestamp = ci_data['times'].iloc[0].strftime('%d.%m.%Y %H:%M:%S Uhr')
    last_timestamp = ci_data['times'].iloc[-1].strftime('%d.%m.%Y %H:%M:%S Uhr')
    ci_data = ci_data.rename(columns={
        'times': 'Zeit',
        'values': 'Verfügbarkeit'
    })
    custom_colors = ['red' if v == 0 else 'green' for v in ci_data['Verfügbarkeit']]
    fig = px.scatter(
        ci_data,
        x = 'Zeit',
        y = 'Verfügbarkeit',
    )
    fig.update_traces(marker=dict(color=custom_colors))
    fig.update_yaxes(tickvals=[0, 1], ticktext=['0', '1'])
    fig.update_layout(yaxis=dict(range=[-0.1, 1.1]))
    ci_info = get_data_of_ci(file_name, ci)
    layout = [
        html.H2('Verfügbarkeit der Komponente ' + str(ci)),
        html.H3(ci_info['product'] + ', ' + ci_info['name'] + ', ' + ci_info['organization']),
        html.A(href=home_url, children = [
            html.Button('Zurück', className = 'button')
        ]),
        html.Div(id = 'statistics', className = 'box', children = [
            html.H3('Statistik'),
            html.Ul([
                html.Li('Anzahl der Werte: ' + str(number_of_values)),
                html.Li('Erster Wert: ' + str(first_timestamp)),
                html.Li('Letzter Wert: ' + str(last_timestamp)),
                html.Li('Verfügbarkeit in diesem Zeitraum: ' + str(mean_availability * 100) + ' %')
            ])
        ]),
        dcc.Graph(figure=fig)
    ]
    return layout

layout = serve_layout