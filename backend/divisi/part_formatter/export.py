import subprocess

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
    
def export_mscz_to_pdf_score_and_parts(input_file_path: str, output_dir: str):
    """
    Uses Musescore to render the provided musescore file and output a pdf of the score
    """
    try:
        subprocess.run(
            ["mscore4", "--export-score-parts", input_file_path], cwd=output_dir, check=True
        )
        return {"status": "success"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}