import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_mscx(mscz_path: Path) -> ET.ElementTree:
    """Extract and parse the MSCX file from a MSCZ archive or MSCX file.
    
    MSCZ files are ZIP archives containing an MSCX XML file along with
    other resources (images, audio, etc.). This function extracts and
    parses the main MSCX file containing the musical score data.
    
    Args:
        mscz_path: Path to the MSCZ file (or MSCX file - both are supported)
        
    Returns:
        ElementTree parsed from the MSCX file, ready for parsing with
        parse_score() or other XML operations
        
    Raises:
        ValueError: If no .mscx file is found in the archive
        
    Example:
        >>> from pathlib import Path
        >>> from scoreforge.parser import parse_score
        >>> tree = extract_mscx(Path("score.mscz"))
        >>> score = parse_score(tree)
    """
    if mscz_path.suffix.lower() == ".mscx":
        return ET.parse(mscz_path)
    with zipfile.ZipFile(mscz_path, "r") as z:
        for name in z.namelist():
            if name.endswith(".mscx"):
                with z.open(name) as f:
                    return ET.parse(f)  # noqa
    raise ValueError("No .mscx found")


def write_mscz(tree: ET.ElementTree, out_path: Path) -> None:
    """Write an ElementTree to a MSCZ file.
    
    Creates a minimal MSCZ archive containing only the MSCX XML file.
    This is suitable for basic scores but does not preserve metadata
    files, images, or other resources from the original file.
    
    Args:
        tree: ElementTree representing the MSCX content to write
        out_path: Path where the MSCZ file should be written
        
    Note:
        This creates a minimal MSCZ file. To preserve all files from
        an original MSCZ, use write_mscz_from_template() instead.
        
    Example:
        >>> from scoreforge.converter import score_to_mscx
        >>> from scoreforge.io import write_mscz
        >>> from pathlib import Path
        >>> tree = score_to_mscx(score)
        >>> write_mscz(tree, Path("output.mscz"))
    """
    temp_mscx = out_path.with_suffix(".mscx")

    tree.write(
        temp_mscx,
        encoding="utf-8",
        xml_declaration=True,
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(temp_mscx, arcname="score.mscx")

    temp_mscx.unlink()


def generate_template_mscx(mscz_path: Path) -> ET.ElementTree:
    """Generate a template MSCX by removing all Measure elements from the input MSCZ.
    
    The template contains all metadata, instrument mappings, and structure,
    but with all musical content (measures) removed.
    
    Args:
        mscz_path: Path to the input MSCZ file
        
    Returns:
        ElementTree with all Measure elements removed
    """
    tree = extract_mscx(mscz_path)
    root = tree.getroot()
    score_el = root.find("Score")
    
    if score_el is not None:
        # Remove all Measure elements from all Staff and Part elements
        for staff_el in score_el.findall(".//Staff"):
            for measure_el in list(staff_el.findall("Measure")):
                staff_el.remove(measure_el)
        
        for part_el in score_el.findall(".//Part"):
            for measure_el in list(part_el.findall("Measure")):
                part_el.remove(measure_el)
    
    return ET.ElementTree(root)


def save_template_mscz(tree: ET.ElementTree, out_path: Path, source_mscz_path: Path) -> None:
    """Save a template MSCZ file, preserving all files except Thumbnails folder.
    
    Args:
        tree: ElementTree representing the template MSCX
        out_path: Path where the template MSCZ file should be written
        source_mscz_path: Path to the original MSCZ file to copy other files from
    """
    temp_mscx = out_path.with_suffix(".mscx")
    
    # Write the template MSCX to a temporary file
    tree.write(
        temp_mscx,
        encoding="utf-8",
        xml_declaration=True,
    )
    
    # Find the original MSCX filename in the source archive
    mscx_filename = None
    with zipfile.ZipFile(source_mscz_path, "r") as source_z:
        for name in source_z.namelist():
            if name.endswith(".mscx"):
                mscx_filename = name
                break
    
    if mscx_filename is None:
        mscx_filename = "score.mscx"
    
    # Create new MSCZ with template MSCX and copy other files (except Thumbnails)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as out_z:
        # Add the template MSCX file
        out_z.write(temp_mscx, arcname=mscx_filename)
        
        # Copy all other files from source, excluding Thumbnails folder
        with zipfile.ZipFile(source_mscz_path, "r") as source_z:
            for name in source_z.namelist():
                # Skip the original MSCX file (we're using our template)
                if name.endswith(".mscx"):
                    continue
                # Skip Thumbnails folder and its contents
                if name.startswith("Thumbnails/") or name == "Thumbnails":
                    continue
                # Copy all other files
                out_z.writestr(name, source_z.read(name))
    
    temp_mscx.unlink()


def write_mscz_from_template(
    tree: ET.ElementTree,
    out_path: Path,
    template_mscz_path: Path
) -> None:
    """Write an ElementTree to a MSCZ file, preserving files from the template MSCZ.
    
    This function creates a new MSCZ file with the provided MSCX tree,
    while preserving all other files (except MSCX) from the template MSCZ.
    
    Args:
        tree: ElementTree to write as the MSCX file
        out_path: Path where the MSCZ file should be written
        template_mscz_path: Path to the template MSCZ file to copy other files from
    """
    temp_mscx = out_path.with_suffix(".mscx")
    
    # Write the MSCX to a temporary file
    tree.write(
        temp_mscx,
        encoding="utf-8",
        xml_declaration=True,
    )
    
    # Find the original MSCX filename in the template archive
    mscx_filename = None
    with zipfile.ZipFile(template_mscz_path, "r") as template_z:
        for name in template_z.namelist():
            if name.endswith(".mscx"):
                mscx_filename = name
                break
    
    if mscx_filename is None:
        mscx_filename = "score.mscx"
    
    # Create new MSCZ with the new MSCX and copy other files from template
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as out_z:
        # Add the new MSCX file
        out_z.write(temp_mscx, arcname=mscx_filename)
        
        # Copy all other files from template (excluding the old MSCX)
        with zipfile.ZipFile(template_mscz_path, "r") as template_z:
            for name in template_z.namelist():
                # Skip the old MSCX file (we're using our new one)
                if name.endswith(".mscx"):
                    continue
                # Copy all other files
                out_z.writestr(name, template_z.read(name))
    
    temp_mscx.unlink()

