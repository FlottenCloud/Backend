from .views import AccountView, SignView
from django.urls import path

urlpatterns = [
    path('register/', AccountView.as_view()),
    path('login/', SignView.as_view()),
]