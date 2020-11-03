from copy import copy
from datetime import datetime, timedelta
from urllib.error import HTTPError

from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import sp
from kivy.properties import StringProperty, ListProperty, Clock, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

from config import DB, find_parent, set_children_color, seconds_converter, set_color, _datetime_parser, \
    fetch_selected_city, fetch_cities, COLOR_CODES
from language import Lang
from providers import Heroku, CollectApi

trans = Lang('en')


class Star(Image):
    def __init__(self, **kwargs):
        star_color = kwargs.pop('color', None) or COLOR_CODES.get('yellow')
        super(Star, self).__init__(**kwargs)
        self.source = 'assets/star.png'
        self.color = star_color
        self.valign = 'center'


class RecordStar(GridLayout):
    def __init__(self, **kwargs):
        text = kwargs.pop('text')
        color = kwargs.pop('color')
        super(RecordStar, self).__init__(cols=2, rows=1, **kwargs)

        label = Label(text=text, padding=(0, 0), height=sp(20))
        star = Star(color=color, size_hint=(None, None), width=sp(20), height=sp(20))
        self.add_widget(label)
        self.add_widget(star)


class RecordLineCheckbox(CheckBox):
    def __init__(self, **kwargs):
        super(RecordLineCheckbox, self).__init__(**kwargs)
        self.disabled = True
        self.size_hint = None, None
        self.width = sp(25)
        self.height = sp(40)


class RecordLine(GridLayout):
    def __init__(self, **kwargs):
        data = kwargs.pop('record')

        super(RecordLine, self).__init__(**kwargs)

        self.cols = 7
        self.rows = 1
        self.size_hint_y = None
        self.height = sp(50)
        pray_time_label = Label(text=data.get('pray_time'), font_size=sp(15), padding=(20, 20))
        sabah_checkbox = RecordLineCheckbox(active=bool(data.get('sabah')))
        ogle_checkbox = RecordLineCheckbox(active=bool(data.get('ogle')))
        ikindi_checkbox = RecordLineCheckbox(active=bool(data.get('ikindi')))
        aksam_checkbox = RecordLineCheckbox(active=bool(data.get('aksam')))
        yatsi_checkbox = RecordLineCheckbox(active=bool(data.get('yatsi')))
        vitr_checkbox = RecordLineCheckbox(active=bool(data.get('vitr')))

        self.add_widget(pray_time_label)
        self.add_widget(sabah_checkbox)
        self.add_widget(ogle_checkbox)
        self.add_widget(ikindi_checkbox)
        self.add_widget(aksam_checkbox)
        self.add_widget(yatsi_checkbox)
        self.add_widget(vitr_checkbox)


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
        root.data.record.clear_widgets()
        root.data.stars.clear_widgets()

        root.load_stars()
        root.load_more_records()


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


class NewDateButton(ButtonBehavior, Label):
    def _clear_widgets(self):
        root = find_parent(self, Praying)
        remove_set = []
        for child in root.data.children:
            if child.__class__ == DateLine:
                remove_set.append(child)
            if child.__class__ == Image and child.source == 'assets/dark_trans.png':
                remove_set.append(child)
        for child in remove_set:
            root.data.remove_widget(child)

    def _refresh(self):
        root = find_parent(self, Praying)
        root.progressbar_path(
            path=list(reversed([
                root.start_progress,
                root.fetch_today_praying_times,
                root.check_praying_status,
                root.reset_missed_prays,
                root.check_missed_prays,
            ])),
            per_step=int(1000 / 9)
        )
        self._clear_widgets()

    def _new_record(self):
        root = find_parent(self, Praying)
        trans_image = Image(source='assets/dark_trans.png', allow_stretch=True, keep_ratio=False)
        root.data.add_widget(trans_image)
        root.data.add_widget(DateLine())

    def _add_new_record(self):
        day, month, year = self.day.text, self.month.values.index(self.month.text) + 1, self.year.text

        try:
            date = datetime(*list(map(int, (year, month, day)))).date()
        except ValueError:
            set_color(self.day, get_color_from_hex('FF6666'))
            return

        key = 'status_{}'.format(date)
        if not DB.store_exists(key):
            DB.store_put(key, {'sabah': None, 'ogle': None, 'ikindi': None, 'aksam': None, 'yatsi': None, 'vitr': None})
            DB.store_sync()

        self._refresh()

    def on_press(self):
        if self.name == 'new_record':
            self._new_record()
        if self.name == 'new_record_add':
            self._add_new_record()
        if self.name == 'new_record_cancel':
            self._clear_widgets()


class NewDateTextInput(TextInput):
    def time_check(self, text):
        if self.name == 'day':
            return int(text) <= 31
        if self.name == 'year':
            return int(text.ljust(4, '0')) <= datetime.now().year

    def insert_text(self, substring, from_undo=False):
        set_color(self, get_color_from_hex('FFFFFF'))
        if substring.isdigit() and self.time_check(self.text + substring):
            return super(NewDateTextInput, self).insert_text(substring, from_undo=from_undo)
        return super(NewDateTextInput, self).insert_text('', from_undo=from_undo)

    def do_backspace(self, from_undo=False, mode='bkspc'):
        set_color(self, get_color_from_hex('FFFFFF'))
        return super(NewDateTextInput, self).do_backspace(from_undo=from_undo, mode=mode)


