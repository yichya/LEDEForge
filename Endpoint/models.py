import json
from multiprocessing import Process

import docker
from django.db import models


# Create your models here.
from Common.Utils.queue_manager import queue_manager


class EndPoint(models.Model):
    name = models.CharField(max_length=128)
    connection_string = models.CharField(max_length=255)

    @property
    def connector(self) -> docker.APIClient:
        if self.connection_string == "fd://":
            return docker.from_env().api
        return docker.APIClient(self.connection_string)

    @property
    def default_connection_string(self) -> str:
        if self.connection_string == "fd://":
            return "http://localhost"
        return self.connection_string.replace("tcp", "http").rstrip("/")

    @property
    def data(self):
        return self.connector.info()

    @property
    def containers(self):
        return self.connector.containers(all=True, filters={'label': 'org.ledeforge.image_type=worker'})

    @property
    def images(self):
        return self.connector.images(filters={'label': 'org.ledeforge.image_type=worker'})

    def docker_run_daemon(self, image_id, expose_port):
        return self.connector.create_container(image_id, ports=[8765], host_config=self.connector.create_host_config(port_bindings={
            8765: expose_port,
        }))

    def docker_build_in_queue(self, build_path):
        queue_id, queue = queue_manager.new_queue()

        def child(q, conn, path):
            if conn == "fd://":
                api = docker.from_env().api
            else:
                api = docker.APIClient(conn)
            q.put({'data': "Building in {}\n".format(conn), 'finished': False})
            s = api.build(path)
            for line in s:
                if line:
                    lx = line.decode().split("\r\n")[0:-1]
                    for l in lx:
                        json_l = json.loads(l)
                        data = json_l.get("stream", "")
                        q.put({'data': data, 'finished': False})
            q.put({'data': "Build Completed", 'finished': True})
            exit(0)

        p = Process(target=child, args=(queue, self.connection_string, build_path))
        p.start()

        return queue_id
