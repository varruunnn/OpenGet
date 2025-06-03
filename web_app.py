import os
import threading
import uuid
from flask import Flask, request, jsonify, render_template, send_file

from src.downloader import download as downloader_download
from src.utils import get_file_info

app = Flask(__name__)

DOWNLOAD_ROOT = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

JOBS = {}
JOBS_LOCK = threading.Lock()

def compute_progress(job):
    total = job["total_size"]
    output_path = job["output_path"]
    temp_folder = output_path + "_parts"
    if job["status"] == "complete" and os.path.exists(output_path):
        return total, total
    downloaded = 0
    if os.path.isdir(temp_folder):
        for fname in os.listdir(temp_folder):
            fpath = os.path.join(temp_folder, fname)
            if os.path.isfile(fpath):
                downloaded += os.path.getsize(fpath)
    return downloaded, total or 0

def background_download(job_id, resume_flag=False):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "downloading"
    url = job["url"]
    connections = job["connections"]
    output_path = job["output_path"]
    try:
        downloader_download(
            url,
            output_path,
            connections=connections,
            resume=resume_flag
        )
        with JOBS_LOCK:
            job["status"] = "complete"
    except Exception as e:
        with JOBS_LOCK:
            job["status"] = "error"
            job["error"] = str(e)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    url = data.get("url")
    connections = data.get("connections", 4)
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        connections = int(connections)
        if connections < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "connections must be a positive integer"}), 400
    try:
        total_size, accepts = get_file_info(url)
    except Exception as e:
        return jsonify({"error": f"Could not fetch file info: {e}"}), 400
    job_id = str(uuid.uuid4())
    output_filename = f"{job_id}.bin"
    output_path = os.path.join(DOWNLOAD_ROOT, output_filename)
    job = {
        "url": url,
        "connections": connections,
        "status": "queued",
        "total_size": total_size,
        "downloaded": 0,
        "error": None,
        "output_path": output_path
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    threading.Thread(
        target=background_download,
        args=(job_id, False),
        daemon=True
    ).start()
    return jsonify({"job_id": job_id}), 202

@app.route("/api/progress")
def api_progress():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id parameter is required"}), 400
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Invalid job_id"}), 404
        status = job["status"]
        total_size = job["total_size"]
        error = job["error"]
    downloaded, total = compute_progress(job)
    percent = round(downloaded / total * 100, 2) if total else 0.0
    can_resume = False
    temp_folder = job["output_path"] + "_parts"
    if status == "error" and os.path.isdir(temp_folder):
        can_resume = True
    return jsonify({
        "status": status,
        "total_size": total,
        "downloaded": downloaded,
        "percent": percent,
        "error": error,
        "can_resume": can_resume
    })

@app.route("/api/resume", methods=["POST"])
def api_resume():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Invalid job_id"}), 404
        if job["status"] != "error":
            return jsonify({"error": "Job is not resumable"}), 400
        job["status"] = "queued"
        job["error"] = None
    threading.Thread(
        target=background_download,
        args=(job_id, True),
        daemon=True
    ).start()
    return jsonify({"message": "Resume started"}), 202

@app.route("/api/file")
def api_file():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id parameter is required"}), 400
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Invalid job_id"}), 404
        if job["status"] != "complete":
            return jsonify({"error": "File not ready"}), 400
        output_path = job["output_path"]
    if not os.path.exists(output_path):
        return jsonify({"error": "Output file not found"}), 404
    return send_file(output_path, as_attachment=True, download_name=f"{job_id}.bin")

@app.route("/api/jobs")
def api_jobs():
    with JOBS_LOCK:
        summary = {
            jid: {
                "status": j["status"],
                "percent": round(compute_progress(j)[0] / (j["total_size"] or 1) * 100, 2)
            }
            for jid, j in JOBS.items()
        }
    return jsonify(summary)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
