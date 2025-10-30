import factory
from factory.django import DjangoModelFactory
from ensembles.models import Ensemble, Arrangement, ArrangementVersion, Diff


class EnsembleFactory(DjangoModelFactory):
    class Meta:
        model = Ensemble

    name = factory.Sequence(lambda n: f"Ensemble {n}")


class ArrangementFactory(DjangoModelFactory):
    class Meta:
        model = Arrangement

    ensemble = factory.SubFactory(EnsembleFactory)
    title = factory.Sequence(lambda n: f"Arrangement {n}")
    subtitle = "Test Subtitle"
    composer = "Composer Name"
    mvt_no = "I"
    style = "Jazz"


class ArrangementVersionFactory(DjangoModelFactory):
    class Meta:
        model = ArrangementVersion


    file_name = "ArrangementFile.mscz"
    arrangement = factory.SubFactory(ArrangementFactory)
    version_label = factory.Sequence(lambda n: f"v1.{n}.0")
    is_latest = False
    num_measures_per_line_score = 8
    num_measures_per_line_part = 6
    num_lines_per_page = 8


class DiffFactory(DjangoModelFactory):
    class Meta:
        model = Diff

    from_version = factory.SubFactory(ArrangementVersionFactory)
    to_version = factory.SubFactory(ArrangementVersionFactory)
    file_name = "comp-diff.pdf"
    status = "pending"
