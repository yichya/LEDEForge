from django.shortcuts import render, render_to_response
from django.views import View

from Repository.models import RepositoryRegistration


class RepositoryListView(View):
    def get(self, request):
        return render_to_response('repository/list.html', {
            'repositories': [x.serialize() for x in RepositoryRegistration.query_all()],
        })


class RepositoryDetailView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        print(repository.serialize_detail())
        return render_to_response('repository/detail.html', {
            'repository': repository.serialize_detail()
        })


class RepositoryPackagesView(View):
    def get(self, request, repository_id):
        keyword = request.GET.get('keyword', None)
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        return render_to_response('repository/packages.html', {
            'keyword': keyword,
            'repository': repository.serialize_detail(),
            'packages': repository.repository.lede_packages(keyword)
        })
