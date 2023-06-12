"""
Entrypoint for CLI.
"""
import typer
import os
import sys
import utils
from sgqlc.endpoint.requests import RequestsEndpoint  # noqa: I900

# from forksearch.commands import users, items

# app = typer.Typer(no_args_is_help=True)
# app.add_typer(users.app, name="users")
# app.add_typer(items.app, name="items")


# def forksearch(repo: str):
#    print("THERE")
#    app()


# @app.callback()
def main(repo: str):
    token = os.getenv("GH_TOKEN")
    token = "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"

    if not token:
        print("GH_TOKEN environment variable must be set")
        sys.exit(-1)

    endpoint = RequestsEndpoint(
        "https://api.github.com/graphql",
        {
            "Authorization": "bearer " + token,
        },
        timeout=600.0,
    )

    utils.query_repo_list(endpoint, [repo])

    # print(f"String: {str}")


if __name__ == "__main__":
    typer.run(main)
    # app()
