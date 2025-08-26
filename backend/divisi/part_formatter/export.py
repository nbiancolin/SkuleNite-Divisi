import subprocess
import os, json, base64, subprocess, binascii

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
from logging import getLogger

logger = getLogger("export")

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
    

def export_score_and_parts_ms4_storage(input_key, output_prefix):
    """
    Export score and parts using Django storage system.
    
    Args:
        input_key: Storage key for the input .mscz file
        output_prefix: Storage path prefix for output files (should end with '/')
    
    Returns:
        dict: {"status": "success|error", "written": [...], "details": "..."}
    """
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")  # safer in containers
    
    # Create temporary directory for local processing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download input file from storage to temporary location
            temp_input = os.path.join(temp_dir, "input.mscz")
            with default_storage.open(input_key, 'rb') as storage_file:
                with open(temp_input, 'wb') as temp_file:
                    temp_file.write(storage_file.read())
            
            # Run mscore4 command
            proc = subprocess.run(
                ["mscore4", "--score-parts-pdf", temp_input],
                check=True, capture_output=True, env=env
            )
            data = json.loads(proc.stdout.decode("utf-8"))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"mscore4 command failed: {e}")
            return {"status": "error", "details": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse mscore4 output: {e}")
            return {"status": "error", "details": f"JSON decode error: {e}"}
        except Exception as e:
            logger.error(f"Failed to download or process input file: {e}")
            return {"status": "error", "details": str(e)}
        
        # Extract base filename without extension
        input_filename = os.path.basename(input_key)
        stem = os.path.splitext(input_filename)[0]
        written = []
        
        try:
            # Full score only
            if "scoreBin" in data:
                full_score_pdf = base64.b64decode(data["scoreBin"])
                score_key = f"{output_prefix}{stem}.pdf"
                default_storage.save(score_key, ContentFile(full_score_pdf))
                written.append(score_key)
                logger.info(f"Saved full score: {score_key}")
            
            # Combined score + parts
            for key in ("scoreFullBin", "fullScoreBin"):
                if key in data:
                    comb_pdf = base64.b64decode(data[key])
                    combined_key = f"{output_prefix}{stem}-Score+Parts.pdf"
                    default_storage.save(combined_key, ContentFile(comb_pdf))
                    written.append(combined_key)
                    logger.info(f"Saved combined score+parts: {combined_key}")
                    break
            
            # Individual parts
            # Two shapes observed: either `parts` array with `{name, bin}` or `partsBin` with `{name, pdf}`
            parts_list = []
            if "parts" in data and isinstance(data["parts"], list):
                parts_list = data["parts"]
            elif "partsBin" in data and isinstance(data["partsBin"], list):
                parts_list = data["partsBin"]
            
            for part in parts_list:
                try:
                    if isinstance(part, dict):
                        name = part.get("name") or part.get("partName") or "Part"
                        b64 = part.get("bin") or part.get("pdf") or part.get("pdfBin")
                    elif isinstance(part, list) and len(part) == 2:
                        name, b64 = part
                    else:
                        logger.warning(f"Unexpected part format, skipping: {part}")
                        continue  # skip unexpected shapes
                    
                    if not b64:
                        logger.warning(f"No PDF data found for part: {name}")
                        continue
                    
                    pdf = base64.b64decode(b64)
                    safe_name = "".join(c for c in name if c not in r'\/:*?"<>|').strip()
                    part_key = f"{output_prefix}{stem} - {safe_name}.pdf"
                    default_storage.save(part_key, ContentFile(pdf))
                    written.append(part_key)
                    logger.info(f"Saved part: {part_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to process part {name if 'name' in locals() else 'unknown'}: {e}")
                    continue
            
            logger.info(f"Successfully exported {len(written)} files")
            return {"status": "success", "written": written}
            
        except Exception as e:
            logger.error(f"Failed to save files to storage: {e}")
            return {"status": "error", "details": f"Storage error: {e}"}
