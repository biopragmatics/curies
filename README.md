<!--
<p align="center">
  <img src="https://github.com/cthoyt/curies/raw/main/docs/source/logo.png" height="150">
</p>
-->

<h1 align="center">
  curies
</h1>

<p align="center">
    <a href="https://github.com/biopragmatics/curies/actions/workflows/tests.yml">
        <img alt="Tests" src="https://github.com/biopragmatics/curies/actions/workflows/tests.yml/badge.svg" />
    </a>
    <a href="https://pypi.org/project/curies">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/curies" />
    </a>
    <a href="https://pypi.org/project/curies">
        <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/curies" />
    </a>
    <a href="https://github.com/cthoyt/curies/blob/main/LICENSE">
        <img alt="PyPI - License" src="https://img.shields.io/pypi/l/curies" />
    </a>
    <a href='https://curies.readthedocs.io/en/latest/?badge=latest'>
        <img src='https://readthedocs.org/projects/curies/badge/?version=latest' alt='Documentation Status' />
    </a>
    <a href="https://codecov.io/gh/cthoyt/curies/branch/main">
        <img src="https://codecov.io/gh/cthoyt/curies/branch/main/graph/badge.svg" alt="Codecov status" />
    </a>
    <a href="https://github.com/cthoyt/cookiecutter-python-package">
        <img alt="Cookiecutter template from @cthoyt" src="https://img.shields.io/badge/Cookiecutter-snekpack-blue" />
    </a>
    <a href='https://github.com/psf/black'>
        <img src='https://img.shields.io/badge/code%20style-black-000000.svg' alt='Code style: black' />
    </a>
    <a href="https://github.com/cthoyt/curies/blob/main/.github/CODE_OF_CONDUCT.md">
        <img src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg" alt="Contributor Covenant"/>
    </a>
    <a href="https://zenodo.org/badge/latestdoi/519905487">
        <img src="https://zenodo.org/badge/519905487.svg" alt="DOI">
    </a>
</p>

Idiomatic conversion between URIs and compact URIs (CURIEs).

```python
import curies

converter = curies.load_prefix_map({
    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    # ... and so on
})

>>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_1")
'CHEBI:1'

>>> converter.expand("CHEBI:1")
'http://purl.obolibrary.org/obo/CHEBI_1'
```

Full documentation is available at [curies.readthedocs.io](https://curies.readthedocs.io).

### CLI Usage

This package comes with a built-in CLI for running a resolver web application or a IRI mapper web application:

```shell
# Run a resolver
python -m curies resolver --host 0.0.0.0 --port 8764 bioregistry

# Run a mapper
python -m curies mapper --host 0.0.0.0 --port 8764 bioregistry
```

The positional argument can be one of the following:

1. A pre-defined prefix map to get from the web (bioregistry, go, obo, monarch, prefixcommons)
2. A local file path or URL to a prefix map, extended prefix map, or one of several formats. Requires specifying
   a `--format`.

The framework can be swapped to use Flask (default) or FastAPI with `--framework`. The
server can be swapped to use Werkzeug (default) or Uvicorn with `--server`. These functionalities
are also available programmatically, see the docs for more information.

## 🧑‍🤝‍🧑 Related

Other packages that convert between CURIEs and URIs:

- https://github.com/prefixcommons/prefixcommons-py (Python)
- https://github.com/prefixcommons/curie-util (Java)
- https://github.com/geneontology/curie-util-py (Python)
- https://github.com/geneontology/curie-util-es5 (Node.js)
- https://github.com/endoli/curie.rs (Rust)
- https://github.com/cthoyt/curies4j (Java)
- https://github.com/biopragmatics/curies.rs (Rust, Node.js, Python)

## 🚀 Installation

The most recent release can be installed from
[PyPI](https://pypi.org/project/curies/) with:

```bash
$ pip install curies
```

This package currently supports both Pydantic v1 and v2. See the
[Pydantic migration guide](https://docs.pydantic.dev/2.0/migration/)
for updating your code.

## 👐 Contributing

Contributions, whether filing an issue, making a pull request, or forking, are appreciated. See
[CONTRIBUTING.md](https://github.com/cthoyt/curies/blob/master/.github/CONTRIBUTING.md) for more information on getting
involved.

## 👋 Attribution

### 🙏 Acknowledgements

This package heavily builds on the [trie](https://en.wikipedia.org/wiki/Trie)
data structure implemented in [`pytrie`](https://github.com/gsakkis/pytrie).

### ⚖️ License

The code in this package is licensed under the MIT License.

### 🍪 Cookiecutter

This package was created with [@audreyfeldroy](https://github.com/audreyfeldroy)'s
[cookiecutter](https://github.com/cookiecutter/cookiecutter) package using [@cthoyt](https://github.com/cthoyt)'s
[cookiecutter-snekpack](https://github.com/cthoyt/cookiecutter-snekpack) template.

## 🛠️ For Developers

<details>
  <summary>See developer instructions</summary>


The final section of the README is for if you want to get involved by making a code contribution.

### Development Installation

To install in development mode, use the following:

```bash
$ git clone git+https://github.com/cthoyt/curies.git
$ cd curies
$ pip install -e .
```

### 🥼 Testing

After cloning the repository and installing `tox` with `pip install tox`, the unit tests in the `tests/` folder can be
run reproducibly with:

```shell
$ tox
```

Additionally, these tests are automatically re-run with each commit in a [GitHub Action](https://github.com/cthoyt/curies/actions?query=workflow%3ATests).

### 📖 Building the Documentation

The documentation can be built locally using the following:

```shell
$ git clone git+https://github.com/cthoyt/curies.git
$ cd curies
$ tox -e docs
$ open docs/build/html/index.html
```

The documentation automatically installs the package as well as the `docs`
extra specified in the [`setup.cfg`](setup.cfg). `sphinx` plugins
like `texext` can be added there. Additionally, they need to be added to the
`extensions` list in [`docs/source/conf.py`](docs/source/conf.py).

### 📦 Making a Release

After installing the package in development mode and installing
`tox` with `pip install tox`, the commands for making a new release are contained within the `finish` environment
in `tox.ini`. Run the following from the shell:

```shell
$ tox -e finish
```

This script does the following:

1. Uses [Bump2Version](https://github.com/c4urself/bump2version) to switch the version number in the `setup.cfg`,
   `src/curies/version.py`, and [`docs/source/conf.py`](docs/source/conf.py) to not have the `-dev` suffix
2. Packages the code in both a tar archive and a wheel using [`build`](https://github.com/pypa/build)
3. Uploads to PyPI using [`twine`](https://github.com/pypa/twine). Be sure to have a `.pypirc` file configured to avoid the need for manual input at this
   step
4. Push to GitHub. You'll need to make a release going with the commit where the version was bumped.
5. Bump the version to the next patch. If you made big changes and want to bump the version by minor, you can
   use `tox -e bumpversion minor` after.

</details>
