import dash
import dash_html_components as html
import dash_core_components as dcc

# Initialize Dash app with responsive meta tags
app = dash.Dash(
    __name__,
    title="Episcopio - Monitoreo Epidemiológico",
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ]
)

# Expose the Flask server for Gunicorn
server = app.server

# Add your additional Dash layouts and callbacks here

# Run the server if this script is executed directly
if __name__ == '__main__':
    app.run_server(debug=True)