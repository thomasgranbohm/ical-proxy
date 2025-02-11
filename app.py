from flask import Flask, make_response, abort
import requests
import re
from icalendar import Calendar
import yaml
import hashlib
import os
import os.path

COMPONENT_NAME = "SUMMARY"

def get_settings():
    settings = {}
    for file_name in os.listdir("./rules"):
        component, extension = file_name.split(".")
        assert extension == "yaml"

        with open(f"./rules/{file_name}", "r") as file:
            settings[component] = yaml.safe_load(file)

    return settings



def generate_regex(field="SUMMARY"):
    with open(f"./rules/{field}.yaml", "r") as file:
        rules = yaml.safe_load(file)

        file.close()

        return rules


def get_transformed(ical_id):
    with open(f"./transformed/{ical_id}") as file:
        cal = Calendar.from_ical(file.read())

        file.close()

        return cal


def find_first(l, d):
    return next(((d[key], i) for i, key in enumerate(l) if key in d), (None, None))

EVENT_FORMAT = {
    "SUMMARY": "%(COURSE_NAME)s — %(TEACHING_ACTIVITY)s", 
    "LOCATION": "%s", 
    "DESCRIPTION": "%s" #"Lärare: {teachers}\nInformation: {information}\nKarta: {map_url}"
}


### I hate writing super specific solution even if the problem is super specific
def transform_calendar(calendar):
    new_calendar = Calendar.from_ical(calendar.to_ical())
    settings = get_settings()

    for ev in new_calendar.walk("VEVENT"):
        for component_name in settings.keys():
            named_information = {}
            component_settings = settings[component_name]
            code_names = ev[component_name].split(component_settings["SPLIT_STR"])

            if "LINE_REMOVALS" in component_settings:
                line_removals = component_settings["LINE_REMOVALS"]
                
                indexes = []
                for removal in line_removals:
                    for i, code_name in enumerate(code_names):
                        if removal in code_name:
                            indexes.append(i)

                code_names = [i.strip() for j, i in enumerate(code_names) if j not in indexes]

            if "STRING_REMOVALS" in component_settings:
                string_removals = component_settings["STRING_REMOVALS"]

                for removal in string_removals:
                    for i in range(len(code_names)):
                        code_name = code_names[i]

                        if removal in code_name:    
                            code_names[i] = "".join(code_name.split(removal)).strip()
                            
                        

            if "REPLACEMENTS" in component_settings:
                replacements = component_settings["REPLACEMENTS"]

                for key, values in replacements.items():
                    found, _ = find_first(code_names, values)

                    if found != None:
                        named_information[key] = found

                try:
                    ev[component_name] = EVENT_FORMAT[component_name] % named_information
                except KeyError as e:
                    print("Could not find matching %s for %s" % (key, code_names))
            else:
                ev[component_name] = EVENT_FORMAT[component_name] % "\n".join(code_names)
            
    return new_calendar


def save_calendar(id, calendar):
    f = open(f"transformed/{id}", "w", encoding="utf8")

    f.write(calendar.to_ical().decode("utf8"))

    f.close()

    return True


def save_hash(id, calendar):
    f = open(f"originals/{id}", "w", encoding="utf8")

    f.write(hashlib.sha256(calendar.to_ical()).hexdigest())

    f.close()

    return True


def create_new_calendar(id, calendar):
    new_calendar = transform_calendar(calendar)

    if len(new_calendar.walk("VEVENT")) == 0:
        raise ValueError("Calendar has no events.")

    save_hash(id, calendar)
    save_calendar(id, new_calendar)

    return new_calendar


app = Flask(__name__)

BASE_TIMEEDIT_URL = "https://cloud.timeedit.net/liu/web/schema"


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/calendar/<string:ical_id>.ics")
def get_calendar(ical_id):
    try:
        if re.fullmatch("^ri([a-zA-Z0-9]+)$", ical_id) == None:
            raise Exception("Not valid id")

        url = f"{BASE_TIMEEDIT_URL}/{ical_id}.ics"

        r = requests.get(url)
    except Exception:
        abort(404)

    raw_cal = r.content.decode('utf-8')

    cal_exists = os.path.isfile(f"./originals/{ical_id}")

    new_calendar = None
    calendar = Calendar.from_ical(raw_cal)

    if cal_exists and "FLASK_DEBUG" not in os.environ:
        with open(f"./originals/{ical_id}", "r") as hash_file:
            hash = hash_file.readline()

            if hash != hashlib.sha256(calendar.to_ical()).hexdigest():
                try:
                    new_calendar = create_new_calendar(ical_id, calendar)
                except ValueError:
                    hash_file.close()
                    abort(404)
            else:
                new_calendar = get_transformed(ical_id)
    else:
        try:
            new_calendar = create_new_calendar(ical_id, calendar)
        except ValueError:
            abort(404)

    resp = make_response(new_calendar.to_ical(), 200)
    resp.headers["Content-Type"] = "text/calendar; charset=utf-8"

    return resp
