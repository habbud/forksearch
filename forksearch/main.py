"""
Entrypoint for CLI.
"""
import typer
from typing_extensions import Annotated
import os
import sys
import gh_utils
import utils
from rich import print
from sgqlc.endpoint.requests import RequestsEndpoint  # noqa: I900

gh_token = os.getenv("GH_TOKEN")
if not gh_token:
    print("GH_TOKEN environment variable must be set")
    sys.exit(-1)

endpoint = RequestsEndpoint(
    "https://api.github.com/graphql",
    {
        "Authorization": "bearer " + gh_token,
    },
    timeout=600.0,
)

app = typer.Typer(no_args_is_help=True)

@app.command()
def check():
    return "check"

# query repositories
@app.command()
def repositories(
    repo: Annotated[str, "owner/repo"] = typer.Argument(..., help="owner/repo"),
):
    owner, repo = repo.split("/")

    # query repositories list
    gh_utils.query_repo_list(endpoint, [(owner, repo)])

@app.command()
def request(
    owner: Annotated[str, "owner name"] = typer.Option(prompt="Owner Name: "),
    repo: Annotated[str, "repository name"] = typer.Option(prompt="Repository Name: ")
):  # noqa: E501
    # initialize database
    db = utils.init_db()
    utils.request_repo(endpoint, db, owner, repo)

if __name__ == "__main__":
    app()
