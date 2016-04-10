# Libraries available on Google cloud service.
import webapp2
import matplotlib

# Google's appengine python libraries.
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel
from google.appengine.api import taskqueue

# Standard python libraries.
import json
import math
from datetime import datetime
from datetime import timedelta
from calendar import timegm

# Constants and helper classes and functions

DEFAULT_CAMPAIGN_NAME = 'production_campaign'

def getCampaignKey(database_name=DEFAULT_CAMPAIGN_NAME):
    key = ndb.Key(TestCampaign, database_name)
    if key is None:
        return TestCampaign(key=database_name, campaignName=database_name).put()
    else:
        return key


def HaversineDistance(location1, location2):
    """Method to calculate Distance between two sets of Lat/Lon.
    Modified from Amyth's StackOverflow answer of 22/5/2012;
    http://stackoverflow.com/questions/10693699/calculate-distance-between-cities-find-surrounding-cities-based-on-geopt-in-p
    """
    lat1, lon1 = location1
    lat2, lon2 = location2
    earth = 6378137 #Earth's equatorial radius in metres.

    #Calculate distance based on Haversine Formula
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = earth * c
    return d


class AnalysisEnum:
    """A three state enumeration to show whether a TestEndpoint object has
    been analysed already and whether it was analysed successfully.
    While this data could also be realised as two boolean values
    it would be possible to store a fourth state (not yet analysed and
    impossible to analyse) that would be nonsensical."""
    UNANALYSED = 0
    IMPOSSIBLE = 1
    SUCCESSFUL = 2


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
    analysed = ndb.IntegerProperty()


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
    test on a GeoJSON or EsriJson API endpoint.
    There is an ndb.JsonProperty object sounds perfect for this use case.
    Unfortunately, we can not be assured of receiving well formed JSON
    and must store incomplete JSON returns as well as complete ones."""
    jsonResponse = ndb.TextProperty()


class NetworkResult(ResultObject):
    """The properties of a device's connection to the network,
    either cellular or wifi."""
    connectionType = ndb.StringProperty()
    carrierName = ndb.StringProperty()
    cellID = ndb.StringProperty()

    def NetworkClass():
        """Classifies mobile broadband networks by their generation,
        i.e. 3.5G, 4G etc as float values.
        N.B. Assume 5 for wifi connections."""
        generation = 0.0

        if self.connectionType == 'CTRadioAccessTechnologyGPRS':
            generation = 2.5
        elif self.connectionType == 'CTRadioAccessTechnologyCDMA1x':
            generation = 2.5
        elif self.connectionType == 'CTRadioAccessTechnologyEdge':
            generation = 2.75
        elif self.connectionType == 'CTRadioAccessTechnologyWCDMA':
            generation = 3.0
        elif self.connectionType == 'CTRadioAccessTechnologyCDMAEVDORev0':
            generation = 3.0
        elif self.connectionType == 'CTRadioAccessTechnologyeHRPD':
            generation = 3.0
        elif self.connectionType == 'CTRadioAccessTechnologyHSDPA':
            generation = 3.5
        elif self.connectionType == 'CTRadioAccessTechnologyHSUPA':
            generation = 3.5
        elif self.connectionType == 'CTRadioAccessTechnologyCDMAEVDORevA':
            generation = 3.5
        elif self.connectionType == 'CTRadioAccessTechnologyCDMAEVDORevB':
            generation = 3.75
        elif self.connectionType == 'CTRadioAccessTechnologyLTE':
            generation = 4.0
        elif self.connectionType == 'Wifi':
            generation = 5.0

        return generation


class LocationResult(ResultObject):
    """A location and time associated with a TestMaster.
    There will be several location objects for each master test."""
    location = ndb.GeoPtProperty()


class PingResult(ResultObject):
    """Holds the response time for a ping test."""
    pingedURL = ndb.StringProperty()
    pingTime = ndb.IntegerProperty()


class Vector(ndb.Model):
    """An analysis data structure, the output of the Analyse() function.
    For each EndpointResult, Analyse() considers the LocationResults,
    NetworkResults and PingResults immediately before and after. The network
    connection may improve or degrade, the ping time increase or decrease
    and so forth. The aim being to illustrate the change in circumstances
    through the test period.
    N.B. We should prefer to show improvement in signal or response time
    with positive numeric values and degradation with negative values.
    Hence subtracting the later pingTime from the prior, but conversely
    subtracting the prior networkClass from the later."""
    test = ndb.StructuredProperty(TestEndpoint)

    testName = ndb.StringProperty()
    testStartDateTime = ndb.DateTimeProperty()
    testFinishDateTime = ndb.DateTimeProperty()
    testResponseTime = ndb.FloatProperty()
    testDeviceType = ndb.StringProperty()
    testDeviceID = ndb.StringProperty()
    testIOSVersion = ndb.StringProperty()
    testServer = ndb.StringProperty()
    testDataset = ndb.StringProperty()
    testHttpMethod = ndb.StringProperty()
    testReturnType = ndb.StringProperty()
    testResponseCode = ndb.IntegerProperty()
    testOnDeviceSuccess = ndb.BooleanProperty()
    testReferenceCheckSuccess = ndb.BooleanProperty()

    preTestLocation = ndb.StructuredProperty(LocationResult)
    postTestLocation = ndb.StructuredProperty(LocationResult)
    preTestNetwork = ndb.StructuredProperty(NetworkResult)
    postTestNetwork = ndb.StructuredProperty(NetworkResult)
    preTestPing = ndb.StructuredProperty(PingResult)
    postTestPing = ndb.StructuredProperty(PingResult)

    distance = ndb.FloatProperty()
    speed = ndb.FloatProperty()

    pingChange = ndb.IntegerProperty()
    networkChange = ndb.IntegerProperty()


class CampaignStats(ndb.Model):
    """A stored record of descriptive statistics for all tests in a
    campaign. Updated when a test is analysed and stored for quick retrieval."""
    campaignName = ndb.StringProperty()
    countTestMasters = ndb.IntegerProperty()
    allDeviceTypes = ndb.StringProperty()
    allOSVersions = ndb.StringProperty()
    countTestEndpoints = ndb.IntegerProperty()
    totalTestEndpointTime = ndb.FloatProperty()
    countTestEndpointsSuccessful = ndb.IntegerProperty()
    countNetworkResults = ndb.IntegerProperty()
    countLocationResults = ndb.IntegerProperty()
    countPingResults = ndb.IntegerProperty()
    totalPingTime = ndb.IntegerProperty()


# Page classes

class TestPage(webapp2.RequestHandler):
    """Responds to requests that test whether the server instance is up and
    running."""
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!\nService is up and running!\n\n')


class Database(webapp2.RequestHandler):
    """The workhorse part of the web application.
    Accepts properly formatted JSON in POST requests then builds
    model objects for storage."""
    def post(self):
        dictResults = {}

        # Check for string request bodies, use either the "load" or "loads"
        # functions depending.
        if type(self.request.body) is str:
            dictResults = json.loads(self.request.body, strict=False)
        else:
            dictResults = json.load(self.request.body)

        try:
            campaignName = dictResults.get('campaignName')
            campaignKey = getCampaignKey(campaignName)

            stats_query = CampaignStats.query(CampaignStats.campaignName == campaignName)
            stats = stats_query.get()

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

                stats.countTestMasters += 1

                if testMaster.deviceType not in stats.allDeviceTypes:
                    stats.allDeviceTypes += testMaster.deviceType
                    stats.allDeviceTypes += ", "

                if testMaster.iOSVersion not in stats.allOSVersions:
                    stats.allOSVersions += testMaster.iOSVersion
                    stats.allOSVersions += ", "

                masterKey = testMaster.put()

                listTestEndpoints = []
                for TE in TM.get('endpointResults', []):
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
                        testEndpoint.analysed = AnalysisEnum.UNANALYSED

                        stats.countTestEndpoints += 1
                        stats.totalTestEndpointTime += (TE.get('finishDatetime') - TE.get('startDatetime'))
                        if testEndpoint.success:
                            stats.countTestEndpointsSuccessful += 1

                        listTestEndpoints.append(testEndpoint)

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

                    stats.countNetworkResults += 1

                    listNetworkResults.append(networkResult)

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

                    stats.countLocationResults += 1

                    listLocationResults.append(locationResult)

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

                    stats.countPingResults += 1
                    stats.totalPingTime += pingResult.pingTime

                    listPingResults.append(pingResult)

                # Push everything to database.
                # This is done at the end to help prevent orphaned objects
                # if the function hits an exception partway through.
                listTestEndpointKeys = ndb.put_multi(listTestEndpoints)
                listNetworkKeys = ndb.put_multi(listNetworkResults)
                listLocationKeys = ndb.put_multi(listLocationResults)
                listPingKeys = ndb.put_multi(listPingResults)

                # Add an analysis task to the default queue for each
                # endpoint test completed.
                for endpoint in listTestEndpoints:
                    taskqueue.add(url='/analyse', params={'campaignName': campaignName, 'testID': endpoint.testID})

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Results successfully uploaded.\n' +
                                'Thank you for contributing!\n\n')

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Improperly formatted JSON uploaded.\n' +
                                'Sorry, your upload was not successful.\n\n' +
                                e.message + '\n\n')

    def get(self):
        """Returns 20 TestMasters and their children tests.
        This page formerly parsed the entire database into a JSON dictionary
        but memory overflows on the Google Apps Engine free tier hardware
        forced a limit on the output."""
        dictDatabase = {}
        testCampaignName = None
        try:
            testCampaignName = self.request.get('campaignName')
            dictDatabase['campaignName'] = testCampaignName
            campaignKey = getCampaignKey(testCampaignName)

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide ?campaignName=\n\n' +
                                e.message + '\n\n')
        else:
            try:
                database_query = TestMaster.query(ancestor=campaignKey).order(TestMaster.startDatetime)
                listTestMasters = database_query.fetch(20)
                listOutputTestMasters = []
                for TM in listTestMasters:
                    dictMaster = TM.to_dict()
                    masterKey = TM.key

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
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, JSON writing error condition ' +
                                    'encountered!\nNo data for you!\n\n' +
                                    e.message + '\n\n')

    def delete(self):
        """Theoretically deletes an entire campaign from the database."""
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = ndb.Key(TestCampaign, campaignName)
            campaignKey.delete()

        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Sorry, JSON writing error condition ' +
                                'encountered!\nNo data for you!\n\n' +
                                e.message + '\n\n')
        else:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Deleted TestCampaign; ' + campaignName)


class Analyse(webapp2.RequestHandler):
    """A class that takes the point based information in each of the
    EndpointTests, LocationTests, NetworkTests and PingTests and
    combines them into line objects called Vectors™.
    Each Vector™ consists of the two LocationTests either side of an
    EndpointTest, determining distance, speed and direction. It gains
    PingTest and NetworkTest results as a vector of, constant, improving
    or degrading signal. The EndpointResult in the middle is the focus,
    its outcomes being compared to the motion and changing signal environment
    of the Vector™.
    This class builds and stores the vectors. Designed to be called by
    a Google App Engine task, a request scheduled according to processor
    availability rather than dependant on a request from the internet."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = getCampaignKey(campaignName)

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide ?campaignName=\n\n' +
                                e.message + '\n\n')
        else:
            try:
                """Fetch a single TestEndpoint object which has not yet been
                analysed.
                It doesn't matter which one, we'll get them all
                eventually. The Database POST method creates a task for each new
                testEndpoint added to the database.
                If the request includes a testID attribute fetch that specific
                test."""
                testID = self.request.get('testID')

                if testID is not None:
                    testEndpoint = TestEndpoint.query(TestEndpoint.testID == testID, TestEndpoint.analysed == 0).get()
                else:
                    testEndpoint = TestEndpoint.query(TestEndpoint.analysed == 0).get()

                if testEndpoint is not None:
                    # Grab the parent TestMaster
                    testMaster = TestMaster.query(TestMaster.testID == testEndpoint.parentID).get()

                    """Get the supporting tests either side of the EndpointTest
                    The query object filters by those tests with the same TestMaster
                    parent and a time greater than the EndpointTest's time. It sorts
                    all the returns by time (ascending or descending depending)
                    and the .get() function returns the first."""
                    preTestLocation = LocationResult.query(ancestor=testMaster.key, LocationResult.datetime < testEndpoint.startDatetime).order(-LocationResult.datetime).get()

                    postTestLocation = LocationResult.query(ancestor=testMaster.key, LocationResult.datetime > testEndpoint.finishDatetime).order(LocationResult.datetime).get()

                    preTestNetwork = NetworkResult.query(ancestor=testMaster.key, NetworkResult.datetime < testEndpoint.startDatetime).order(-NetworkResult.datetime).get()

                    postTestNetwork = NetworkResult.query(ancestor=testMaster.key, NetworkResult.datetime > testEndpoint.finishDatetime).order(NetworkResult.datetime).get()

                    preTestPing = PingResult.query(ancestor=testMaster.key, PingResult.datetime < testEndpoint.startDatetime).order(-PingResult.datetime).get()

                    postTestPing = PingResult.query(ancestor=testMaster.key, PingResult.datetime > testEndpoint.finishDatetime).order(PingResult.datetime).get()

                    # Each TestEndpoint should have a LocationTest, NetworkTest and
                    # PingTest before AND afterwards, if all six are present proceed
                    if preTestLocation and postTestLocation and preTestNetwork and postTestNetwork and preTestPing and postTestPing:

                        # Create a new Vector™ analysis data structure.
                        vector = Vector(parent=campaignKey)

                        # Assign all the TestEndpoint's relevant attributes to Vector™
                        vector.test = testEndpoint
                        vector.testName = testEndpoint.testName
                        vector.testStartDateTime = testEndpoint.startDatetime
                        vector.testFinishDateTime = testEndpoint.finishDatetime
                        vector.testResponseTime = timedelta(testEndpoint.finishDatetime - testEndpoint.startDatetime).total_seconds()
                        vector.testServer = testEndpoint.server
                        vector.testDataset = testEndpoint.dataset
                        vector.testHttpMethod = testEndpoint.httpMethod
                        vector.testReturnType = testEndpoint.returnType
                        vector.testResponseCode = testEndpoint.responseCode
                        vector.testOnDeviceSuccess = testEndpoint.success

                        # Assign the TestMaster's attributes
                        vector.testDeviceType = testMaster.deviceType
                        vector.testDeviceID = testMaster.deviceID
                        vector.testIOSVersion = testMaster.iOSVersion

                        # Assign all the supporting tests to the Vector™
                        vector.preTestLocation = preTestLocation
                        vector.postTestLocation = postTestLocation
                        vector.preTestNetwork = preTestNetwork
                        vector.postTestNetwork = postTestNetwork
                        vector.preTestPing = preTestPing
                        vector.postTestPing = postTestPing

                        # Calculate the change in environment during the test
                        vector.distance = HaversineDistance(preTestLocation.location, postTestLocation.location)
                        vector.speed = vector.distance / timedelta(postTestLocation.datetime - preTestLocation.datetime).total_seconds()

                        vector.pingChange = preTestPing.pingTime - postTestPing.pingTime
                        vector.networkChange = postTestNetwork.NetworkClass() - preTestNetwork.NetworkClass()

                        # All being well, we mark the testEndpoint object with
                        # the analysis SUCCESSFUL enum and put it back.
                        testEndpoint.analysed = AnalysisEnum.SUCCESSFUL
                        endpointKey = testEndpoint.put()

                        # The Vector™ object built successfully, so store it.
                        vectorKey = vector.put()

                        self.response.headers['Content-Type'] = 'text/plain'
                        self.response.write('Analysis complete!\n' +
                                            'Thank you and have an educational day!\n\n')

                    else:
                        """If we don't have all six supporting tests (as is possible
                        where a TestMaster may have been cancelled) the analysis
                        is IMPOSSIBLE, mark the testEndpoint with the enum so we
                        may ignore it in the future."""
                        testEndpoint.analysed = AnalysisEnum.IMPOSSIBLE
                        endpointKey = testEndpoint.put()

                        self.response.set_status(555, message="Custom error response code.")
                        self.response.headers['Content-Type'] = 'text/plain'
                        self.response.write('Sorry, analysis is impossible ' +
                                            'for this endpoint test!\n\n')

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, analysis exception condition ' +
                                    'encountered!\nAnalysis aborted!\n\n' +
                                    e.message + '\n\n')


