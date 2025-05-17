from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from App.routes import main_bp

app = Flask(__name__, 
    template_folder='App/templates',
    static_folder='App/static'
)

# Enable CORS for the extension
CORS(app, resources={r"/api/*": {"origins": "chrome-extension://*"}})

# Register blueprints
app.register_blueprint(main_bp)

# API endpoints for the extension
@app.route('/api/save-page', methods=['POST'])
def save_page():
    data = request.json
    # Here you can add logic to save the page data to your database
    # For now, we'll just return a success message
    return jsonify({
        "message": f"Successfully saved page: {data['title']}",
        "status": "success"
    })

@app.route('/api/example', methods=['GET'])
def example_api():
    return jsonify({"message": "Hello from Flask!"})

@app.route('/api/example', methods=['POST'])
def example_post():
    data = request.json
    return jsonify({"status": "success", "data": data})

if __name__ == '__main__':
    app.run(debug=True)