class DateLine(FloatLayout):
    pass


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

        self.reward_success()

    def progressbar_path(self, path=None, per_step=0):
        path = path or []
        try:
            path.pop()()
        except IndexError:
            self.transition = SlideTransition(direction='left')
            self.current = 'entrance'
            return
        self.welcome.progressbar.value += per_step

        Clock.schedule_once(lambda dt: self.progressbar_path(path, per_step), .1)

    def animation_complete(self, animation, widget):
        self.entrance.remove_widget(widget)

    def reward_success(self):
        daily = DB.store_exists('DAILY') and DB.store_get('DAILY') or 0
        weekly = DB.store_exists('WEEKLY') and DB.store_get('WEEKLY') or 0
        monthly = DB.store_exists('MONTHLY') and DB.store_get('MONTHLY') or 0
        yearly = DB.store_exists('YEARLY') and DB.store_get('YEARLY') or 0

        count = 0
        for key in DB.store_keys():
            if key.startswith('status'):
                count += not list(filter(lambda x: not x[1], DB.store_get(key).items())) and 1 or 0

        calc_yearly, count = int(count / 365), count % 365
        calc_monthly, count = int(count / 28), count % 28
        calc_weekly, count = int(count / 7), count % 7
        calc_daily = count

        stars = []
        if calc_yearly > yearly:
            stars.append(Star(color=COLOR_CODES.get('purple')))
        if calc_monthly > monthly:
            stars.append(Star(color=COLOR_CODES.get('red')))
        if calc_weekly > weekly:
            stars.append(Star(color=COLOR_CODES.get('orange')))
        if calc_daily > daily:
            stars.append(Star(color=COLOR_CODES.get('yellow')))

        self.run_stars(stars)

        DB.store_put('YEARLY', calc_yearly)
        DB.store_put('MONTHLY', calc_monthly)
        DB.store_put('WEEKLY', calc_weekly)
        DB.store_put('DAILY', calc_daily)
        DB.store_sync()

        Clock.schedule_once(lambda dt: self.reward_success(), .5)

    def run_stars(self, star_set):
        try:
            star_widget = star_set.pop()
            self.entrance.add_widget(star_widget)
            anim = Animation(pos=(-1 * Window.size[0] / 2, Window.size[1] / 2), t='in_circ', d=1.5)
            anim.start(star_widget)
            anim.bind(on_complete=self.animation_complete)
        except IndexError:
            return
        Clock.schedule_once(lambda dt: self.run_stars(star_set), .5)

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
        visits = []
        for key in DB.store_keys():
            if key.startswith('status'):
                visits.append(datetime.strptime(key.strip('status_'), '%Y-%m-%d').date())

        visits = sorted(visits)
        d1 = visits and visits[0] or datetime.now().date()
        d2 = visits and visits[-1] or datetime.now().date()
        days = set([d1 + timedelta(n) for n in range(1, int((d2 - d1).days))])
        for day in days.difference(set(visits)):
            key = 'status_{}'.format(day)
            DB.store_put(key, copy(times))

        DB.store_sync()
        days = [d1] + list(days) + [d2]
        for day in days:
            key = 'status_{}'.format(day)
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

        for time in times:
            layout = getattr(self.entrance.missed, 'missed_{}'.format(time))
            set_children_color(layout, get_color_from_hex('B8D5CD'))

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

    def load_stars(self):
        daily = DB.store_exists('DAILY') and DB.store_get('DAILY') or 0
        weekly = DB.store_exists('WEEKLY') and DB.store_get('WEEKLY') or 0
        monthly = DB.store_exists('MONTHLY') and DB.store_get('MONTHLY') or 0
        yearly = DB.store_exists('YEARLY') and DB.store_get('YEARLY') or 0

        self.data.stars.add_widget(
            RecordStar(text=str(daily), color=COLOR_CODES.get('yellow'))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(weekly), color=COLOR_CODES.get('orange'))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(monthly), color=COLOR_CODES.get('red'))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(yearly), color=COLOR_CODES.get('purple'))
        )

    def load_more_records(self):
        for child in self.data.record.children:
            if child.__class__.__name__ == 'Widget':
                self.data.record.remove_widget(child)
                break

        existed_lines = len(self.data.record.children)

        records = []
        for key in DB.store_keys():
            if key.startswith('status'):
                record = {'pray_time': key.strip('status_')}
                record.update(**DB.store_get(key))
                records.append(record)

        records = sorted(records, key=lambda x: datetime.strptime(x['pray_time'], '%Y-%m-%d'), reverse=True)
        for rec in records[existed_lines:existed_lines + 10]:
            self.data.record.add_widget(RecordLine(record=rec))
        self.data.record.add_widget(Widget())

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
