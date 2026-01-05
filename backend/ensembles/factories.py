import factory
from factory.django import DjangoModelFactory
from ensembles.models import Ensemble, Arrangement, ArrangementVersion, Diff, Part

from django.contrib.auth import get_user_model


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
    mvt_no = "1"
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

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda n: f"user{n}@gmail.com")
    password = factory.PostGenerationMethodCall('set_password', 'password123')

class EnsembleUsershipFactory(DjangoModelFactory):
    class Meta:
        model = 'ensembles.EnsembleUsership'

    user = factory.SubFactory(UserFactory)
    ensemble = factory.SubFactory(EnsembleFactory)
    # role = 'member' TODO: Add roles to userships


class PartFactory(DjangoModelFactory):
    class Meta:
        model = Part
    
    arrangement_version = factory.SubFactory(ArrangementVersionFactory)
    name = factory.Sequence(lambda n: f"Part {n}")
    file_key = factory.LazyAttribute(lambda obj: f"test/{obj.name.lower()}.pdf")
    is_score = False