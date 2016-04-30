
# Google's appengine python libraries.
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

# Model classes

class TestCampaign(ndb.Model):
    """TestCampaign is a superclass meant to link many TestMasters
    by a single parent ID."""
    campaignName = ndb.StringProperty()


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
    # endpointResults - a list of TestEndpoint subclass objects, normally dozens of them.
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
    responseData = ndb.TextProperty()
    errorResponse = ndb.StringProperty()
    analysed = ndb.IntegerProperty()

"""Previously we needed separate subclasses of each TestEndpoint response
type as their responseData were stored in different properties
(JsonProperty(), ImageProperty() and StringProperty()).
It was recently discovered that the best method is make them all
TextProperty()'s so concrete subclasses aren't necessary anymore."""
# sub-subclasses for json, xml, images
# class ImageEndpoint(TestEndpoint):
#     """An API endpoint test designed to return an image for example a WMTS call
#     returning a map tile.
#     Importantly, in order to transmit images in JSON we must first convert them
#     to 64 bit text. We keep them in this format for ease of comparison to
#     a reference copy of the image, and we do not plan to display images."""
#     imageResponse = ndb.TextProperty()
#
#
# class XmlEndpoint(TestEndpoint):
#     """A concrete class designed to hold a GML response from
#     a test on an OGC API endpoint."""
#     xmlResponse = ndb.TextProperty()
#
#
# class JsonEndpoint(TestEndpoint):
#     """A concrete class to hold the JSON response from a
#     test on a GeoJSON or EsriJson API endpoint.
#     There is an ndb.JsonProperty object sounds perfect for this use case.
#     Unfortunately, we can not be assured of receiving well formed JSON
#     and must store incomplete JSON returns as well as complete ones."""
#     jsonResponse = ndb.TextProperty()


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
    pingTime = ndb.FloatProperty()


