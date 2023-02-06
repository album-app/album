# REST API

Album can launch a server which provides a REST API for all command line calls. 
Please be cautious since this enables others with access to the API to run arbitrary scripts on the system.

## Installing the server functionality

Activate the Album environment and run this command:
```
pip install album-server
```

## Launching the server
Activate the Album environment and run this command:
```
album server --port 1234
```

## Synchronous calls

- Test if the server is running: 
  ```
  http://192.0.0.1:1234/
  ```
- Get configuration parameters of the Album installation the server is running on:
  ```
  http://192.0.0.1:1234/config
  ```
- Add a catalog to the Album installation the server is running on (the src can be a local folder or a URL - make sure to encode it, for example using [this tool](https://www.urlencoder.org/):
  ```
  http://192.0.0.1:1234/add-catalog?src=URL_OR_PATH_ENCODED
  ```
- Remove a catalog from the Album installation the server is running on:
  ```
  http://192.0.0.1:1234/remove-catalog?src=URL_OR_PATH_ENCODED
  ```
- Update the local Album installation cache of a catalog index (in case src is missing, all catalogs will be updated):
  ```
  http://192.0.0.1:1234/update?src=CATALOG_URL_OR_PATH_ENCODED
  ```
- Upgrade the local Album installation collection of solutions by updating all entries regarding a specific catalog index (if src is provided) or for all catalogs:
  ```
  http://192.0.0.1:1234/upgrade?src=CATALOG_URL_OR_PATH_ENCODED
  ```
- Search for solutions:
  ```
  http://192.0.0.1:1234/search/keyword
  ```
- Terminate the server instance (the REST service will no longer be available after calling this):
  ```
  http://192.0.0.1:1234/shutdown
  ```

## Asynchronous calls

These calls will immediately return a JSON message indicating that the process was launched. 

- Install a solution, specified by the catalog name, the group name, the solution name and it's version:
  ```
  http://192.0.0.1:1234/install/<catalog>/<group>/<name>/<version>
  ```
- Run a solution, specified by the catalog name, the group name, the solution name and it's version:
  ```
  http://192.0.0.1:1234/run/<catalog>/<group>/<name>/<version>
  ```
- Uninstall a solution, specified by the catalog name, the group name, the solution name and it's version:
  ```
  http://192.0.0.1:1234/uninstall/<catalog>/<group>/<name>/<version>
  ```
- Test a solution, specified by the catalog name, the group name, the solution name and it's version:
  ```
  http://192.0.0.1:1234/test/<catalog>/<group>/<name>/<version>
  ```
- Clone a solution, specified by the catalog name, the group name, the solution name and it's version into a given target directory:
  ```
  http://192.0.0.1:1234/clone/<catalog>/<group>/<name>/<version>?target_dir=TARGET_DIR&name=NEW_SOLUTION_NAME
  ```
- Clone a solution, specified by it's path (local or URL, encoded) into a given target directory:
  ```
  http://192.0.0.1:1234/clone?path=SOLUTION_PATH_OR_URL&target_dir=TARGET_DIR&name=NEW_SOLUTION_NAME
  ```
- Clone a catalog template into a given target directory (available catalog templates are the names of all repositories in [this group](https://gitlab.com/album-app/catalogs/templates)):
  ```
  http://192.0.0.1:1234/clone/<template_name>?target_dir=TARGET_DIR&name=NEW_CATALOG_NAME
  ```
- Deploy a solution from a given path to a specific catalog:
  ```
  http://192.0.0.1:1234/deploy?path=PATH_TO_SOLUTION&catalog_name=CATALOG_NAME
  ```

### Tracking process of an asynchronous task
- Status of a task, specified by task id (check return value of asynchronous calls), returns a status and all the log entries associated with this task.
  ```
  http://192.0.0.1:1234/status/<id>
  ```
