import json
import urllib.request
from datetime import datetime, timedelta

from kivy import Config
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, Clock
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager
from kivy.utils import get_color_from_hex

from config import DB, find_parent, set_children_color, seconds_converter, WEEKDAYS, MONTHS


class PrayedCheckBox(CheckBox):
    name = StringProperty()

    def on_press(self):
        set_children_color(self.parent, get_color_from_hex('B8D5CD'))

        self.disabled = True
        root = find_parent(self, Praying)
        key = 'status_{}'.format(root.today)
        record = DB.store_get(key)
        record[self.name] = str(datetime.now())
        DB.store_put(key, record)
        DB.store_sync()


class MissedCheckBox(CheckBox):
    name = StringProperty()
    db_keys = ListProperty(defaultvalue=[])

    def __init__(self, **kwargs):
        super(MissedCheckBox, self).__init__(**kwargs)
        self.disabled = self.active = True
        set_children_color(self.parent, get_color_from_hex('B8D5CD'))

    def on_press(self):
        root = find_parent(self, Praying)
        time = self.name
        key = self.db_keys.pop()

        record = DB.store_get(key)
        record[time] = str(datetime.now())
        DB.store_put(key, record)
        DB.store_sync()

        layout = getattr(root.entrance.missed, 'missed_{}'.format(time))
        label = getattr(layout, '{}_count'.format(time))

        count = max(0, (label.text and int(label.text) or 0) - 1)
        if count > 0:
            label.text = str(count)
            self.active = False
        else:
            label.text = ''
            self.disabled = True
            set_children_color(self.parent, get_color_from_hex('B8D5CD'))


class Praying(ScreenManager):
    def __init__(self, **kwargs):
        super(Praying, self).__init__(**kwargs)
        self.today = datetime.now().date()
        self.entrance.today.text = '{} {} {}, {}'.format(self.today.day, MONTHS[self.today.month],
                                                         self.today.year, WEEKDAYS[self.today.weekday()])
        self.times = self.fetch_today_praying_times()
        self.check_praying_status()
        self.check_missed_prays()
        self.check_counter()

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
            f = urllib.request.urlopen('http://ezanvakti.herokuapp.com/vakitler?ilce=9541')
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

        update = False
        for pray_name, pray_slot in self.times.items():
            if record[pray_name]:  # Kilindi
                button = getattr(self.entrance, pray_name)
                button.active = button.disabled = True
                set_children_color(button.parent, get_color_from_hex('B8D5CD'))
                update = True
            elif datetime.now() > self._datetime_parser(pray_slot[1]):  # Kacirdi
                button = getattr(self.entrance, pray_name)
                button.disabled = True
                set_children_color(button.parent, get_color_from_hex('FF6666'))
                update = True
            elif datetime.now() < self._datetime_parser(pray_slot[0]):  # daha var
                button = getattr(self.entrance, pray_name)
                button.disabled = True
                set_children_color(button.parent, get_color_from_hex('D2D1BE'))
                update = True
            else:  # Zaman var
                button = getattr(self.entrance, pray_name)
                button.disabled = False
                set_children_color(button.parent, get_color_from_hex('FFFFFF'))
                update = True

        if update:
            DB.store_put(key, record)
            DB.store_sync()

        Clock.schedule_once(lambda dt: self.check_praying_status(), .5)

    def check_missed_prays(self):
        times = {'sabah': None, 'ogle': None, 'ikindi': None, 'aksam': None, 'yatsi': None, 'vitr': None}
        removable_keys = []
        for key in DB.store_keys():
            if key.startswith('status'):
                rec = list(filter(lambda x: not x[1], DB.store_get(key).items()))
                for time, _ in rec:
                    if key.find(str(self.today)) != -1:
                        if datetime.now() < self._datetime_parser(self.times[time][1]):
                            continue
                    times.pop(time)
                    layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
                    button = getattr(layout, '{}_button'.format(time))
                    label = getattr(layout, '{}_count'.format(time))
                    button.active = button.disabled = False
                    button.db_keys.append(key)
                    label.text = str((label.text and int(label.text) or 0) + 1)
                    set_children_color(layout, get_color_from_hex('FF6666'))
                if not rec:
                    removable_keys.append(key)

        for time in times:
            layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
            set_children_color(layout, get_color_from_hex('B8D5CD'))

        for key in removable_keys:
            DB.store_delete(key)

        DB.store_sync()

    def check_counter(self):
        order = ['sabah', 'ogle', 'ikindi', 'aksam', 'yatsi']
        now = datetime.now()
        record = DB.store_get(str(self.today))
        upcoming = None
        current = None
        total_second = 0
        for key in order:
            start, end, = list(map(lambda x: self._datetime_parser(x), record[key]))
            if start < now < end:
                current = end
                break
            if start > now:
                upcoming = start
                break

        if current is not None:
            total_second = int((current - now).total_seconds())
        if upcoming is not None:
            total_second = int((upcoming - now).total_seconds())

        hours, minutes, seconds = seconds_converter(total_second)
        self.entrance.info.hours.text = hours
        self.entrance.info.minutes.text = minutes
        self.entrance.info.seconds.text = seconds

        Clock.schedule_once(lambda dt: self.check_counter(), .5)


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
