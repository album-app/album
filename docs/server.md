Using the server
================

## Launching the server

    album server --port 1234 

## Server REST API

### Synchronous calls

- Test if the server is running: 
  
  `http://192.0.0.1:1234/`
- Get configuration parameters of the album installation the server is running on:

  `http://192.0.0.1:1234/config`
- Add a catalog to the album installation the server is running on (the src can be a local folder or a URL - make sure to encode it, for example using [this tool](https://www.urlencoder.org/):

  `http://192.0.0.1:1234/add-catalog?src=URL_OR_PARH_ENCODED`
- Remove a catalog from the album installation the server is running on:

  `http://192.0.0.1:1234/remove-catalog?src=URL_OR_PATH_ENCODED`
- Update the local album installation cache of a catalog index (in case src is missing, all catalogs will be updated):

  `http://192.0.0.1:1234/update?src=CATALOG_URL_OR_PATH_ENCODED`
- Upgrade the local album installation collection of solutions by updating all entries regarding a specific catalog index (if src is provided) or for all catalogs:

  `http://192.0.0.1:1234/upgrade?src=CATALOG_URL_OR_PATH_ENCODED`
- Search for solutions:

  `http://192.0.0.1:1234/search/keyword`
- Terminate the server instance (the REST service will no longer be available after calling this):

  `http://192.0.0.1:1234/shutdown`

### Asynchronous calls

These calls will immediately return a JSON message indicating that the process was launched. 

- Install a solution, specified by the catalog name, the group name, the solution name and it's version:

  `http://192.0.0.1:1234/install/<catalog>/<group>/<name>/<version>`
- Run a solution, specified by the catalog name, the group name, the solution name and it's version:

  `http://192.0.0.1:1234/run/<catalog>/<group>/<name>/<version>`
- Remove a solution, specified by the catalog name, the group name, the solution name and it's version:

  `http://192.0.0.1:1234/remove/<catalog>/<group>/<name>/<version>`
- Test a solution, specified by the catalog name, the group name, the solution name and it's version:

  `http://192.0.0.1:1234/test/<catalog>/<group>/<name>/<version>`
- Deploy a solution from a given path to a specific catalog:

  `http://192.0.0.1:1234/deploy?path=PATH_TO_SOLUTION&catalog_id=CATALOG_ID`

### Tracking process of an asynchronous task
- Status of a task, specified by task id (check return value of asynchronous calls), returns a status and all the log entries associated with this task.

  `http://192.0.0.1:1234/status/<id>`