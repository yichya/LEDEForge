from django.shortcuts import render, render_to_response, redirect
from django.urls import reverse
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
        keyword = request.GET.get('keyword', "")
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        return render_to_response('repository/packages.html', {
            'keyword': keyword,
            'repository': repository.serialize_detail(),
            'packages': repository.repository.lede_packages(keyword)
        })


class RepositoryAmendCustomizationsView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.amend_customizations()
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class RepositoryUpdateCodeView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.update_code()
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class RepositoryUpdateFeedsView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.update_feeds()
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class RepositoryInstallFeedsView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.install_feeds()
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class RepositoryMakeWizardView(View):
    def get(self, request, repository_id):
        return render_to_response("repository/make.html", {
            'repository_id': repository_id,
        })


class RepositoryMakeView(View):
    def get(self, request, repository_id):
        args = request.GET.getlist("args")
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.make(args)
        return redirect(reverse("queue_output", args=(queue_id,)))


class RepositoryCleanView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.clean()
        return redirect(reverse("queue_output", args=(queue_id,)))


class RepositoryDirCleanView(View):
    def get(self, request, repository_id):
        repository = RepositoryRegistration.query_first_by_id(id=repository_id)
        queue_id = repository.repository.dirclean()
        return redirect(reverse("queue_output", args=(queue_id,)))
