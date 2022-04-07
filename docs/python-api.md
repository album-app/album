# Python API

The command line tools are also available via Python API. Here is an example:

```python
from album.api import Album


album = Album.Builder().base_cache_path('/my/album/dir').build()

album.load_or_create_collection()

solution1 = 'album:template-imagej2:0.1.0'
solution2 = 'album:template-napari:0.1.0'

if not album.is_installed(solution1):
    album.install(solution1)

if not album.is_installed(solution2):
    album.install(solution2)

image_path = ''

album.run(solution1, ['', '--output_image_path', image_path])
album.run(solution2, ['', '--input_image_path', image_path])
```

This makes it possible to script album workflows, also directly from an album solution. Check out the [album template solution](https://gitlab.com/album-app/catalogs/default-dev/-/tree/main/template-album).

We will provide a full API documentation shortly.
