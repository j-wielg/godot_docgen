# Godot Docgen

A tool for automatically documenting Godot projects. Using the Godot engine's 
[documentation comment](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_documentation_comments.html)
syntax, this program parses your GDScript files and scene files to generate reStructuredText (.rst files), which can be used with Sphinx to
generate html documentation.

Most of the code for parsing and generating documentation for classes has been modified from [this file](https://github.com/godotengine/godot/blob/master/doc/tools/make_rst.py)
in the Godot project's main repository.

## Usage

The project does not currently have a stable API. This section will be updated as the project nears completion.

## Development Roadmap

- Build a stable API to let people try the project
- Generate .rst files for scenes
- Integrate with external .rst files (such as tutorials)
- Package the python project using setuptools
