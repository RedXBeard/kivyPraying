import json
from datetime import datetime
from urllib.error import HTTPError

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, Clock, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.utils import get_color_from_hex

from config import DB, REPO_FILE, find_parent, set_children_color, seconds_converter, set_color, _datetime_parser, \
    fetch_selected_city, fetch_cities
from language import Lang
from providers import Heroku, CollectApi

trans = Lang('en')


class ResetButton(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super(ResetButton, self).__init__(**kwargs)
        self.press_count = 0

    def on_press(self):
        self.disabled = True
        self.press_count += 1
        if self.press_count == 1:
            set_color(self, get_color_from_hex('FF6666'))
            Clock.schedule_once(lambda dt: self.check_press(), 1)
        if self.press_count > 1:
            root = find_parent(self, Praying)
            root.welcome.progressbar.value = 0
            trans.lang = 'en'

            DB.store_clear()

            self.press_count = 0

            root.progressbar_path(
                path=list(reversed([
                    root.start_progress,
                    root.switch_lang,
                    root.fetch_cities,
                    root.fetch_selected_city,
                    root.fetch_today_praying_times,
                    root.check_praying_status,
                    root.reset_missed_prays,
                    root.check_missed_prays,
                ])),
                per_step=int(1000 / 9)
            )

            set_color(self, get_color_from_hex('FFFFFF'))
        self.disabled = False

    def check_press(self):
        self.press_count = 0
        set_color(self, get_color_from_hex('FFFFFF'))


class RecordButton(ButtonBehavior, Label):
    def on_press(self):
        root = find_parent(self, Praying)
        root.transition = SlideTransition(direction='left')
        root.current = 'data'
        try:
            f = open(REPO_FILE)
            data = f.read()
            f.close()
            data = json.dumps(json.loads(data), sort_keys=True, indent=2)
        except TypeError:
            data = 'please click reset button on previous screen'
        root.data.record.text = data


class BackButton(ButtonBehavior, Label):
    def on_press(self):
        root = find_parent(self, Praying)
        root.transition = SlideTransition(direction='right')
        root.current = 'entrance'


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
    day = NumericProperty()
    month = NumericProperty()
    year = NumericProperty()
    weekday = NumericProperty()

    def __init__(self, **kwargs):
        super(Praying, self).__init__(**kwargs)

        self.today = datetime.now().date()
        self.day = self.today.day
        self.month = self.today.month
        self.year = self.today.year
        self.weekday = self.today.weekday()
        self.times = None
        self.city = None

        self.progressbar_path(
            path=list(reversed([
                self.fetch_cities,
                self.fetch_selected_city,
                self.fetch_today_praying_times,
                self.check_praying_status,
                self.check_missed_prays,
                self.check_counter
            ])),
            per_step=int(1000 / 6)
        )

    def progressbar_path(self, path=None, per_step=0):
        path = path or []
        try:
            path.pop()()
        except IndexError:
            self.transition = SlideTransition(direction='left')
            self.current = 'entrance'
            return
        self.welcome.progressbar.value += per_step

        Clock.schedule_once(lambda dt: self.progressbar_path(path, per_step), .5)

    def start_progress(self):
        self.transition = SlideTransition(direction='right')
        self.current = 'welcome'

    @staticmethod
    def fetch_cities():
        fetch_cities()

    def fetch_selected_city(self):
        self.city = fetch_selected_city()
        self.entrance.city_selection.set_text()

    def fetch_today_praying_times(self):
        record = None
        try:
            record = DB.store_get(str(self.today))
        except KeyError:
            for provider in (Heroku(), CollectApi()):
                try:
                    record = provider(self.today, self.city)
                    break
                except (HTTPError, IndexError):
                    pass

            if record:
                DB.store_put(str(self.today), record)
                DB.store_sync()
        self.times = record

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
            elif datetime.now() > _datetime_parser(pray_slot[1]):  # Kacirdi
                button = getattr(self.entrance, pray_name)
                button.disabled = True
                set_children_color(button.parent, get_color_from_hex('FF6666'))
                update = True
            elif datetime.now() < _datetime_parser(pray_slot[0]):  # daha var
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

    def reset_missed_prays(self):
        times = {'sabah': None, 'ogle': None, 'ikindi': None, 'aksam': None, 'yatsi': None, 'vitr': None}
        for time in times:
            layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
            button = getattr(layout, '{}_button'.format(time))
            label = getattr(layout, '{}_count'.format(time))
            button.active = button.disabled = True
            label.text = '0'
            set_children_color(layout, get_color_from_hex('B8D5CD'))

    def check_missed_prays(self):
        times = {'sabah': None, 'ogle': None, 'ikindi': None, 'aksam': None, 'yatsi': None, 'vitr': None}
        # removable_keys = []
        for key in DB.store_keys():
            if key.startswith('status'):
                rec = list(filter(lambda x: not x[1], DB.store_get(key).items()))
                for time, _ in rec:
                    if key.find(str(self.today)) != -1:
                        if datetime.now() < _datetime_parser(self.times[time][1]):
                            continue
                    times.pop(time, None)
                    layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
                    button = getattr(layout, '{}_button'.format(time))
                    label = getattr(layout, '{}_count'.format(time))
                    button.active = button.disabled = False
                    button.db_keys.append(key)
                    label.text = str((label.text and int(label.text) or 0) + 1)
                    set_children_color(layout, get_color_from_hex('FF6666'))
                # if not rec:
                #     removable_keys.append(key)

        for time in times:
            layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
            set_children_color(layout, get_color_from_hex('B8D5CD'))

        # for key in removable_keys:
        #     DB.store_delete(key)

        # DB.store_sync()

    def check_counter(self, **kwargs):
        order = ['sabah', 'ogle', 'ikindi', 'aksam', 'yatsi']
        now = datetime.now()
        try:
            record = DB.store_get(str(self.today))
        except KeyError:
            Clock.schedule_once(lambda dt: self.check_counter(), .5)
            return
        upcoming = None
        current = None
        total_second = 0
        for key in order:
            start, end, = list(map(lambda x: _datetime_parser(x), record[key]))
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

    def switch_lang(self, lang=None):
        lang = lang or trans.lang
        trans.switch_lang(lang)
        DB.store_put('language', lang)
        DB.store_sync()
        self.entrance.lang_selection.set_text()


class PrayingApp(App):
    def __init__(self, **kwargs):
        super(PrayingApp, self).__init__(**kwargs)
        Builder.load_file('assets/praying.kv')
        self.title = 'Kivy Praying'

    def build(self):
        try:
            lang = DB.store_get('language')
            trans.switch_lang(lang)
        except KeyError:
            pass
        fetch_cities()
        fetch_selected_city()
        return Praying()


if __name__ == '__main__':
    Window.clearcolor = get_color_from_hex('E2DDD5')
    Window.keyboard_anim_args = {'d': .2, 't': 'in_out_expo'}
    Window.softinput_mode = 'below_target'
    PrayingApp().run()
