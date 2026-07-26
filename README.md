# NE Loader

[![CI](https://github.com/erictunn/NE_loader_package/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/erictunn/NE_loader_package/actions/workflows/ci.yml)

A simple, robust Python package to download and load Natural Earth map data using GeoPandas.

## Features

- Download and cache Natural Earth datasets
- Load shapefiles as GeoDataFrames

## Installation

```bash
pip install ne-loader
```

## Usage

```python
from ne_loader import map_loader

world = map_loader.get_natural_earth("cultural", "admin_0_countries")
```

Errors are raised by default. To return the caught exception instead:

```python
result = map_loader.get_natural_earth(
    "cultural",
    "admin_0_countries",
    error_mode="return",
)
```

## CLI

The CLI executable is ne-loader.
If you are using uv, write ```uv run``` before each command listed, if it otherwise does not work.

```bash
ne-loader --help
```

To set an environment override for the NE data save path:

```bash
export NATURAL_EARTH_CACHE_DIR="..."
```

Some commands include:  
List cached datasets.  

```bash
ne-loader list
```

Query where the cached datasets are.  
If you change NATURAL_EARTH_CACHE_DIR, the command shows the active cache path for the current environment.

```bash
ne-loader where
```

Download a Natural Earth Dataset. Default resolution is 10m.

```bash
ne-loader download {category} {name} --res {res}
```

Example usage to download 10m_admin_0_countries

```bash
ne-loader download cultural admin_0_countries
```

Delete either one dataset or all, from current cache directory.

```bash
ne-loader rm {dataset}
# or
ne-loader rm --all
```

## Tests

```bash
python3 -m pytest tests
```

## License

MIT
