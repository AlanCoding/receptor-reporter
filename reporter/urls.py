from django.contrib import admin
from django.urls import path


# Hook up the admin site straight to root
urlpatterns = [
    path('', admin.site.urls),
]
