from sphinx.cmd.build import main

main(["-M", "html", "test/sphinx_matlab/source", "test/sphinx_matlab/build"])
