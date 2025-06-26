from django.shortcuts import render, redirect

from .models import Score
from .forms import ScoreForm

from django.http import HttpResponse


def index(request):
    if request.method == 'POST':
        form = ScoreForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('scores')
    else:
        form = ScoreForm()
    return render(request, 'index.html', {'form': form})


def scores(request):
    all_scores = Score.objects.order_by('-uploaded_at')
    return render(request, 'scores.html', {'scores': all_scores})