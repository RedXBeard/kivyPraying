import http.client
import json
import ssl
import urllib.request
from datetime import timedelta

from config import _concat_date_time, _date_parser


class BaseProvider(object):
    def get(self, today):
        raise NotImplementedError

    def __call__(self, today):
        return self.get(today)


class Heroku(BaseProvider):
    def get(self, today):
        ssl._create_default_https_context = ssl._create_unverified_context
        f = urllib.request.urlopen('http://ezanvakti.herokuapp.com/vakitler?ilce=9541')
        data = json.loads(f.read().decode('utf-8'))
        times = list(filter(lambda x: _date_parser(x['MiladiTarihKisa']) == today, data))[0]
        next_day = filter(lambda x: _date_parser(x['MiladiTarihKisa']) == today + timedelta(days=1), data)
        next_day = list(next_day)[0]
        record = {'sabah': (_concat_date_time(times['Imsak'], today), _concat_date_time(times['Gunes'], today)),
                  'ogle': (_concat_date_time(times['Ogle'], today), _concat_date_time(times['Ikindi'], today)),
                  'ikindi': (_concat_date_time(times['Ikindi'], today), _concat_date_time(times['Aksam'], today)),
                  'aksam': (_concat_date_time(times['Aksam'], today), _concat_date_time(times['Yatsi'], today)),
                  'yatsi': (_concat_date_time(times['Yatsi'], today),
                            _concat_date_time(next_day['Imsak'], today + timedelta(days=1))),
                  'vitr': (_concat_date_time(times['Yatsi'], today),
                           _concat_date_time(next_day['Imsak'], today + timedelta(days=1)))}
        return record


class CollectApi(BaseProvider):
    def get(self, today):
        ssl._create_default_https_context = ssl._create_unverified_context
        next_day = today + timedelta(days=1)
        conn = http.client.HTTPSConnection("api.collectapi.com")
        headers = {
            'content-type': "application/json",
            'authorization': 'apikey 7lGnm6P6iiycQ9dvxj7z5K:1hxqBVW7UuNkM6X7fPHJGQ'
        }
        conn.request("GET", "/pray/all?data.city=istanbul", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))['result']
        times = dict(list(map(lambda x: list(x.values())[::-1], data)))

        record = {'sabah': (_concat_date_time(times['İmsak'], today), _concat_date_time(times['Güneş'], today)),
                  'ogle': (_concat_date_time(times['Öğle'], today), _concat_date_time(times['İkindi'], today)),
                  'ikindi': (_concat_date_time(times['İkindi'], today), _concat_date_time(times['Akşam'], today)),
                  'aksam': (_concat_date_time(times['Akşam'], today), _concat_date_time(times['Yatsı'], today)),
                  'yatsi': (_concat_date_time(times['Yatsı'], today), _concat_date_time('00:00', next_day)),
                  'vitr': (_concat_date_time(times['Yatsı'], today), _concat_date_time('00:00', next_day))}
        return record
