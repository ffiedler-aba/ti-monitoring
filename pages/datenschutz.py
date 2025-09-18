import dash
from dash import html, dcc
import os
from mylibrary import *

# Register the page
dash.register_page(__name__, path='/datenschutz', title='Datenschutz')

def load_markdown_content(filename):
    """Load and render markdown content from assets directory"""
    try:
        # Get the path to the assets directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(current_dir, '..', 'assets')
        file_path = os.path.join(assets_dir, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            return html.Div([
                html.H2("Datei nicht gefunden", style={'color': '#e74c3c'}),
                html.P(f"Die Datei {filename} wurde nicht gefunden. Bitte erstellen Sie die Datei im assets-Verzeichnis.")
            ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})

        # Read and render markdown
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Use dcc.Markdown for proper rendering in Dash
        return html.Div([
            dcc.Markdown(
                markdown_content,
                className='markdown-content'
            )
        ], style={'padding': '20px'})

    except Exception as e:
        return html.Div([
            html.H2("Fehler beim Laden", style={'color': '#e74c3c'}),
            html.P(f"Ein Fehler ist beim Laden der Datei aufgetreten: {str(e)}")
        ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})

def create_page_header(title):
    """Create consistent page header with logo"""
    return html.Header([
        html.Div([
            html.Div(id='logo-wrapper', children=[
                html.A(href='/', children=[
                    html.Img(id='logo', src='/assets/logo.svg', alt='TI-Monitoring Logo', height=50, width=50)
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
        'borderBottom': '2px solid #3498db',
        'paddingBottom': '10px'
    })

def serve_layout():
    """Serve the datenschutz page layout"""
    return html.Div([
        # Header section with logo and title
        create_page_header('Datenschutz'),

        # Main content area
        html.Div([
            load_markdown_content('datenschutz.md')
        ], style={
            'backgroundColor': 'white',
            'borderRadius': '12px',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
            'marginBottom': '30px'
        }),

        # Footer section
        html.Div([
            html.Hr(style={'borderColor': '#e9ecef', 'margin': '40px 0 20px 0'}),
            html.P([
                'Diese Datenschutzerklärung ist Teil des ',
                html.A('TI-Monitoring Systems', href='/', style={'color': '#3498db', 'textDecoration': 'none'}),
                '. Für weitere Informationen besuchen Sie bitte unsere ',
                html.A('Startseite', href='/', style={'color': '#3498db', 'textDecoration': 'none'}),
                ' oder das ',
                html.A('Impressum', href='/impressum', style={'color': '#3498db', 'textDecoration': 'none'}),
                '.'
            ], style={
                'color': '#6c757d',
                'fontSize': '14px',
                'textAlign': 'center',
                'marginBottom': '20px'
            }),
            html.P([
                'Stand: ',
                html.Span(current_date, style={'fontWeight': '500'})
            ], style={
                'color': '#6c757d',
                'fontSize': '12px',
                'textAlign': 'center'
            })
        ], style={'marginTop': 'auto'})
    ], style={
        'maxWidth': '1200px',
        'margin': '0 auto',
        'padding': '20px',
        'minHeight': '100vh',
        'display': 'flex',
        'flexDirection': 'column'
    })

# Static timestamp - no callback needed
from datetime import datetime
current_date = datetime.now().strftime('%d.%m.%Y')

layout = serve_layout
