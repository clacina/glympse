import tornado.web, tornado.ioloop
from tornado import gen
import motor


class NewMessageHandler(tornado.web.RequestHandler):
    def get(self):
        """Show a 'compose message' form."""
        self.write('''
        <form method="post">
            <input type="text" name="msg">
            <input type="submit">
        </form>''')

    # Method exits before the HTTP request completes, thus "asynchronous"
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Insert a message."""
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
        """Display all messages."""
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


db = motor.motor_tornado.MotorClient("mongodb://clacina:ptYpRKAqNvK7@ds023000.mlab.com:23000/glympse_web_socket-clacina")

application = tornado.web.Application(
    [
        (r'/compose', NewMessageHandler),
        (r'/', MessagesHandler)
    ],
    db=db
)

print('Listening on http://localhost:8888')
application.listen(8888)
tornado.ioloop.IOLoop.instance().start()