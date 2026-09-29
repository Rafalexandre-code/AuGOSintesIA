# Contributing

Contributions are welcome — bug fixes, new features, benchmarks, and docs.

## How to contribute

1. Fork [atomgptlab/alignn](https://github.com/atomgptlab/alignn) and create a topic
   branch off `develop`.
2. Install in development mode:
   ```bash
   git clone https://github.com/<you>/alignn
   cd alignn
   python -m pip install -e .
   ```
3. Make your change and add or update tests in `alignn/tests/`.
4. Run the test suite:
   ```bash
   pytest alignn/tests
   ```
5. Open a pull request targeting `develop`.

Detailed instructions mirror the general JARVIS guide:
[Contribution.rst](https://github.com/atomgptlab/jarvis/blob/master/Contribution.rst).

## Code of conduct

See the JARVIS [Code of Conduct](https://github.com/atomgptlab/jarvis/blob/master/CODE_OF_CONDUCT.md).

## Reporting issues

Open a GitHub issue at <https://github.com/atomgptlab/alignn/issues>. Please include:

- The ALIGNN version (`pip show alignn`)
- PyTorch and DGL versions
- Operating system and GPU (if applicable)
- A minimal reproducer (config, a few structures, the command you ran)
- The full error traceback
