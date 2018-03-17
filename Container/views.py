from django.http import JsonResponse
from django.views import View
from django.shortcuts import render_to_response

from Common.Utils.docker import DockerAccess
from terminal import container_terminal_manager


class ContainerView(View):
    def get(self, request):
        return render_to_response('container/index.html', {
            'containers': DockerAccess().containers,
            'sessions': container_terminal_manager.terminals
        })


class ContainerStatusView(View):
    def post(self, request, container_name):
        action = request.POST.get('action', None)
        if action in ['start', 'stop', 'restart']:
            container = DockerAccess().get_container_by_id(container_name)
            getattr(container, action)()

            return JsonResponse(data={
                'code': 0,
                'status': container.status
            })

        return {
            'code': 1
        }


class ContainerExecView(View):
    def post(self, request, container_name):
        shell_command = ['docker', 'exec', '-it', container_name, request.POST.get('shell_command')]
        name, terminal = container_terminal_manager.new_named_terminal(shell_command=shell_command)
        setattr(terminal, 'container_name', container_name)
        return JsonResponse({'terminal': name})
