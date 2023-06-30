import argparse
import os
import utils
from rich import print
from database import GitDB
from sgqlc.endpoint.requests import RequestsEndpoint  # noqa: I900

def init_parser():
    parser = argparse.ArgumentParser(description="ForkSearch CLI")
    parser.add_argument("--token", help="Github token (Default token with environment variable GH_TOKEN)", default=os.getenv("GH_TOKEN"))
    parser.add_argument("--host", help="Neo4j host", default="localhost")
    parser.add_argument("--port", help="Neo4j port", default=7687)
    parser.add_argument("--username", help="Neo4j username", default="neo4j")
    parser.add_argument("--password", help="Neo4j password", default="password")
    parser.add_argument("-f", "--file", help="file containing list of owner/repo", default=None)
    parser.add_argument("-r", "--repo", help="owner/repo (Default: dbrumley/forksearch)", default="dbrumley/forksearch")
    parser.add_argument("-q", "--quiet", action="store_true", help="Not printing repo information", default=False)
    parser.add_argument("-y", "--yes", action="store_true", help="Yes to all confirmation", default=False)
    parser.add_argument("-t", "--trace", action="store_true", help="Trace back to the parent repository", default=False)
    args = parser.parse_args()
    return args

def quiet_info(*args, **kwargs):
    pass

if __name__ == '__main__':
    args = init_parser()

    if args.token is None:
        print ("Set token with --token or GH_TOKEN environment variable")
        exit(-1)

    endpoint = RequestsEndpoint(
        "https://api.github.com/graphql",
        {
            "Authorization": "bearer " + args.token,
        },
        timeout=600.0,
    )

    db = GitDB(args.host, args.port, args.username, args.password)

    if args.file is not None:
        with open(args.file, 'r') as f:
            repos = [repo.strip() for repo in f.readlines()]
    else:
        repos = [args.repo]

    for repo in repos:
        print (f'Processing [italic blue]{repo}[/italic blue]')
        owner, repo = repo.split("/")
        utils.request_repo(endpoint, db, owner, repo, quiet_info if args.quiet else utils.print_info, args.trace, args.yes)

    db.close()