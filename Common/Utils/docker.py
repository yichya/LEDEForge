# coding=utf8
import docker
from multiprocessing import Process
from Common.Utils.queue_manager import queue_manager


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
        return self.container.exec_run(command, stream=stream)

    def exec_command_in_new_queue(self, cmd):
        queue_id, queue = queue_manager.new_queue()

        def child(q, container_id, workdir, command_prefix, command):
            # re-create client for generators cannot be pickled
            _, s = DockerContainerAccess(container_id, workdir, command_prefix).exec_command(command, stream=True)
            q.put({'data': command + "\n", 'finished': False})
            for line in s:
                if line:
                    l = line.decode()
                    q.put({'data': l, 'finished': False})
            q.put({'data': "Process Finished", 'finished': True})
            exit(0)

        p = Process(target=child, args=(queue, self.container_id, self.workdir, self.command_prefix, cmd))
        p.start()

        return queue_id


