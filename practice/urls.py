from django.urls import path

from . import views

app_name = "practice"

urlpatterns = [
    path("", views.home, name="home"),
    path("topics/", views.topic_list, name="topics"),
    path("topics/<slug:slug>/", views.topic_detail, name="topic_detail"),
    path("activity/<int:pk>/", views.activity, name="activity"),
]
