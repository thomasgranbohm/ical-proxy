import re
import icalendar
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

rules = [
	("SUMMARY", [
		(", Undervisningstyp: ", " - "),
		("FÖ", "Föreläsning"),
		("GU", "Grupparbete"),
		("SE", "Seminarium"),
		("LE", "Lektion"),
		("WSHOP", "Workshop"),
		("LE", "Lektion"),
		("HA", "Handledning"),
		("DATALAB", "Datalabb"),
		("RE", "Redovisning"),
		("TMKT58", "Formgivning och formseende"),
		("TATA42", "Envariabelanalys 2"),
		("TATA41", "Envariabelanalys 1"),
		("TDDE33", "Användardriven produktutveckling"),
		("THEN18", "Engelska"),
	]),
	("LOCATION", [("Lokal: ", "")]),
	("DESCRIPTION", [
		(r"\nID \d+", ""),
		(r" \nLärare: ", ", "),
		(r" \nFöreläsning", "")
	])
]

cal = (
	"https://cloud.timeedit.net/liu/web/schema/ri617QQQY88Zn1Q5758709Z6y6Z06.ics",
	rules
)

hostName = "localhost"
serverPort = 8080

class MyServer(BaseHTTPRequestHandler):
	def do_GET(self):
		calendar = icalendar.Calendar.from_ical(requests.get(cal[0]).text)

		for event in calendar.walk("VEVENT"):
			for (t, transforms) in rules:
				for (i, o) in transforms:
					c = re.compile(i)
					event[t] = c.sub(o, event[t])

		self.send_response(200)
		self.send_header("Content-type", "text/calendar")
		self.end_headers()
		self.wfile.write(calendar.to_ical())

if __name__ == "__main__":		
	webServer = HTTPServer((hostName, serverPort), MyServer)

	try:
		webServer.serve_forever()
	except KeyboardInterrupt:
		pass

	webServer.server_close()
	print("Server stopped.")