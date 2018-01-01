import os.path
import tornado.web
import tornado.ioloop
from terminado import TermSocket, UniqueTermManager


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class TerminalPageHandler(tornado.web.RequestHandler):
    def get(self):
        return self.render("termpage.html", static=self.static_url, ws_url_path="/websocket")


def main():
    term_manager = UniqueTermManager(shell_command=['/bin/bash', '--rcfile', '~/.bash_profile'])
    handlers = [
        (r"/websocket", TermSocket, {'term_manager': term_manager}),
        (r"/", TerminalPageHandler),
    ]
    app = tornado.web.Application(handlers, static_path=STATIC_DIR, template_path=TEMPLATE_DIR)
    app.listen(8765, 'localhost')

    loop = tornado.ioloop.IOLoop.instance()
    try:
        loop.start()
    except KeyboardInterrupt:
        print("Shutting down on SIGINT")
    finally:
        term_manager.shutdown()
        loop.close()


if __name__ == '__main__':
    main()
