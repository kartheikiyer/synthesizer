# Contributing 

Please feel free to submit issues and pull requests to this repository. 
The github workflow will automatically run [flake8](https://flake8.pycqa.org/en/latest/) and [pytest](https://docs.pytest.org/en/7.2.x/) on any contributions; builds that fail these tests will not be accepted. Further notes on code style are detailed below.

**Contents:**
- [Style guide](#style-guide)
- [Contributing to the Documentation](#contributing-to-the-documentation)
    - [Getting set up](#getting-set-up)
    - [Adding notebooks](#adding-notebooks)
    - [Adding example scripts](#adding-example-scripts)


## Style guide
All new PRs should follow these guidelines. We adhere to the pep8 style guide, and verify using flake8. We use the [Google docstring format](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings).

Some specific examples of common style issues:
- Do not use capatilised single letters for attributes. For example, `T` could be transmission or temperature. Instead, one should write out the full word.
- Operators should be surrounded with whitespace.

## Contributing to the Documentation
The synthesizer documentation is written in a combination of restructuredText, Jupyter notebooks and Python scripts. 
Adding content should be relatively simple, if you follow the instructions below.

### Getting set up

First we're going to make some small changes to the git configuration to prevent excessive git diffs in the future when contributing changes to notebooks.

1. First, add the following lines to the end of the `.git/config` file at the root of the synthesizer repository

    [filter "strip-notebook-output"]
    clean = "jupyter nbconvert --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --to=notebook --stdin --stdout --log-level=ERROR"

2. Then (if it does not already exist) create a file called `.gitattributes` in the root of the synthesizer repository, and add the following

    *.ipynb filter=strip-notebook-output


This will reset all instances of `execution_count` with `null`, and replace the `metadata` tag with an empty dictionary, and prevent spurious git diffs to notebooks when they have been run multiple times.

    ...
    "execution_count": null,
    "metadata": {},
    ...

### Adding notebooks
To add jupyter notebooks to the documentation:

1. Add your jupyter notebook to the `source` directory. Make sure that you 'Restart Kernel and run all cells' to ensure that the notebook is producing up to date, consistent outputs.
2. Add your notebook to the relevant toctree. See below for an example toctree. Each toctree is contained within a sphinx `.rst` file in each documentation source directory. The top level file is `source/index.rst`. If your file is in a subfolder, you need to update the `.rst` file in that directory.

- If you're creating a new sub-directory of documentation, you will need to carry out a couple more steps:
1. Create a new `.rst` file in that directory
2. Update `source/index.rst` with the path to that `.rst` file
3. Add a line to the *pytest* section of `.github/workflows/python-app.yml` to add the ntoebooks to the testing suite. It should look something like this

    ...
    name: Test with pytest
      run: |
        pytest
        pytest --nbmake docs/source/*.ipynb
        pytest --nbmake docs/source/cosmo/*.ipynb
        pytest --nbmake docs/source/grids/*.ipynb
        pytest --nbmake docs/source/imaging/*.ipynb
        pytest --nbmake docs/source/parametric/*.ipynb
        pytest --nbmake docs/source/your_new_directory/*.ipynb

Example toctree:

    .. toctree::
       :maxdepth: 2
       :caption: Contents
    
       installation
       grids/grids
       parametric/parametric
       cosmo/cosmo
       imaging/imaging
       filters
       grid_generation

### Adding example scripts

The `examples/` top level directory contains a number of self contained example scripts for particular use cases that may not belong in the main documentation, but are still useful for many users. We use the [sphinx-gallery](https://sphinx-gallery.github.io/stable/index.html) extension to build a gallery of our examples in the documentation.

**Important**: each script should have a top level docstring written in reST, with a header. Examples that do not will fail the automated build process. Further details are provided [here](https://sphinx-gallery.github.io/stable/syntax.html). For example:

    """
    "This" is my example-script
    ===========================

    This example doesn't do much, it just makes a simple plot
    """


Subfolders of examples should contain a `README.rst` with a section heading (please follow the template in other subfolders).

If an example is named `plot_*.py` then `sphinx-gallery` will attempt to run the script and use any images generated in the gallery thumbnail. Images should be generated using `plt.show()` and not saved to disk.
