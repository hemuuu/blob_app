from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import os, subprocess, threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
# no need for broadcast arg
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = os.path.join("static", "uploads")
OUTPUT_FOLDER = os.path.join("static", "output")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED = {"mp4", "mov", "avi", "mkv"}

def allowed_file(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED

@socketio.on('connect')
def on_connect():
    print("📡 Client connected")

def run_blob_script(input_path, output_path):
    # Start at 0%
    socketio.emit("process_progress", {"progress": 0})

    proc = subprocess.Popen(
        ["python", "blob_processor.py", input_path, output_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    total = None
    for line in proc.stdout:
        if total is None and "Processing" in line and "frames" in line:
            try:
                total = int(line.split("Processing")[1].split("frames")[0].strip())
            except:
                total = None

        if total and "Frame" in line and "/" in line:
            parts = line.strip().split()
            for t in parts:
                if "/" in t:
                    try:
                        i, _ = t.split("/")
                        percent = int(int(i) / total * 100)
                        socketio.emit("process_progress", {"progress": percent})
                    except:
                        pass
                    break

    proc.wait()
    # Final 100%
    socketio.emit("process_progress", {"progress": 100})
    socketio.emit("process_complete", {"filename": os.path.basename(output_path)})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["video"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid filename"}), 400

    fname    = secure_filename(file.filename)
    in_path  = os.path.join(UPLOAD_FOLDER, fname)
    file.save(in_path)

    # upload is done
    socketio.emit("upload_progress", {"progress": 100})

    out_name = f"processed_{fname}"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)

    threading.Thread(
        target=run_blob_script,
        args=(in_path, out_path),
        daemon=True
    ).start()

    return jsonify({"status":"ok","filename":out_name})

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    socketio.run(app, debug=True)
