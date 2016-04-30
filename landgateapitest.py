""" LandgateAPITest Web App

Created by Aiden Price,
Curtin University Masters of Geospatial Science candidate,
Submitted June 2016"""

# Standard python libraries.
import json
import math
import random
import cStringIO

from datetime import datetime
from datetime import timedelta
from calendar import timegm

# Libraries available on Google cloud service.
import webapp2
import os
import matplotlib
import numpy

# Matplotlib OO library imports
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm as cm

# Google's appengine python libraries.
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel
from google.appengine.api import taskqueue

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

def getCampaignKey(database_name=DEFAULT_CAMPAIGN_NAME):
    key = ndb.Key(TestCampaign, database_name)
    if key is None:
        return TestCampaign(key=database_name, campaignName=database_name).put()
    else:
        return key


def NetworkClass(connectionType):
    """Classifies mobile broadband networks by their generation,
    i.e. 3.5G, 4G etc as float values.
    N.B. Assume 5 for wifi connections."""
    generation = 0.0

    if connectionType == 'CTRadioAccessTechnologyGPRS':
        generation = 2.5
    elif connectionType == 'CTRadioAccessTechnologyCDMA1x':
        generation = 2.5
    elif connectionType == 'CTRadioAccessTechnologyEdge':
        generation = 2.75
    elif connectionType == 'CTRadioAccessTechnologyWCDMA':
        generation = 3.0
    elif connectionType == 'CTRadioAccessTechnologyCDMAEVDORev0':
        generation = 3.0
    elif connectionType == 'CTRadioAccessTechnologyeHRPD':
        generation = 3.0
    elif connectionType == 'CTRadioAccessTechnologyHSDPA':
        generation = 3.5
    elif connectionType == 'CTRadioAccessTechnologyHSUPA':
        generation = 3.5
    elif connectionType == 'CTRadioAccessTechnologyCDMAEVDORevA':
        generation = 3.5
    elif connectionType == 'CTRadioAccessTechnologyCDMAEVDORevB':
        generation = 3.75
    elif connectionType == 'CTRadioAccessTechnologyLTE':
        generation = 4.0
    elif connectionType == 'Wifi':
        generation = 5.0
    return generation


