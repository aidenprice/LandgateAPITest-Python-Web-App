""" LandgateAPITest Web App

Model schema update module

Created by Aiden Price,
Curtin University Masters of Geospatial Science candidate,
Submitted June 2016"""

# Libraries available on Google cloud service.
import webapp2

# Google's appengine python libraries.
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel
from google.appengine.api import taskqueue
from google.appengine.datastore.datastore_query import Cursor

# Local model imports
from landgateapitestmodel import TestCampaign
from landgateapitestmodel import ResultObject
from landgateapitestmodel import TestMaster
from landgateapitestmodel import TestEndpoint
from landgateapitestmodel import NetworkResult
from landgateapitestmodel import LocationResult
from landgateapitestmodel import PingResult
from landgateapitestmodel import ReferenceObject
from landgateapitestmodel import Vector
from landgateapitestmodel import CampaignStats

# Constants and helper classes and functions

DEFAULT_CAMPAIGN_NAME = 'production_campaign'

BATCH_SIZE = 50  # ideal batch size may vary based on entity size.

class UpdateSchemaWorker(webapp2.RequestHandler):
    def get(self):
        cursorString = self.request.get('cursor')

        cursor = None
        if cursorString != 'None':
            cursor = Cursor(urlsafe=cursorString)

        listVectors, next_cursor, more = Vector.query().fetch_page(BATCH_SIZE, start_cursor=cursor)
        to_put = []

        for vector in listVectors:
            if any([
            (vector.server == 'OGC' and vector.dataset == 'BusStops' and vector.name == 'GetCapabilities' and vector.httpMethod == 'GET' and vector.returnType == 'XML'),
            (vector.server == 'OGC' and vector.dataset == 'BusStops' and vector.name == 'AttributeFilter' and vector.httpMethod == 'GET' and vector.returnType == 'JSON'),
            (vector.server == 'OGC' and vector.dataset == 'BusStops' and vector.name == 'GetCapabilities' and vector.httpMethod == 'POST' and vector.returnType == 'XML'),
            (vector.server == 'OGC' and vector.dataset == 'Topo' and vector.name == 'Big' and vector.httpMethod == 'GET' and vector.returnType == 'Image'),
            (vector.server == 'OGC' and vector.dataset == 'Topo' and vector.name == 'Small' and vector.httpMethod == 'GET' and vector.returnType == 'Image'),
            (vector.server == 'GME' and vector.dataset == 'BusStops' and vector.name == 'Small' and vector.httpMethod == 'GET' and vector.returnType == 'JSON'),
            (vector.server == 'GME' and vector.dataset == 'AerialPhoto' and vector.name == 'WMSGetCapabilities' and vector.httpMethod == 'GET' and vector.returnType == 'XML'),
            (vector.server == 'GME' and vector.dataset == 'AerialPhoto' and vector.name == 'WMTSGetCapabilities' and vector.httpMethod == 'GET' and vector.returnType == 'XML')
            ]):
                vector.referenceCheckValid = False
                print 'Changed flag! False!'
                to_put.append(vector)
            else:
                vector.referenceCheckValid = True
                print 'Changed flag! True!'
                to_put.append(vector)

        if to_put:
            ndb.put_multi(to_put)

        if more:
            print next_cursor.urlsafe()
            taskqueue.add(url='/updateschemaworker', method='GET', params={'cursor':next_cursor.urlsafe()})

class UpdateSchema(webapp2.RequestHandler):
    def get(self):
        q = taskqueue.Queue('default')
        print q
        q.purge()

        taskqueue.add(url='/updateschemaworker', method='GET', params={'cursor':'None'})

# WSGI app
# Handles incoming requests according to supplied URL.
app = webapp2.WSGIApplication([
    ('/updateschema', UpdateSchema),
    ('/updateschemaworker', UpdateSchemaWorker)
], debug=True)
