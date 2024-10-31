"""
A traitgen generator that outputs a markdown document based on the
openassetio_traitgen PackageDefinition model.
"""

import logging
import os
import re

import jinja2

from ..datamodel import PackageDeclaration, PropertyType


__all__ = ["generate"]


def generate(
    package_declaration: PackageDeclaration,
    globals_: dict,
    output_directory: str,
    creation_callback,
    logger: logging.Logger,
):
    """
    Generates markdown documents for the supplied definition under outputDirPath.
    """
    env = _create_jinja_env(globals_, logger)

    def render_template(name: str, path: str, variables: dict):
        """
        A convenience to render a named template into its corresponding
        file and call the creationCallback.
        """
        # pylint: disable=line-too-long
        # NB: Jinja assumes '/' on all plaftorms:
        template = env.get_template(f"markdown/{name}.md.in")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(template.render(variables))
        creation_callback(path)

    def create_dir_with_path_components(*args) -> str:
        """
        A convenience to create a directory from the supplied path
        components, calling the creationCallback and returning its path
        as a string.
        """
        path = os.path.join(*args)
        os.makedirs(path, exist_ok=True)
        creation_callback(path)
        return path

    output_dir_path = create_dir_with_path_components(
        output_directory, f"{package_declaration.id}-md"
    )

    trait_namespaces = []
    specification_namespaces= []

    for kind in ("traits", "specifications"):
        namespaces = getattr(package_declaration, kind, None)
        if namespaces:
            if kind == "traits":
                trait_namespaces.extend(namespaces)
            else:
                specification_namespaces.extend(namespaces)

            render_template(
                kind,
                os.path.join(output_dir_path, f"{kind}.md"),
                {
                    "package": package_declaration,
                    "namespaces": namespaces,
                },
            )

    render_template(
        "index",
        os.path.join(output_dir_path, "index.md"),
        {
            "package": package_declaration,
            "trait_namespaces": trait_namespaces,
            "specification_namespaces": specification_namespaces,
        },
    )


#
## Jinja setup
#


def _create_jinja_env(env_globals, logger):
    """
    Creates a custom Jinja2 environment with:
     - A package a loader that automatically finds templates within a
       'templates' directory in the openassetio_traitgen python package.
     - Updated globals.
     - Custom filters.
    """
    env = jinja2.Environment(loader=jinja2.PackageLoader("openassetio_traitgen"))
    env.globals.update(env_globals)
    _install_custom_filters(env, logger)
    return env


# Custom filters


def _install_custom_filters(environment, logger):
    """
    Installs custom filters in to the Jinja template environment that allow
    data from the model to be conformed to markdown-specific standards.
    """
    def cleanup_md_string(string: str):
        """
        Tidies up a string for markdown.
        """
        # Some instances of lists may not be formatted correctly for markdown
        new_string = re.sub("(:\s*)([-\*])", r":\n \2", string)
        # Specifc area in traits.yaml that doesn't work so well
        new_string = re.sub('asset - `"seq003"`', 'asset\n- `"seq003"`', new_string)
        return new_string

    type_map = {
        PropertyType.STRING: "string",
        PropertyType.INTEGER: "integer",
        PropertyType.FLOAT: "float",
        PropertyType.BOOL: "boolean",
        PropertyType.DICT: "dict",  # This must be InfoDictionary, but this isn't bound
    }

    def to_type_pretty_name(declaration_type):
        """
        Returns a pretty name for the property declaration (PropertyType).
        """
        if declaration_type == PropertyType.DICT:
            raise TypeError("Dictionary types are not yet supported as trait properties")
        return type_map[declaration_type]

    environment.filters["cleanup_md_string"] = cleanup_md_string
    environment.filters["to_type_pretty_name"] = to_type_pretty_name
