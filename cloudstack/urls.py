from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.Cloudstack.as_view()),    # 인스턴스 페이지 관련
    path('<int:instance_pk>/', views.CloudstackInstanceInfo.as_view()),
    path('<int:instance_pk>/logs/', views.CloudstackInstanceLogShower.as_view()),
    path('dashboard/', views.DashBoard.as_view()),  # dashboard 관련
    path('instance-start/', views.InstanceStart.as_view()), # 인스턴스 start btn에 붙일 url
    path('instance-stop/', views.InstanceStop.as_view()),   # 인스턴스 stop btn에 붙일 url
    path('instance-console/', views.InstanceConsole.as_view()),
]