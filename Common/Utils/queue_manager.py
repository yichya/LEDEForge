import uuid
from multiprocessing import Queue


class QueueManager(object):
    def __init__(self):
        self.queues = {}

    def new_queue(self):
        queue = Queue()
        queue_id = uuid.uuid4().hex
        self.queues[queue_id] = queue
        print("new queue started", queue_id)
        return queue_id, queue

    def get_queue(self, queue_id):
        return self.queues.get(queue_id, None)

    def get_all_contents_from_queue(self, queue_id):
        queue = self.get_queue(queue_id)
        if queue is None:
            return []
        contents = []
        while not queue.empty():
            contents.append(queue.get())
        return contents


queue_manager = QueueManager()
