from django.conf.urls import url

from Repository.views import RepositoryListView, RepositoryDetailView, RepositoryPackagesView

repository_urlpatterns = [
    url(r'^list/$', RepositoryListView.as_view(), name='repository_list'),
    url(r'^(?P<repository_id>[0-9]+)/$', RepositoryDetailView.as_view(), name='repository_detail'),
    url(r'^(?P<repository_id>[0-9]+)/packages/$', RepositoryPackagesView.as_view(), name='repository_packages')
]
