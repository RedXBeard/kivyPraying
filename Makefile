.PHONY: po mo

po:
	xgettext -Lpython --output=messages.pot main.py assets/praying.kv
	msgmerge --update --no-fuzzy-matching --backup=off assets/po/en.po messages.pot
	msgmerge --update --no-fuzzy-matching --backup=off assets/po/tr.po messages.pot

mo:
	mkdir -p assets/locales/en/LC_MESSAGES
	mkdir -p assets/locales/tr/LC_MESSAGES
	msgfmt -c -o assets/locales/en/LC_MESSAGES/kivypraying.mo assets/po/en.po
	msgfmt -c -o assets/locales/tr/LC_MESSAGES/kivypraying.mo assets/po/tr.po
