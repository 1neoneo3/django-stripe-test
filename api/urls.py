from django.urls import path
from api import views

urlpatterns = [
    path('search/', views.SearchView.as_view(), name='search'),
]
