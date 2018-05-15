import os
import json
import uuid
import shlex
from collections import defaultdict
from functools import partial

import tornado.gen
import tornado.log
import tornado.web
import tornado.wsgi
import tornado.queues
import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.autoreload
from terminado import TermSocket, NamedTermManager


from tornado.gen import coroutine, Task, Return
from tornado.process import Subprocess
from tornado.ioloop import IOLoop


class SpecificNamedTermManager(NamedTermManager):
    def new_named_terminal(self, *args, **kwargs):
        name = uuid.uuid4().hex
        command = kwargs.get('shell_command')
        term = self.new_terminal(shell_command=command)
        term.term_name = name
        self.terminals[name] = term
        self.start_reading(term)
        return name, term

    def get_terminal(self, term_name):
        if term_name in self.terminals:
            return self.terminals[term_name]
        raise KeyError(term_name)


class BaseHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        super(BaseHandler, self).data_received(chunk)

    def write_json(self, obj):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(obj))


class ProcessManager(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.processes = {}
        self.process_output = {}

    async def call_subprocess_async(self, cmd):
        sub_process = Subprocess(shlex.split(cmd), stdin=None, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
        self.processes[sub_process.proc.pid] = sub_process

        result = await Task(sub_process.stdout.read_until_close)
        error = await Task(sub_process.stderr.read_until_close)

        return result, error

    def call_subprocess(self, cmd):
        sub_process = Subprocess(shlex.split(cmd), stdin=None, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM)
        self.processes[sub_process.proc.pid] = sub_process
        tornado.ioloop.IOLoop.instance().add_callback(
            sub_process.stdout.fileno(),
            partial(self.on_subprocess_return, sub_process.proc.pid)
        )

    def on_subprocess_return(self, pid, *args, **kwargs):
        pass

    def start(self, path, stream=False):
        pass

    def kill(self, pid):
        self.processes[pid].proc.kill()

    def get_output(self, pid):
        pass


class ProcessHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(ProcessHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.process_manager = kwargs.get('process')


class ProcessAccessHandler(ProcessHandler):
    def get(self, *args, **kwargs):
        # get output
        pass

    def post(self, *args, **kwargs):
        # kill
        pass


class ProcessManageHandler(ProcessHandler):
    def get(self):
        pass

    def post(self, *args, **kwargs):
        pass


class TerminalManager(object):
    def __init__(self, tm, command_prefix):
        self.tm = tm
        self.command_prefix = command_prefix
        self.terminal_commands = defaultdict(dict)

    def create(self, command, terminal_type="default"):
        full_command = "{prefix} {command}".format(prefix=self.command_prefix, command=command).strip()
        commands = shlex.split(full_command)
        name, term = self.tm.new_named_terminal(shell_command=commands)
        self.terminal_commands[terminal_type][name] = full_command
        return name

    def list(self, terminal_type="default"):
        return [{'name': name, 'command': command} for name, command in self.terminal_commands[terminal_type].items()]

    def delete(self, name):
        pass

    def __del__(self):
        self.tm.shutdown()


class TerminalHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TerminalHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.terminal_manager = kwargs.get('terminal')


class TerminalAccessHandler(TerminalHandler):
    def get(self, terminal_name):
        for t in self.terminal_manager.terminal_commands.values():
            if terminal_name in t.keys():
                self.render("templates/terminal.html", terminal_name=terminal_name)
        raise tornado.web.HTTPError(404)


class TerminalManageHandler(TerminalHandler):
    def post(self, *args, **kwargs):
        data = tornado.escape.json_decode(self.request.body or "{}")
        command = data.get("command", "fish")
        name = self.terminal_manager.create(command=command)
        self.write_json({"name": name})

    def get(self):
        self.write_json(self.terminal_manager.list())


class TestEnvManager(object):
    def __init__(self, terminal):
        self.terminal = terminal
        self.test_env_cmdline = {}

    def create(self, image_file, image_config=None, network_config=None):
        if image_config:
            image_config = "," + image_config
        cmdline = "qemu-system-x86_64 -nographic -serial mon:stdio -boot c -drive file={image_file}{image_config}"
        full_command_line = cmdline.format(image_file=image_file, image_config=image_config)
        name = self.terminal.create(command=full_command_line, terminal_type="testenv")
        self.test_env_cmdline[name] = full_command_line
        return name


class TestEnvHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TestEnvHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.testenv_manager = kwargs.get('testenv')

    def get(self):
        self.write_json(self.testenv_manager.test_env_cmdline)

    def post(self):
        data = tornado.escape.json_decode(self.request.body or "{}")
        image_file = data.get("image_file")
        image_config = data.get("image_config", "if=virtio")
        name = self.testenv_manager.create(image_file=image_file, image_config=image_config)
        self.write_json({"name": name})


def create_app():
    term_manager = SpecificNamedTermManager(shell_command=["nologin"])
    terminal = TerminalManager(term_manager, "")
    testenv = TestEnvManager(terminal)
    handlers = [
        (r"/terminal/", TerminalManageHandler, {'terminal': terminal}),
        (r"/terminal/(\w+)", TerminalAccessHandler, {'terminal': terminal}),
        (r"/terminal/ws/(\w+)", TermSocket, {'term_manager': term_manager}),
        (r"/testenv/", TestEnvHandler, {'testenv': testenv}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "static")}),
    ]

    return tornado.web.Application(handlers)


def start_server(host, port):
    create_app().listen(port, host)

    loop = tornado.ioloop.IOLoop.instance()
    try:
        loop.start()
    except KeyboardInterrupt:
        print("Shutting down on SIGINT")
    finally:
        loop.close()


configurations = {}

if __name__ == '__main__':
    start_server("0.0.0.0", 8765)
