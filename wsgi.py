# from flask import Flask, make_response
# import warnings
# import requests
import re
from icalendar import Calendar
import yaml

content = ""

with open("schedule.ics", "r", encoding="utf8") as schedule:
    content = schedule.read()

calendar = Calendar.from_ical(content)

component_name = "SUMMARY"


def generate_regex(field="SUMMARY"):
    with open(f"./rules/{field}.yaml", "r") as file:
        return yaml.safe_load(file)


for (i, ev) in enumerate(calendar.walk("VEVENT")):
    c = re.compile(
        "(?P<KURSKOD>([a-zA-Z0-9, ]+)), Undervisningstyp: (?P<UNDERVISNINGSTYP>[A-ö0-9]+),"
    )

    rules = generate_regex(component_name)
    groups = c.match(ev[component_name]).groupdict()

    data = {}
    passes_normally = True

    for group_name in groups:
        captured = groups[group_name]
        values = captured if len(captured.split(
            ", ")) == 1 else captured.split(", ")

        try:
            if rules[group_name] != None:
                if type(values) is str:
                    data[group_name] = rules[group_name][captured]
                else:
                    for v in values:
                        if v in rules[group_name]:
                            data[group_name] = rules[group_name][v]
                            break
        except:
            passes_normally = False

    if passes_normally:
        ev[component_name] = data["KURSKOD"] + " - " + data["UNDERVISNINGSTYP"]

f = open("transformed.ics", "w", encoding="utf8")
f.write(calendar.to_ical().decode("utf8"))
f.close()

# app = Flask(__name__)


# @app.route("/")
# def hello_world():
# 	 return "<p>Hello, World!</p>"


# @app.route("/calendar/<string:ical_id>")
# def get_calendar(ical_id):
# 	 calendar = icalendar.Calendar.from_ical(
# 		 requests.get(f"{BASE_TIMEEDIT_URL}/{ical_id}.ical").text
# 	 )

# 	 for event in calendar.walk("VEVENT"):
# 		 for t, transforms in rules:
# 			 for i, o in transforms:
# 				 c = re.compile(i)
# 				 event[t] = c.sub(o, event[t])

# 	 resp = make_response(calendar.to_ical(), 200)
# 	 resp.headers["Content-Type"] = "text/plain; charset=utf-8"

# 	 return resp


# SUMMARY: [KURSKOD], Undervisningstyp: <UNDERVISNINGSTYP>, [GRUPPER]
# DESCRIPTION: []
