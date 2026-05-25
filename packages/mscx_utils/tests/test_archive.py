from mscx_utils import (
    is_excerpt_mscx_arc,
    mscx_path_from_extract_dir,
    partition_mscx_arcs,
    pick_main_mscx_arc_from_namelist,
)


def test_pick_main_mscx_prefers_non_excerpt():
    namelist = [
        "Excerpts/Piano/Piano.mscx",
        "Test-Score.mscx",
        "META-INF/container.xml",
    ]
    assert pick_main_mscx_arc_from_namelist(namelist) == "Test-Score.mscx"


def test_partition_mscx_arcs():
    arcs = {"score.mscx", "Excerpts/Flute/Flute.mscx"}
    main, excerpts = partition_mscx_arcs(arcs)
    assert main == "score.mscx"
    assert excerpts == {"Excerpts/Flute/Flute.mscx"}


def test_mscx_path_from_extract_dir():
    path = mscx_path_from_extract_dir("/tmp/out", "Folder/Score.mscx")
    assert path.replace("\\", "/").endswith("Folder/Score.mscx")


def test_is_excerpt_mscx_arc():
    assert is_excerpt_mscx_arc("Excerpts/Part.mscx")
    assert not is_excerpt_mscx_arc("MyScore.mscx")
