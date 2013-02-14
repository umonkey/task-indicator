using Gtk;

public class TaskWindow : Window {
	public TreeView view;
	public ListStore model;
	public TreeModelFilter filter;
	public Entry search;

	public TaskWindow() {
		this.title = "TaskWarrior";
		this.border_width = 2;
		this.window_position = WindowPosition.CENTER;
		this.set_default_size(250, 100);
		this.destroy.connect(Gtk.main_quit);

		this.icon = new Gdk.Pixbuf.from_file("icon.png");

		var vbox = new VBox(false, 4);
		vbox.pack_start(this.setup_search_field(), false);
		vbox.pack_start(this.setup_treeview());

		this.add(vbox);

		this.fetch_tasks();
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
		parser.load_from_data(tasks_fixed);

		TreeIter iter;

		foreach (var _item in parser.get_root().get_array().get_elements()) {
			var item = _item.get_object();

			this.model.append(out iter);
			this.model.set(iter,
				0, "%lld".printf(item.get_int_member("id")),
				1, item.get_string_member("project"),
				2, item.get_string_member("description"));
		}
	}

	private bool get_program_output(string[] command, out string ls_stdout) {
		try {
			string[] spawn_env = Environ.get();

			string ls_stderr;
			int ls_status;

			Process.spawn_sync("/", command, spawn_env, SpawnFlags.SEARCH_PATH,
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
