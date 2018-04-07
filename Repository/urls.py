from django.conf.urls import url

from Repository.views import RepositoryListView, RepositoryDetailView, RepositoryPackagesView, RepositoryUpdateCodeView, \
    RepositoryUpdateFeedsView, RepositoryCleanView, RepositoryDirCleanView, RepositoryMakeView, \
    RepositoryMakeWizardView, RepositoryInstallFeedsView, RepositoryAmendCustomizationsView

repository_urlpatterns = [
    url(r'^list/$', RepositoryListView.as_view(), name='repository_list'),
    url(r'^(?P<repository_id>[0-9]+)/$', RepositoryDetailView.as_view(), name='repository_detail'),
    url(r'^(?P<repository_id>[0-9]+)/packages/$', RepositoryPackagesView.as_view(), name='repository_packages'),
    url(r'^(?P<repository_id>[0-9]+)/amend_customizations/$', RepositoryAmendCustomizationsView.as_view(), name='repository_amend_customizations'),
    url(r'^(?P<repository_id>[0-9]+)/update_code/$', RepositoryUpdateCodeView.as_view(), name='repository_update_code'),
    url(r'^(?P<repository_id>[0-9]+)/update_feeds/$', RepositoryUpdateFeedsView.as_view(), name='repository_update_feeds'),
    url(r'^(?P<repository_id>[0-9]+)/install_feeds/$', RepositoryInstallFeedsView.as_view(), name='repository_install_feeds'),
    url(r'^(?P<repository_id>[0-9]+)/make_wizard/$', RepositoryMakeWizardView.as_view(), name='repository_make_wizard'),
    url(r'^(?P<repository_id>[0-9]+)/make/$', RepositoryMakeView.as_view(), name='repository_make'),
    url(r'^(?P<repository_id>[0-9]+)/clean/$', RepositoryCleanView.as_view(), name='repository_clean'),
    url(r'^(?P<repository_id>[0-9]+)/dirclean/$', RepositoryDirCleanView.as_view(), name='repository_dirclean'),
]
