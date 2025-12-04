from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('genealogy/', include('genealogy.urls', namespace="genealogy")),
    path('users/', include('users.urls', namespace="users")),
    path('records/', include('records.urls', namespace="records")),
    path('api/', include('genealogy.api.urls', namespace="api")),
    path('api/dj-rest-auth/', include('dj_rest_auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )