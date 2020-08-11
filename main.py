import json
import urllib.request
from datetime import datetime, timedelta

from kivy import Config
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager
from kivy.utils import get_color_from_hex

from config import DB, find_parent


class PrayedCheckBox(CheckBox):
    name = StringProperty()

    def on_press(self):
        self.disabled = True
        root = find_parent(self, Praying)
        key = 'status_{}'.format(root.today)
        record = DB.store_get(key)
        record[self.name] = str(datetime.now())
        DB.store_put(key, record)
        DB.store_sync()


class MissedCheckBox(CheckBox):
    name = StringProperty()


class Praying(ScreenManager):
    def __init__(self, **kwargs):
        super(Praying, self).__init__(**kwargs)
        self.today = datetime.now().date()
        self.entrance.today.text = str(self.today)
        self.times = self.fetch_today_praying_times()
        self.check_praying_status()

    @staticmethod
    def _date_parser(rec):
        return datetime.strptime(rec, '%d.%m.%Y').date()

    @staticmethod
    def _datetime_parser(rec):
        return datetime.strptime(rec, '%d.%m.%Y %H:%M')

    def _concat_date_time(self, time, date=None):
        date = date or self.today
        date = '{}.{}.{}'.format(date.day, date.month, date.year)
        return '{} {}'.format(date, time)

    def fetch_today_praying_times(self):
        try:
            record = DB.store_get(str(self.today))
        except KeyError:
            f = urllib.request.urlopen('https://ezanvakti.herokuapp.com/vakitler?ilce=9541')
            data = json.loads(f.read().decode('utf-8'))
            times = list(filter(lambda x: self._date_parser(x['MiladiTarihKisa']) == self.today, data))[0]
            next_day = filter(lambda x: self._date_parser(x['MiladiTarihKisa']) == self.today + timedelta(days=1), data)
            next_day = list(next_day)[0]
            record = {'sabah': (self._concat_date_time(times['Imsak']), self._concat_date_time(times['Gunes'])),
                      'ogle': (self._concat_date_time(times['Ogle']), self._concat_date_time(times['Ikindi'])),
                      'ikindi': (self._concat_date_time(times['Ikindi']), self._concat_date_time(times['Aksam'])),
                      'aksam': (self._concat_date_time(times['Aksam']), self._concat_date_time(times['Yatsi'])),
                      'yatsi': (self._concat_date_time(times['Yatsi']),
                                self._concat_date_time(next_day['Imsak'], self.today + timedelta(days=1))),
                      'vitr': (self._concat_date_time(times['Yatsi']),
                               self._concat_date_time(next_day['Imsak'], self.today + timedelta(days=1)))}

            DB.store_put(str(self.today), record)
            DB.store_sync()
        return record

    def check_praying_status(self):
        key = 'status_{}'.format(self.today)
        try:
            record = DB.store_get(key)
        except KeyError:
            record = {'sabah': None, 'ogle': None, 'ikindi': None, 'aksam': None, 'yatsi': None, 'vitr': None}

        for pray_name, pray_slot in self.times.items():
            if record[pray_name]:
                button = getattr(self.entrance, pray_name)
                button.active = button.disabled = True
            elif datetime.now() > self._datetime_parser(pray_slot[1]):
                button = getattr(self.entrance, pray_name)
                button.disabled = True

        DB.store_put(key, record)
        DB.store_sync()


class PrayingApp(App):
    def __init__(self, **kwargs):
        super(PrayingApp, self).__init__(**kwargs)
        Builder.load_file('assets/praying.kv')
        self.title = 'Kivy Praying'

    def build(self):
        return Praying()


if __name__ == '__main__':
    Config.set('kivy', 'desktop', 1)
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    Window.clearcolor = get_color_from_hex('E2DDD5')
    Window.size = 600, 600
    PrayingApp().run()
