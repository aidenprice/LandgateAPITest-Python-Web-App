# Libraries available on Google cloud service.
import webapp2

# Google's appengine python libraries.
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

# Standard python libraries.
import json
from datetime import datetime
from calendar import timegm

# Constants

DEFAULT_CAMPAIGN_NAME = 'production_campaign'

def getCampaignKey(database_name=DEFAULT_CAMPAIGN_NAME):
    key = ndb.Key(TestCampaign, database_name)
    print key
    if key is None:
        return TestCampaign(key=database_name, campaignName=database_name).put()
    else:
        return key


class CustomEncoder(json.JSONEncoder):
    """A custom JSON encoder to serialise date time properties into timestamps
    and geopt properties into individual lat and lon entries.
    All other types get the superclass implementation."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return str(timegm(obj.timetuple()))
        elif isinstance(obj, ndb.GeoPt):
            return {'lat': obj.lat, 'lon': obj.lon}
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(CustomEncoder, self).default(obj)


# Model classes

class TestCampaign(ndb.Model):
    """TestCampaign is a superclass meant to link many TestMasters
    by a single parent ID."""
    campaignName = ndb.StringProperty()
    # TestMasters - a list of all the TestMaster objects, usually just one.


class ResultObject(polymodel.PolyModel):
    """An abstract superclass for all result classes."""
    testID = ndb.StringProperty()
    parentID = ndb.StringProperty()
    datetime = ndb.DateTimeProperty()
    success = ndb.BooleanProperty()
    comment = ndb.StringProperty()


class TestMaster(ResultObject):
    """The main class, each TestMaster object represents a single test
    from the user's point of view, but actually initiates many TestEndpoints."""
    startDatetime = ndb.DateTimeProperty()
    finishDatetime = ndb.DateTimeProperty()
    deviceType = ndb.StringProperty()
    deviceID = ndb.StringProperty()
    iOSVersion = ndb.StringProperty()
    # endpointResults - a list of TestEndpoint subclass objects, normally dozens
    #                 of them. Must be one of ImageEndpoint, XmlEndpoint
    #                 or JsonEndpoint.
    # networkResults - a list of NetworkResult objects.
    # locationResults - a list of LocationResult objects.
    # pingResults - a list of PingResult objects.


class TestEndpoint(ResultObject):
    """An abstract superclass for all endpoint tests.
    An actual test on a specific URL with parameters."""
    startDatetime = ndb.DateTimeProperty()
    finishDatetime = ndb.DateTimeProperty()
    server = ndb.StringProperty()
    dataset = ndb.StringProperty()
    returnType = ndb.StringProperty()
    testName = ndb.StringProperty()
    httpMethod = ndb.StringProperty()
    testedURL = ndb.StringProperty()
    responseCode = ndb.IntegerProperty()
    errorResponse = ndb.StringProperty()


# sub-subclasses for json, xml, images
class ImageEndpoint(TestEndpoint):
    """An API endpoint test designed to return an image for example a WMTS call
    returning a map tile.
    Importantly, in order to transmit images in JSON we must first convert them
    to 64 bit text. We keep them in this format for ease of comparison to
    a reference copy of the image, and we do not plan to display images."""
    imageResponse = ndb.TextProperty()


class XmlEndpoint(TestEndpoint):
    """A concrete class designed to hold a GML response from
    a test on an OGC API endpoint."""
    xmlResponse = ndb.TextProperty()


class JsonEndpoint(TestEndpoint):
    """A concrete class to hold the JSON response from a
    test on a GeoJSON or EsriJson API endpoint."""
    jsonResponse = ndb.JsonProperty()


class NetworkResult(ResultObject):
    """The properties of a device's connection to the network,
    either cellular or wifi."""
    connectionType = ndb.StringProperty()
    carrierName = ndb.StringProperty()
    cellID = ndb.StringProperty()


class LocationResult(ResultObject):
    """A location and time associated with a TestMaster.
    There will be several location objects for each master test."""
    location = ndb.GeoPtProperty()


class PingResult(ResultObject):
    """Holds the response time for a ping test."""
    pingedURL = ndb.StringProperty()
    pingTime = ndb.IntegerProperty()


# Page classes

