from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.Openstack.as_view()),
    path('dashboard/', views.DashBoard.as_view()),
    path('instance-start/', views.InstanceStartButton.as_view()),
    path('instance-stop/', views.InstanceStopButton.as_view()),
]