import tornado.web, tornado.ioloop
from tornado import gen
import motor
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import string
import random
import time

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

clients = dict()

current_milli_time = lambda: int(round(time.time() * 1000))


def random_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/connect", ChatSocketHandler),
        ],
        settings = dict(
            cookie_secret=random_generator(),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

"""
class NewMessageHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('''
        <form method="post">
            <input type="text" name="msg">
            <input type="submit">
        </form>''')

    # Method exits before the HTTP request completes, thus "asynchronous"
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        msg = self.get_argument('msg')
        db = self.settings['db']['glympse_web_socket-clacina']

        # insert() returns a Future. Yield the Future to get the result.
        result = yield db.glKeyStore.insert({'msg': msg})

        # Success
        self.redirect('/')


class MessagesHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        self.write('<a href="/compose">Compose a message</a><br>')
        self.write('<ul>')
        db = self.settings['db']['glympse_web_socket-clacina']
        cursor = db.glKeyStore.find().sort([('_id', -1)])
        while (yield cursor.fetch_next):
            message = cursor.next_object()
            self.write('<li>%s</li>' % message['msg'])

        # Iteration complete
        self.write('</ul>')
        self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def connect(self):
        self.write("hello")
        self.finish()
"""

class ClientStat:
    def __init__(self, obj):
        self.start_time = current_milli_time()
        self.msg_count = 0
        self.object = obj


class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        print("Web socket opened")
        self.id = random_generator()
        self.stream.set_nodelay(True)

        clients[self.id] = ClientStat(self)
        self.write_message("hello")

    def on_close(self):
        print("Web socket closed")
        del clients[self.id]

    def on_message(self, message):
        clients[self.id].msg_count += 1

        logging.info("got message %r", message)
        msg = message.split()
        if len(msg) < 2:
            self.write_error("Invalid Command")
        else:
            if msg[0].lower() == 'get':
                del msg[0]
                key = " ".join(msg)
                self.write_message("Looking for " + key)

                self.find_key(key)
                # if data is not None:
                #     record = yield data
                #     self.write_message(record['value'])
                # else:
                #     self.write_message('null')
                print("done")
            elif msg[0].lower() == 'set':
                print("Set command")
            else:
                output = "Unknown Command [" + msg[0] + "]"
                self.write_message(output)

    def check_origin(self, origin):
        return True

    def select_subprotocol(self, subprotocols):
        for l in subprotocols:
            print(l)

    @gen.coroutine
    def find_key(self, key):
        db = self.settings['db']['glympse_web_socket-clacina']
        doc = yield db.glKeyStore.find_one({"key": key})
        if doc is not None:
            self.write_message(doc['value'])
        else:
            self.write_message("null")


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello")
        self.finish()
        # self.render("index.html", messages=ChatSocketHandler.cache)


class ConnectionsHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("[")
        first_entry = True
        for c in clients.values():
            if not first_entry:
                self.write(",")
            self.write('{"uptime_ms":')
            etime = current_milli_time()
            etime = etime - c.start_time
            self.write(str(etime))
            self.write(', "messages":')
            self.write(str(c.msg_count))
            self.write('}')
            first_entry = False
        self.write("]")
        self.finish()

db = motor.motor_tornado.MotorClient(
    "mongodb://clacina:ptYpRKAqNvK7@ds023000.mlab.com:23000/glympse_web_socket-clacina")

application = tornado.web.Application(
    [
        (r"/", MainHandler),
        (r"/connect", ChatSocketHandler),
        (r"/connections", ConnectionsHandler),
    ],
    db=db
)

tornado.options.parse_command_line()
print('Listening on port ' + str(options.port))
application.listen(options.port)
tornado.ioloop.IOLoop.instance().start()