class TestPage(webapp2.RequestHandler):
    """Handles requests to test the server is up and running."""
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!\nService is up and running!')


class MainPage(webapp2.RequestHandler):
    """The workhorse part of the web application.
    Accepts properly formatted JSON in POST requests then builds
    model objects for storage.
    Dumps the entire datastore as JSON on a successful GET request."""
    def post(self):
        dictResults = {}
        if type(self.request.body) is str:
            dictResults = json.loads(self.request.body.decode('string-escape').strip('"'))
        else:
            dictResults = json.load(self.request.body)

        try:
            campaignKey = getCampaignKey(dictResults.get('campaignName'))


            for TM in dictResults.get('TestMasters', []):
                testMaster = TestMaster(parent=campaignKey)
                testMaster.testID = TM.get('testID')
                testMaster.parentID = TM.get('parentID')
                testMaster.startDatetime = datetime.utcfromtimestamp(float(TM.get('startDatetime')))
                testMaster.finishDatetime = datetime.utcfromtimestamp(float(TM.get('finishDatetime')))
                testMaster.success = bool(TM.get('success'))
                testMaster.comment = TM.get('comment')
                testMaster.deviceType = TM.get('deviceType')
                testMaster.deviceID = TM.get('deviceID')
                testMaster.iOSVersion = TM.get('iOSVersion')

                masterKey = testMaster.put()

                listTestEndpoints = []
                for TE in TM.get('endpointResults', []):
                    print TE
                    testEndpoint = None
                    keys = TE.keys()
                    if 'imageResponse' in keys:
                        testEndpoint = ImageEndpoint(parent=masterKey)
                        testEndpoint.imageResponse = str(TE.get('imageResponse'))
                    elif 'xmlResponse' in keys:
                        testEndpoint = XmlEndpoint(parent=masterKey)
                        testEndpoint.xmlResponse = TE.get('xmlResponse')
                    elif 'jsonResponse' in keys:
                        testEndpoint = JsonEndpoint(parent=masterKey)
                        testEndpoint.jsonResponse = TE.get('jsonResponse')
                    elif 'responseData' in keys:
                        # There was no response to the original request (likely no connectivity)
                        # Here we set to a null json response.
                        testEndpoint = JsonEndpoint(parent=masterKey)
                        testEndpoint.jsonResponse = None

                    if any(['imageResponse' in keys, 'xmlResponse' in keys, 'jsonResponse' in keys, 'responseData' in keys]):
                        testEndpoint.testID = TE.get('testID')
                        testEndpoint.parentID = TE.get('parentID')
                        testEndpoint.startDatetime = datetime.utcfromtimestamp(float(TE.get('startDatetime')))
                        testEndpoint.finishDatetime = datetime.utcfromtimestamp(float(TE.get('finishDatetime')))
                        testEndpoint.success = bool(TE.get('success'))
                        testEndpoint.comment = TE.get('comment')
                        testEndpoint.server = TE.get('server')
                        testEndpoint.dataset = TE.get('dataset')
                        testEndpoint.returnType = TE.get('returnType')
                        testEndpoint.testName = TE.get('testName')
                        testEndpoint.httpMethod = TE.get('httpMethod')
                        testEndpoint.testedURL = TE.get('testedURL')
                        testEndpoint.responseCode = int(TE.get('responseCode'))
                        testEndpoint.errorResponse = TE.get('errorResponse')

                        listTestEndpoints.append(testEndpoint)

                print listTestEndpoints

                listNetworkResults = []
                for NR in TM.get('networkResults', []):
                    networkResult = NetworkResult(parent=masterKey)
                    networkResult.testID = NR.get('testID')
                    networkResult.parentID = NR.get('parentID')
                    networkResult.datetime = datetime.utcfromtimestamp(float(NR.get('datetime')))
                    networkResult.success = bool(NR.get('success'))
                    networkResult.comment = NR.get('comment')
                    networkResult.connectionType = NR.get('connectionType')
                    networkResult.carrierName = NR.get('carrierName')
                    networkResult.cellID = NR.get('cellID')

                    listNetworkResults.append(networkResult)

                print listNetworkResults

                listLocationResults = []
                for LR in TM.get('locationResults', []):
                    locationResult = LocationResult(parent=masterKey)
                    locationResult.testID = LR.get('testID')
                    locationResult.parentID = LR.get('parentID')
                    locationResult.datetime = datetime.utcfromtimestamp(float(LR.get('datetime')))
                    locationResult.success = bool(LR.get('success'))
                    locationResult.comment = LR.get('comment')
                    locationResult.location = ndb.GeoPt(str(LR.get('latitude')) + ', ' +
                                                        str(LR.get('longitude')))

                    listLocationResults.append(locationResult)

                print listLocationResults

                listPingResults = []
                for PR in TM.get('pingResults', []):
                    pingResult = PingResult(parent=masterKey)
                    pingResult.testID = PR.get('testID')
                    pingResult.parentID = PR.get('parentID')
                    pingResult.datetime = datetime.utcfromtimestamp(float(PR.get('datetime')))
                    pingResult.success = bool(PR.get('success'))
                    pingResult.comment = PR.get('comment')
                    pingResult.pingedURL = PR.get('pingedURL')
                    pingResult.pingTime = int(PR.get('pingTime'))

                    listPingResults.append(pingResult)

                print listPingResults

                # Push everything to database.
                # This is done at the end to help prevent orphaned objects
                # if the function hits an exception partway through.
                listTestEndpointKeys = ndb.put_multi(listTestEndpoints)
                listNetworkKeys = ndb.put_multi(listNetworkResults)
                listLocationKeys = ndb.put_multi(listLocationResults)
                listPingKeys = ndb.put_multi(listPingResults)


            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Results successfully uploaded.\n' +
                                'Thank you for contributing!')

        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Improperly formatted JSON uploaded.\n' +
                                'Sorry, your upload was not successful.\n\n' +
                                e.message)

    def get(self):
        dictDatabase = {}
        testCampaignName = None
        try:
            testCampaignName = self.request.get('campaignName')
            print testCampaignName
            dictDatabase['campaignName'] = testCampaignName
            campaignKey = getCampaignKey(testCampaignName)
            print campaignKey
        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide \"campaignName=\"\n\n' +
                                e.message)
        else:
            try:
                database_query = TestMaster.query(ancestor=campaignKey).order(TestMaster.startDatetime)

                listTestMasters = database_query.fetch()
                listOutputTestMasters = []
                for TM in listTestMasters:
                    dictMaster = TM.to_dict()
                    masterKey = TM.key
                    print masterKey

                    testEndpoint_query = TestEndpoint.query(ancestor=masterKey).order(TestEndpoint.startDatetime)
                    listTestEndpoints = testEndpoint_query.fetch()
                    listOutputTestEndpoints = []
                    for TE in listTestEndpoints:
                        listOutputTestEndpoints.append(TE.to_dict())

                    dictMaster['TestEndpoints'] = listOutputTestEndpoints

                    networkResult_query = NetworkResult.query(ancestor=masterKey).order(NetworkResult.datetime)
                    listNetworkResults = networkResult_query.fetch()
                    listOutputNetworkResults = []
                    for NR in listNetworkResults:
                        listOutputNetworkResults.append(NR.to_dict())

                    dictMaster['NetworkResults'] = listOutputNetworkResults

                    locationResult_query = LocationResult.query(ancestor=masterKey).order(LocationResult.datetime)
                    listLocationResults = locationResult_query.fetch()
                    listOutputLocationResults = []
                    for LR in listLocationResults:
                        listOutputLocationResults.append(LR.to_dict())

                    dictMaster['LocationResults'] = listOutputLocationResults

                    pingResult_query = PingResult.query(ancestor=masterKey).order(PingResult.datetime)
                    listPingResults = pingResult_query.fetch()
                    listOutputPingResults = []
                    for PR in listPingResults:
                        listOutputPingResults.append(PR.to_dict())

                    dictMaster['PingResults'] = listOutputPingResults

                    listOutputTestMasters.append(dictMaster)

                dictDatabase['TestMasters'] = listOutputTestMasters

                self.response.headers['Content-Type'] = 'application/json'
                self.response.write(json.dumps(dictDatabase, indent=4, cls=CustomEncoder))

            except Exception as e:
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, JSON writing error condition ' +
                                    'encountered!\nNo data for you!\n\n' +
                                    e.message)

    def delete(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = ndb.Key(TestCampaign, campaignName)
            campaignKey.delete()

        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Sorry, JSON writing error condition ' +
                                'encountered!\nNo data for you!\n\n' +
                                e.message)
        else:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Deleted TestCampaign; ' + campaignName)


