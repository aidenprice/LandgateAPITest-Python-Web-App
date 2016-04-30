""" LandgateAPITest Web App

Map plotting module

Created by Aiden Price,
Curtin University Masters of Geospatial Science candidate,
Submitted June 2016"""

# Libraries available on Google cloud service.
import webapp2

# Google's appengine python libraries.
from google.appengine.ext import ndb

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

PRETEXT = "<!DOCTYPE html><html><head><title>LandgateAPITest Web Map</title><link rel='stylesheet' href='https://cdn.jsdelivr.net/leaflet/1.0.0-rc.1/leaflet.css' /><script src='https://cdn.jsdelivr.net/leaflet/1.0.0-rc.1/leaflet-src.js'></script><style>html, body {height: 100%; width: 100%; }#map { width: 100%; height: 100%; }</style></head><body><div id='map'></div><script src='https://rawgit.com/Leaflet/Leaflet.heat/gh-pages/dist/leaflet-heat.js'></script><script>var map = L.map('map').setView([-27, 148], 5);var tiles = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {attribution: '&copy; <a href=\"http://osm.org/copyright\">OpenStreetMap</a> contributors',}).addTo(map);testPoints = "

POSTTEXT = ';var heat = L.heatLayer(testPoints).addTo(map);</script></body></html>'

def getCampaignKey(database_name=DEFAULT_CAMPAIGN_NAME):
    key = ndb.Key(TestCampaign, database_name)
    if key is None:
        return TestCampaign(key=database_name, campaignName=database_name).put()
    else:
        return key


class MapPlotter(webapp2.RequestHandler):
    """Returns an interactive Leaflet map with the locations."""
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
                listVectors = Vector.query(ancestor=campaignKey, projection=[Vector.preTestLocation.location]).fetch()
                listLatsAndLongs = [[vector.preTestLocation.location.lat, vector.preTestLocation.location.lon, 1.0] for vector in listVectors]

                outString = PRETEXT + str(listLatsAndLongs) + POSTTEXT
                print outString
                self.response.headers['Content-Type'] = 'text/html'
                self.response.write(outString)

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, mapping error condition ' +
                                    'encountered!\nNo map for you!\n\n' +
                                    e.message + '\n\n')


class StaticMapPlotter(webapp2.RequestHandler):
    """Returns a static Leaflet map with the locations."""
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
                listVectors = Vector.query(ancestor=campaignKey, projection=[Vector.preTestLocation.location]).fetch()
                listLatsAndLongs = [[vector.preTestLocation.location.lat, vector.preTestLocation.location.lon, 1.0] for vector in listVectors]

                outString = PRETEXT + str(listLatsAndLongs) + POSTTEXT
                print outString
                self.response.headers['Content-Type'] = 'text/html'
                self.response.write(outString)

            except Exception as e:
                self.response.set_status(555, message="Custom error response code.")
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write('Sorry, mapping error condition ' +
                                    'encountered!\nNo map for you!\n\n' +
                                    e.message + '\n\n')


# WSGI app
# Handles incoming requests according to supplied URL.
app = webapp2.WSGIApplication([
    ('/map', MapPlotter),
    ('/staticmap', StaticMapPlotter)
], debug=True)
