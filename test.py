# Libraries available on Google cloud service.
import webapp2


class MainPage(webapp2.RequestHandler):
    """Handles requests to test the server is up and running."""
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!\nService is up and running!')


app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)