def HaversineDistance(location1, location2):
    """Method to calculate Distance between two sets of Lat/Lon.
    Modified from Amyth's StackOverflow answer of 22/5/2012;
    http://stackoverflow.com/questions/10693699/calculate-distance-between-cities-find-surrounding-cities-based-on-geopt-in-p
    """
    lat1 = location1.lat
    lon1 = location1.lon
    # lat1, lon1 = location1
    lat2 = location2.lat
    lon2 = location2.lon
    # lat2, lon2 = location2
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

            # Get the CampaignStats record for this campaign.
            stats_query = CampaignStats.query(CampaignStats.campaignName == campaignName)
            stats = stats_query.get()

            # There is no extant CampaignStats record for this campaign.
            # Instantiate one with blank values.
            if stats is None:
                stats = CampaignStats(parent=campaignKey)
                stats.campaignName = campaignName
                stats.countTestMasters = 0
                stats.allDeviceTypes = ""
                stats.allOSVersions = ""
                stats.countTestEndpoints = 0
                stats.totalTestEndpointTime = 0.0
                stats.countTestEndpointsSuccessful = 0
                stats.countNetworkResults = 0
                stats.countLocationResults = 0
                stats.countPingResults = 0
                stats.countPingResultsSuccessful = 0
                stats.totalPingTime = 0
                stats.ESRI_BusStops_AttributeFilter_GET_JSON = 0
                stats.ESRI_BusStops_AttributeFilter_POST_JSON = 0
                stats.ESRI_BusStops_Big_GET_JSON = 0
                stats.ESRI_BusStops_Big_POST_JSON = 0
                stats.ESRI_BusStops_FeatureByID_GET_JSON = 0
                stats.ESRI_BusStops_FeatureByID_POST_JSON = 0
                stats.ESRI_BusStops_GetCapabilities_GET_JSON = 0
                stats.ESRI_BusStops_GetCapabilities_POST_JSON = 0
                stats.ESRI_BusStops_IntersectFilter_GET_JSON = 0
                stats.ESRI_BusStops_IntersectFilter_POST_JSON = 0
                stats.ESRI_BusStops_Small_GET_JSON = 0
                stats.ESRI_BusStops_Small_POST_JSON = 0
                stats.ESRI_Topo_Big_POST_Image = 0
                stats.ESRI_Topo_Small_GET_Image = 0
                stats.ESRI_Topo_Small_POST_Image = 0
                stats.GME_AerialPhoto_Big_GET_Image = 0
                stats.GME_AerialPhoto_GetTileKVP_GET_Image = 0
                stats.GME_AerialPhoto_GetTileKVP2_GET_Image = 0
                stats.GME_AerialPhoto_GetTileKVP3_GET_Image = 0
                stats.GME_AerialPhoto_GetTileKVP4_GET_Image = 0
                stats.GME_AerialPhoto_Small_GET_Image = 0
                stats.GME_AerialPhoto_WMSGetCapabilities_GET_XML = 0
                stats.GME_AerialPhoto_WMTSGetCapabilities_GET_XML = 0
                stats.GME_BusStops_AttributeFilter_GET_JSON = 0
                stats.GME_BusStops_Big_GET_JSON = 0
                stats.GME_BusStops_DistanceFilter_GET_JSON = 0
                stats.GME_BusStops_FeatureByID_GET_JSON = 0
                stats.GME_BusStops_IntersectFilter_GET_JSON = 0
                stats.GME_BusStops_Small_GET_JSON = 0
                stats.OGC_AerialPhoto_GetTileKVP_GET_Image = 0
                stats.OGC_AerialPhoto_GetTileRestful_GET_Image = 0
                stats.OGC_BusStops_AttributeFilter_GET_JSON = 0
                stats.OGC_BusStops_AttributeFilter_GET_XML = 0
                stats.OGC_BusStops_AttributeFilter_POST_JSON = 0
                stats.OGC_BusStops_AttributeFilter_POST_XML = 0
                stats.OGC_BusStops_Big_GET_JSON = 0
                stats.OGC_BusStops_Big_GET_XML = 0
                stats.OGC_BusStops_Big_POST_JSON = 0
                stats.OGC_BusStops_Big_POST_XML = 0
                stats.OGC_BusStops_FeatureByID_GET_JSON = 0
                stats.OGC_BusStops_FeatureByID_GET_XML = 0
                stats.OGC_BusStops_FeatureByID_POST_JSON = 0
                stats.OGC_BusStops_FeatureByID_POST_XML = 0
                stats.OGC_BusStops_GetCapabilities_GET_XML = 0
                stats.OGC_BusStops_GetCapabilities_POST_XML = 0
                stats.OGC_BusStops_IntersectFilter_GET_JSON = 0
                stats.OGC_BusStops_IntersectFilter_GET_XML = 0
                stats.OGC_BusStops_IntersectFilter_POST_JSON = 0
                stats.OGC_BusStops_IntersectFilter_POST_XML = 0
                stats.OGC_BusStops_Small_GET_JSON = 0
                stats.OGC_BusStops_Small_GET_XML = 0
                stats.OGC_BusStops_Small_POST_JSON = 0
                stats.OGC_BusStops_Small_POST_XML = 0
                stats.OGC_Topo_Big_GET_Image = 0
                stats.OGC_Topo_Small_GET_Image = 0
                stats.ESRI_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_AttributeFilter_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_Big_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_Big_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_FeatureByID_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_GetCapabilities_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_GetCapabilities_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_IntersectFilter_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_Small_GET_JSON_ReferenceSuccess = 0
                stats.ESRI_BusStops_Small_POST_JSON_ReferenceSuccess = 0
                stats.ESRI_Topo_Big_POST_Image_ReferenceSuccess = 0
                stats.ESRI_Topo_Small_GET_Image_ReferenceSuccess = 0
                stats.ESRI_Topo_Small_POST_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_Big_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_GetTileKVP_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_GetTileKVP2_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_GetTileKVP3_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_GetTileKVP4_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_Small_GET_Image_ReferenceSuccess = 0
                stats.GME_AerialPhoto_WMSGetCapabilities_GET_XML_ReferenceSuccess = 0
                stats.GME_AerialPhoto_WMTSGetCapabilities_GET_XML_ReferenceSuccess = 0
                stats.GME_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = 0
                stats.GME_BusStops_Big_GET_JSON_ReferenceSuccess = 0
                stats.GME_BusStops_DistanceFilter_GET_JSON_ReferenceSuccess = 0
                stats.GME_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = 0
                stats.GME_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = 0
                stats.GME_BusStops_Small_GET_JSON_ReferenceSuccess = 0
                stats.OGC_AerialPhoto_GetTileKVP_GET_Image_ReferenceSuccess = 0
                stats.OGC_AerialPhoto_GetTileRestful_GET_Image_ReferenceSuccess = 0
                stats.OGC_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_AttributeFilter_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_AttributeFilter_POST_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_AttributeFilter_POST_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_Big_GET_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_Big_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_Big_POST_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_Big_POST_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_FeatureByID_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_FeatureByID_POST_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_FeatureByID_POST_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_GetCapabilities_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_GetCapabilities_POST_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_IntersectFilter_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_IntersectFilter_POST_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_IntersectFilter_POST_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_Small_GET_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_Small_GET_XML_ReferenceSuccess = 0
                stats.OGC_BusStops_Small_POST_JSON_ReferenceSuccess = 0
                stats.OGC_BusStops_Small_POST_XML_ReferenceSuccess = 0
                stats.OGC_Topo_Big_GET_Image_ReferenceSuccess = 0
                stats.OGC_Topo_Small_GET_Image_ReferenceSuccess = 0

            # Loop through all the TestMasters and their children
            # creating database records and updating stats as we go.
            for TM in dictResults.get('TestMasters', []):
                # print TM
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
                    # print TE
                    testEndpoint = TestEndpoint(parent=masterKey)

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
                    testEndpoint.responseData = TE.get('responseData', '')
                    testEndpoint.errorResponse = TE.get('errorResponse')
                    testEndpoint.analysed = AnalysisEnum.UNANALYSED

                    stats.countTestEndpoints += 1
                    stats.totalTestEndpointTime += (TE.get('finishDatetime') - TE.get('startDatetime'))
                    stats.countTestEndpointsSuccessful += testEndpoint.success

                    testString = testEndpoint.server + "_" + testEndpoint.dataset + "_" + testEndpoint.testName + "_" + testEndpoint.httpMethod + "_" + testEndpoint.returnType
                    print testString

                    if hasattr(stats, testString):
                        newValue = getattr(stats, testString) + 1
                        setattr(stats, testString, newValue)

                    listTestEndpoints.append(testEndpoint)

                    """No longer need to make concrete subclasses of
                    TestEndpoint as all three types store their responseData
                    in TextProperty()'s nowadays.'"""
                    # testEndpoint = None
                    # keys = TE.keys()
                    # if 'imageResponse' in keys:
                    #     testEndpoint = ImageEndpoint(parent=masterKey)
                    #     testEndpoint.imageResponse = str(TE.get('imageResponse'))
                    # elif 'xmlResponse' in keys:
                    #     testEndpoint = XmlEndpoint(parent=masterKey)
                    #     testEndpoint.xmlResponse = TE.get('xmlResponse')
                    # elif 'jsonResponse' in keys:
                    #     testEndpoint = JsonEndpoint(parent=masterKey)
                    #     testEndpoint.jsonResponse = TE.get('jsonResponse')
                    # elif 'responseData' in keys:
                    #     # There was no response to the original request (likely no connectivity)
                    #     # Here we set to a null json response.
                    #     testEndpoint = JsonEndpoint(parent=masterKey)
                    #     testEndpoint.jsonResponse = None
                    #
                    # if any(['imageResponse' in keys, 'xmlResponse' in keys, 'jsonResponse' in keys, 'responseData' in keys]):
                    #     testEndpoint.testID = TE.get('testID')
                    #     testEndpoint.parentID = TE.get('parentID')
                    #     testEndpoint.startDatetime = datetime.utcfromtimestamp(float(TE.get('startDatetime')))
                    #     testEndpoint.finishDatetime = datetime.utcfromtimestamp(float(TE.get('finishDatetime')))
                    #     testEndpoint.success = bool(TE.get('success'))
                    #     testEndpoint.comment = TE.get('comment')
                    #     testEndpoint.server = TE.get('server')
                    #     testEndpoint.dataset = TE.get('dataset')
                    #     testEndpoint.returnType = TE.get('returnType')
                    #     testEndpoint.testName = TE.get('testName')
                    #     testEndpoint.httpMethod = TE.get('httpMethod')
                    #     testEndpoint.testedURL = TE.get('testedURL')
                    #     testEndpoint.responseCode = int(TE.get('responseCode'))
                    #     testEndpoint.errorResponse = TE.get('errorResponse')
                    #     testEndpoint.analysed = AnalysisEnum.UNANALYSED
                    #
                    #     stats.countTestEndpoints += 1
                    #     stats.totalTestEndpointTime += (TE.get('finishDatetime') - TE.get('startDatetime'))
                    #     if testEndpoint.success:
                    #         stats.countTestEndpointsSuccessful += 1
                    #
                    #     listTestEndpoints.append(testEndpoint)

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
                    pingResult.pingTime = float(PR.get('pingTime'))

                    stats.countPingResults += 1
                    stats.countPingResultsSuccessful += pingResult.success
                    stats.totalPingTime += pingResult.pingTime

                    listPingResults.append(pingResult)

                # Push everything to database.
                # This is done at the end to help prevent orphaned objects
                # if the function hits an exception partway through.
                listTestEndpointKeys = ndb.put_multi(listTestEndpoints)
                listNetworkKeys = ndb.put_multi(listNetworkResults)
                listLocationKeys = ndb.put_multi(listLocationResults)
                listPingKeys = ndb.put_multi(listPingResults)
                stats.put()

                # Add an analysis task to the default queue for each
                # endpoint test completed.
                for endpoint in listTestEndpoints:
                    taskqueue.add(url='/analyse', method='GET', params={'campaignName': campaignName, 'testID': endpoint.testID})

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
        """Returns one TestMaster and its children tests.
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
                database_query = TestMaster.query(ancestor=campaignKey)
                listTestMasters = database_query.fetch(1)
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
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Sorry, JSON writing error condition ' +
                                'encountered!\nNo data for you!\n\n' +
                                e.message + '\n\n')
        else:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Deleted TestCampaign; ' + campaignName)


class StoreReferences(webapp2.RequestHandler):
    """A very simple class to add a task to the default task queue
    to store the referenceObjects in the folder.
    The idea being to let the app start task execution when the CPU is
    not under heavy load."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = ndb.Key(TestCampaign, campaignName)

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide ?campaignName=\n\n' +
                                e.message + '\n\n')
        else:
            taskqueue.add(url='/storereferencesworker', method='GET', params={'campaignName': campaignName})
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Task added to store referenceObjects for ' + campaignName)


