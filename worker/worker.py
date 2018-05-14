import os
import json
import uuid
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
    def write_json(self, obj):
        self.write(json.dumps(obj))


class Process(object):
    def __init__(self, prefix, path, stream=False):
        self.prefix = prefix
        self.path = path
        self.stream = stream

    def start(self):
        pass

    def kill(self):
        pass

    def get_output(self):
        pass


class Terminal(object):
    def __init__(self, terminal_manager, command_prefix):
        self.terminal_manager = terminal_manager
        self.command_prefix = command_prefix
        self.terminal_commands = {}

    def create(self, command):
        full_command = "{prefix} {command}".format(prefix=self.command_prefix, command=command)
        commands = [x for x in full_command.split(" ", 1) if x]
        name, term = self.terminal_manager.new_named_terminal(shell_command=commands)
        self.terminal_commands[name] = full_command
        return name

    def list(self):
        return self.terminal_commands.items()

    def delete(self):
        pass

    def __del__(self):
        self.terminal_manager.shutdown()


class TerminalHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TerminalHandler, self).__init__(*args, **kwargs)

    def initialize(self, terminal):
        self.terminal = terminal


class TerminalAccessHandler(TerminalHandler):
    def get(self, terminal_name):
        self.render("templates/terminal.html", terminal_name=terminal_name)


class TerminalManageHandler(TerminalHandler):
    def initialize(self, terminal):
        super(TerminalManageHandler, self).initialize(terminal)

    def post(self, *args, **kwargs):
        data = tornado.escape.json_decode(self.request.body or "{}")
        command = data.get("command", "fish")
        name = self.terminal.create(command=command)
        self.write_json({"name": name})

    def get(self):
        self.write_json(self.terminal.list())


def create_app():
    terminal_manager = SpecificNamedTermManager(shell_command=["nologin"])
    terminal = Terminal(terminal_manager, "")
    handlers = [
        (r"/terminal/", TerminalManageHandler, {'terminal': terminal}),
        (r"/terminal/(\w+)", TerminalAccessHandler, {'terminal': terminal}),
        (r"/terminal/ws/(\w+)", TermSocket, {'term_manager': terminal.terminal_manager}),
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
