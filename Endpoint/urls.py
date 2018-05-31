from django.conf.urls import url
from Endpoint.views import EndpointListView

endpoint_urlpatterns = [
    url(r"^list/$", EndpointListView.as_view(), name="endpoint_list")
]