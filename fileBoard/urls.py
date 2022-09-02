from . import views
from django.urls import path

urlpatterns = [
    path('', views.InstanceImg.as_view()),
]