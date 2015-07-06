#!/usr/bin/python

import httplib2
import sys
import os
import BaseHTTPServer, SimpleHTTPServer
import SocketServer
import argparse
import json

from apiclient import errors
from apiclient.discovery import build
from datetime import datetime, timedelta
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
import logging
logging.basicConfig(filename='debug.log',level=logging.DEBUG)

import argparse
import json

class Server(BaseHTTPServer.HTTPServer):
	allow_reuse_address = True

class RedirectHandler(SimpleHTTPServer. SimpleHTTPRequestHandler):
	def do_GET(self):
		code = self.path.split('?')[1].split('code=')[1]
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		self.wfile.write("<html><head><title>oauth</title></head>")
		self.wfile.write("<body><p>Your code: %s</p>" % code)
		self.wfile.write("</body></html>")
		self.wfile.close()

parser = argparse.ArgumentParser(prog='PROG')
parser.add_argument('-a', '--application', help='[admin | docs | login | token]')
parser.add_argument('-s', '--start', help='How many days before you want to query')

arg = parser.parse_args()

application = arg.application
start=int(arg.start)+1

httpd = Server(('', 8888), RedirectHandler)
#Google Web Application Client ID in developer console
CLIENT_ID = '<client-id>'
# The client secret of this web application
CLIENT_SECRET = '<client-secret>'

# Check https://developers.google.com/admin-sdk/reports/v1/guides/authorizing for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/admin.reports.audit.readonly'

# Redirect URI for installed apps
REDIRECT_URI = 'http://localhost:8888/google/oauth2callback'
# Credentials file
storage = Storage('gapi-credentials')
credentials = storage.get()
# Create an httplib2.Http object and authorize it with our credentials
http = httplib2.Http()
if credentials:
	if credentials.access_token_expired:
		try:
			print '***** Token expired ******'
			credentials.refresh(http)
		except:
			print "Token refesh error"
			os.remove('gapi-credentials')
			sys.exit()
else:
	flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI, access_type='offline', approval_prompt='force')
	authorize_url = flow.step1_get_authorize_url()
	print 'Go to the following link in your browser: ' + authorize_url
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	code = raw_input('Enter verification code: ').strip()
	credentials = flow.step2_exchange(code)

http = credentials.authorize(http)
storage.put(credentials)

reports_service = build('admin', 'reports_v1', http=http)

# Set start time
time_shift = datetime.now() - timedelta(days=start) + timedelta(hours=8)
#time_shift = datetime.now() - timedelta(days=start)
start_time = time_shift.isoformat('T') + 'Z'

# Set today: 00:00:00.00 to be end time
now = datetime.now() + timedelta(hours=8)
#now = datetime.now()
now_str = str(now.year) + str(now.month) + str(now.day)
end_time = datetime.strptime(now_str, '%Y%m%d').isoformat('T') + 'Z'

all_logins = []
page_token = None
#Set Report params. Application name can change to: {Admin | token | doc} if you want.
params = {'applicationName': application, 'userKey': 'all', 'startTime': start_time, 'endTime': end_time}

while True:
	try:
		if page_token:
			param['pageToken'] = page_token
		current_page = reports_service.activities().list(**params).execute()

		all_logins.extend(current_page['items'])
		page_token = current_page.get('nextPageToken')
		if not page_token:
			break
	except errors.HttpError as error:
		print 'An error occurred: %s' % error
		break

for activity in all_logins:
	time_ = datetime.strptime(activity['id']['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
	print time_
	for event in activity['events']:
		print "===================================================="
		print json.dumps(event, separators=(',',':'))
		print "===================================================="
		print ""