class StoreReferencesWorker(webapp2.RequestHandler):
    """A class to copy reference objects from text files to the
    Google App Engine datastore. Only needed once, in theory."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = ndb.Key(TestCampaign, campaignName)

        except Exception as e:
            self.response.set_status(555, message="Custom error response code.")
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Missing or invalid parameter in request.\n' +
                                'Please provide ?campaignName=\n\n' +
                                e.message + '\n\n')
        else:
            # Get the path to this file and get the ReferenceObjects folder by
            # appending the extra folder path component.
            appPath = os.path.split(__file__)[0]
            referenceFolderPath = os.path.join(appPath, 'ReferenceObjects')

            for root, directories, filenames in os.walk(referenceFolderPath):
                for filename in filenames:
                    # Split the file into its name and extension
                    filenameParts = os.path.splitext(filename)

                    # If this is a text file proceed, otherwise skip.
                    if filenameParts[1].lower() == '.txt':
                        # Split the file name into all the test properties.
                        properties = filenameParts[0].split("_")

                        # Check whether a referenceObject already exists for
                        # this test, if so we'll overwrite instead.
                        referenceObject = None

                        referenceObject = ReferenceObject.query(ReferenceObject.server == properties[0], ReferenceObject.dataset == properties[1], ReferenceObject.name == properties[2], ReferenceObject.httpMethod == properties[3], ReferenceObject.returnType == properties[4]).get()

                        if referenceObject is None:
                            # There is no pre-existing referenceObject
                            # go ahead and create a new one.
                            referenceObject = ReferenceObject(parent=campaignKey)

                            referenceObject.server = properties[0]
                            referenceObject.dataset = properties[1]
                            referenceObject.name = properties[2]
                            referenceObject.httpMethod = properties[3]
                            referenceObject.returnType = properties[4]

                        # Join the filename to the root directory path
                        referenceFilePath = os.path.join(root, filename)

                        # Read the file contents into the referenceText property
                        with open(referenceFilePath, 'r') as referenceText:
                            referenceObject.reference = referenceText.read()

                        # Store the new data.
                        key = referenceObject.put()

            # Complete success, write output.
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Stored referenceObjects for ' + campaignName)



class Analyse(webapp2.RequestHandler):
    """A class that takes the point based information in each of the
    EndpointTests, LocationTests, NetworkTests and PingTests and
    combines them into line objects called Vectors.
    Each Vector consists of the two LocationTests either side of an
    EndpointTest, determining distance, speed and direction. It gains
    PingTest and NetworkTest results as a vector of, constant, improving
    or degrading signal. The EndpointResult in the middle is the focus,
    its outcomes being compared to the motion and changing signal environment
    of the Vector.
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
                    preTestLocation = LocationResult.query(ancestor=testMaster.key).filter(LocationResult.datetime < testEndpoint.startDatetime).order(-LocationResult.datetime).get()
                    # print preTestLocation

                    postTestLocation = LocationResult.query(ancestor=testMaster.key).filter(LocationResult.datetime > testEndpoint.finishDatetime).order(LocationResult.datetime).get()
                    # print postTestLocation

                    preTestNetwork = NetworkResult.query(ancestor=testMaster.key).filter(NetworkResult.datetime < testEndpoint.startDatetime).order(-NetworkResult.datetime).get()
                    # print preTestNetwork

                    postTestNetwork = NetworkResult.query(ancestor=testMaster.key).filter(NetworkResult.datetime > testEndpoint.finishDatetime).order(NetworkResult.datetime).get()
                    # print postTestNetwork

                    preTestPing = PingResult.query(ancestor=testMaster.key).filter(PingResult.datetime < testEndpoint.startDatetime).order(-PingResult.datetime).get()
                    # print preTestPing

                    postTestPing = PingResult.query(ancestor=testMaster.key).filter(PingResult.datetime > testEndpoint.finishDatetime).order(PingResult.datetime).get()
                    # print postTestPing

                    # Each TestEndpoint should have a LocationTest, NetworkTest and
                    # PingTest before AND afterwards, if all six are present proceed
                    if preTestLocation and postTestLocation and preTestNetwork and postTestNetwork and preTestPing and postTestPing:
                        # Create a new Vector analysis data structure.
                        vector = Vector(parent=campaignKey)

                        # Assign all the TestEndpoint's relevant attributes to Vector
                        vector.test = testEndpoint
                        vector.name = testEndpoint.testName
                        vector.startDateTime = testEndpoint.startDatetime
                        vector.finishDateTime = testEndpoint.finishDatetime
                        vector.responseTime = (testEndpoint.finishDatetime - testEndpoint.startDatetime).total_seconds()
                        vector.server = testEndpoint.server
                        vector.dataset = testEndpoint.dataset
                        vector.httpMethod = testEndpoint.httpMethod
                        vector.returnType = testEndpoint.returnType
                        vector.responseCode = testEndpoint.responseCode
                        vector.onDeviceSuccess = testEndpoint.success

                        # Get the 'True' referenceObject from the store
                        referenceObject = ReferenceObject.query(ReferenceObject.server == vector.server, ReferenceObject.dataset == vector.dataset, ReferenceObject.name == vector.name, ReferenceObject.httpMethod == vector.httpMethod, ReferenceObject.returnType == vector.returnType).get()

                        vectorString = vector.server + "_" + vector.dataset + "_" + vector.name + "_" + vector.httpMethod + "_" + vector.returnType + "_ReferenceSuccess"

                        # Default to false for reference check truthiness.
                        vector.referenceCheckSuccess = False

                        # Check whether the referenceObject's text can
                        # be found in the testEndpoint's response.
                        if referenceObject is not None:
                            responseData = testEndpoint.responseData.encode('ascii', 'ignore').replace('\r\n', '').replace('\n', '').replace(' ', '').replace('   ', '')
                            reference = referenceObject.reference.encode('ascii', 'ignore').replace('\r\n', '').replace('\n', '').replace(' ', '').replace('   ', '')
                            if responseData in reference:
                                vector.referenceCheckSuccess = True

                        print vector.referenceCheckSuccess

                        stats_query = CampaignStats.query(CampaignStats.campaignName == campaignName)
                        stats = stats_query.get()

                        if hasattr(stats, vectorString):
                            newValue = getattr(stats, vectorString) +  vector.referenceCheckSuccess
                            print 'Setting referenceCheckSuccess on Stats; ' + str(newValue)
                            setattr(stats, vectorString, newValue)
                            stats.put()

                        # Assign the TestMaster's attributes
                        vector.deviceType = testMaster.deviceType
                        vector.deviceID = testMaster.deviceID
                        vector.iOSVersion = testMaster.iOSVersion

                        # Assign all the supporting tests to the Vector
                        vector.preTestLocation = preTestLocation
                        vector.postTestLocation = postTestLocation
                        vector.preTestNetwork = preTestNetwork
                        vector.postTestNetwork = postTestNetwork
                        vector.preTestPing = preTestPing
                        vector.postTestPing = postTestPing

                        # Calculate the change in environment during the test
                        location1 = vector.preTestLocation.location
                        location2 = vector.postTestLocation.location
                        vector.distance = HaversineDistance(location1, location2)

                        vector.speed = vector.distance / (postTestLocation.datetime - preTestLocation.datetime).total_seconds()

                        vector.pingChange = vector.preTestPing.pingTime - vector.postTestPing.pingTime

                        vector.networkChange = (NetworkClass(vector.postTestNetwork.connectionType) - NetworkClass(vector.preTestNetwork.connectionType))

                        # All being well, we mark the testEndpoint object with
                        # the analysis SUCCESSFUL enum and put it back.
                        testEndpoint.analysed = AnalysisEnum.SUCCESSFUL
                        endpointKey = testEndpoint.put()

                        # Store the Vector object.
                        vectorKey = vector.put()
                        print "Analysis SUCCESSFUL"

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
                        print "Analysis IMPOSSIBLE"

                        self.response.headers['Content-Type'] = 'text/plain'
                        self.response.write('Sorry, analysis is impossible ' +
                                            'for this endpoint test!\n\n')

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, analysis exception condition ' +
                                    'encountered!\nAnalysis aborted!\n\n' +
                                    e.message + '\n\n')


