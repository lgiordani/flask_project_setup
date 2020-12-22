#! /usr/bin/env python

import os
import json
import signal
import subprocess
import time
import shutil

import click
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# Ensure an environment variable exists and has a value
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


setenv("APPLICATION_CONFIG", "development")

APPLICATION_CONFIG_PATH = "config"
DOCKER_PATH = "docker"


def app_config_file(config):
    return os.path.join(APPLICATION_CONFIG_PATH, f"{config}.json")


def docker_compose_file(config):
    return os.path.join(DOCKER_PATH, f"{config}.yml")


def configure_app(config):
    # Read configuration from the relative JSON file
    with open(app_config_file(config)) as f:
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


def docker_compose_cmdline(commands_string=None):
    config = os.getenv("APPLICATION_CONFIG")
    configure_app(config)

    compose_file = docker_compose_file(config)

    if not os.path.isfile(compose_file):
        raise ValueError(f"The file {compose_file} does not exist")

    command_line = [
        "docker-compose",
        "-p",
        config,
        "-f",
        compose_file,
    ]

    if commands_string:
        command_line.extend(commands_string.split(" "))

    return command_line


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=click.Path())
def compose(subcommand):
    cmdline = docker_compose_cmdline() + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


def run_sql(statements):
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOSTNAME"),
        port=os.getenv("POSTGRES_PORT"),
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    for statement in statements:
        cursor.execute(statement)

    cursor.close()
    conn.close()


def wait_for_logs(cmdline, message):
    logs = subprocess.check_output(cmdline)
    while message not in logs.decode("utf-8"):
        time.sleep(0.1)
        logs = subprocess.check_output(cmdline)


@cli.command()
def create_initial_db():
    configure_app(os.getenv("APPLICATION_CONFIG"))

    try:
        run_sql([f"CREATE DATABASE {os.getenv('APPLICATION_DB')}"])
    except psycopg2.errors.DuplicateDatabase:
        print(
            f"The database {os.getenv('APPLICATION_DB')} already exists and will not be recreated"
        )


@cli.command()
@click.argument("filenames", nargs=-1)
def test(filenames):
    os.environ["APPLICATION_CONFIG"] = "testing"
    configure_app(os.getenv("APPLICATION_CONFIG"))

    cmdline = docker_compose_cmdline("up -d")
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline("logs db")
    wait_for_logs(cmdline, "ready to accept connections")

    run_sql([f"CREATE DATABASE {os.getenv('APPLICATION_DB')}"])

    cmdline = ["pytest", "-svv", "--cov=application", "--cov-report=term-missing"]
    cmdline.extend(filenames)
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline("down")
    subprocess.call(cmdline)


@cli.group()
def scenario():
    pass


@scenario.command()
@click.argument("name")
def up(name):
    os.environ["APPLICATION_CONFIG"] = f"scenario_{name}"
    config = os.getenv("APPLICATION_CONFIG")

    scenario_config_source_file = app_config_file("scenario")
    scenario_config_file = app_config_file(config)

    if not os.path.isfile(scenario_config_source_file):
        raise ValueError(f"File {scenario_config_source_file} doesn't exist")
    shutil.copy(scenario_config_source_file, scenario_config_file)

    scenario_docker_source_file = docker_compose_file("scenario")
    scenario_docker_file = docker_compose_file(config)

    if not os.path.isfile(scenario_docker_source_file):
        raise ValueError(f"File {scenario_docker_source_file} doesn't exist")
    shutil.copy(docker_compose_file("scenario"), scenario_docker_file)

    configure_app(f"scenario_{name}")

    cmdline = docker_compose_cmdline("up -d")
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline("logs db")
    wait_for_logs(cmdline, "ready to accept connections")

    cmdline = docker_compose_cmdline("port db 5432")
    out = subprocess.check_output(cmdline)
    port = out.decode("utf-8").replace("\n", "").split(":")[1]
    os.environ["POSTGRES_PORT"] = port

    run_sql([f"CREATE DATABASE {os.getenv('APPLICATION_DB')}"])

    scenario_module = f"scenarios.{name}"
    scenario_file = os.path.join("scenarios", f"{name}.py")
    if os.path.isfile(scenario_file):
        import importlib

        os.environ["APPLICATION_SCENARIO_NAME"] = name

        scenario = importlib.import_module(scenario_module)
        scenario.run()

    cmdline = " ".join(
        docker_compose_cmdline(
            "exec db psql -U {} -d {}".format(
                os.getenv("POSTGRES_USER"), os.getenv("APPLICATION_DB")
            )
        )
    )
    print("Your scenario is ready. If you want to open a SQL shell run")
    print(cmdline)


@scenario.command()
@click.argument("name")
def down(name):
    os.environ["APPLICATION_CONFIG"] = f"scenario_{name}"
    config = os.getenv("APPLICATION_CONFIG")

    cmdline = docker_compose_cmdline("down")
    subprocess.call(cmdline)

    scenario_config_file = app_config_file(config)
    os.remove(scenario_config_file)

    scenario_docker_file = docker_compose_file(config)
    os.remove(scenario_docker_file)


if __name__ == "__main__":
    cli()
