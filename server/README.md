# Eclipse BaSyx Python SDK - HTTP Server

This package contains a Dockerfile to spin up an exemplary HTTP/REST server following the [Specification of the AAS Part 2 API][6] with ease.
The server currently implements the following interfaces:

- [Asset Administration Shell Repository Service][4]
- [Submodel Repository Service][5]

It uses the [HTTP API][1] and the [AASX][7], [JSON][8], and [XML][9] Adapters of the [BaSyx Python SDK][3], to serve regarding files from a given directory.
The files are only read, changes won't persist.

Alternatively, the container can also be told to use the [Local-File Backend][2] instead, which stores AAS and Submodels as individual JSON files and allows for persistent changes (except supplementary files, i.e. files referenced by `File` submodel elements).
See [below](#options) on how to configure this.

## Building
The container image can be built via:
```
$ docker buildx build -t basyx-python-sdk-http-server .
```

## Running

### Storage
The container needs to be provided with the directory `/storage` to store AAS and Submodel files: AASX, JSON, XML or JSON files of Local-File Backend.

This directory can be mapped via the `-v` option from another image or a local directory.
To map the directory `storage` inside the container, `-v ./storage:/storage` can be used.
The directory `storage` will be created in the current working directory, if it doesn't already exist.

### Port
The HTTP server inside the container listens on port 80 by default.
To expose it on the host on port 8080, use the option `-p 8080:80` when running it.

### Options
The container can be configured via environment variables:
- `API_BASE_PATH` determines the base path under which all other API paths are made available.
  Default: `/api/v3.0`
- `STORAGE_TYPE` can be one of `LOCAL_FILE_READ_ONLY` or `LOCAL_FILE_BACKEND`:
  - When set to `LOCAL_FILE_READ_ONLY` (the default), the server will read and serve AASX, JSON, XML files from the storage directory.
    The files are not modified, all changes done via the API are only stored in memory.
  - When instead set to `LOCAL_FILE`, the server makes use of the [LocalFileBackend][2], where AAS and Submodels are persistently stored as JSON files.
    Supplementary files, i.e. files referenced by `File` submodel elements, are not stored in this case.
- `STORAGE_PATH` sets the directory to read the files from *within the container*. If you bind your files to a directory different from the default `/storage`, you can use this variable to adjust the server accordingly.

### Running Examples

Putting it all together, the container can be started via the following command:
```
$ docker run -p 8080:80 -v ./storage:/storage basyx-python-sdk-http-server
```

Since Windows uses backslashes instead of forward slashes in paths, you'll have to adjust the path to the storage directory there:
```
> docker run -p 8080:80 -v .\storage:/storage basyx-python-sdk-http-server
```

Per default, the server will use the `LOCAL_FILE_READ_ONLY` storage type and serve the API under `/api/v3.0` and read files from `/storage`. If you want to change this, you can do so like this:
```
$ docker run -p 8080:80 -v ./storage2:/storage2 -e API_BASE_PATH=/api/v3.1 -e STORAGE_TYPE=LOCAL_FILE_BACKEND -e STORAGE_PATH=/storage2 basyx-python-sdk-http-server
```

## Building and running the image with docker-compose

The container image can also be built and run via:
```
$ docker compose up
```

This is the exemplary `docker-compose` file for the server:
````yaml
services:
  app:
    build: .
    ports:
    - "8080:80"
    volumes:
      - ./storage:/storage

````

Here files are read from `/storage` and the server can be accessed at http://localhost:8080/api/v3.0/ from your host system. 
To get a different setup this compose.yaml file can be adapted and expanded.

## Acknowledgments

This Dockerfile is inspired by the [tiangolo/uwsgi-nginx-docker][10] repository.

[1]: https://github.com/eclipse-basyx/basyx-python-sdk/pull/238
[2]: https://basyx-python-sdk.readthedocs.io/en/latest/backend/local_file.html
[3]: https://github.com/eclipse-basyx/basyx-python-sdk
[4]: https://app.swaggerhub.com/apis/Plattform_i40/AssetAdministrationShellRepositoryServiceSpecification/V3.0.1_SSP-001
[5]: https://app.swaggerhub.com/apis/Plattform_i40/SubmodelRepositoryServiceSpecification/V3.0.1_SSP-001
[6]: https://industrialdigitaltwin.org/content-hub/aasspecifications/idta_01002-3-0_application_programming_interfaces
[7]: https://basyx-python-sdk.readthedocs.io/en/latest/adapter/aasx.html#adapter-aasx
[8]: https://basyx-python-sdk.readthedocs.io/en/latest/adapter/json.html
[9]: https://basyx-python-sdk.readthedocs.io/en/latest/adapter/xml.html
[10]: https://github.com/tiangolo/uwsgi-nginx-docker
