#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import SimpleHTTPServer

from os import curdir, sep
import cgi
import sys
import psycopg2
import json

def main():
	try:
		psql = connectToPostgres()
	except:
		print "could not connect to postgres"
		sys.exit(2)

	#startServer(psql)
	try:
		startServer(psql)
	except Exception as e:
		print e
		print "server died"
		sys.exit(2)

def connectToPostgres():
	try:
	    psql = psycopg2.connect("dbname='bikeability' user='alex' host='localhost' password=''")
	    return psql
	except Exception as e:
	    raise e

def validate(data):
	try:
		dataJSON = json.loads(data)
		print dataJSON

		if not ("lat" and "lng" and "description" and "category" in dataJSON):
			print "fields are improper"
			return False

		lat = float(dataJSON["lat"])
		lng = float(dataJSON["lng"])

		if not (lat >= -90 and lat <= 90 and lng <= 180 and lng >= -180):
			print "lat and lng not valid"
			return False
	except Exception as e:
		print e
		return False

	return True

def updatePostgres(data, psql):
	cur = psql.cursor()
	dataJSON = json.loads(data)

	lat = dataJSON['lat']
	lng = dataJSON['lng']
	description = dataJSON['description']
	category = dataJSON['category']

	try:
		cur.execute("insert into hazards values (%s, %s, %s, %s);", (lat, lng, str(description), str(category)));
		psql.commit()
		return True
	except Exception as e:
		print "failed to insert into psql"
		print e
		return False
 
def createRecord(data, psql, self):
	if validate(data):
		if updatePostgres(data, psql):
			self.send_response(200)
			self.finalise_headers()
			self.wfile.write("{}")
		else:
			self.send_response(500)
			self.finalise_headers()
			self.wfile.write("{}")
	else:
		self.send_response(400)
		self.finalise_headers()
		self.wfile.write("{}")

def pullPostgres(psql):
	cur = psql.cursor()
	#cur.execute("select * from hazards;")
	cur.execute("select row_to_json(t) from (select * from hazards) t")
	rows = cur.fetchall()
	data = '{"data": ['
	for index, row in enumerate(rows):
		end = len(row) - 2
		if (index == len(rows) - 1):
			end = len(row) - 3
		row = str(row)[1:end]
		#print row
		data += row
	data = data.replace("'", '"')
	data = data.replace('u"', '"')
	data += ']}'
	return data

def sendEverything(psql, self):
	data = pullPostgres(psql)
	if data:
		self.send_response(200)
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Content-type", "application/json")
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header("Access-Control-Allow-Headers", "Origin, Accept, X-Requested-With, Access-Control-Allow-Origin, Content-Type")
		self.end_headers()
		
		self.wfile.write(data)
		self.wfile.write('\n')
		return
	else:
		self.send_response(500)
		self.finalise_headers()
		self.wfile.write("{}")
		return

def startServer(psql):
	PORT_NUMBER = 8082

	class myHandler(BaseHTTPRequestHandler):
		def do_OPTIONS(self):
			self.send_response(200, "ok")
			self.send_header('Access-Control-Allow-Origin', '*')
			self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
			self.send_header("Access-Control-Allow-Headers", "Origin, Accept, X-Requested-With, Access-Control-Allow-Origin, Content-Type")

		def finalise_headers(self):
			self.send_header("Access-Control-Allow-Origin", "*")
			self.send_header("Access-Control-Expose-Headers", "Access-Control-Allow-Origin")
			self.send_header("Access-Control-Allow-Headers", "Origin, Accept, X-Requested-With, Access-Control-Allow-Origin, Content-Type")

		def do_GET(self):
			if self.path=="/hazards":
				print "got a GET"
				end = sendEverything(psql, self)
				return

		def do_POST(self):
			if self.path == "/hazards":
				print "got a POST"
				length = int(self.headers.getheader('content-length'))
				data = self.rfile.read(length)
				createRecord(data, psql, self)
				return			
				
	try:
		server = HTTPServer(('', PORT_NUMBER), myHandler)
		print 'Started httpserver on port' , PORT_NUMBER
		
		server.serve_forever()

	except KeyboardInterrupt as e:
		server.socket.close()
		raise e

if __name__ == "__main__":
	main()