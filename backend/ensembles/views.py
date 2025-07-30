from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from .models import Arrangement, Ensemble
from .serializers import CreateEnsembleSerializer, CreateArrangementSerializer, EnsembleSerializer, ArrangementSerializer


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

class ArrangementListView(APIView):
    def get(self, request, ensemble_name):
        try:
            ens = Ensemble.objects.get(name=ensemble_name)
        except Ensemble.DoesNotExist:
            return Response({"detail": "Ensemble not found."}, status=status.HTTP_404_NOT_FOUND)

        arrangements = ens.arrangements.all() #TODO: Check if this is a legit error
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)