class StatsPage(webapp2.RequestHandler):
    """Returns a short JSON dict of descriptive statistics."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = getCampaignKey(campaignName)

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide \"campaignName=\"\n\n' +
                                e.message + '\n\n')
        else:
            try:
                dictStats = {}

                """This section calculated the descriptive statistics
                in the first version of the web app.
                Unfortunately once pushed to production levels of input
                this page regularly returned 500 series errors.
                Digging into the logs showed memory usage in excess of
                the free tier Google Cloud plan.
                Rather than fix the memory leak, this section is deprecated.
                Circumventing the issue by storing descriptive statistics in
                the datastore."""

                # countTestMasters = 0
                # totalTestMasterTime = 0.0
                # allDeviceTypes = set()
                # allOSVersions = set()
                # countTestEndpoints = 0
                # totalTestEndpointTime = 0.0
                # countTestEndpointsSuccessful = 0
                # countNetworkResults = 0
                # countNetworkResultsSuccessful = 0
                # countLocationResults = 0
                # countPingResults = 0
                # totalPingTime = 0
                #
                # database_query = TestMaster.query(ancestor=campaignKey).order(TestMaster.startDatetime)
                # listTestMasters = database_query.fetch()
                #
                # for TM in listTestMasters:
                #     countTestMasters += 1
                #     totalTestMasterTime += (TM.finishDatetime - TM.startDatetime).total_seconds()
                #     allDeviceTypes.add(TM.deviceType)
                #     allOSVersions.add(TM.iOSVersion)
                #
                #     masterKey = TM.key
                #     testEndpoint_query = TestEndpoint.query(ancestor=masterKey).order(TestEndpoint.startDatetime)
                #     listTestEndpoints = testEndpoint_query.fetch()
                #     for TE in listTestEndpoints:
                #         countTestEndpoints += 1
                #         countTestEndpointsSuccessful += TE.success
                #         # print 'TE success; ' + str(TE.success)
                #         # print countTestEndpointsSuccessful
                #         totalTestEndpointTime += (TE.finishDatetime - TE.startDatetime).total_seconds()
                #
                #     networkResult_query = NetworkResult.query(ancestor=masterKey).order(NetworkResult.datetime)
                #     listNetworkResults = networkResult_query.fetch()
                #     for NR in listNetworkResults:
                #         countNetworkResults += 1
                #         countNetworkResultsSuccessful += NR.success
                #         # print 'NR success; ' + str(NR.success)
                #         # print countNetworkResultsSuccessful
                #
                #     locationResult_query = LocationResult.query(ancestor=masterKey).order(LocationResult.datetime)
                #     listLocationResults = locationResult_query.fetch()
                #     for LR in listLocationResults:
                #         countLocationResults += 1
                #
                #     pingResult_query = PingResult.query(ancestor=masterKey).order(PingResult.datetime)
                #     listPingResults = pingResult_query.fetch()
                #     for PR in listPingResults:
                #         countPingResults += 1
                #         totalPingTime += PR.pingTime

                stats = CampaignStats.query(CampaignStats.campaignName == campaignName).get()

                dictStats['campaignName'] = stats.campaignName
                dictStats['countTestMasters'] = stats.countTestMasters
                dictStats['allDeviceTypes'] = stats.allDeviceTypes
                dictStats['allOSVersions'] = stats.allOSVersions
                dictStats['countTestEndpoints'] = stats.countTestEndpoints
                dictStats['averageTestEndpointResponseTime'] = stats.totalTestEndpointTime / (stats.countTestEndpoints * 1.0)
                dictStats['percentTestEndpointsSuccessful'] = ((stats.countTestEndpointsSuccessful * 1.0) / (stats.countTestEndpoints * 1.0)) * 100
                dictStats['countNetworkResults'] = stats.countNetworkResults
                dictStats['countLocationResults'] = stats.countLocationResults
                dictStats['countPingResults'] = stats.countPingResults
                dictStats['averagePingTime'] = (totalPingTime *1.0) / (countPingResults * 1.0)


                self.response.headers['Content-Type'] = 'application/json'
                self.response.write(json.dumps(dictStats, indent=4, cls=CustomEncoder))

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, JSON writing error condition ' +
                                    'encountered!\nNo data for you!\n\n' +
                                    e.message + '\n\n')


class GraphsPage(webapp2.RequestHandler):
    """"A page that produces a graph for a given campaign.
    The request must specify which of the graph types they want returned.
    Graphs generated from latest available data using the Python
    matplotlib library."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = getCampaignKey(campaignName)
            graphName = self.request.get('graphName')
            if !graphName in ('graph1', 'graph2'):
                raise ValueError('No such graph as ' + graphName +
                                 '. This is a custom exception.')

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide ?campaignName=&graphName=\n\n' +
                                e.message + '\n\n')
        else:
            try:
                graph = None

                if graphName == 'graph1':

                elif graphName == 'graph2':



                self.response.headers['Content-Type'] = 'image/png'
                self.response.write(graph)

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, graphing error condition ' +
                                    'encountered!\nNo image for you!\n\n' +
                                    e.message + '\n\n')


# WSGI app
# Handles incoming requests according to supplied URL.
app = webapp2.WSGIApplication([
    ('/servicetest', TestPage),
    ('/database', Database),
    ('/analyse', Analyse),
    ('/stats', StatsPage),
    ('/graphs', GraphsPage)
], debug=True)
