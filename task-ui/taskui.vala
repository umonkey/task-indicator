using Gtk;

public class TaskWindow : Window {
	public TreeView view;
	public ListStore model;

	public TaskWindow() {
		this.title = "TaskWarrior";
		this.border_width = 0;
		this.window_position = WindowPosition.CENTER;
		this.set_default_size(250, 100);
		this.destroy.connect(Gtk.main_quit);

		this.icon = new Gdk.Pixbuf.from_file("icon.png");

		this.setup_treeview(this);

		this.fetch_tasks();
	}

	private void setup_treeview(Window parent) {
		this.model = new ListStore(4, typeof(string), typeof(string), typeof(string), typeof(string));
		this.view = new TreeView();

		this.view.set_model(this.model);

		this.view.insert_column_with_attributes(-1, "Id", new CellRendererText(), "text", 0);
		this.view.insert_column_with_attributes(-1, "Project", new CellRendererText(), "text", 1);
		this.view.insert_column_with_attributes(-1, "Description", new CellRendererText(), "text", 2);

		var scroll = new ScrolledWindow(null, null);
		scroll.set_policy(PolicyType.AUTOMATIC, PolicyType.AUTOMATIC);
		scroll.add(this.view);

		parent.add(scroll);
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
