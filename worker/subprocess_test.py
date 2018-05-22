import shlex
import tornado.ioloop
import tornado.process


STREAM = tornado.process.Subprocess.STREAM


def call_subprocess(cmd, cb_stdout, cb_stderr, cb_exit):
    sub_process = tornado.process.Subprocess(cmd, stdout=STREAM, stderr=STREAM)
    sub_process.stdout.read_until_close(streaming_callback=cb_stdout)
    sub_process.stderr.read_until_close(streaming_callback=cb_stderr)
    sub_process.set_exit_callback(cb_exit)
    return sub_process.proc.pid


def main(cmd):
    def data_callback_stdout(data):
        print(data)

    def data_callback_stderr(data):
        print(data)

    def exit_callback(code):
        print(code)
        tornado.ioloop.IOLoop.instance().stop()

    def func():
        pid = call_subprocess(shlex.split(cmd), data_callback_stdout, data_callback_stderr, exit_callback)
        print(pid)
    return func


if __name__ == "__main__":
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_callback(main("dmesg"))
    ioloop.start()
