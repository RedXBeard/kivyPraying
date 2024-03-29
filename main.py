from datetime import datetime, timedelta
from urllib.error import HTTPError

from colour import Color
from dateutil.relativedelta import relativedelta
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import sp
from kivy.properties import StringProperty, NumericProperty, ListProperty, DictProperty
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

from config import (
    find_parent,
    set_children_color,
    seconds_converter,
    set_color,
    fetch_selected_city,
    fetch_cities,
    fetch_countries,
    COLOR_CODES,
    fetch_selected_country, PRAYER_TIMES,
)
from language import Lang
from models import City, Time, Status, Language, Reward
from providers import Heroku, CollectApi, Aladhan
from raw_sql import full_prayed_dates, check_none, fetch_missing_prays
from storage import SQLiteDB

trans = Lang("en")


class RoundedLabel(Label):
    pass


class Star(Image):
    def __init__(self, **kwargs):
        star_color = kwargs.pop("color", None) or COLOR_CODES.get("yellow")
        super(Star, self).__init__(**kwargs)
        self.source = "assets/star.png"
        self.color = star_color
        self.valign = "center"


class RecordStar(GridLayout):
    def __init__(self, **kwargs):
        text = kwargs.pop("text")
        color = kwargs.pop("color")
        super(RecordStar, self).__init__(cols=2, rows=1, **kwargs)

        label = Label(
            text=text,
            padding=(0, 0),
            height=sp(20),
            font_size=sp(15),
            color=get_color_from_hex("#000000"),
        )
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
        data = kwargs.pop("record")

        super(RecordLine, self).__init__(**kwargs)

        self.cols = 7
        self.rows = 1
        self.size_hint_y = None
        self.height = sp(50)
        pray_time_label = RoundedLabel(
            text=data.get("pray_time"), font_size=sp(15), padding=(20, 20)
        )
        sabah_checkbox = RecordLineCheckbox(active=bool(data.get("sabah")))
        ogle_checkbox = RecordLineCheckbox(active=bool(data.get("ogle")))
        ikindi_checkbox = RecordLineCheckbox(active=bool(data.get("ikindi")))
        aksam_checkbox = RecordLineCheckbox(active=bool(data.get("aksam")))
        yatsi_checkbox = RecordLineCheckbox(active=bool(data.get("yatsi")))
        vitr_checkbox = RecordLineCheckbox(active=bool(data.get("vitr")))

        self.add_widget(pray_time_label)
        self.add_widget(sabah_checkbox)
        self.add_widget(ogle_checkbox)
        self.add_widget(ikindi_checkbox)
        self.add_widget(aksam_checkbox)
        self.add_widget(yatsi_checkbox)
        self.add_widget(vitr_checkbox)


class ResetButton(ButtonBehavior, RoundedLabel):
    def __init__(self, **kwargs):
        super(ResetButton, self).__init__(**kwargs)
        self.press_count = 0

    def on_press(self):
        self.disabled = True
        self.press_count += 1
        if self.press_count == 1:
            set_color(self, get_color_from_hex("FF6666"))
            Clock.schedule_once(lambda dt: self.check_press(), 1)
        if self.press_count > 1:
            root = find_parent(self, Praying)
            root.welcome.progressbar.value = 0
            trans.lang = "en"

            Status.delete()

            self.press_count = 0

            root.progressbar_path(
                path=list(
                    reversed(
                        [
                            root.start_progress,
                            root.fetch_today_praying_times,
                            root.reset_missed_prays,
                            root.check_praying_status,
                            root.check_missed_prays(),
                        ]
                    )
                ),
                per_step=int(1000 / 9),
            )

            set_color(self, get_color_from_hex("FFFFFF"))
        self.disabled = False

    def check_press(self):
        self.press_count = 0
        set_color(self, get_color_from_hex("FFFFFF"))


