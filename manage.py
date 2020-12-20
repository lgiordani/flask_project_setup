#! /usr/bin/env python

import os
import json
import signal
import subprocess
import time

import click


# Ensure an environment variable exists and has a value
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


setenv("APPLICATION_CONFIG", "development")


def configure_app(config):
    # Read configuration from the relative JSON file
    with open(os.path.join("config", f"{config}.json")) as f:
        config_data = json.load(f)

    # Convert the config into a usable Python dictionary
    config_data = dict((i["name"], i["value"]) for i in config_data)

    for key, value in config_data.items():
        setenv(key, value)


@click.group()
def cli():
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=click.Path())
def flask(subcommand):
    configure_app(os.getenv("APPLICATION_CONFIG"))

    cmdline = ["flask"] + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


def docker_compose_cmdline(config):
    configure_app(os.getenv("APPLICATION_CONFIG"))

    docker_compose_file = os.path.join("docker", f"{config}.yml")

    if not os.path.isfile(docker_compose_file):
        raise ValueError(f"The file {docker_compose_file} does not exist")

    return [
        "docker-compose",
        "-p",
        config,
        "-f",
        docker_compose_file,
    ]


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=click.Path())
def compose(subcommand):
    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


@cli.command()
@click.argument("filenames", nargs=-1)
def test(filenames):
    os.environ["APPLICATION_CONFIG"] = "testing"
    configure_app(os.getenv("APPLICATION_CONFIG"))

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["up", "-d"]
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["logs", "db"]
    logs = subprocess.check_output(cmdline)
    while "ready to accept connections" not in logs.decode("utf-8"):
        time.sleep(0.1)
        logs = subprocess.check_output(cmdline)

    cmdline = ["pytest", "-svv", "--cov=application", "--cov-report=term-missing"]
    cmdline.extend(filenames)
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["down"]
    subprocess.call(cmdline)


if __name__ == "__main__":
    cli()
