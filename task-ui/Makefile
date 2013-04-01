all: taskui

taskui: taskui.vala
	valac -o $@ --pkg gtk+-2.0 --pkg json-glib-1.0 $<

clean:
	rm -f taskui

debian-depends:
	sudo apt-get install valac libgtk2.0-dev libjson-glib-dev
