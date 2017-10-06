# Coralillo

A redis ORM

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