def percentCalculator(stats, key):
    """Calculates the percentage successful for reference checks.
    The intention being to completely disregard test types with
    0% reference check success rates. Assuming a process or
    logic error."""
    successfulKey = key + '_ReferenceSuccess'

    countReferences = getattr(stats, key)
    countReferencesSuccessful = getattr(stats, successfulKey)

    percentSuccessful = 0.0

    if countReferences is not None and countReferencesSuccessful is not None and countReferences != 0:
        percentSuccessful = ((countReferencesSuccessful * 1.0) / (countReferences * 1.0)) * 100

    return percentSuccessful


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

                print campaignName

                stats = CampaignStats.query(CampaignStats.campaignName == campaignName).get()

                print stats

                if stats is not None:
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
                    dictStats['averagePingTime'] = stats.totalPingTime / (stats.countPingResultsSuccessful * 1.0)
                    dictStats['percentPingTestsSuccessful'] = ((stats.countPingResultsSuccessful * 1.0) / (stats.countPingResults * 1.0)) * 100
                    dictStats['ESRI_BusStops_AttributeFilter_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_AttributeFilter_GET_JSON')
                    dictStats['ESRI_BusStops_AttributeFilter_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_AttributeFilter_POST_JSON')
                    dictStats['ESRI_BusStops_Big_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_Big_GET_JSON')
                    dictStats['ESRI_BusStops_Big_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_Big_POST_JSON')
                    dictStats['ESRI_BusStops_FeatureByID_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_FeatureByID_GET_JSON')
                    dictStats['ESRI_BusStops_FeatureByID_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_FeatureByID_POST_JSON')
                    dictStats['ESRI_BusStops_GetCapabilities_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_GetCapabilities_GET_JSON')
                    dictStats['ESRI_BusStops_GetCapabilities_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_GetCapabilities_POST_JSON')
                    dictStats['ESRI_BusStops_IntersectFilter_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_IntersectFilter_GET_JSON')
                    dictStats['ESRI_BusStops_IntersectFilter_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_IntersectFilter_POST_JSON')
                    dictStats['ESRI_BusStops_Small_GET_JSON'] = percentCalculator(stats, 'ESRI_BusStops_Small_GET_JSON')
                    dictStats['ESRI_BusStops_Small_POST_JSON'] = percentCalculator(stats, 'ESRI_BusStops_Small_POST_JSON')
                    dictStats['ESRI_Topo_Big_POST_Image'] = percentCalculator(stats, 'ESRI_Topo_Big_POST_Image')
                    dictStats['ESRI_Topo_Small_GET_Image'] = percentCalculator(stats, 'ESRI_Topo_Small_GET_Image')
                    dictStats['ESRI_Topo_Small_POST_Image'] = percentCalculator(stats, 'ESRI_Topo_Small_POST_Image')
                    dictStats['GME_AerialPhoto_Big_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_Big_GET_Image')
                    dictStats['GME_AerialPhoto_GetTileKVP_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_GetTileKVP_GET_Image')
                    dictStats['GME_AerialPhoto_GetTileKVP2_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_GetTileKVP2_GET_Image')
                    dictStats['GME_AerialPhoto_GetTileKVP3_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_GetTileKVP3_GET_Image')
                    dictStats['GME_AerialPhoto_GetTileKVP4_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_GetTileKVP4_GET_Image')
                    dictStats['GME_AerialPhoto_Small_GET_Image'] = percentCalculator(stats, 'GME_AerialPhoto_Small_GET_Image')
                    dictStats['GME_AerialPhoto_WMSGetCapabilities_GET_XML'] = percentCalculator(stats, 'GME_AerialPhoto_WMSGetCapabilities_GET_XML')
                    dictStats['GME_AerialPhoto_WMTSGetCapabilities_GET_XML'] = percentCalculator(stats, 'GME_AerialPhoto_WMTSGetCapabilities_GET_XML')
                    dictStats['GME_BusStops_AttributeFilter_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_AttributeFilter_GET_JSON')
                    dictStats['GME_BusStops_Big_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_Big_GET_JSON')
                    dictStats['GME_BusStops_DistanceFilter_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_DistanceFilter_GET_JSON')
                    dictStats['GME_BusStops_FeatureByID_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_FeatureByID_GET_JSON')
                    dictStats['GME_BusStops_IntersectFilter_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_IntersectFilter_GET_JSON')
                    dictStats['GME_BusStops_Small_GET_JSON'] = percentCalculator(stats, 'GME_BusStops_Small_GET_JSON')
                    dictStats['OGC_AerialPhoto_GetTileKVP_GET_Image'] = percentCalculator(stats, 'OGC_AerialPhoto_GetTileKVP_GET_Image')
                    dictStats['OGC_AerialPhoto_GetTileRestful_GET_Image'] = percentCalculator(stats, 'OGC_AerialPhoto_GetTileRestful_GET_Image')
                    dictStats['OGC_BusStops_AttributeFilter_GET_JSON'] = percentCalculator(stats, 'OGC_BusStops_AttributeFilter_GET_JSON')
                    dictStats['OGC_BusStops_AttributeFilter_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_AttributeFilter_GET_XML')
                    dictStats['OGC_BusStops_AttributeFilter_POST_JSON'] = percentCalculator(stats, 'OGC_BusStops_AttributeFilter_POST_JSON')
                    dictStats['OGC_BusStops_AttributeFilter_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_AttributeFilter_POST_XML')
                    dictStats['OGC_BusStops_Big_GET_JSON'] = percentCalculator(stats, 'OGC_BusStops_Big_GET_JSON')
                    dictStats['OGC_BusStops_Big_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_Big_GET_XML')
                    dictStats['OGC_BusStops_Big_POST_JSON'] = percentCalculator(stats, 'OGC_BusStops_Big_POST_JSON')
                    dictStats['OGC_BusStops_Big_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_Big_POST_XML')
                    dictStats['OGC_BusStops_FeatureByID_GET_JSON'] = percentCalculator(stats, 'OGC_BusStops_FeatureByID_GET_JSON')
                    dictStats['OGC_BusStops_FeatureByID_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_FeatureByID_GET_XML')
                    dictStats['OGC_BusStops_FeatureByID_POST_JSON'] = percentCalculator(stats, 'OGC_BusStops_FeatureByID_POST_JSON')
                    dictStats['OGC_BusStops_FeatureByID_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_FeatureByID_POST_XML')
                    dictStats['OGC_BusStops_GetCapabilities_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_GetCapabilities_GET_XML')
                    dictStats['OGC_BusStops_GetCapabilities_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_GetCapabilities_POST_XML')
                    dictStats['OGC_BusStops_IntersectFilter_GET_JSON'] = percentCalculator(stats, 'OGC_BusStops_IntersectFilter_GET_JSON')
                    dictStats['OGC_BusStops_IntersectFilter_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_IntersectFilter_GET_XML')
                    dictStats['OGC_BusStops_IntersectFilter_POST_JSON'] = percentCalculator(stats, 'OGC_BusStops_IntersectFilter_POST_JSON')
                    dictStats['OGC_BusStops_IntersectFilter_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_IntersectFilter_POST_XML')
                    dictStats['OGC_BusStops_Small_GET_JSON'] = percentCalculator(stats, 'OGC_BusStops_Small_GET_JSON')
                    dictStats['OGC_BusStops_Small_GET_XML'] = percentCalculator(stats, 'OGC_BusStops_Small_GET_XML')
                    dictStats['OGC_BusStops_Small_POST_JSON'] = percentCalculator(stats, 'OGC_BusStops_Small_POST_JSON')
                    dictStats['OGC_BusStops_Small_POST_XML'] = percentCalculator(stats, 'OGC_BusStops_Small_POST_XML')
                    dictStats['OGC_Topo_Big_GET_Image'] = percentCalculator(stats, 'OGC_Topo_Big_GET_Image')
                    dictStats['OGC_Topo_Small_GET_Image'] = percentCalculator(stats, 'OGC_Topo_Small_GET_Image')

                else:
                    dictStats['campaignName'] = "No campaign found!"


                self.response.headers['Content-Type'] = 'application/json'
                self.response.write(json.dumps(dictStats, indent=4, cls=CustomEncoder))

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, JSON writing error condition ' +
                                    'encountered!\nNo data for you!\n\n' +
                                    e.message + '\n\n')