class RecordButton(ButtonBehavior, RoundedLabel):
    def on_press(self):
        root = find_parent(self, Praying)
        root.transition = SlideTransition(direction="left")
        root.current = "data"
        root.data.record.clear_widgets()
        root.data.missing_record.clear_widgets()
        root.data.stars.clear_widgets()

        statuses = sorted(Status.list(), key=lambda x: x.date)
        root.data.info_button.info_text = str(statuses[0].date)

        for status in statuses:
            root.records.setdefault(status.date, {}).update(
                {status.time_name: bool(status.is_prayed), "pray_time": str(status.date)}
            )

        root.load_stars()
        root.load_more_missed_records()
        root.load_more_records()


class SettingsButton(ButtonBehavior, RoundedLabel):
    def on_press(self):
        root = find_parent(self, Praying)
        root.app_size = root.calculate_app_size()
        root.transition = SlideTransition(direction="left")
        root.current = "settings"


class TimesButton(ButtonBehavior, RoundedLabel):
    def on_press(self):
        root = find_parent(self, Praying)
        root.transition = SlideTransition(direction="left")
        root.current = "praying_times"


class BackButton(ButtonBehavior, RoundedLabel):
    def on_press(self):
        root = find_parent(self, Praying)
        root.transition = SlideTransition(direction="right")
        root.current = "entrance"


class AddOneDateButton(ButtonBehavior, Label):
    def on_press(self):
        root = find_parent(self, Praying)
        statuses = sorted(Status.list(), key=lambda x: x.date)
        day = statuses[0].date - timedelta(days=1)
        for time_name in PRAYER_TIMES:
            Status.create(time_name=time_name, date=day)
            root.records.setdefault(day, {}).update(
                {time_name: False, "pray_time": str(day)}
            )

        root.data.record.clear_widgets()
        root.data.missing_record.clear_widgets()
        root.data.stars.clear_widgets()

        root.load_stars()
        root.load_more_missed_records()
        root.load_more_records()

        root.data.info_button.info_text = str(day)

        root.reset_missed_prays()
        root.check_missed_prays()()


class PrayedCheckBox(CheckBox):
    name = StringProperty()

    def on_press(self):
        set_children_color(self.parent, get_color_from_hex("B8D5CD"))

        self.disabled = True
        root = find_parent(self, Praying)
        status = Status.get(date=root.today, time_name=self.name)
        Status.update(status, is_prayed=True)


class MissedCheckBox(CheckBox):
    name = StringProperty()
    db_keys = ListProperty(defaultvalue=[])

    def __init__(self, **kwargs):
        super(MissedCheckBox, self).__init__(**kwargs)
        self.disabled = self.active = True
        set_children_color(self.parent, get_color_from_hex("B8D5CD"))

    def on_press(self):
        root = find_parent(self, Praying)
        time = self.name
        status = None

        for status in sorted(
                Status.list(time_name=time, is_prayed=False),
                key=lambda x: x.date,
                reverse=True,
        ):
            try:
                index = self.db_keys.index(status.pk)
                self.db_keys.pop(index)
                break
            except ValueError:
                pass

        if not status:
            return

        Status.update(status, is_prayed=True)

        layout = getattr(root.entrance.missed, "missed_{}".format(time))
        label = getattr(layout, "{}_count".format(time))

        count = max(0, (label.text and int(label.text) or 0) - 1)
        if count > 0:
            label.text = str(count)
            self.active = False
        else:
            label.text = ""
            self.disabled = True
            set_children_color(self.parent, get_color_from_hex("B8D5CD"))


