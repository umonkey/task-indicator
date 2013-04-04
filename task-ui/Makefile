all: taskui

taskui: taskui.vala
	valac -o $@ --pkg gtk+-2.0 --pkg json-glib-1.0 --pkg appindicator-0.1 $<

clean:
	rm -f taskui

debian-depends:
	sudo apt-get install valac libgtk2.0-dev libjson-glib-dev libappindicator-dev

install-icons:
	sudo cp taskui.svg /usr/share/icons/hicolor/scalable/
	sudo cp taskui-active.svg /usr/share/icons/hicolor/scalable/
	#sudo cp taskui.svg /usr/share/icons/hicolor/24x24/
	sudo cp taskui.svg /usr/share/pixmaps/
	sudo cp taskui-active.svg /usr/share/pixmaps/
