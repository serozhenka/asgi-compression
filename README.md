# ASGI Compression

A framework and platform-independent compression middleware for ASGI applications.

## ✨ Features

- 🚀 **Framework Independent** - Works with any ASGI-compatible framework (FastAPI, Starlette, Litestar, Django, Falcon, etc.)
- 📦 **Multiple Compression Algorithms** - Supports gzip, brotli, and zstandard compression algorithms
- 🔄 **Content Negotiation** - Automatically selects the best compression algorithm based on the client's Accept-Encoding header
- 🛠️ **Fully Configurable** - Control minimum size for compression, compression levels, and more
- 📏 **Minimal Dependencies** - Single external dependency (multidict) apart from optional compression libraries
- 📝 **Fully Typed** - Complete type annotations for excellent IDE support and code safety
- 🐍 **Wide Python Support** - Compatible with Python 3.9 to 3.13
- 🔍 **Streaming Support** - Efficiently compresses both standard and streaming responses
- 🖥️ **Platform Independent** - Supports macOS, Linux, and Windows.

## 📥 Installation

Install the package with pip:

```bash
# Basic installation (includes gzip compression)
pip install asgi-compression

# With gzip and brotli support
pip install asgi-compression[br]

# With gzip and zstandard support
pip install asgi-compression[zstd]

# With gzip, brotli and zstandard support
pip install asgi-compression[all]
```

## 🚀 Usage

### Basic Example

```python
from asgi_compression import CompressionMiddleware, GzipAlgorithm

app = ...  # Your ASGI application

# Apply gzip compression with default settings
app = CompressionMiddleware(
    app=app,
    algorithms=[GzipAlgorithm()],
)
```

### Multiple Algorithms Example

```python
from asgi_compression import (
    BrotliAlgorithm, 
    CompressionMiddleware, 
    GzipAlgorithm, 
    ZstdAlgorithm
)

app = ...  # Your ASGI application

# Apply multiple compression algorithms in order of preference
app = CompressionMiddleware(
    app=app,
    algorithms=[
        BrotliAlgorithm(),  # Brotli will be used if the client supports it
        ZstdAlgorithm(),    # Zstandard will be used as a fallback
        GzipAlgorithm(),    # Gzip as a last resort
    ],
    minimum_size=1000,      # Only compress responses larger than 1KB
)
```

### Framework-Specific Examples

#### FastAPI

```python
from fastapi import FastAPI
from asgi_compression import CompressionMiddleware, GzipAlgorithm, BrotliAlgorithm

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

# Apply compression middleware
app.add_middleware(
    CompressionMiddleware,
    algorithms=[BrotliAlgorithm(), GzipAlgorithm()],
)
```

#### Starlette

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from asgi_compression import CompressionMiddleware, GzipAlgorithm

async def homepage(request):
    return JSONResponse({"hello": "world"})

routes = [
    Route("/", homepage)
]

app = Starlette(routes=routes)
app = CompressionMiddleware(app=app, algorithms=[GzipAlgorithm()])
```

#### Litestar

```python
from litestar import Litestar, get
from asgi_compression import CompressionMiddleware, BrotliAlgorithm

@get("/")
async def homepage() -> dict:
    return {"hello": "world"}

app = Litestar(route_handlers=[homepage])
app = CompressionMiddleware(app=app, algorithms=[BrotliAlgorithm()])
```

## 🙌 Inspired by

This project was brought to life thanks to inspiration from:

- [Startlette's](https://github.com/encode/starlette) Gzip middleware
- [brotli-asgi](https://github.com/fullonic/brotli-asgi)
- [zstd-asgi](https://github.com/tuffnatty/zstd-asgi)

Kudos to devs & maintainers of those amazing libraries!

## 📜 License

This project is licensed under the terms of the MIT license.
