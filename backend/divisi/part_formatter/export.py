import subprocess
import os, json, base64, subprocess, binascii

def export_mscz_to_pdf_score(input_file_path: str, output_path: str):
    """
    Uses Musescore to render the provided musescore file and output a pdf of the score
    """
    try:
        subprocess.run(
            ["mscore4", input_file_path, "-o", output_path], check=True
        )
        return {"status": "success", "output": output_path}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}
    

# Thank you GPT - remind me to open a ticket with musescore people to figure out why parts export is not working...
def _b64_pdf(s: str) -> bytes:
    # Handle single or double base64 (MS 4.5.x bug)
    first = base64.b64decode(s)
    if first.startswith(b"%PDF-"):
        return first
    try:
        second = base64.b64decode(first)
        if second.startswith(b"%PDF-"):
            return second
    except binascii.Error:
        pass
    return first  # fall back

def export_score_and_parts_ms4(input_file, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")  # safer in containers

    try:
        proc = subprocess.run(
            ["mscore4", "--score-parts-pdf", input_file],
            check=True, capture_output=True, env=env
        )
        data = json.loads(proc.stdout.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}

    stem = os.path.splitext(os.path.basename(input_file))[0]
    written = []

    # Full score only
    if "scoreBin" in data:
        full_score_pdf = base64.b64decode(data["scoreBin"])
        p = os.path.join(out_dir, f"{stem}.pdf")
        with open(p, "wb") as f: f.write(full_score_pdf)
        written.append(p)

    # Combined score + parts
    for key in ("scoreFullBin", "fullScoreBin"):
        if key in data:
            comb_pdf = _b64_pdf(data[key])
            p = os.path.join(out_dir, f"{stem}-Score+Parts.pdf")
            with open(p, "wb") as f: f.write(comb_pdf)
            written.append(p)
            break

    # Individual parts
    # Two shapes observed: either `parts` array with `{name, bin}` or `partsBin` with `{name, pdf}`
    parts_list = []
    if "parts" in data and isinstance(data["parts"], list):
        parts_list = data["parts"]
    elif "partsBin" in data and isinstance(data["partsBin"], list):
        parts_list = data["partsBin"]

    for part in parts_list:
        if isinstance(part, dict):
            name = part.get("name") or part.get("partName") or "Part"
            b64 = part.get("bin") or part.get("pdf") or part.get("pdfBin")
        elif isinstance(part, list) and len(part) == 2:
            name, b64 = part
        else:
            continue  # skip unexpected shapes

        pdf = base64.b64decode(b64)
        safe_name = "".join(c for c in name if c not in r'\/:*?"<>|').strip()
        p = os.path.join(out_dir, f"{stem} - {safe_name}.pdf")
        with open(p, "wb") as f:
            f.write(pdf)
        written.append(p)

    return {"status": "success", "written": written}