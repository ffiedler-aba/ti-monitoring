import dash
from dash import html, dcc
import os
import markdown
from mylibrary import *

# Register the page
dash.register_page(__name__, path='/impressum', title='Impressum')

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

        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])

        # Return the HTML content with proper styling
        return html.Div([
            html.Div(html_content, dangerouslySetInnerHTML={'__html': html_content}, className='markdown-content')
        ], style={'padding': '20px'})

    except Exception as e:
        return html.Div([
            html.H2("Fehler beim Laden", style={'color': '#e74c3c'}),
            html.P(f"Ein Fehler ist beim Laden der Datei aufgetreten: {str(e)}")
        ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})

def serve_layout():
    """Serve the impressum page layout"""
    return html.Div([
        # Header section with title
        html.Div([
            html.H1('Impressum', style={
                'color': '#2c3e50',
                'fontWeight': '600',
                'marginBottom': '30px',
                'borderBottom': '2px solid #3498db',
                'paddingBottom': '10px'
            })
        ], style={'marginBottom': '30px'}),

        # Main content area
        html.Div([
            load_markdown_content('impressum.md')
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
                'Dieses Impressum ist Teil des ',
                html.A('TI-Monitoring Systems', href='/', style={'color': '#3498db', 'textDecoration': 'none'}),
                '. Für weitere Informationen besuchen Sie bitte unsere ',
                html.A('Startseite', href='/', style={'color': '#3498db', 'textDecoration': 'none'}),
                ' oder die ',
                html.A('Datenschutzerklärung', href='/datenschutz', style={'color': '#3498db', 'textDecoration': 'none'}),
                '.'
            ], style={
                'color': '#6c757d',
                'fontSize': '14px',
                'textAlign': 'center',
                'marginBottom': '20px'
            }),
            html.P([
                'Stand: ',
                html.Span(id='last-updated', style={'fontWeight': '500'})
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

# Store component for dynamic content updates
dcc.Store(id='impressum-store', data={'loaded': True})

# Callback to update last updated timestamp
@callback(
    Output('last-updated', 'children'),
    Input('impressum-store', 'data')
)
def update_last_updated(data):
    """Update the last updated timestamp"""
    from datetime import datetime
    return datetime.now().strftime('%d.%m.%Y')

layout = serve_layout
