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


def export_score_and_parts_ms4_storage(input_storage_key, output_prefix_key):
    """
    Export score and parts using storage keys instead of file paths.
    
    Args:
        input_storage_key: Storage key for the input file
        output_prefix_key: Prefix for output storage keys (without filename)
    
    Returns:
        dict: Status and list of storage keys written
    """
    
    # Check if input file exists
    if not default_storage.exists(input_storage_key):
        return {"status": "error", "details": f"Input file does not exist: {input_storage_key}"}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download input file to temporary location
            input_filename = os.path.basename(input_storage_key)
            temp_input_path = os.path.join(temp_dir, input_filename)
            
            # Better file download with proper binary handling
            with default_storage.open(input_storage_key, 'rb') as storage_file:
                with open(temp_input_path, 'wb') as temp_file:
                    # Use shutil.copyfileobj for more reliable copying
                    import shutil
                    shutil.copyfileobj(storage_file, temp_file)
            
            logger.info(f"Downloaded input file to: {temp_input_path}")
            
            # Verify the downloaded file exists and has content
            if not os.path.exists(temp_input_path) or os.path.getsize(temp_input_path) == 0:
                return {"status": "error", "details": "Downloaded file is empty or missing"}
            
            # Run mscore4 export
            env = os.environ.copy()
            env.setdefault("QT_QPA_PLATFORM", "offscreen")
            
            proc = subprocess.run(
                ["mscore4", "--score-parts-pdf", temp_input_path],
                check=True, capture_output=True, env=env, text=False  # Ensure binary output
            )
            
            # Decode stdout as text for JSON parsing
            stdout_text = proc.stdout.decode("utf-8")
            data = json.loads(stdout_text)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            return {"status": "error", "details": f"mscore4 failed: {error_msg}"}
        except json.JSONDecodeError as e:
            return {"status": "error", "details": f"Failed to parse mscore4 output as JSON: {str(e)}"}
        except Exception as e:
            return {"status": "error", "details": f"Unexpected error: {str(e)}"}
        
        # Process the results and upload to storage
        stem = os.path.splitext(input_filename)[0]
        written_keys = []
        
        try:
            # Full score only
            if "scoreBin" in data:
                try:
                    full_score_pdf = base64.b64decode(data["scoreBin"])
                    # Validate it's actually a PDF
                    if not full_score_pdf.startswith(b'%PDF'):
                        logger.warning("Score PDF doesn't start with PDF header")
                    
                    storage_key = f"{output_prefix_key}{stem}.pdf"
                    
                    # Use io.BytesIO for better memory handling
                    from io import BytesIO
                    pdf_file = BytesIO(full_score_pdf)
                    default_storage.save(storage_key, ContentFile(pdf_file.getvalue(), name=f"{stem}.pdf"))
                    written_keys.append(storage_key)
                    logger.info(f"Uploaded full score to: {storage_key} ({len(full_score_pdf)} bytes)")
                except Exception as e:
                    logger.error(f"Failed to process full score: {str(e)}")
            
            # Combined score + parts
            for key in ("scoreFullBin", "fullScoreBin"):
                if key in data:
                    try:
                        comb_pdf = base64.b64decode(data[key])
                        # Validate PDF header
                        if not comb_pdf.startswith(b'%PDF'):
                            logger.warning(f"Combined PDF ({key}) doesn't start with PDF header")
                        
                        storage_key = f"{output_prefix_key}{stem}-Score+Parts.pdf"
                        pdf_file = BytesIO(comb_pdf)
                        default_storage.save(storage_key, ContentFile(pdf_file.getvalue(), name=f"{stem}-Score+Parts.pdf"))
                        written_keys.append(storage_key)
                        logger.info(f"Uploaded combined score+parts to: {storage_key} ({len(comb_pdf)} bytes)")
                        break
                    except Exception as e:
                        logger.error(f"Failed to process combined PDF ({key}): {str(e)}")
            
            # Individual parts
            parts_list = []
            if "parts" in data and isinstance(data["parts"], list):
                parts_list = data["parts"]
            elif "partsBin" in data and isinstance(data["partsBin"], list):
                parts_list = data["partsBin"]
            
            for i, part in enumerate(parts_list):
                try:
                    if isinstance(part, dict):
                        name = part.get("name") or part.get("partName") or f"Part{i+1}"
                        b64 = part.get("bin") or part.get("pdf") or part.get("pdfBin")
                    elif isinstance(part, list) and len(part) == 2:
                        name, b64 = part
                    else:
                        logger.warning(f"Skipping part {i}: unexpected format")
                        continue
                    
                    if not b64:
                        logger.warning(f"Skipping part {i} ({name}): no PDF data")
                        continue
                    
                    # Decode and validate
                    pdf = base64.b64decode(b64)
                    if not pdf.startswith(b'%PDF'):
                        logger.warning(f"Part '{name}' doesn't start with PDF header")
                    
                    # Sanitize filename
                    safe_name = "".join(c for c in name if c not in r'\/:*?"<>|').strip()
                    if not safe_name:
                        safe_name = f"Part{i+1}"
                    
                    storage_key = f"{output_prefix_key}{stem} - {safe_name}.pdf"
                    pdf_file = BytesIO(pdf)
                    default_storage.save(storage_key, ContentFile(pdf_file.getvalue(), name=f"{safe_name}.pdf"))
                    written_keys.append(storage_key)
                    logger.info(f"Uploaded part '{safe_name}' to: {storage_key} ({len(pdf)} bytes)")
                    
                except Exception as e:
                    logger.error(f"Failed to upload part {i} ('{name if 'name' in locals() else 'unknown'}'): {str(e)}")
                    continue
            
            return {"status": "success", "written": written_keys}
            
        except Exception as e:
            return {"status": "error", "details": f"Error uploading files: {str(e)}"}