"""Creates a pie chart with the supplied property."""
def pieCharter(figureArg, colourMap, campaign, chartProperty):
    listVectors = Vector.query(ancestor=campaign, projection=[Vector._properties[chartProperty]]).fetch()
    listProperty = [getattr(vector, chartProperty) for vector in listVectors]
    listNames = list(set(listProperty))
    listCounts = [listProperty.count(server) for server in listNames]
    listColours = colourMap(numpy.linspace(0., 1., len(listNames)))

    ax = figureArg.add_subplot(1, 1, 1)
    listPieWedges = ax.pie(listCounts, labels=listNames, colors=listColours,  autopct='%1.1f%%', startangle=90)
    ax.set_aspect('equal')

    for wedge in listPieWedges[0]:
        wedge.set_edgecolor('white')
        wedge.set_linewidth(4.0)

    return ax

"""Calculates R Squared value for a set of coefficients."""
def calculateRSquared(coeffs, x, y):
    """Adapted from leif's answer on StackOverflow, found here;
    http://stackoverflow.com/questions/893657/how-do-i-calculate-r-squared-using-python-and-numpy"""
    p = numpy.poly1d(coeffs)
    # fit values, and mean
    yhat = p(x)
    ybar = numpy.sum(y)/len(y)
    ssreg = numpy.sum((yhat-ybar)**2)
    sstot = numpy.sum((y - ybar)**2)
    return ssreg / sstot

