# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

We use the following:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

## [unreleased]

### Added

- Shared resources: the `resource_file` of a solution and of its parents is downloaded on install, checked against its `hash`, and shared between solutions that ask for the same content (scope `global`, `catalog` or `solution`) (!331). A failed download or a hash mismatch fails `album install`. `album deploy` validates the resource file. Solutions that are installed at the same time and share a resource download it once (!337, #277). Replaces !253.
- `CITATION.cff` lists everyone who contributed to album; the package authors in `pyproject.toml` stay the core team. The README and the citation text of released solutions cite the album paper v2 (!332).
- `album run --install` installs the solution first if it is not installed (!337, #250)
- `album upgrade-solutions [solution ...]` installs the latest version of installed solutions from their catalogs and uninstalls the versions it replaces (!341, #194, #244). It upgrades their catalogs first, as `album upgrade` does. A replaced version stays as long as another installed solution runs in its environment, and the newest installed version of a solution always stays: a parent the upgraded solutions no longer run in is listed, not uninstalled. Without a solution, all installed solutions are upgraded; solutions installed from a file, URL or DOI are not. `--dry-run` shows what would happen, `--json` prints the result, and `Album.upgrade_solutions()` does the same from Python. `album upgrade`, `album upgrade-solutions` and `album install --reinstall` run one at a time: another album process waits until the running one is done.
- `album install --reinstall` installs an installed solution again, for example after it was deployed again with the same version (!341, #79). It is installed from its catalog, or from the file, URL or DOI given; a solution installed from a file, URL or DOI and given by `group:name:version` is installed from its copy in album. The solutions running in its environment are installed again with it if they come from a catalog; if one of them was installed from a file, URL or DOI, nothing is changed, as album leaves the environment of such a solution untouched. Everything is downloaded before anything is uninstalled, so a failed download changes nothing.
- `album deploy --no-replicability` (!348, #265). Without it, `album deploy` stops at a solution that is not technically replicable and names the reasons: a resource from a url without a hash, a parent not given by a DOI or by `group:name:version` (e.g. by a path), and a version that replaces one deployed before; replacing a `-SNAPSHOT` version only gets a warning. With it, the solution is deployed. These reasons, and those that do not stop the deployment, a resource without a hash and a deployment without a lock file, are stored with the solution in `solution.yml` under `replicability`. `album deploy` also warns about a resource from a url with a hash, which can become unavailable, and when the files of a solution take more than 5 MB in the catalog. The warning that a shared resource has no hash is one of these reasons now.
- `album install` says when a solution is not technically replicable (!349, #265): the reasons `album deploy` stored with it, that it has no lock file and its environment is solved now (before, without a word), and that it is installed from a url. `album run` does not repeat them. A solution with a lock file still fails to install when conda-lock is not found, now with a message that names `ENVIRONMENT_CONDA_LOCK_PATH` instead of "No conda-lock executable found!".
- `album install --no-conda-lock` (!349, #265) solves the environment of a solution instead of installing it from its lock file, e.g. when the lock file does not install on this system, with a warning that it is not technically replicable. It also applies with `--reinstall`, and to a parent installed with the solution. The errors when conda-lock is not found or the lock file does not install name it.

### Changed

- Git authentication: `add-catalog`, `deploy` and `undeploy` send fewer requests to the catalog remote, so without a git credential helper they ask for the password less often (`deploy` to a direct catalog: 2 times instead of 6) (!192). `deploy` and `undeploy` push the tag change together with the commit in one atomic push, so a failed push no longer leaves a commit without its tag.
- album's version and authors are read from the installed package metadata (`pyproject.toml`) only (!219). `album-catalog-admin` reports album's version instead of 0.1.0, and the first commit of a catalog created with `album clone template:<name>` is again made by `album <album@kyleharrington.com>` instead of an identity listing three addresses.
- The Anaconda defaults channels are kept out of album's own environments: the default environment of a solution without an environment file, `album.yml` and `album-full.yml` add `nodefaults` after `conda-forge` (!254). Environment files that come with a solution are not changed.
- `album deploy --force-deploy` now enables overwriting, as its help text says; the flag used to be inverted (`store_false`) (!291). Without the flag, `album deploy` no longer overwrites a solution that is already deployed to a direct catalog, and with the flag it now does.
- Zenodo client: unknown status codes, non-JSON errors, `to_dict()` side effect, stray print, `--force-retrieve type=bool` (!306). `--force-retrieve` of `album-catalog-admin` is now a plain flag: before, any value, including `False`, enabled it; now a value such as `--force-retrieve=True`, as in the album-docs catalog CI template, is rejected, so pass the bare flag.
- Tooling: the Docker image is based on `ubuntu:24.04` instead of the unpinned `ubuntu`; `.pre-commit-config.yaml` has one pyupgrade entry and the new stage names, and needs pre-commit 3.2.0 or later (!322)
- `--allow-recursive`: the album-in-album check recognises every conda and pip spelling of an album dependency, and every spec other than an unpinned album or the running version (another version, a range, `~=`, a URL) now needs `--allow-recursive`; before, most of them passed without a warning (!329). The flag is passed on to the installation of the parent, and its help says what it allows.
- CI: the unit tests also run on Python 3.10, the oldest version album supports (!330)
- CI: the Linux jobs install the dev versions of album-solution-api and album-environments when `api_change_runner` or `api_change_env` appears anywhere in the branch name, not only at its start (!333)
- CI: the jobs create the album environment with `zstandard` from conda-forge (!338). `zstandard`, which conda-lock needs and album-environments installs, has no wheels for Python 3.15 on PyPI yet, and the runners have no compiler to build it, so pip failed on 3.15. PyYAML, which has no 3.15 wheels either, is built without libyaml (`PYYAML_FORCE_LIBYAML=0`): on Windows its build failed without a compiler instead of falling back to pure Python.
- README with badges, a quick start, the Album suite and where Album is listed; the PyPI sidebar links to the changelog, the paper, conda-forge, Docker Hub and Helmholtz RSD (!335)
- album only recognizes its long options in full (!337). Every argument album does not know is passed on to the solution, but an abbreviation was taken for an album option: a solution argument `--js` or `--lo` became album's `--json` or `--log`. This also applies to the commands of plugins and to `album-catalog-admin`.
- A solution that is not installed is reported by name, with the call that installs it: `Solution "<solution>" is not installed. "album install <solution>" installs it.` `run`, `test`, `repl` and `uninstall` used to say "Solution seems not to be installed! Please install solution first!", or "Solution not found in database!" for a solution file that was never installed (!337).
- `requires-python` has no upper bound anymore (was `<3.15`) (!337). On Python 3.15, pip skipped every album release with the bound and installed album 0.12.0, the newest release without it. Python 3.15 is not tested in CI yet.
- album checks the operating system the same way everywhere, with `sys.platform` (`sys.platform == "win32"` for Windows), instead of `sys.platform` in some places and `platform.system()` in others (!342, #241). Nothing changes for users.
- `album upgrade` warns when an installed solution changed in its catalog without a new version, and names the `album install --reinstall` call that installs it again (!341, #194). The installation stays as it was until then.
- A relative path of an `environment_file` or `resource_file` starts at the solution folder, the folder `solution.py` is deployed or installed from, e.g. `"environment.yml"` (!343, #225). A solution that names a file by a relative path is installed and deployed as its folder: `album install` and `album deploy` of its `solution.py` alone fail with a message to give the folder instead. A solution without one is installed and deployed as `solution.py` alone as before. A file that does not exist fails `album install` and `album deploy` with a message that names the file album looked for. `album install --reinstall` checks this before it uninstalls anything: a solution whose files are gone is uninstalled and installed by hand. `album deploy` writes the environment album installs, the one of the solution with album-solution-api, which conda-lock locks, to `solution.environment.yml` next to the solution, also without a lock file, and the resource list to `solution.resources.yml`. Installing a deployed solution takes these instead of the files the solution names, so an environment or resource file outside the solution folder also works after `album deploy` (#253), and without its lock file a deployed solution gets the environment that was locked.
- A parent given by `group`, `name` and `version` is looked up in the catalog of the solution first (!349, #265). Before, album took the first match of all catalogs, solutions installed from a file first, so which parent a solution got depended on the catalogs of the installing album. A parent found only in another catalog is still installed, with a warning that the solution is not technically replicable. `album uninstall --uninstall-deps` removes the parent from the catalog the collection records for it.
- `album install --reinstall` checks the parents of the solutions it installs again, and retrieves their resources, before it uninstalls anything (!350, #265): a parent that is not found, one with another API version, or a resource that cannot be downloaded stops it, and nothing is changed. Before, such a solution was uninstalled and not installed again. A resource with the scope `solution` they have is kept, not downloaded again.

### Deprecated

- Solution plugins (`dependencies.plugins`), and with them album-socket and album-client: a solution that declares plugins logs a warning when it runs; the plugins are still activated (!324, #266)
- album-server (`album server`) is deprecated, and its repository is archived (#268). Running solutions remotely stays a goal (#276).

### Removed

- `pexpect` and `pre-commit` are no longer runtime dependencies of album; only its tests and its developers use them (!334). Updating album does not uninstall them.
- `DefaultValues.server_port` and `DefaultValues.server_host`: album never used them, only the album-server and album-socket plugins read them, and both are archived (!336, #268, #266).

### Fixed

- Legacy runner: parse test-goal arguments after `pre_test()`, so a required argument can come from it (!290)
- DOI resolution: accept the `/records/<id>` URL form Zenodo redirects to (!292)
- Resolving an ambiguous name raises `IndexError` when no candidate is installed (!293)
- `album clone template:<unknown>` succeeds silently; its `LookupError` message is never formatted (!294)
- Catalog index: solution versions are ordered as strings (!295)
- Any input containing one slash is treated as a DOI (!296)
- Argument description is optional in the schema but mandatory in the code (!297)
- Framework sanity check inspects the current working directory (!299)
- Resource download: the error path raises `KeyError`/`TypeError` itself (!300)
- `url_operations.download` leaks file descriptors and ignores HTTP errors (!301)
- `Database.is_created(close=True)` and `next_id(close=True)` leave a closed connection cached (!302)
- Repository context managers do not close the repo when the body raises (!303)
- Migration failures are swallowed and the backup restore path is hard-coded (!304)
- `uninstall` crashes with `remove_environment(None)` when the solution file cannot be loaded (!305)
- `undeploy`: tag lookup by prefix mixes up solutions whose names share a prefix (!307)
- Parent detection for DB-loaded solutions: cleanup removes the parent environment (!308)
- `git_operations`: debug log dereferences parent before the `None` check; misleading `force_download` docstring (!309)
- Every Album instance wipes the shared tmp directory (!310). Each instance now uses its own folder in `<base>/tmp/`, removed when the instance is closed, and leftovers older than 7 days are removed on startup. `IConfiguration` has a new abstract method `close()`.
- `last_execution` is bumped on every DB update instead of on run (!311)
- Text files are opened without an explicit encoding (!312). `album deploy` now reads a solution's `CHANGELOG.md` as UTF-8, so one with non-ASCII text in cp1252, as older album versions wrote it on Windows, fails with a `UnicodeDecodeError`.
- Dead code and logic slips: unreachable install check, convoluted test routine condition, `close()` rebuilding handlers, `is_cache()` crashing on an empty source (!313)
- Resource manager: `.yaml` environment files are rejected and an existing setuptools spec gets a second pin (!314)
- Parallel installs: a second album process removes the installation the first one is still running (!316, #186). Installing, uninstalling and downloading a solution hold a lock per solution in `<base>/locks/`; a process waits (up to 2 hours) only for another one working on the same solution or its parent, and a failed or interrupted installation is removed right away.
- A solution whose parent has a parent runs in an environment that does not exist (!317, #264)
- `album search`: keywords are matched case-sensitively (!318)
- Test aggregators run the whole suite when they are imported (!319)
- Deprecated `Logger.warn` and `Thread.setDaemon` calls; tree views (`album index`, `album update`) lose their closing line from the 258th entry on; re-raises drop their cause (!320)
- Catalog handler: metadata JSON is built by string concatenation, so catalog names with quotes or backslashes break it; a name clash is reported as "Cannot add catalog twice" (!321)
- Collection database: concurrent writers can hand out the same id, and catalogs have no unique key (!323). Catalog id, name and source are now unique; an existing collection gets the unique indexes on load, exact duplicate catalog rows are removed, and other duplicates are reported with a warning.
- `Album.search()` with a string searches every character; `force_retrieve` is described wrongly (!325, #272, #275)
- Database migration: every step records the final version, and the backup cannot be restored on Windows while the index is open (!326, #269)
- `album uninstall`: a solution that is not installed or not found is reported as "Cannot load solution" and resolved twice (!327, #270)
- `update_solution()` lets attributes redirect the update to another entry; a failed `last_execution` write fails a finished run (!328, #271)
- Help texts: `album undeploy` asks for the path of the solution file, but takes `group:name:version` (#182); `install`, `run`, `info`, `test`, `uninstall` and `repl` only mention a path, although they also take coordinates, a DOI or a URL; `--uninstall-deps` offers True and False, but is a flag (!337)
- `album deploy` of a folder copies hidden files and folders (`.git`, `.DS_Store`, `.ipynb_checkpoints`, ...) and `__pycache__` into the catalog (!337, #229). They are left out now, and the deploy log names them.
- `album upgrade` breaks the solutions installed in the environment of a parent that is deployed again with the same version, and drops installed solutions that are removed from their catalog (!340, #194). The solutions keep their parent now: before, they ran in an environment that does not exist, the parent could be uninstalled before them, and installing them again failed with "has several parents", as did installing a solution again after `album upgrade --override` gave it another parent. An installed solution that is removed from its catalog stays in the collection, with a warning, until it is uninstalled, and the next `album upgrade` removes it; before, it could no longer be run or uninstalled, and its environment was left behind. An unfinished installation stays marked as such, so the next installation still removes it. A solution that already lost its parent can be uninstalled and installed again.
- `album upgrade` can undo what another album process records while it installs the same solution: the finished installation then counts as unfinished, and the next installation removes it (!346). A changed or removed catalog entry is now applied once such an installation or uninstallation is done, to the status it left.
- `album uninstall --uninstall-deps` uninstalls the solution and then fails when another installed solution still runs in the environment of its parent (!340, #194). The parent now stays, and the log says which solutions need it. `album uninstall` of a parent that other installed solutions run in did nothing and reported no error when that parent had a parent itself; it now fails as it does for any other parent.
- Resolving a solution by name or `group:name` fails when several versions match and one of them is not of the form `1.2.3`, such as `0.1.0-SNAPSHOT`, `1.0` or `0.1.0rc1` (!340). Versions are now ordered as in `album index` and `album deploy`: PEP 440 versions by number, other versions by string, below them.
- An `environment_file` or `resource_file` given as a path is only found when album runs in the folder it is relative to (!343, #225). The path is now relative to the solution folder, wherever album runs, also for a solution installed from a catalog. `album deploy` no longer replaces an `environment.yml` that comes with the solution by the environment it hands to conda-lock, which has album-solution-api added; that one is deployed as `solution.environment.yml` now. A lock file in the folder of a solution, e.g. of one cloned from a catalog, is no longer deployed with it when `album deploy --no-conda-lock` creates none.
- `album clone` of a deployed solution, e.g. a template, copies the files `album deploy` wrote for it: installing the new solution took the lock file of the cloned one, whatever the new one declares (!343). The clone leaves out `solution.yml`, `solution.conda-lock.yml`, `solution.environment.yml` and `solution.resources.yml`.

## [0.12.2]

### Changed

- refactor album catalog admin: Zenodo releases use the concept DOI, each new version is created from the latest published version, and the DOI is looked up to detect an already published deposit
- keep DOIs across deploy of several versions
- use the user's CHANGELOG.md if present over the one generated from the database
- improved error handling for the Zenodo API and improved CI log
- the default Python version of solution environments is 3.10 (was 3.9)
- solutions that use the old album-runner get Python 3.9 and `setuptools<71` pinned in their default environment
- the default album-solution-api version, used when a solution does not set `album_api_version`, is 0.7.1 (was 0.6.1)
- solution scripts run with the caller's full environment on every platform; on Linux and macOS they used to get only the album variables
- task API: `ITask.id()` and `Task.id()` are renamed to `task_id()`, and task arguments are typed as a tuple; plugins that call `task.id()`, such as album-gui before 0.5.1, fail with an `AttributeError`
- `ResolveResult.coordinates()` and `loaded_solution()` raise a `RuntimeError` instead of returning `None` when the value is not set, and `IEnvironmentManager` and `IMigrationManager` have new abstract methods
- `album.core.__version__` is read from the installed package metadata
- the Docker image uses micromamba 2.5.0 (was 1.5.6)

### Removed

- documentation sources and the Read the Docs configuration; the documentation now lives in [album-docs](https://gitlab.com/album-app/album-docs)

### Fixed

- Zenodo API call to trigger a new version
- re-running the release pipeline: every step can be re-run, and a leftover draft deposit is caught
- uploading to an existing Zenodo deposit, such as a new version draft: removing the previous files failed with a `TypeError`; now only files that are no longer part of the solution are deleted, and the deposit gets the new version's metadata instead of the inherited one
- stale files of the previous version are deleted before the new merge request is created
- DOI and version resolving in the release pipeline, including the records API fallback
- query status parameter for Zenodo queries that require a certain deposit status
- the fork point of the deploy branch is updated before committing, and a stale guard prevents race-condition merge conflicts
- force push after rebase in the catalog admin merge path
- the `CHANGELOG.md` generated for a solution deployed to a request catalog includes the version being deployed
- installing by DOI downloads the Zenodo record's files archive and extracts the `solution.zip` inside it; a solution zip archive or folder resolves to the `solution.py` inside it
- `pkg_resources` import: solution plugins are looked up with `importlib.metadata`
- git clones use `--no-local`, since hard links failed

## [0.12.1]

### Changed

- improved zenodo API for CI
- pyproject.toml over setup.cfg

## [0.12.0]

### Added

- reconstruct changelog
- changelog to the repository (#233)

[unreleased]: https://gitlab.com/album-app/album/-/compare/v0.12.2...HEAD
[0.12.2]: https://gitlab.com/album-app/album/-/compare/v0.12.1...v0.12.2
[0.12.1]: https://gitlab.com/album-app/album/-/compare/v0.12.0...v0.12.1
[0.12.0]: https://gitlab.com/album-app/album/-/compare/v0.11.0...v0.12.0
[0.11.0]: https://gitlab.com/album-app/album/-/compare/v0.10.4...v0.11.0
[0.10.4]: https://gitlab.com/album-app/album/-/compare/v0.10.3...v0.10.4
[0.10.3]: https://gitlab.com/album-app/album/-/compare/v0.10.2...v0.10.3
[0.10.2]: https://gitlab.com/album-app/album/-/compare/v0.10.1...v0.10.2
[0.10.1]: https://gitlab.com/album-app/album/-/compare/v0.10.0...v0.10.1
[0.10.0]: https://gitlab.com/album-app/album/-/compare/v0.9.3...v0.10.0
[0.9.3]: https://gitlab.com/album-app/album/-/compare/v0.9.2...v0.9.3
[0.9.2]: https://gitlab.com/album-app/album/-/compare/v0.9.1...v0.9.2
[0.9.1]: https://gitlab.com/album-app/album/-/compare/v0.9.0...v0.9.1
[0.9.0]: https://gitlab.com/album-app/album/-/compare/v0.8.0...v0.9.0
[0.8.0]: https://gitlab.com/album-app/album/-/compare/v0.7.1...v0.8.0
[0.7.1]: https://gitlab.com/album-app/album/-/compare/v0.7.0...v0.7.1
[0.7.0]: https://gitlab.com/album-app/album/-/compare/v0.6.2...v0.7.0
[0.6.2]: https://gitlab.com/album-app/album/-/compare/v0.6.1...v0.6.2
[0.6.1]: https://gitlab.com/album-app/album/-/compare/v0.6.0...v0.6.1
[0.6.0]: https://gitlab.com/album-app/album/-/compare/v0.5.0...v0.6.0
[0.5.0]: https://gitlab.com/album-app/album/-/compare/v0.4.0...v0.5.0
[0.4.0]: https://gitlab.com/album-app/album/-/compare/v0.3.1...v0.4.0
[0.3.1]: https://gitlab.com/album-app/album/-/compare/v0.3.0...v0.3.1
[0.3.0]: https://gitlab.com/album-app/album/-/compare/v0.2.2...v0.3.0
[0.2.2]: https://gitlab.com/album-app/album/-/compare/v0.2.1...v0.2.2
[0.2.1]: https://gitlab.com/album-app/album/-/compare/v0.2.0...v0.2.1
[0.2.0]: https://gitlab.com/album-app/album/-/tags/v0.2.0
