from kivy.factory import Factory
from kivy.metrics import sp
from kivy.properties import ListProperty, BooleanProperty, ObjectProperty, string_types
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.dropdown import DropDown
from kivy.utils import get_color_from_hex

from config import set_children_color, find_parent
from main import trans, RoundedLabel
from models import Language, City


class SpinnerOption(ButtonBehavior, RoundedLabel):
    pass


class CustomSpinner(ButtonBehavior, RoundedLabel):
    values = ListProperty()
    text_autoupdate = BooleanProperty(False)
    option_cls = ObjectProperty(SpinnerOption)
    dropdown_cls = ObjectProperty(DropDown)
    is_open = BooleanProperty(False)
    sync_height = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._dropdown = None
        super(CustomSpinner, self).__init__(**kwargs)
        fbind = self.fbind
        build_dropdown = self._build_dropdown
        fbind('on_release', self._toggle_dropdown)
        fbind('dropdown_cls', build_dropdown)
        fbind('option_cls', build_dropdown)
        fbind('values', self._update_dropdown)
        fbind('size', self._update_dropdown_size)
        fbind('text_autoupdate', self._update_dropdown)
        build_dropdown()

    def set_text(self):
        raise NotImplemented

    def _build_dropdown(self, *largs):
        if self._dropdown:
            self._dropdown.unbind(on_select=self._on_dropdown_select)
            self._dropdown.unbind(on_dismiss=self._close_dropdown)
            self._dropdown.dismiss()
            self._dropdown = None
        cls = self.dropdown_cls
        if isinstance(cls, string_types):
            cls = Factory.get(cls)
        self._dropdown = cls()
        self._dropdown.bind(on_select=self._on_dropdown_select)
        self._dropdown.bind(on_dismiss=self._close_dropdown)
        self._update_dropdown()

    def _update_dropdown_size(self, *largs):
        if not self.sync_height:
            return
        dp = self._dropdown
        if not dp:
            return

        container = dp.container
        if not container:
            return
        h = self.height
        for item in container.children[:]:
            item.height = h

    def _update_dropdown(self, *largs):
        dp = self._dropdown
        cls = self.option_cls
        values = self.values
        text_autoupdate = self.text_autoupdate
        if isinstance(cls, string_types):
            cls = Factory.get(cls)
        dp.clear_widgets()
        for value in values:
            item = cls(text=value, font_size=sp(15), halign='center')
            item.height = sp(30)  # self.height if self.sync_height else item.height
            item.bind(on_release=lambda option: dp.select(option.text))
            dp.add_widget(item)
            set_children_color(item.parent, get_color_from_hex('D2D1BE'))
        self.set_text()
        if text_autoupdate:
            if values:
                if not self.text or self.text not in values:
                    self.text = values[0]
            else:
                self.text = ''

    def _toggle_dropdown(self, *largs):
        if self.values:
            self.is_open = not self.is_open

    def _close_dropdown(self, *largs):
        self.is_open = False

    def _on_dropdown_select(self, instance, data, *largs):
        self.text = data
        self.is_open = False

    def on_is_open(self, instance, value):
        if value:
            self._dropdown.open(self)
        else:
            if self._dropdown.attach_to:
                self._dropdown.dismiss()


class LangSpinner(CustomSpinner):
    values_dict = {'Türkçe': 'tr', 'English': 'en'}

    def set_text(self):
        try:
            lang = Language.get(selected=True).lang
        except AttributeError:
            lang = trans.lang
        self.text = dict(list(map(lambda x: list(reversed(list(x))), self.values_dict.items())))[lang]

    def _on_dropdown_select(self, instance, data, *largs):
        from main import Praying
        super(LangSpinner, self)._on_dropdown_select(instance=instance, data=data, *largs)
        root = find_parent(self, Praying)
        root.switch_lang(self.values_dict.get(data))


class CitySpinner(CustomSpinner):
    def __init__(self, **kwargs):
        super(CitySpinner, self).__init__(**kwargs)
        self.values = sorted(list(map(lambda x: x.name, City.list())))

    def set_text(self):
        self.text = City.get(selected=True).name

    def _on_dropdown_select(self, instance, data, *largs):
        from main import Praying
        super(CitySpinner, self)._on_dropdown_select(instance=instance, data=data, *largs)
        root = find_parent(self, Praying)
        
        for city in City.list():
            selected = city.name == data
            City.update(city, selected=selected)

        root.welcome.progressbar.value = 0

        root.progressbar_path(
            path=list(reversed([
                root.start_progress,
                root.fetch_selected_city,
                root.fetch_today_praying_times,
                root.check_praying_status,
                root.reset_missed_prays,
                root.check_missed_prays,
            ])),
            per_step=int(1000 / 6)
        )


class MonthSpinner(CustomSpinner):
    def set_text(self):
        return ''