class NewDateButton(ButtonBehavior, RoundedLabel):
    def _clear_widgets(self):
        root = find_parent(self, Praying)
        remove_set = []
        for child in root.data.children:
            if child.__class__ == DateLine:
                remove_set.append(child)
            if child.__class__ == Image and child.source == "assets/dark_trans.png":
                remove_set.append(child)
        for child in remove_set:
            root.data.remove_widget(child)

    def _refresh(self, is_prayed=False):
        root = find_parent(self, Praying)
        root.progressbar_path(
            path=list(
                reversed(
                    [
                        root.start_progress,
                        root.fetch_today_praying_times,
                        root.reset_missed_prays,
                        root.check_praying_status,
                        root.check_missed_prays(is_prayed=is_prayed),
                    ]
                )
            ),
            per_step=int(1000 / 9),
        )
        self._clear_widgets()

    def _new_record(self):
        root = find_parent(self, Praying)
        trans_image = Image(
            source="assets/dark_trans.png", allow_stretch=True, keep_ratio=False
        )
        root.data.add_widget(trans_image)
        root.data.add_widget(DateLine())

    def _add_new_record(self):
        day, month, year = (
            self.day.text,
            self.month.values.index(self.month.text) + 1,
            self.year.text,
        )

        try:
            date = datetime(*list(map(int, (year, month, day)))).date()
        except ValueError:
            set_color(self.day, get_color_from_hex("FF6666"))
            return

        for time in PRAYER_TIMES:
            Status.create(date=date, time_name=time, is_prayed=self.prayed.active)

        self._refresh(is_prayed=self.prayed.active)

    def on_press(self):
        if self.name == "new_record":
            self._new_record()
        if self.name == "new_record_add":
            self._add_new_record()
        if self.name == "new_record_cancel":
            self._clear_widgets()


class NewDateTextInput(TextInput):
    def time_check(self, text):
        if self.name == "day":
            return int(text) <= 31
        if self.name == "year":
            return int(text.ljust(4, "0")) <= datetime.now().year

    def insert_text(self, substring, from_undo=False):
        set_color(self, get_color_from_hex("FFFFFF"))
        if substring.isdigit() and self.time_check(self.text + substring):
            return super(NewDateTextInput, self).insert_text(
                substring, from_undo=from_undo
            )
        return super(NewDateTextInput, self).insert_text("", from_undo=from_undo)

    def do_backspace(self, from_undo=False, mode="bkspc"):
        set_color(self, get_color_from_hex("FFFFFF"))
        return super(NewDateTextInput, self).do_backspace(
            from_undo=from_undo, mode=mode
        )


class DateLine(FloatLayout):
    pass


class InfoButton(ButtonBehavior, Label):
    def on_press(self):
        pass


