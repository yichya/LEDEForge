import os
import json
import uuid
import shlex
import tornado.log
import tornado.web
import tornado.wsgi
import tornado.queues
import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.autoreload
from terminado import TermSocket, NamedTermManager


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
        self.write(json.dumps(obj))


class ProcessManager(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.processes = {}

    def start(self, path, stream=False):
        pass

    def kill(self, pid):
        pass

    def get_output(self, pid):
        pass


class TerminalManager(object):
    def __init__(self, tm, command_prefix):
        self.tm = tm
        self.command_prefix = command_prefix
        self.terminal_commands = {}

    def create(self, command):
        full_command = "{prefix} {command}".format(prefix=self.command_prefix, command=command).strip()
        commands = shlex.split(full_command)
        name, term = self.tm.new_named_terminal(shell_command=commands)
        self.terminal_commands[name] = full_command
        return name

    def list(self):
        return [{'name': name, 'command': command} for name, command in self.terminal_commands.items()]

    def delete(self, name):
        pass

    def __del__(self):
        self.tm.shutdown()


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


class TerminalHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TerminalHandler, self).__init__(*args, **kwargs)

    def initialize(self, **kwargs):
        self.terminal_manager = kwargs.get('terminal')


class TerminalAccessHandler(TerminalHandler):
    def get(self, terminal_name):
        if terminal_name not in self.terminal_manager.terminal_commands.keys():
            raise tornado.web.HTTPError(404)
        self.render("templates/terminal.html", terminal_name=terminal_name)


class TerminalManageHandler(TerminalHandler):
    def post(self, *args, **kwargs):
        data = tornado.escape.json_decode(self.request.body or "{}")
        command = data.get("command", "fish")
        name = self.terminal_manager.create(command=command)
        self.write_json({"name": name})

    def get(self):
        self.write_json(self.terminal_manager.list())


def create_app():
    term_manager = SpecificNamedTermManager(shell_command=["nologin"])
    terminal = TerminalManager(term_manager, "")
    handlers = [
        (r"/terminal/", TerminalManageHandler, {'terminal': terminal}),
        (r"/terminal/(\w+)", TerminalAccessHandler, {'terminal': terminal}),
        (r"/terminal/ws/(\w+)", TermSocket, {'term_manager': term_manager}),
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