class ReferenceObject(ndb.Model):
    """An object with a 'True' version of the response for a single
    endpoint request."""
    server = ndb.StringProperty()
    dataset = ndb.StringProperty()
    name = ndb.StringProperty()
    httpMethod  = ndb.StringProperty()
    returnType = ndb.StringProperty()
    reference = ndb.TextProperty()


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

    name = ndb.StringProperty()
    startDateTime = ndb.DateTimeProperty()
    finishDateTime = ndb.DateTimeProperty()
    responseTime = ndb.FloatProperty()
    deviceType = ndb.StringProperty()
    deviceID = ndb.StringProperty()
    iOSVersion = ndb.StringProperty()
    server = ndb.StringProperty()
    dataset = ndb.StringProperty()
    httpMethod = ndb.StringProperty()
    returnType = ndb.StringProperty()
    responseCode = ndb.IntegerProperty()
    onDeviceSuccess = ndb.BooleanProperty()
    referenceCheckSuccess = ndb.BooleanProperty()

    preTestLocation = ndb.StructuredProperty(LocationResult)
    postTestLocation = ndb.StructuredProperty(LocationResult)
    preTestNetwork = ndb.StructuredProperty(NetworkResult)
    postTestNetwork = ndb.StructuredProperty(NetworkResult)
    preTestPing = ndb.StructuredProperty(PingResult)
    postTestPing = ndb.StructuredProperty(PingResult)

    distance = ndb.FloatProperty()
    speed = ndb.FloatProperty()

    pingChange = ndb.FloatProperty()
    networkChange = ndb.FloatProperty()


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
    countPingResultsSuccessful = ndb.IntegerProperty()
    totalPingTime = ndb.FloatProperty()
    ESRI_BusStops_AttributeFilter_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_AttributeFilter_POST_JSON = ndb.IntegerProperty()
    ESRI_BusStops_Big_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_Big_POST_JSON = ndb.IntegerProperty()
    ESRI_BusStops_FeatureByID_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_FeatureByID_POST_JSON = ndb.IntegerProperty()
    ESRI_BusStops_GetCapabilities_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_GetCapabilities_POST_JSON = ndb.IntegerProperty()
    ESRI_BusStops_IntersectFilter_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_IntersectFilter_POST_JSON = ndb.IntegerProperty()
    ESRI_BusStops_Small_GET_JSON = ndb.IntegerProperty()
    ESRI_BusStops_Small_POST_JSON = ndb.IntegerProperty()
    ESRI_Topo_Big_POST_Image = ndb.IntegerProperty()
    ESRI_Topo_Small_GET_Image = ndb.IntegerProperty()
    ESRI_Topo_Small_POST_Image = ndb.IntegerProperty()
    GME_AerialPhoto_Big_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP2_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP3_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP4_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_Small_GET_Image = ndb.IntegerProperty()
    GME_AerialPhoto_WMSGetCapabilities_GET_XML = ndb.IntegerProperty()
    GME_AerialPhoto_WMTSGetCapabilities_GET_XML = ndb.IntegerProperty()
    GME_BusStops_AttributeFilter_GET_JSON = ndb.IntegerProperty()
    GME_BusStops_Big_GET_JSON = ndb.IntegerProperty()
    GME_BusStops_DistanceFilter_GET_JSON = ndb.IntegerProperty()
    GME_BusStops_FeatureByID_GET_JSON = ndb.IntegerProperty()
    GME_BusStops_IntersectFilter_GET_JSON = ndb.IntegerProperty()
    GME_BusStops_Small_GET_JSON = ndb.IntegerProperty()
    OGC_AerialPhoto_GetTileKVP_GET_Image = ndb.IntegerProperty()
    OGC_AerialPhoto_GetTileRestful_GET_Image = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_GET_JSON = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_POST_JSON = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_POST_XML = ndb.IntegerProperty()
    OGC_BusStops_Big_GET_JSON = ndb.IntegerProperty()
    OGC_BusStops_Big_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_Big_POST_JSON = ndb.IntegerProperty()
    OGC_BusStops_Big_POST_XML = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_GET_JSON = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_POST_JSON = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_POST_XML = ndb.IntegerProperty()
    OGC_BusStops_GetCapabilities_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_GetCapabilities_POST_XML = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_GET_JSON = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_POST_JSON = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_POST_XML = ndb.IntegerProperty()
    OGC_BusStops_Small_GET_JSON = ndb.IntegerProperty()
    OGC_BusStops_Small_GET_XML = ndb.IntegerProperty()
    OGC_BusStops_Small_POST_JSON = ndb.IntegerProperty()
    OGC_BusStops_Small_POST_XML = ndb.IntegerProperty()
    OGC_Topo_Big_GET_Image = ndb.IntegerProperty()
    OGC_Topo_Small_GET_Image = ndb.IntegerProperty()
    ESRI_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_AttributeFilter_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_Big_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_Big_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_FeatureByID_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_GetCapabilities_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_GetCapabilities_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_IntersectFilter_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_Small_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_BusStops_Small_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_Topo_Big_POST_Image_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_Topo_Small_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    ESRI_Topo_Small_POST_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_Big_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP2_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP3_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_GetTileKVP4_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_Small_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_WMSGetCapabilities_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    GME_AerialPhoto_WMTSGetCapabilities_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_Big_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_DistanceFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    GME_BusStops_Small_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_AerialPhoto_GetTileKVP_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    OGC_AerialPhoto_GetTileRestful_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_AttributeFilter_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Big_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Big_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Big_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Big_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_FeatureByID_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_GetCapabilities_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_GetCapabilities_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_IntersectFilter_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Small_GET_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Small_GET_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Small_POST_JSON_ReferenceSuccess = ndb.IntegerProperty()
    OGC_BusStops_Small_POST_XML_ReferenceSuccess = ndb.IntegerProperty()
    OGC_Topo_Big_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
    OGC_Topo_Small_GET_Image_ReferenceSuccess = ndb.IntegerProperty()
