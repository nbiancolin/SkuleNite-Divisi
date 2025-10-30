from ensembles.models import Arrangement

BATCH_SIZE = 10

def backfill_populate_mvt_no():
    print("Backfill Starting...")

    qs = Arrangement.objects.filter(mvt_no__isnull=True)

    while batch := qs[:BATCH_SIZE]:
        for arr in batch:
            if arr.act_number:
                arr.mvt_no = f"{arr.act_number}-{arr.piece_number}"
            else:
                arr.mvt_no = f"{arr.piece_number}"

            #want to bulk write:
            # arr.save(update_fields=["mvt_no"])