from flask import Flask, jsonify, make_response, request


app = Flask(__name__)

@app.get("/test")
def test():
    return make_response(jsonify({"args": request.args}), 200)

if __name__ == "__main__":
    app.run()