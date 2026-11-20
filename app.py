import os, subprocess, tempfile, shutil
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

def esc(t):
    return (t or "").replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace("%", "\\%")[:90]

@app.get("/")
def health():
    return jsonify(ok=True)

@app.post("/render")
def render():
    d = request.get_json(force=True)
    url, start, end = d["videoUrl"], float(d["start"]), float(d["end"])
    hook = esc(d.get("hook", ""))
    dur = max(5.0, end - start)
    tmp = tempfile.mkdtemp()
    try:
        raw = os.path.join(tmp, "raw.mp4")
        out = os.path.join(tmp, "reel.mp4")
        # download only the needed section
        subprocess.run([
            "yt-dlp", "-f", "bv*[height<=720]+ba/b[height<=720]",
            "--download-sections", f"*{start}-{end}", "--force-keyframes-at-cuts",
            "--merge-output-format", "mp4", "-o", raw, url], check=True, timeout=600)
        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        # blurred 9:16 background + sharp centred foreground + slow zoom punch-in + hook caption
        fc = (
            "[0:v]split=2[a][b];"
            "[a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=30:5[bg];"
            "[b]scale=720:-2,zoompan=z='min(1.0+0.0008*on,1.12)':d=1:s=720x405:fps=30[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v1];"
            f"[v1]drawtext=fontfile={font}:text='{hook}':fontsize=44:fontcolor=white:"
            "borderw=4:bordercolor=black:x=(w-text_w)/2:y=160:enable='between(t,0,4)',"
            f"fade=t=in:d=0.3,fade=t=out:st={dur-0.4}:d=0.4[v]"
        )
        subprocess.run([
            "ffmpeg", "-y", "-i", raw, "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
            "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.2,afade=t=out:st={dur-0.4}:d=0.4",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-r", "30", out],
            check=True, timeout=900)
        resp = send_file(out, mimetype="video/mp4", download_name="reel.mp4")
        resp.call_on_close(lambda: shutil.rmtree(tmp, ignore_errors=True))
        return resp
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
