from .views import AccountView, SignView, LogView
from django.urls import path

urlpatterns = [
    path('', AccountView.as_view()),
    path('login/', SignView.as_view()),
    path('<str:user_id>/logs/', LogView.as_view()),
]