"""Creates a scatter plot for two supplied properties.
Divides them up by succeeded and failed tests (failures being those
that either failed on device or failed their reference check).
Then Performs OLS linear regression on each set of scatters and overlays
the line of best fit on the chart."""
def scatterCharter(figureArg, campaign, chartXProperty, chartYProperty):
    listVectors = Vector.query(ancestor=campaign, projection=[Vector._properties[chartXProperty], Vector._properties[chartYProperty], Vector.onDeviceSuccess, Vector.referenceCheckSuccess]).fetch()

    listAll = [(getattr(vector, chartXProperty), getattr(vector, chartYProperty), vector.onDeviceSuccess, vector.referenceCheckSuccess) for vector in listVectors]
    listSuccesses = [vector for vector in listAll if vector[2] and vector[3]]
    listFailures = [vector for vector in listAll if not vector[2] and vector[3]]

    ax = figureArg.add_subplot(1, 1, 1)

    xSuccess = numpy.array([vector[0] for vector in listSuccesses])
    ySuccess = numpy.array([vector[1] for vector in listSuccesses])
    ax.scatter(xSuccess, ySuccess, c='green')
    fitSuccess = numpy.polyfit(xSuccess, ySuccess, deg=1)
    rSquaredSuccess = calculateRSquared(fitSuccess, xSuccess, ySuccess)
    print rSquaredSuccess
    labelSuccess = 'Success, r squared = ' + str(round(rSquaredSuccess, 2))
    ax.plot(xSuccess, fitSuccess[0] * xSuccess + fitSuccess[1], color='green', linestyle='dashed', label=labelSuccess)

    xFailure = numpy.array([vector[0] for vector in listFailures])
    yFailure = numpy.array([vector[1] for vector in listFailures])
    ax.scatter(xFailure, yFailure, c='red')
    fitFailure = numpy.polyfit(xFailure, yFailure, deg=1)
    rSquaredFailure = calculateRSquared(fitFailure, xFailure, yFailure)
    print rSquaredFailure
    labelFailure = 'Failure, r squared = ' + str(round(rSquaredFailure, 2))
    ax.plot(xFailure, fitFailure[0] * xFailure + fitFailure[1], color='red', linestyle='dashed', label=labelFailure)
    ax.legend(loc='best')

    return ax

