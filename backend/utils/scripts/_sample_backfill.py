from ensembles.models import ArrangementVersion


#Tip 1: Declare a batch size, helps to not lock up the database when doing lots of writes
# 100 is a safe number
BATCH_SIZE = 100

#Tip 2, sometimes, we make mistakes in our backfills and they run far too long.
# Using a max loops, we ensure that only a set number of records are processed in one iteration.
#(We can always run the backfill twice!)
MAX_LOOPS = 2

def sample_backfill():
    print("Running backfill <<your name>>")



    #Part 1: (lazily) get all objects you're working with
    # EG, in this example we want to set the "someflag" value for all arrangement versions on something
    qs = ArrangementVersion.objects.filter(someflag__isnull=True)
    total_objs_processed, num_loops = 0, 0
    #Part 2: Loop by batch size
    while batch := qs[:BATCH_SIZE]:

        #Part 2a, update the records
        for version in batch:
            version.some_flag = "DEFAULT VALUE"

        #part 3: Save in BULK to reduce queries to DB
        ArrangementVersion.objects.bulk_update(batch, "some_flag")