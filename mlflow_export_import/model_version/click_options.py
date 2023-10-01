import click


# == Export model version

def opt_version(function):
    function = click.option("--version",
        help="Registered model version.",
        type=str,
        required=True
    )(function)
    return function


# == Import model version

def opt_create_model(function):
    function = click.option("--create-model",
        help="Create an empty registered model before creating model version.",
        type=bool,
        show_default=True,
        required=False
    )(function)
    return function

def opt_experiment_name(function):
    function = click.option("--experiment-name",
        help="Destination experiment name for the version's run.",
        type=str,
        required=True
    )(function)
    return function
