import dash
from dash import html


def create_admin_header(title):
    """Create consistent admin header with logo"""
    return html.Header([
        html.Div([
            html.Div(id='logo-wrapper', children=[
                html.A(href='/', children=[
                    html.Img(id='logo', src='/assets/logo.svg', alt='TI-Stats Logo', height=50, width=50)
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}),
            html.H1(title, style={
                'margin': '0',
                'fontSize': '1.6rem',
                'color': '#2c3e50'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '16px'})
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'marginBottom': '30px',
        'borderBottom': '2px solid #e74c3c',
        'paddingBottom': '10px'
    })
