# pyclidata 0.2.1

* Added `install_instantclient()`, a Windows-only one-time setup step
  that downloads and installs Oracle Instant Client automatically,
  fixing `DPY-3015` connection errors for accounts (like CLIDATA's own)
  that need thick mode. See the README's "Connection error: DPY-3015"
  section.

* `open_clidatadb()`/`open_oracledb()` errors now include a specific,
  actionable hint when a `DPY-3015` failure is caused by a missing
  Oracle Instant Client, instead of just relaying Oracle's raw message.


# pyclidata 0.2.0

Initial release. Connect to CLIDATA/Oracle (`open_clidatadb()`), store
credentials (`set_user_creds()`), and discover/fetch tables and views
(`list_tables()`, `list_views()`, `list_variables()`, `get_table()`).
