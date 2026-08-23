# pyclidata

Thin `python-oracledb` wrapper for connecting to a
[CLIDATA](https://www.clidata.cz/) Oracle database -- the climate database
management system developed by ATACO, used operationally at ANAM-BF and
30+ other national meteorological services. This package is not CLIDATA
itself, just a thin connector for it, defaulting to ANAM-BF's instance.
Credentials are stored securely via `keyring` (OS credential store),
never in plain text.

This is the Python port of the [rclidata](https://github.com/oousmane/rclidata) R package. It uses
`python-oracledb`, which needs no JDK and no driver jar -- unlike the R
package (which wraps RJDBC and needs a JVM + `ojdbc` jar installed
first), there is no separate Java setup step here at all.

Some Oracle DB (including CLIDATA) use an older password
format that requires an extra one-time setup step -- see
[Connection error: DPY-3015](#connection-error-dpy-3015) below if you
run into that.

The connection itself is a standard Oracle connection -- nothing about it
is CLIDATA-specific beyond the default host/service (see `set_host()`) --
so it works against most any Oracle database you have credentials for,
not just CLIDATA. `open_oracledb()`/`close_oracledb()` are aliases of
`open_clidatadb()`/`close_clidatadb()` for that more general use. This
package is developed against and tested with a CLIDATA instance.

## Installation

pyclidata is managed with [pixi](https://pixi.sh/). From this directory:

```bash
pixi install
```

This installs everything you need -- no separate JDK or driver setup
required.

## Platform support

pyclidata works on **macOS (Intel and Apple Silicon), Linux (x86_64),
and Windows (x64)**.

Windows on ARM64 is not currently supported (a required dependency,
`pyarrow`, isn't available there yet).

## Usage

```python
import pyclidata as clidata

# Store your credentials once (password entered via secure, non-echoed
# prompt) -- persists your username (never the password) to
# ~/.config/pyclidata/config.env, so future sessions, including
# non-interactive ones, don't need this call repeated
clidata.set_user_creds("oousmane")

# Only needed if the DB isn't at the default clidatadb1:1521/CLIDATA --
# also persists by default
clidata.set_host(host="10.0.0.5")

con = clidata.open_clidatadb()

rdata_r = clidata.get_table("RDATA_R",con = con)
rdata_r
clidata.close_clidatadb(con)

# get_table() always returns a lazy ibis Table expression -- safe for
# tables too large to load in full (CLIDATA's own V_DAY_ALL_NULL, for
# instance, is 1.5+ billion rows). Nothing runs until you materialize it;
# .filter()/.select()/.limit() chained on first are pushed down to SQL
# rather than pulling everything into memory first.
con = clidata.open_clidatadb()
v_day = clidata.get_table("V_DAY_ALL_NULL", con=con)
v_day.filter(v_day["YEAR"] == 2024).to_pandas()  # only this filtered slice is fetched
clidata.close_clidatadb(con)

# Discover what's there
con = clidata.open_clidatadb()
clidata.list_tables(con)                          # tables in the CLIDATA schema
clidata.list_views(con)                           # views in the CLIDATA schema
clidata.list_variables("V_DAY_ALL_NULL", con=con) # its columns (table or view)
# or, from an already-fetched get_table() result:
clidata.list_variables(clidata.get_table("V_DAY_ALL_NULL", con=con))
clidata.close_clidatadb(con)

# Connecting to a different (non-CLIDATA) Oracle database
clidata.set_host(host="10.0.0.9", port="1521", service="OTHERDB")
con = clidata.open_oracledb(user="someuser")
clidata.close_oracledb(con)
```

## Examples

Full runnable examples (plain script and notebooks, pulling real CLIDATA
data both the wide-format and long-format ways) live in a companion repo:
[pyclidata-examples](https://github.com/oousmane/pyclidata-examples).

```bash
git clone https://github.com/oousmane/pyclidata-examples.git
cd pyclidata-examples
pixi install
pixi run python example.py
```

See that repo's own README for the notebook versions and first-time
credential setup.

## Functions

| Function              | Purpose                                                        |
|------------------------|------------------------------------------------------------------|
| `set_user_creds()`    | Store username/password securely via `keyring`, persisting the username |
| `get_user_creds()`    | Retrieve stored credentials                                     |
| `set_host()`          | Override host/port/service, persisting it                       |
| `get_host()`          | Get current host/port/service (defaults if unset)                |
| `open_clidatadb()`    | Build and return a ready-to-use `oracledb.Connection`            |
| `close_clidatadb()`   | Close a connection returned by `open_clidatadb()`                |
| `open_oracledb()`     | Alias of `open_clidatadb()`, for connecting to a non-CLIDATA Oracle DB |
| `close_oracledb()`    | Alias of `close_clidatadb()`                                     |
| `get_table()`         | Get a CLIDATA table/view as a lazy ibis `Table` |
| `list_tables()`       | List tables in a schema (default: the CLIDATA schema)            |
| `list_views()`        | List views in a schema (default: the CLIDATA schema)             |
| `list_variables()`    | List the columns of a table/view or a `get_table()` result       |
| `install_instantclient()` | Windows only: one-time setup to fix `DPY-3015` connection errors ([details](#connection-error-dpy-3015)) |

Connection defaults: `host = "clidatadb1"`, `port = "1521"`, `service = "CLIDATA"`.

## Connection error: DPY-3015

Some Oracle accounts -- including CLIDATA's own -- use an older password
format that pyclidata can't authenticate against out of the box. If
`open_clidatadb()` fails with an error like:

```
DPY-3015: password verifier type 0x939 is not supported by python-oracledb in thin mode
```

your account needs a one-time additional setup step. What to do depends
on your platform:

**macOS and Linux** -- nothing to do. `pixi install` already set up
everything required; if you're still seeing this error, run `pixi
install` again to make sure your environment is up to date.

**Windows** -- run this once:

```python
import pyclidata as clidata
clidata.install_instantclient()
```

This sets up the missing piece automatically.

> **Important:** close this Python session completely and open a new
> one before connecting -- re-running `open_clidatadb()` in the same
> session will still fail. Once you're in a fresh session, connect as
> usual.

If the download fails, Oracle may have retired the specific package
version pyclidata points to. Download the current "Instant Client Basic
Light" package for Windows x64 yourself from [Oracle's downloads
page](https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html),
copy its link, and pass it in directly:

```python
clidata.install_instantclient(url="<link you copied>")
```

## Differences from the R package (`rclidata`)

- **No JDK/driver install.** Unlike R's RJDBC (which always needs a JVM
  + `ojdbc` jar), `install_jdk()`/`install_ojdbc()` have no Python
  equivalent here -- `python-oracledb` needs neither by default, and the
  occasional extra setup step some accounts need (see
  [Connection error: DPY-3015](#connection-error-dpy-3015)) is one line,
  not a manual driver install.
- **`get_table()` is lazy via [ibis](https://ibis-project.org/) instead
  of `dbplyr`.** Same idea as R -- filters/selects are pushed down to
  SQL and nothing is fetched until you materialize (`.to_pandas()`,
  `.execute()`) -- different underlying SQL-compilation library. Ibis
  opens its own connection to the same target/credentials (needed to
  compile and run SQL lazily), cached per `con`, alongside the raw
  `oracledb.Connection` used by `list_tables()`/`list_views()`/
  `list_variables()`. (Schema introspection for `get_table()` is done
  by `pyclidata` itself rather than ibis's own, to work around a
  [known ibis bug](https://github.com/ibis-project/ibis/issues/10403)
  that breaks it on any pre-23c Oracle Database -- see `tables.py`.)
- **Config persists to `~/.config/pyclidata/config.env`** instead of
  `~/.Renviron`, loaded automatically on `import pyclidata` (mirroring R
  sourcing `~/.Renviron` at every startup).

## Development

```bash
pixi run test
```
