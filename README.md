# pyclidata

Thin `python-oracledb` wrapper for connecting to a
[CLIDATA](https://www.clidata.cz/) Oracle database -- the climate database
management system developed by ATACO, used operationally at ANAM-BF and
30+ other national meteorological services. This package is not CLIDATA
itself, just a thin connector for it, defaulting to ANAM-BF's instance.
Credentials are stored securely via `keyring` (OS credential store),
never in plain text.

This is the Python port of the [rclidata](../rclidata) R package. It uses
`python-oracledb`, which needs no JDK and no driver jar -- unlike the R
package (which wraps RJDBC and needs a JVM + `ojdbc` jar installed
first), there is no separate Java setup step here at all.

By default `python-oracledb` runs in pure-Python **thin mode** -- no
Oracle Instant Client needed either. However, some Oracle accounts
(including CLIDATA's own) use a legacy pre-11G password verifier that
thin mode simply can't authenticate (`DPY-3015`). For that, `pyclidata`
auto-upgrades to **thick mode** whenever an Oracle Instant Client is
available, and stays in thin mode otherwise -- see
[Thick mode / Instant Client](#thick-mode--instant-client) below.

The connection itself is a standard Oracle connection -- nothing about it
is CLIDATA-specific beyond the default host/service (see `set_host()`) --
so it works against most any Oracle database you have credentials for,
not just CLIDATA. `open_oracledb()`/`close_oracledb()` are aliases of
`open_clidatadb()`/`close_clidatadb()` for that more general use. This
package is developed against and tested with a CLIDATA instance.

## Setup

This project is managed with [pixi](https://pixi.sh/). From this directory:

```bash
pixi install
```

That resolves and installs everything declared in `pyproject.toml`
(`oracledb`, `keyring`, `pandas`, `ibis-framework[oracle]`, and
`pyclidata` itself in editable mode) into a local `.pixi` environment --
no JDK required. On macOS/Linux it also installs the `oracle-instant-client`
conda package automatically, for thick-mode support (see below).

## Platform support

`pyclidata` installs and works on **macOS (Intel and Apple Silicon),
Linux x86_64, and Windows x64** -- verified both via `pip` dependency
resolution against PyPI and via `pixi install` across all four.

**It does not work on Windows ARM64 (`win_arm64`).** Root cause:
`pyarrow` -- a transitive dependency of `ibis-framework[oracle]`, needed
for `get_table()`'s lazy table support -- has never published `win_arm64`
wheels, in any version. This is an upstream
[Apache Arrow](https://arrow.apache.org/) limitation, not something
fixable in `pyclidata` itself without dropping `ibis`/lazy tables or
making them an optional extra. Not currently planned unless it turns out
someone actually needs it there.

## Usage

```python
import pyclidata as clidata

# Store your credentials once (password entered via secure, non-echoed
# prompt) -- persists your username (never the password) to
# ~/.config/pyclidata/config.env, so future sessions, including
# non-interactive ones, don't need this call repeated
clidata.set_user_creds("jdupont")

# Only needed if the DB isn't at the default clidatadb1:1521/CLIDATA --
# also persists by default
clidata.set_host(host="10.0.0.5")

con = clidata.open_clidatadb()
import pandas as pd
pd.read_sql("SELECT * FROM some_table WHERE ROWNUM <= 5", con)
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

Connection defaults: `host = "clidatadb1"`, `port = "1521"`, `service = "CLIDATA"`.

## Thick mode / Instant Client

`python-oracledb` defaults to pure-Python thin mode -- no native Oracle
libraries needed. But CLIDATA's own DB account (and likely others on
older/operational Oracle instances) uses a legacy pre-11G password
verifier that thin mode can't authenticate at all, failing with:

```
DPY-3015: password verifier type 0x939 is not supported by python-oracledb in thin mode
```

`pyclidata` handles this automatically: on `import`, it looks for an
Oracle Instant Client and switches the whole process to thick mode if
one is found, silently staying in thin mode otherwise (this is
`python-oracledb`'s own documented pattern for supporting both). On
macOS and Linux, `pyproject.toml` declares the `oracle-instant-client`
conda package so `pixi install` sets this up automatically -- nothing
manual required. On other platforms (or if you're consuming `pyclidata`
as an editable dependency from another pixi project), add it to that
project's own manifest:

```bash
pixi add oracle-instant-client
```

(This is a conda package, not a PyPI one -- it doesn't propagate
automatically through `pyclidata`'s own dependency on it the way a
regular Python dependency would; each consuming project needs it
declared directly.)

## Differences from the R package (`rclidata`)

- **No JDK/driver install.** Unlike R's RJDBC (which always needs a JVM
  + `ojdbc` jar), `install_jdk()`/`install_ojdbc()` have no Python
  equivalent here -- `python-oracledb` needs neither in thin mode, and
  thick mode (see above) is set up automatically via a conda package
  when needed, not a separate manual install step.
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