class GraphsPage(webapp2.RequestHandler):
    """"A page that produces a graph for a given campaign.
    The request must specify which of the graph types they want returned.
    Graphs generated from latest available data using the Python
    matplotlib library."""
    def get(self):
        try:
            campaignName = self.request.get('campaignName')
            campaignKey = getCampaignKey(campaignName)
            graphName = self.request.get('graphName').lower()
            if graphName not in ('graph1', 'graph2', 'graph3', 'graph4', 'graph5', 'graph6', 'graph7', 'graph8', 'graph9', 'graph10', 'graph11', 'graph12', 'graph13', 'graph14'):
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
                fig = Figure()
                canvas = FigureCanvas(fig)
                cmap = cm.Pastel2

                if graphName == 'graph1':
                    ax = pieCharter(fig, cmap, campaignKey, 'server')

                elif graphName == 'graph2':
                    ax = pieCharter(fig, cmap, campaignKey, 'httpMethod')

                elif graphName == 'graph3':
                    ax = pieCharter(fig, cmap, campaignKey, 'name')

                elif graphName == 'graph4':
                    ax = pieCharter(fig, cmap, campaignKey, 'returnType')

                elif graphName == 'graph5':
                    ax = pieCharter(fig, cmap, campaignKey, 'responseCode')

                elif graphName == 'graph6':
                    ax = pieCharter(fig, cmap, campaignKey, 'onDeviceSuccess')

                elif graphName == 'graph7':
                    ax = pieCharter(fig, cmap, campaignKey, 'referenceCheckSuccess')

                elif graphName == 'graph8':
                    ax = pieCharter(fig, cmap, campaignKey, 'deviceType')

                elif graphName == 'graph9':
                    ax = pieCharter(fig, cmap, campaignKey, 'iOSVersion')

                elif graphName == 'graph10':
                    ax = pieCharter(fig, cmap, campaignKey, 'deviceID')

                elif graphName == 'graph11':
                    ax = scatterCharter(fig, campaignKey, 'speed', 'responseTime')

                    ax.set_xlim(0.01, 100.0)
                    ax.set_ylim(0.01, 100.0)
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel("Speed (m/s)")
                    ax.set_ylabel("Response Time (seconds)")
                    ax.set_title("Device Speed versus Response Time")
                    ax.legend()

                elif graphName == 'graph12':
                    ax = scatterCharter(fig, campaignKey, 'distance', 'responseTime')

                    ax.set_xlim(0.01, 1000.0)
                    ax.set_ylim(0.01, 100.0)
                    ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel("Distance (m)")
                    ax.set_ylabel("Response Time (seconds)")
                    ax.set_title("Device Distance Travelled versus Response Time")
                    ax.legend()

                elif graphName == 'graph13':
                    ax = scatterCharter(fig, campaignKey, 'networkChange', 'responseTime')

                    # ax.set_xlim(0.01, 100.0)
                    # ax.set_ylim(0.01, 100.0)
                    # ax.set_xscale('log')
                    # ax.set_yscale('log')
                    ax.set_xlabel("Network Class Change")
                    ax.set_ylabel("Response Time (seconds)")
                    ax.set_title("Network Class Change versus Response Time")
                    ax.legend()

                elif graphName == 'graph14':
                    ax = scatterCharter(fig, campaignKey, 'pingChange', 'responseTime')

                    # ax.set_xlim(0.01, 100.0)
                    # ax.set_ylim(0.01, 100.0)
                    # ax.set_xscale('log')
                    ax.set_yscale('log')
                    ax.set_xlabel("Ping Response Time Change")
                    ax.set_ylabel("Response Time (seconds)")
                    ax.set_title("Ping Response Time Change versus Response Time")
                    ax.legend()

                strOutput = cStringIO.StringIO()
                fig.savefig(strOutput, format="svg")
                graphImage = strOutput.getvalue()

                self.response.headers['Content-Type'] = 'text/html'
                # self.response.write("""<html><head/><body>""")
                self.response.write(graphImage)
                # self.response.write("""</body> </html>""")

                # canvas.close()

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
    ('/storereferences', StoreReferences),
    ('/storereferencesworker', StoreReferencesWorker),
    ('/analyse', Analyse),
    ('/stats', StatsPage),
    ('/graphs', GraphsPage)
], debug=True)
