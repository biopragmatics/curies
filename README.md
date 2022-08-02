<!--
<p align="center">
  <img src="https://github.com/cthoyt/curies/raw/main/docs/source/logo.png" height="150">
</p>
-->

<h1 align="center">
  curies
</h1>

<p align="center">
    <a href="https://github.com/cthoyt/curies/actions?query=workflow%3ATests">
        <img alt="Tests" src="https://github.com/cthoyt/curies/workflows/Tests/badge.svg" />
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
from curies import Converter

converter = Converter.from_prefix_map({
   "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
   "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
   "GO": "http://purl.obolibrary.org/obo/GO_",
   # ... and so on
   "OBO": "http://purl.obolibrary.org/obo/",
})

>>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_1")
'CHEBI:1'

>>> converter.expand("CHEBI:1")
'http://purl.obolibrary.org/obo/CHEBI_1'

# Unparsable
>>> assert converter.compress("http://example.com/missing:0000000") is None
>>> assert converter.expand("missing:0000000") is None
```

When some URI prefixes are partially overlapping (e.g.,
`http://purl.obolibrary.org/obo/GO_` for `GO` and
`http://purl.obolibrary.org/obo/` for ``OBO``), the longest
URI prefix will always be matched. For example, parsing
`http://purl.obolibrary.org/obo/GO_0032571`
will return `GO:0032571` instead of `OBO:GO_0032571`.

A converter can be instantiated from a web-based resource in JSON-LD format:

```python
from curies import Converter

url = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
converter = Converter.from_jsonld_url(url)
```

Several converters can be instantiated from pre-defined web-based resources:

```python
import curies

# Uses the Bioregistry, an integrative, comprehensive registry
bioregistry_converter = curies.get_bioregistry_converter()

# Uses the OBO Foundry, a registry of ontologies
obo_converter = curies.get_obo_converter()

# Uses the Monarch Initative's project-specific context
monarch_converter = curies.get_monarch_converter()
```

Full documentation is available [here](https://curies.readthedocs.io).

## 🧑‍🤝‍🧑 Related

Other packages that convert between CURIEs and URIs:

- https://github.com/prefixcommons/prefixcommons-py (Python)
- https://github.com/prefixcommons/curie-util (Java)
- https://github.com/geneontology/curie-util-py (Python)
- https://github.com/geneontology/curie-util-es5 (Node.js)

## 🚀 Installation

The most recent release can be installed from
[PyPI](https://pypi.org/project/curies/) with:

```bash
$ pip install curies
```

## 👐 Contributing

Contributions, whether filing an issue, making a pull request, or forking, are appreciated. See
[CONTRIBUTING.md](https://github.com/cthoyt/curies/blob/master/.github/CONTRIBUTING.md) for more information on getting involved.

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
