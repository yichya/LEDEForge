import os
import tornado.log
import tornado.web
import tornado.wsgi
import tornado.ioloop
import tornado.options
import tornado.autoreload
import django.core.handlers.wsgi
from terminado import TermSocket
from LedeForge.views import container_terminal_manager, source_terminal_manager, virtual_machine_terminal_manager


def create_app():
    os.environ["DJANGO_SETTINGS_MODULE"] = 'LedeForge.settings'
    django.setup()
    wsgi_app = tornado.wsgi.WSGIContainer(django.core.handlers.wsgi.WSGIHandler())

    handlers = [
        (r"/terminal/container/(\w+)", TermSocket, {'term_manager': container_terminal_manager}),
        (r"/terminal/source/(\w+)", TermSocket, {'term_manager': source_terminal_manager}),
        (r"/terminal/virtual_machine/(\w+)", TermSocket, {'term_manager': virtual_machine_terminal_manager}),
        ('.*', tornado.web.FallbackHandler, {'fallback': wsgi_app}),
    ]

    return tornado.web.Application(handlers, static_path=os.path.join(os.path.dirname(__file__), "static"))


def start_server(host, port):
    create_app().listen(port, host)

    loop = tornado.ioloop.IOLoop.instance()
    try:
        tornado.autoreload.start(loop)
        loop.start()
    except KeyboardInterrupt:
        print("Shutting down on SIGINT")
    finally:
        container_terminal_manager.shutdown()
        source_terminal_manager.shutdown()
        virtual_machine_terminal_manager.shutdown()
        loop.close()


if __name__ == '__main__':
    start_server("0.0.0.0", 8765)