class StatsPage(webapp2.RequestHandler):
    """Returns a short JSON dict of descriptive stats."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = getCampaignKey(campaignName)
            print campaignKey

        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide \"campaignName=\"\n\n' +
                                e.message)
        else:
            try:
                dictStats = {}

                countTestMasters = 0
                totalTestMasterTime = 0.0
                allDeviceTypes = set()
                allOSVersions = set()
                countTestEndpoints = 0
                totalTestEndpointTime = 0.0
                countTestEndpointsSuccessful = 0
                countNetworkResults = 0
                countNetworkResultsSuccessful = 0
                countLocationResults = 0
                countPingResults = 0
                totalPingTime = 0

                database_query = TestMaster.query(ancestor=campaignKey).order(TestMaster.startDatetime)
                listTestMasters = database_query.fetch()

                for TM in listTestMasters:
                    countTestMasters += 1
                    totalTestMasterTime += (TM.finishDatetime - TM.startDatetime).total_seconds()
                    allDeviceTypes.add(TM.deviceType)
                    allOSVersions.add(TM.iOSVersion)

                    masterKey = TM.key
                    testEndpoint_query = TestEndpoint.query(ancestor=masterKey).order(TestEndpoint.startDatetime)
                    listTestEndpoints = testEndpoint_query.fetch()
                    for TE in listTestEndpoints:
                        countTestEndpoints += 1
                        countTestEndpointsSuccessful += TE.success
                        print 'TE success; ' + str(TE.success)
                        print countTestEndpointsSuccessful
                        totalTestEndpointTime += (TE.finishDatetime - TE.startDatetime).total_seconds()

                    networkResult_query = NetworkResult.query(ancestor=masterKey).order(NetworkResult.datetime)
                    listNetworkResults = networkResult_query.fetch()
                    for NR in listNetworkResults:
                        countNetworkResults += 1
                        countNetworkResultsSuccessful += NR.success
                        print 'NR success; ' + str(NR.success)
                        print countNetworkResultsSuccessful

                    locationResult_query = LocationResult.query(ancestor=masterKey).order(LocationResult.datetime)
                    listLocationResults = locationResult_query.fetch()
                    for LR in listLocationResults:
                        countLocationResults += 1

                    pingResult_query = PingResult.query(ancestor=masterKey).order(PingResult.datetime)
                    listPingResults = pingResult_query.fetch()
                    for PR in listPingResults:
                        countPingResults += 1
                        totalPingTime += PR.pingTime

                dictStats['countTestMasters'] = countTestMasters
                dictStats['meanTestMasterTime'] = totalTestMasterTime / countTestMasters
                dictStats['allDeviceTypes'] = allDeviceTypes
                dictStats['allOSVersions'] = allOSVersions
                dictStats['countTestEndpoints'] = countTestEndpoints
                dictStats['meanTestEndpointResponseTime'] = totalTestEndpointTime / countTestEndpoints
                dictStats['percentTestEndpointsSuccessful'] = ((countTestEndpointsSuccessful * 1.0) / countTestEndpoints) * 100
                dictStats['countNetworkResults'] = countNetworkResults
                dictStats['percentNetworkTestsSuccessful'] = ((countNetworkResultsSuccessful * 1.0) / countNetworkResults) * 100
                dictStats['countLocationResults'] = countLocationResults
                dictStats['countPingResults'] = countPingResults
                dictStats['meanPingTime'] = totalPingTime / countPingResults


                self.response.headers['Content-Type'] = 'application/json'
                self.response.write(json.dumps(dictStats, indent=4, cls=CustomEncoder))

            except Exception as e:
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, JSON writing error condition ' +
                                    'encountered!\nNo data for you!\n\n' +
                                    e.message)


# WSGI app
# Handles incoming requests according to supplied URL.
app = webapp2.WSGIApplication([
    ('/servicetest', TestPage),
    ('/stats', StatsPage),
    ('/database', MainPage),
], debug=True)
