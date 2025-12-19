import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Discord bot big guy ok"

def run():
    # Use the port assigned by the host, or default to 8080 if running locally
    port = int(os.environ.get("PORT", 8080))
    # host="0.0.0.0" is required to make the server accessible externally
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    # daemon=True ensures the thread dies if the main program exits
    t.daemon = True
    t.start()