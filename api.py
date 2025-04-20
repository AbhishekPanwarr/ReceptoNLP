from flask import Flask, request, jsonify
from pyngrok import ngrok
from run import find_best_linkedin_match

app = Flask(__name__)

@app.route('/persona', methods=['POST'])
def handle_persona():
    data = request.get_json()
    

    persona = data.get("persona", {})
    result = find_best_linkedin_match(persona)
    response = {
        "message": "Status 200!",
        "Result": result
    }

    return jsonify(response)

if __name__ == '__main__':

    public_url = ngrok.connect(5000)
    print(f"Public ngrok URL: {public_url}/persona")

    app.run(port=5000)
