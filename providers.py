import http.client
import json
import ssl
import requests
from datetime import timedelta

from config import _concat_date_time, _date_parser

ssl._create_default_https_context = ssl._create_unverified_context


class BaseProvider(object):
    def get(self, today, city):
        raise NotImplementedError

    def __call__(self, today, city):
        return self.get(today, city)


class Heroku(BaseProvider):
    @staticmethod
    def fetch_countries():
        data = requests.get("http://ezanvakti.herokuapp.com/ulkeler").json()
        record = []
        for rec in data:
            record.append(
                {
                    "name": rec["UlkeAdi"].capitalize(),
                    "key": rec["UlkeAdiEn"].lower(),
                    "id": rec["UlkeID"],
                }
            )
        return record

    @staticmethod
    def fetch_cities(country):
        data = requests.get(f"http://ezanvakti.herokuapp.com/sehirler/{country.id}").json()
        record = []

        if len(data) == 1:
            city_id = data[0]["SehirID"]
            data = requests.get(f"http://ezanvakti.herokuapp.com/ilceler/{city_id}").json()

            for rec in data:
                record.append(
                    {
                        "city_id": city_id,
                        "name": rec["IlceAdi"].capitalize(),
                        "key": rec["IlceAdiEn"].lower(),
                        "id": rec["IlceID"],
                    }
                )
        else:
            for rec in data:
                record.append(
                    {
                        "name": rec["SehirAdi"].capitalize(),
                        "key": rec["SehirAdiEn"].lower(),
                        "id": rec["SehirID"],
                    }
                )
        return record

    @staticmethod
    def fetch_districts(city):
        if city.direct_city_id:
            return city.id

        data = requests.get(f"http://ezanvakti.herokuapp.com/ilceler/{city.id}").json()
        return list(filter(lambda x: x["IlceAdiEn"].lower() == city.city_key, data))[0]["IlceID"]

    def get(self, today, city):
        tomorrow = today + timedelta(days=1)
        data = requests.get(f"http://ezanvakti.herokuapp.com/vakitler?ilce={self.fetch_districts(city)}").json()
        times = list(filter(lambda x: _date_parser(x["MiladiTarihKisa"]) == today, data))[0]
        next_day = filter(
            lambda x: _date_parser(x["MiladiTarihKisa"]) == today + timedelta(days=1),
            data,
        )
        next_day = list(next_day)[0]
        record = {
            "imsak": (
                _concat_date_time(times["İmsak"], today),
                _concat_date_time(times["İmsak"], today),
            ),
            "sabah": (
                _concat_date_time(times["Imsak"], today),
                _concat_date_time(times["Gunes"], today),
            ),
            "ogle": (
                _concat_date_time(times["Ogle"], today),
                _concat_date_time(times["Ikindi"], today),
            ),
            "ikindi": (
                _concat_date_time(times["Ikindi"], today),
                _concat_date_time(times["Aksam"], today),
            ),
            "aksam": (
                _concat_date_time(times["Aksam"], today),
                _concat_date_time(times["Yatsi"], today),
            ),
            "yatsi": (
                _concat_date_time(times["Yatsi"], today),
                _concat_date_time(next_day["Imsak"], tomorrow),
            ),
            "vitr": (
                _concat_date_time(times["Yatsi"], today),
                _concat_date_time(next_day["Imsak"], tomorrow),
            ),
        }
        return record


class CollectApi(BaseProvider):
    def __init__(self):
        self.headers = {
            "content-type": "application/json",
            "authorization": "apikey 7lGnm6P6iiycQ9dvxj7z5K:1hxqBVW7UuNkM6X7fPHJGQ",
        }

    def get(self, today, city):
        tomorrow = today + timedelta(days=1)
        conn = http.client.HTTPSConnection("api.collectapi.com")
        conn.request("GET", "/pray/all?data.city={}".format(city.city_key), headers=self.headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8")).get("result")
        if not data:
            raise IndexError
        times = dict(list(map(lambda x: list(x.values())[::-1], data)))

        record = {
            "imsak": (
                _concat_date_time(times["İmsak"], today),
                _concat_date_time(times["İmsak"], today),
            ),
            "sabah": (
                _concat_date_time(times["İmsak"], today),
                _concat_date_time(times["Güneş"], today),
            ),
            "ogle": (
                _concat_date_time(times["Öğle"], today),
                _concat_date_time(times["İkindi"], today),
            ),
            "ikindi": (
                _concat_date_time(times["İkindi"], today),
                _concat_date_time(times["Akşam"], today),
            ),
            "aksam": (
                _concat_date_time(times["Akşam"], today),
                _concat_date_time(times["Yatsı"], today),
            ),
            "yatsi": (
                _concat_date_time(times["Yatsı"], today),
                _concat_date_time("00:00", tomorrow),
            ),
            "vitr": (
                _concat_date_time(times["Yatsı"], today),
                _concat_date_time("00:00", tomorrow),
            ),
        }
        return record


class Aladhan(BaseProvider):
    def get(self, today, city):
        tomorrow = today + timedelta(days=1)
        times = requests.get(
            f"https://api.aladhan.com/v1/timingsByCity/{today}?city={city.name}&country={city.country.name}"
        ).json()["data"]["timings"]
        record = {
            "imsak": (
                _concat_date_time(times["Imsak"], today),
                _concat_date_time(times["Fajr"], today),
            ),
            "sabah": (
                _concat_date_time(times["Fajr"], today),
                _concat_date_time(times["Sunrise"], today),
            ),
            "ogle": (
                _concat_date_time(times["Dhuhr"], today),
                _concat_date_time(times["Asr"], today),
            ),
            "ikindi": (
                _concat_date_time(times["Asr"], today),
                _concat_date_time(times["Sunset"], today),
            ),
            "aksam": (
                _concat_date_time(times["Maghrib"], today),
                _concat_date_time(times["Isha"], today),
            ),
            "yatsi": (
                _concat_date_time(times["Isha"], today),
                _concat_date_time(times["Imsak"], tomorrow),
            ),
            "vitr": (
                _concat_date_time(times["Isha"], today),
                _concat_date_time(times["Imsak"], tomorrow),
            ),
        }
        return record
