#
# CONFIDENTIAL
# __________________
#
# [2016] Chris J Lacina
# clacina@mindspring.com
# All Rights Reserved.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

import logging
import motor
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import random
import string
import time

from tornado import gen

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("mongodb-host", default="mongodb://clacina:ptYpRKAqNvK7@ds023000.mlab.com:23000/glympse_web_socket-clacina", help="Mongo DB Host")
define("mongodb-database", default="glympse_web_socket-clacina", help="Mongo DB Database")
define("mongodb-collection", default="glKeyStore", help="Mongo DB Collection")

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
        logging.info("/connect")
        self.id = random_generator()
        self.stream.set_nodelay(True)

        clients[self.id] = ClientStat(self)
        self.write_message("hello")

    def on_close(self):
        logging.info(self.id + " disconnected")
        del clients[self.id]

    def on_message(self, message):
        logging.info("got message %r", message)
        msg = message.split()
        if len(msg) < 2:
            self.write_message("Invalid Command")
        else:
            if msg[0].lower() == 'get':
                del msg[0]
                key = " ".join(msg)
                self.find_key(key)
            elif msg[0].lower() == 'set':
                del msg[0]      # delete 'set'
                key = msg[0]    # pull 'key'
                del msg[0]      # delete 'key'
                value = " ".join(msg)     # join 'value'
                self.insert_key_value_pair(key, value)
            else:
                output = "Unknown Command [" + msg[0] + "]"
                self.write_message(output)

    def check_origin(self, origin):
        return True     # allow all origins

    @gen.coroutine
    def find_key(self, key):
        db = self.settings['db'][options.mongodb_database]
        doc = yield db[options.mongodb_collection].find_one({"key": key})
        if doc is not None:
            self.write_message(doc['value'])
            clients[self.id].msg_count += 1
        else:
            self.write_message("null")

    @gen.coroutine
    def insert_key_value_pair(self, key, value):
        db = self.settings['db'][options.mongodb_database]
        # need to see if it exists first
        doc = yield db[options.mongodb_collection].find_one({"key": key})
        if doc is not None:
            doc['value'] = value
            result = yield db[options.mongodb_collection].save(doc)
        else:
            result = yield db[options.mongodb_collection].insert({'key': key, 'value': value})

        if result is None:
            self.write_message("error")
        else:
            clients[self.id].msg_count += 1
            self.write_message("ok")


# Web Page Request Handler for /connections
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


# start our main loop
tornado.options.parse_command_line()

# configure the database connection
db_connection = motor.motor_tornado.MotorClient(host=options.mongodb_host)

# configure our application handlers
application = tornado.web.Application(
    [
        (r"/connect", ChatSocketHandler),
        (r"/connections", ConnectionsHandler),
    ],
    db=db_connection
)

print('Listening on port ' + str(options.port))
application.listen(options.port)
tornado.ioloop.IOLoop.instance().start()
