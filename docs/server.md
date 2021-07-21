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
- Add a catalog to the album installation the server is running on:

  `http://192.0.0.1:1234/add-catalog/URL`
- Remove a catalog from the album installation the server is running on:

  `http://192.0.0.1:1234/remove-catalog/URL`
- Search for solutions:

  `http://192.0.0.1:1234/search/keyword`

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

### Tracking process of an asynchronous task
- Status of a task, specified by task id (check return value of asynchronous calls), returns a status and all the log entries associated with this task.

  `http://192.0.0.1:1234/status/<id>`