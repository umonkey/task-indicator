using Gtk;
using AppIndicator;


public class TaskWindow : Window {
	public TreeView view;
	public ListStore model;
	public TreeModelFilter filter;
	public Entry search;
	public Gdk.Pixbuf app_icon;

	public Indicator indicator;
	public Gtk.MenuItem item_total;

	public TaskWindow() {
		this.title = "TaskWarrior";
		this.border_width = 2;
		this.window_position = WindowPosition.CENTER;
		this.set_default_size(600, 300);
		this.setup_app_icon();

		// this.destroy.connect(Gtk.main_quit);
		this.delete_event.connect(() => {
			this.hide();
			return true;
		});

		var vbox = new VBox(false, 4);
		vbox.pack_start(this.setup_search_field(), false);
		vbox.pack_start(this.setup_treeview());

		this.add(vbox);

		this.setup_indicator();
		this.fetch_tasks();
	}

	/**
	 * Loads the application icon.
	 *
	 * The use of this property is unknown, perhaps some window managers
	 * display it in the window corner.  The icon used in the Unity app bar and
	 * in the alt-tab window switcher is read directly from the system folder
	 * /usr/share/pixmaps/taskui.svg.
	 */
	private void setup_app_icon() {
		try {
			this.app_icon = new Gdk.Pixbuf.from_file("taskui.svg");
		} catch (GLib.Error e) {
			stderr.printf("Unable to load application icon: %s.\n", e.message);
			return;
		}

		this.icon = this.app_icon;
	}

	private void setup_indicator() {
		this.indicator = new Indicator(this.title, "taskui",
			IndicatorCategory.APPLICATION_STATUS);
		this.indicator.set_status(IndicatorStatus.ACTIVE);
		this.indicator.set_attention_icon("taskui-active");

		var menu = new Gtk.Menu();

		var item = new Gtk.MenuItem.with_label("Too many tasks.");
		item.sensitive = false;
		item.show();
		menu.append(item);
		this.item_total = item;

		item = new Gtk.MenuItem();
		item.show();
		menu.append(item);

		item = new Gtk.MenuItem.with_label("Show");
		item.show();
		item.activate.connect(() => {
				this.show();
				// indicator.set_status(IndicatorStatus.ATTENTION);
		});
		menu.append(item);

		item = new Gtk.MenuItem.with_label("Exit");
		item.show();
		item.activate.connect(() => {
				Gtk.main_quit();
		});
		menu.append(item);

		this.indicator.set_menu(menu);
	}

	private Widget setup_search_field() {
		this.search = new Entry();

		this.search.changed.connect(() => {
			this.filter.refilter();
		});

		return this.search;
	}

	private Widget setup_treeview() {
		this.model = new ListStore(4, typeof(string), typeof(string), typeof(string), typeof(string));

		this.filter = new TreeModelFilter(this.model, null);
		this.filter.set_visible_func(this.filter_tree);

		this.view = new TreeView();
		this.view.set_model(this.filter);

		this.view.insert_column_with_attributes(-1, "Id", new CellRendererText(), "text", 0);
		this.view.insert_column_with_attributes(-1, "Project", new CellRendererText(), "text", 1);
		this.view.insert_column_with_attributes(-1, "Description", new CellRendererText(), "text", 2);

		var scroll = new ScrolledWindow(null, null);
		scroll.set_policy(PolicyType.AUTOMATIC, PolicyType.AUTOMATIC);
		scroll.add(this.view);

		return scroll;
	}

	private bool filter_tree(TreeModel model, TreeIter iter) {
		string query = this.search.text;
		if (query.length == 0)
			return true;

		string text;

		model.get(iter, 1, out text, -1);
		if (text == null)
			return false;
		else if (text.index_of(query) >= 0)
			return true;

		model.get(iter, 2, out text, -1);
		if (text == null)
			return false;
		else if (text.index_of(query) >= 0)
			return true;

		return false;
	}

	private void fetch_tasks() {
		string tasks;

		if (!this.get_program_output({"task", "status:pending", "export"}, out tasks)) {
			stderr.printf("Could not fetch tasks.\n");
			return;
		}

		string tasks_fixed = "[%s]".printf(tasks);

		var parser = new Json.Parser();
		try {
			parser.load_from_data(tasks_fixed);

			TreeIter iter;

			int count = 0;
			foreach (var _item in parser.get_root().get_array().get_elements()) {
				var item = _item.get_object();

				this.model.append(out iter);
				this.model.set(iter,
					0, "%s".printf(item.get_int_member("id").to_string()),
					1, item.get_string_member("project"),
					2, item.get_string_member("description"));

				count++;
			}

			var msg = "%u pending tasks.".printf(count);
			this.item_total.label = msg;
		} catch (GLib.Error e) {
			stderr.printf("Could not load JSON: %s.\n", e.message);
		}
	}

	private bool get_program_output(string[] command, out string ls_stdout) {
		try {
			string ls_stderr;
			int ls_status;

			Process.spawn_sync("/", command, null, SpawnFlags.SEARCH_PATH,
				null, out ls_stdout, out ls_stderr, out ls_status);

			// stdout.printf("output: %s\n", ls_stdout);
			return true;
		} catch (SpawnError e) {
			stderr.printf("Error: %s\n", e.message);
			return false;
		}
	}
}


public static int main (string[] args) {
    Gtk.init(ref args);

	var app = new TaskWindow();
	app.show_all();
    Gtk.main();

    return 0;
}
