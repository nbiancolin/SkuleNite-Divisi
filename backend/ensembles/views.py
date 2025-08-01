from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import CreateEnsembleSerializer, CreateArrangementSerializer, EnsembleSerializer, ArrangementSerializer, ArrangementVersionSerializer
from logging import getLogger

logger = getLogger("EnsembleViews")


class EnsembleViewSet(viewsets.ModelViewSet):
    queryset = Ensemble.objects.all()
    serializer_class = EnsembleSerializer
    lookup_field = "slug"  # use slug instead of pk

    @action(detail=True, methods=['get'], url_path='arrangements')
    def arrangements(self, request, slug=None):
        """Return all arrangements for a specific ensemble."""
        ensemble = self.get_object()
        arrangements = ensemble.arrangements.all()
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)


class ArrangementViewSet(viewsets.ModelViewSet):
    queryset = Arrangement.objects.all()
    serializer_class = ArrangementSerializer
    lookup_field = "slug"

class ArrangementVersionViewSet(viewsets.ModelViewSet):
    queryset = ArrangementVersion.objects.all()
    serializer_class = ArrangementSerializer

"""
How arrangement versions should work
- Arranger opens their ensemble home page
- Selects the arrangememnt that they are working on
- On the arrangement page, they select "Upload New Version"
- Select version type, and style settings, then upload new arrangement version
BE:
- Create New Version, FE sends version type (major, minor, hotfix) and arrangement pk
- BE creates version, sends MSCZ file to be processed, then updates arranementVersion with file paths
    - if new version, gets prev version and umps it (how?)
"""



"""
Ideal URL Patterns
BASE = http://divisi.nbiancolin.ca/divisi

FE URL Patterns
View (all arrangements in) Ensemble: BASE/ensembles/<name>
(Alt: BASe/home) (If we restrict users to only be in one ensemble at a time)
View Arrangement: BAr: BASE/arrangements/<pk> (haven't decided which is best)
(Alt: BASE/arr/<title> orsion:  BASE/arrangements/<pk>
Upload New Arrangement <Arr-url>/upload



BE Url Patterns don't really matter, they're just APIs, so IG model viewsets for all of them
"""

#OLD: TODO remove

class CreateEnsembleView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateEnsembleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        ens = Ensemble.objects.create(name=serializer.validated_data["name"])

        return Response(
            {"message": "Ensemble Created Successfully", "sanitized_name": ens.sanitized_name},
            status=status.HTTP_200_OK,
        )

class CreateArrangementView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateArrangementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        ens = Ensemble.objects.get(name=serializer.validated_data["ensemble_name"])

        arr = Arrangement.objects.create(
            ensemble_id=ens.pk,
            title=serializer.validated_data["title"],
            subtitle=serializer.validated_data.get("subtitle"),
            act_number=serializer.validated_data.get("act_number"),
            piece_number=serializer.validated_data["piece_number"],
        )

        return Response(
            {"message": "Ensemble Created Successfully", "sanitized_title": arr.sanitized_title},
            status=status.HTTP_200_OK,
        )

        arrangements = ens.arrangements.all() #TODO: Check if this is a legit error
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)