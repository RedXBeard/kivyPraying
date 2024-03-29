from datetime import datetime
from urllib.error import HTTPError

from models import City, Country


PRAYER_TIMES = ["sabah", "ogle", "ikindi", "aksam", "yatsi", "vitr"]


def find_parent(cur_class, target_class):
    """find wanted widget from selected or current one"""
    req_class = cur_class
    while True:
        cls = str(req_class.__class__).split(".")[1].replace("'>", "")
        if cls == target_class.__name__:
            break
        elif cls == "core":
            req_class = None
            break

        req_class = req_class.parent
    return req_class


def get_colors(obj):
    u"""Color of widget returns."""
    obj_colors = []
    try:
        obj_colors.append(
            list(
                filter(lambda x: str(x).find("Color") != -1, obj.canvas.before.children)
            )[0]
        )
    except IndexError:
        pass

    try:
        obj_colors.append(
            list(
                filter(lambda x: str(x).find("Color") != -1, obj.canvas.after.children)
            )[0]
        )
    except IndexError:
        pass

    return obj_colors


def set_color(obj, color):
    obj_colors = get_colors(obj)
    for obj_color in obj_colors:
        try:
            obj_color.rgba = color
        except AttributeError:
            pass


def set_children_color(obj, color):
    for child in getattr(obj, "children", []):
        set_color(child, color)


def seconds_converter(scnds):
    seconds = scnds % 60
    mnts = (scnds - seconds) / 60
    minutes = mnts % 60
    hours = (mnts - minutes) / 60

    return list(map(lambda x: str(x).zfill(2), map(int, [hours, minutes, seconds])))


def fetch_countries():
    from providers import Heroku

    counties = Country.list()
    if not counties:
        try:
            countries = Heroku().fetch_countries()
        except HTTPError:
            countries = []

        for country in countries:
            Country.create(
                name=country["name"], country_key=country["key"], id=country["id"]
            )
    counties = Country.list()
    return counties


def fetch_cities():
    from providers import Heroku

    country = Country.get(selected=True)
    cities = City.list(country_id=country.id)

    if not cities:
        try:
            cities = Heroku().fetch_cities(country)
        except HTTPError:
            cities = []

        for city in cities:
            City.create(
                direct_city_id=city.get('city_id'),
                name=city["name"],
                city_key=city["key"],
                id=city["id"],
                country_id=country.id,
            )

    for city in City.list(country_id=None):
        City.update(city, country_id=country.pk)

    cities = City.list(country_id=country.id)
    return cities


def fetch_selected_country():
    country = Country.get(selected=True)
    if not country:
        country = Country.get(country_key="turkey")
        for db_country in Country.list():
            selected = db_country.pk == country.pk
            Country.update(db_country, selected=selected)

    return country


def fetch_selected_city():
    city = City.get(selected=True)
    if not city:
        country = Country.get(selected=True)
        city = City.list(country_id=country.id)[0]
        for db_city in City.list():
            selected = db_city.pk == city.pk
            City.update(db_city, selected=selected)

    return city


def _date_parser(rec):
    return datetime.strptime(rec, "%d.%m.%Y").date()


def _datetime_parser(rec):
    return datetime.strptime(rec, "%d.%m.%Y %H:%M")


def _concat_date_time(time, date):
    date = "{}.{}.{}".format(date.day, date.month, date.year)
    return "{} {}".format(date, time.split(" ")[0])


COLOR_CODES = {
    "yellow": (240 / 255.0, 201 / 255.0, 117 / 255.0, 1),
    "orange": (237 / 255.0, 165 / 255.0, 108 / 255.0, 1),
    "red": (218 / 255.0, 130 / 255.0, 119 / 255.0, 1),
    "purple": (176 / 255.0, 112 / 255.0, 193 / 255.0, 1),
    "blue": (131 / 255.0, 168 / 255.0, 240 / 255.0, 1),
    "green": (125 / 255.0, 182 / 255.0, 140 / 255.0, 1),
}
