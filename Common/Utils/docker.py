# coding=utf8
import docker


class DockerAccess(object):
    def __init__(self):
        self.client = docker.from_env()

    @property
    def containers(self):
        return self.client.containers.list(all=True)

    def get_container_by_id(self, container_id):
        return self.client.containers.get(container_id)


class DockerContainerAccess(object):
    def __init__(self, container_id, workdir='~', command_prefix='su -c'):
        self.client = docker.from_env()
        self.container_id = container_id
        self.workdir = workdir
        self.command_prefix = command_prefix

    @property
    def container(self):
        return self.client.containers.get(self.container_id)

    def exec_command(self, cmd, stream=False):
        wdp = 'cd %s' % self.workdir
        command = '%s bash -c "%s; %s"' % (self.command_prefix, wdp, cmd)
        print(command)
        return self.container.exec_run(command, stream=stream)