class Praying(ScreenManager):
    day = NumericProperty()
    month = NumericProperty()
    year = NumericProperty()
    weekday = NumericProperty()
    records = DictProperty()
    app_size = StringProperty(defaultvalue='0 MB')

    def __init__(self, **kwargs):
        super(Praying, self).__init__(**kwargs)

        self.today = datetime.now().date()
        self.day = self.today.day
        self.month = self.today.month
        self.year = self.today.year
        self.weekday = self.today.weekday()
        self.times = None
        self.country = None
        self.city = None
        self.app_size = self.calculate_app_size()
        check_none()
        self.progressbar_path(
            path=list(
                reversed(
                    [
                        self.fetch_countries,
                        self.fetch_selected_country,
                        self.fetch_cities,
                        self.fetch_selected_city,
                        self.fetch_today_praying_times,
                        self.check_praying_status,  # hold
                        self.check_missed_prays(),
                        self.check_counter,
                    ]
                )
            ),
            per_step=int(1000 / 6),
        )

        self.reward_success()
        # self.call = 0

    @staticmethod
    def calculate_app_size():
        return "{:.2f} MB".format(SQLiteDB.get_size() * 0.0009765625 * 0.0009765625)

    def progressbar_path(self, path=None, per_step=0):
        path = path or []
        try:
            path.pop()()
        except IndexError:
            self.transition = SlideTransition(direction="left")
            self.current = "entrance"
            return
        self.welcome.progressbar.value += per_step

        Clock.schedule_once(lambda dt: self.progressbar_path(path, per_step), 0.1)

    def animation_complete(self, animation, widget):
        self.entrance.remove_widget(widget)

    def reward_success(self):
        daily = Reward.get(name="daily")
        weekly = Reward.get(name="weekly")
        monthly = Reward.get(name="monthly")
        yearly = Reward.get(name="yearly")

        try:
            start_date = full_prayed_dates(min_date=True)
            end_date = full_prayed_dates(max_date=True)
            missing_between = fetch_missing_prays(start_date, end_date)
            end_date -= timedelta(days=missing_between)
            time_difference = relativedelta(end_date, start_date)
            calc_yearly = time_difference.years
            calc_monthly = time_difference.months
            calc_weekly = int(time_difference.days / 7)
            calc_daily = time_difference.days % 7
        except TypeError:
            calc_yearly = 0
            calc_monthly = 0
            calc_weekly = 0
            calc_daily = 0

        stars = []
        if calc_yearly > yearly.count:
            stars.append(Star(color=COLOR_CODES.get("purple")))
        if calc_monthly > monthly.count:
            stars.append(Star(color=COLOR_CODES.get("red")))
        if calc_weekly > weekly.count:
            stars.append(Star(color=COLOR_CODES.get("orange")))
        if calc_daily > daily.count:
            stars.append(Star(color=COLOR_CODES.get("yellow")))

        self.run_stars(stars)

        Reward.update(daily, count=calc_daily)
        Reward.update(weekly, count=calc_weekly)
        Reward.update(monthly, count=calc_monthly)
        Reward.update(yearly, count=calc_yearly)

        Clock.schedule_once(lambda dt: self.reward_success(), 0.5)

    def run_stars(self, star_set):
        try:
            star_widget = star_set.pop()
            self.entrance.add_widget(star_widget)
            anim = Animation(
                pos=(-1 * Window.size[0] / 2, Window.size[1] / 2), t="in_circ", d=1.5
            )
            anim.start(star_widget)
            anim.bind(on_complete=self.animation_complete)
        except IndexError:
            return
        Clock.schedule_once(lambda dt: self.run_stars(star_set), 0.5)

    def start_progress(self):
        self.transition = SlideTransition(direction="right")
        self.current = "welcome"

    @staticmethod
    def fetch_countries():

        # Time.delete()
        # Country.delete()
        # City.delete()

        fetch_countries()

    @staticmethod
    def fetch_cities():
        fetch_cities()

    def fetch_selected_country(self):
        self.country = fetch_selected_country()
        self.settings.country_selection.set_text()

    def fetch_selected_city(self):
        self.city = fetch_selected_city()
        self.settings.city_selection.set_text()
        self.settings.city_selection.values = sorted(
            list(map(lambda x: x.name, City.list(country_id=self.city.country_id)))
        )

    def fetch_today_praying_times(self):
        record = {}
        city = City.get(selected=True)
        times = Time.list(date=self.today, city_id=city.pk)

        if not times:
            for provider in (Aladhan(), Heroku(), CollectApi(),):
                try:
                    record = provider(self.today, self.city)
                    break
                except (HTTPError, IndexError) as e:
                    pass

            for time in record.items():
                Time.create(
                    city_id=city.pk,
                    time_name=time[0],
                    from_time=time[1][0],
                    to_time=time[1][1],
                    date=self.today,
                )
        self.times = Time.list(date=self.today, city_id=city.pk)

        self.check_praying_time_left()

    def check_praying_time_left(self):
        now = datetime.now()
        # now = datetime(2021, 3, 24, 14) + timedelta(seconds=self.call * 60)
        from_color = Color("#B8D5CD")
        to_color = Color("#FF6666")
        for praying_time_name in PRAYER_TIMES:
            praying_time_obj = list(
                filter(lambda x: x.time_name == praying_time_name, self.times)
            )[0]
            praying_time = praying_time_obj.from_time
            label = getattr(self.praying_times, "{}_time".format(praying_time_name))
            label.text = praying_time.strftime("%H:%M")

            if praying_time_obj.from_time <= now <= praying_time_obj.to_time:
                frame = int(
                    (
                            praying_time_obj.to_time - praying_time_obj.from_time
                    ).total_seconds()
                    / 60
                )
                index = int((now - praying_time_obj.from_time).total_seconds() / 60) - 1
                color_set = list(from_color.range_to(to_color, frame))
                current_hex = color_set[index].get_hex().strip("#")
                set_color(label, get_color_from_hex(current_hex))
        # self.call += 1
        Clock.schedule_once(lambda dt: self.check_praying_time_left(), 10)

    def check_praying_status(self):
        if not Status.get(date=self.today):
            for time_name in PRAYER_TIMES:
                Status.create(time_name=time_name, date=self.today)

        for pray_time in self.times:
            time_name = pray_time.time_name
            if Status.get(date=self.today, time_name=time_name).is_prayed:  # Prayed
                button = getattr(self.entrance, time_name)
                button.active = button.disabled = True
                set_children_color(button.parent, get_color_from_hex("B8D5CD"))
            elif datetime.now() > pray_time.to_time:  # Missed
                button = getattr(self.entrance, time_name)
                button.disabled = True
                set_children_color(button.parent, get_color_from_hex("FF6666"))

                layout = getattr(self.entrance.missed, "missed_{}".format(time_name))
                button = getattr(layout, "{}_button".format(time_name))
                label = getattr(layout, "{}_count".format(time_name))

                status = Status.get(time_name=time_name, date=self.today)
                if status.pk not in button.db_keys:
                    button.db_keys.append(status.pk)

                    button.active = button.disabled = False
                    label.text = str((label.text and int(label.text) or 0) + 1)
                    set_children_color(layout, get_color_from_hex("FF6666"))

            elif datetime.now() < pray_time.from_time:  # on time
                button = getattr(self.entrance, time_name)
                button.disabled = True
                set_children_color(button.parent, get_color_from_hex("D2D1BE"))
            else:  # wait for time
                button = getattr(self.entrance, time_name)
                button.disabled = button.active = False
                set_children_color(button.parent, get_color_from_hex("FFFFFF"))

        Clock.schedule_once(lambda dt: self.check_praying_status(), 0.5)

    def reset_missed_prays(self):
        times = {
            "sabah": None,
            "ogle": None,
            "ikindi": None,
            "aksam": None,
            "yatsi": None,
            "vitr": None,
        }
        for time in times:
            layout = getattr(self.entrance.missed, "missed_{}".format(time))
            button = getattr(layout, "{}_button".format(time))
            label = getattr(layout, "{}_count".format(time))
            button.active = button.disabled = True
            button.db_keys = []
            label.text = ""
            set_children_color(layout, get_color_from_hex("B8D5CD"))

    def check_missed_prays(self, is_prayed=False):
        def inner():
            times = {
                "sabah": None,
                "ogle": None,
                "ikindi": None,
                "aksam": None,
                "yatsi": None,
                "vitr": None,
            }
            visits = list(
                map(lambda x: x.date, set(filter(lambda x: x.date, Status.list())))
            )

            visits = sorted(visits)
            d1 = visits and visits[0] or datetime.now()
            d2 = visits and visits[-1] or datetime.now()
            days = set([d1 + timedelta(n) for n in range(1, int((d2 - d1).days))])
            chunks = []
            for day in days.difference(set(visits)):
                for time in times:
                    chunks.append(dict(time_name=time, date=day, is_prayed=is_prayed))
            if chunks:
                Status.create_bulk(chunks=chunks)

            for status in Status.list(is_prayed=False):
                if status.date == self.today:
                    continue

                layout = getattr(
                    self.entrance.missed, "missed_{}".format(status.time_name)
                )
                button = getattr(layout, "{}_button".format(status.time_name))
                label = getattr(layout, "{}_count".format(status.time_name))

                button.active = button.disabled = False
                button.db_keys.append(status.pk)
                label.text = str((label.text.isdigit() and int(label.text) or 0) + 1)
                set_children_color(layout, get_color_from_hex("FF6666"))
                times.pop(status.time_name, None)

            for time in times:
                layout = getattr(self.entrance.missed, "missed_{}".format(time))
                button = getattr(layout, "{}_button".format(time))
                if button.db_keys:
                    continue
                set_children_color(layout, get_color_from_hex("B8D5CD"))

        return inner

    def check_counter(self, **kwargs):
        now = datetime.now()
        records = Time.list(date=self.today)
        if not records:
            Clock.schedule_once(lambda dt: self.check_counter(), 0.5)
            return
        upcoming = None
        current = None
        total_second = 0
        for key in PRAYER_TIMES:
            record = list(filter(lambda x: x.time_name == key, records))[0]
            if record.from_time < now < record.to_time:
                current = record.to_time
                break
            if record.from_time > now:
                upcoming = record.from_time
                break

        if current is not None:
            total_second = int((current - now).total_seconds())
        if upcoming is not None:
            total_second = int((upcoming - now).total_seconds())

        hours, minutes, seconds = seconds_converter(total_second)
        self.entrance.info.hours.text = hours
        self.entrance.info.minutes.text = minutes
        self.entrance.info.seconds.text = seconds

        Clock.schedule_once(lambda dt: self.check_counter(), 0.5)

    def load_stars(self):
        daily = Reward.get(name="daily").count
        weekly = Reward.get(name="weekly").count
        monthly = Reward.get(name="monthly").count
        yearly = Reward.get(name="yearly").count

        self.data.stars.add_widget(
            RecordStar(text=str(daily), color=COLOR_CODES.get("yellow"))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(weekly), color=COLOR_CODES.get("orange"))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(monthly), color=COLOR_CODES.get("red"))
        )
        self.data.stars.add_widget(
            RecordStar(text=str(yearly), color=COLOR_CODES.get("purple"))
        )

    def load_more_missed_records(self):
        for child in self.data.missing_record.children:
            if child.__class__.__name__ == "Widget":
                self.data.missing_record.remove_widget(child)
                break

        existed_lines = len(self.data.missing_record.children)

        records = list(filter(lambda x: False in x.values(), self.records.values()))

        records = sorted(
            records,
            key=lambda x: datetime.strptime(x["pray_time"], "%Y-%m-%d"),
            reverse=True,
        )
        for rec in records[existed_lines: existed_lines + 10]:
            self.data.missing_record.add_widget(RecordLine(record=rec))
        self.data.missing_record.add_widget(Widget())

    def load_more_records(self):
        for child in self.data.record.children:
            if child.__class__.__name__ == "Widget":
                self.data.record.remove_widget(child)
                break

        existed_lines = len(self.data.record.children)

        records = list(self.records.values())

        records = sorted(
            records,
            key=lambda x: datetime.strptime(x["pray_time"], "%Y-%m-%d"),
            reverse=True,
        )
        for rec in records[existed_lines: existed_lines + 10]:
            self.data.record.add_widget(RecordLine(record=rec))
        self.data.record.add_widget(Widget())

    def switch_lang(self, lang=None):
        lang = lang or trans.lang
        trans.switch_lang(lang)
        for language in Language.list():
            selected = language.lang == lang
            Language.update(language, selected=selected)
        self.settings.lang_selection.set_text()


class PrayingApp(App):
    def __init__(self, **kwargs):
        super(PrayingApp, self).__init__(**kwargs)
        Builder.load_file("assets/praying.kv")
        self.title = "Kivy Praying"

    def build(self):
        try:
            lang = Language.get(selected=True).lang
            trans.switch_lang(lang)
        except AttributeError:
            pass
        fetch_countries()
        fetch_selected_country()
        fetch_cities()
        fetch_selected_city()
        return Praying()


if __name__ == "__main__":
    Window.clearcolor = get_color_from_hex("E2DDD5")
    Window.keyboard_anim_args = {"d": 0.2, "t": "in_out_expo"}
    Window.softinput_mode = "below_target"
    PrayingApp().run()
