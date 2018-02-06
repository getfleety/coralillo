# Coralillo

[![Build Status](https://travis-ci.org/getfleety/coralillo.svg?branch=master)](https://travis-ci.org/getfleety/coralillo)

A redis ORM. This project is in active development, if you think it is useful contact me so we can talk about its usage, features and future of the project.

## Installation

```bash
$ pip install coralillo
```

## Testing

Runing the test suite:

```bash
$ python setup.py test
```

Or you can run individual tests using builtin unittest API:

```bash
$ python coralillo/tests/test_all.py [-f] [TestCaseClass[.test_function]]
```

## Deploy

Make a tag with the corresponding release number, then:

```bash
$ make clean
$ make release
```
