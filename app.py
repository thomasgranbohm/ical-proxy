from flask import Flask, make_response, abort
import requests
import re
from icalendar import Calendar
import yaml
import hashlib
import os.path

component_name = "SUMMARY"


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


def transform_calendar(calendar):
    new_calendar = Calendar.from_ical(calendar.to_ical())

    for ev in new_calendar.walk("VEVENT"):
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
            ev[component_name] = data["KURSKOD"] + \
                " - " + data["UNDERVISNINGSTYP"]

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

    if cal_exists:
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
