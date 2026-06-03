from collections import defaultdict
from itertools import combinations

from django.db.models import Value, IntegerField
from django.db.models.functions import Coalesce

from ensembles.models import PartAsset, PartName


def build_part_name_matrix(ensemble):
    """
    Build arrangement × part-name matrix data for the ensemble editor UI.
    Uses latest arrangement versions only; excludes score PDFs.
    """
    from django.db.models.expressions import RawSQL

    arrangements = list(
        ensemble.arrangements.annotate(
            first_num=RawSQL(
                "CAST((regexp_matches(mvt_no, '^([0-9]+)'))[1] AS INTEGER)",
                [],
            ),
            second_num=RawSQL(
                "CAST((regexp_matches(mvt_no, '^[0-9]+(?:-|m)([0-9]+)'))[1] AS INTEGER)",
                [],
            ),
        ).order_by("first_num", "second_num", "mvt_no", "id")
    )

    columns = list(
        PartName.objects.filter(ensemble=ensemble).order_by(
            Coalesce("order", Value(999999, output_field=IntegerField())), "id"
        )
    )

    part_assets = (
        PartAsset.objects.filter(
            arrangement_version__arrangement__ensemble=ensemble,
            arrangement_version__is_latest=True,
            is_score=False,
        )
        .select_related("arrangement_version__arrangement")
    )

    cells = []
    part_names_by_version = defaultdict(set)

    for asset in part_assets:
        arrangement_id = asset.arrangement_version.arrangement_id
        cells.append(
            {
                "arrangement_id": arrangement_id,
                "part_name_id": asset.part_name_id,
                "part_asset_id": asset.id,
            }
        )
        part_names_by_version[asset.arrangement_version_id].add(asset.part_name_id)

    merge_conflicts = []
    seen_pairs = set()
    for part_name_ids in part_names_by_version.values():
        unique_ids = sorted(part_name_ids)
        if len(unique_ids) < 2:
            continue
        for id_a, id_b in combinations(unique_ids, 2):
            pair = (id_a, id_b)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                merge_conflicts.append([id_a, id_b])

    return {
        "arrangements": [
            {"id": a.id, "title": a.title, "mvt_no": a.mvt_no} for a in arrangements
        ],
        "columns": [
            {"id": c.id, "display_name": c.display_name, "order": c.order}
            for c in columns
        ],
        "cells": cells,
        "merge_conflicts": merge_conflicts,
    }
