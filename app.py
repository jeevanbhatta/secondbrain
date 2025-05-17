from flask import Flask, render_template
from App.routes import main_bp

app = Flask(__name__, 
    template_folder='App/templates',
    static_folder='App/static'
)

# Register blueprints
app.register_blueprint(main_bp)

if __name__ == '__main__':
    app.run(debug=True)
