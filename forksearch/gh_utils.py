"""
Utility functions for the CLI
"""
import sys
import time
import os
import logging
import json
from typing import List, Tuple
from dateutil import parser
from pathlib import Path
from re import sub
from sgqlc.operation import Operation  # noqa: I900
from sgqlc.endpoint.requests import RequestsEndpoint  # noqa: I900
from github import github_schema as schema  # noqa: I900
from sgqlc.types import Arg, String, Variable  # noqa: I900
import xdg.BaseDirectory

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def compact_fmt(d):
    s = []
    for k, v in d.items():
        if isinstance(v, dict):
            v = compact_fmt(v)
        elif isinstance(v, (list, tuple)):
            lst = []
            for e in v:
                if isinstance(e, dict):
                    lst.append(compact_fmt(e))
                else:
                    lst.append(repr(e))
            s.append("%s=[%s]" % (k, ", ".join(lst)))
            continue
        s.append("%s=%r" % (k, v))
    return "(" + ", ".join(s) + ")"


def report_download_errors(errors):
    for i, e in enumerate(errors):
        msg = e.pop("message")
        extra = ""
        if e:
            extra = " %s" % compact_fmt(e)
        print(f"Error #{i+1}: %{msg}%{extra}")
    print(f"Total errors: {len(errors)}")

def camel_case(s: str):
    """Rewrite s with unallowable graphql characters to camelCase"""
    s = sub(r"(_|-|\.)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def set_user_fields(n: schema.User):
    """Set the fields we use on a Github User object.

    See https://docs.github.com/en/graphql/reference/objects#user for all
    options. Note that sqglc replaces camelCase for snake_case.
    """
    n.__fields__(
        id=True,
        login=True,
        company=True,
        url=True,
        email=True,
        twitter_username=True,
        website_url=True,
        name=True,
        __typename__=True,
    )


def set_org_fields(n: schema.Organization):
    """Set the fields we use on a Github Organization object.

    See https://docs.github.com/en/graphql/reference/objects#organization for
    all options. Note that sqglc replaces camelCase for snake_case.
    """
    n.__fields__(
        id=True,
        login=True,
        url=True,
        email=True,
        website_url=True,
        name=True,
        __typename__=True,
    )


def set_owner_fields(n: schema.RepositoryOwner):
    """Set the fields we use on a RepositoryOwner.

    See https://docs.github.com/en/graphql/reference/interfaces#repositoryowner
    Note that the repositoryOwner is actually a sum type that can include
    information for a User or Organization.
    """
    n.__fields__(url=True, __typename__=True)
    u = n.__as__(schema.User)
    set_user_fields(u)
    o = n.__as__(schema.Organization)
    set_org_fields(o)

def set_parent_fields(n: schema.Repository):
    n.__fields__(url=True)
    set_owner_fields(n.owner)


def select_forks(repo, first=100, after=None):
    args = {}
    args["first"] = first
    if after:
        args["after"] = after

    conn = repo.forks(**args)
    conn.__fields__(total_count=True, __typename__=True)
    conn.page_info.__fields__(has_next_page=True, end_cursor=True)
    conn.nodes.__fields__(url=True, __typename__=True, is_fork=True, name=True, id=True)
    set_owner_fields(conn.nodes.owner)

def select_stargazers(repo, first=100, after=None):
    """Helper to paginate a Repository.stargazers() query"""
    args = {}
    args["first"] = first
    if after:
        args["after"] = after

    conn = repo.stargazers(**args)
    conn.page_info.__fields__(has_next_page=True, end_cursor=True)
    set_user_fields(conn.nodes)


def select_watchers(repo, first=100, after=None):
    args = {}
    args["first"] = first
    if after:
        args["after"] = after

    conn = repo.watchers(**args)
    conn.__fields__(total_count=True)
    conn.page_info.__fields__(has_next_page=True, end_cursor=True)
    set_user_fields(conn.nodes)


def select_repo(
    op,
    owner,
    name,
    forks_page_cursor=None,
    stargazers_page_cursor=None,
    watchers_page_cursor=None,
):
    r = op.repository(name=name, owner=owner, __alias__=camel_case(name))
    r.__fields__(
        id=True,
        url=True,
        created_at=True,
        description=True,
        description_html=True,
        has_issues_enabled=True,
        homepage_url=True,
        is_archived=True,
        is_in_organization=True,
        is_locked=True,
        is_mirror=True,
        license_info=True,
        lock_reason=True,
        mirror_url=True,
        name=True,
        name_with_owner=True,
        pushed_at=True,
        short_description_html=True,
        updated_at=True,
        code_of_conduct=True,
        stargazer_count=True,
        fork_count=True,
        database_id=True,
        funding_links=True,
        is_security_policy_enabled=True,
        primary_language=True,
        security_policy_url=True,
        ssh_url=True,
        __typename__=True,
        is_fork=True,
    )

    set_owner_fields(r.owner)
    r.repository_topics(first=10)

    select_forks(r, after=forks_page_cursor)
    select_stargazers(r, after=stargazers_page_cursor)
    select_watchers(r, after=watchers_page_cursor)


def next_cursor(info=None):
    if info and info.has_next_page:
        return info.end_cursor
    return None


def has_next_page(info):
    return info and info.has_next_page


def repo_has_more_pages(r):
    if r.forks and has_next_page(r.forks.page_info):
        return True
    if r.stargazers and has_next_page(r.stargazers.page_info):
        return True
    if r.watchers and has_next_page(r.watchers.page_info):
        return True

    return False


def repos_with_next_page(repos):
    return list(filter(lambda r: repo_has_more_pages(repos[r]), repos))


def sleep_off_primary_rate_limit(rate_limit):
    remaining = rate_limit.remaining
    reset_time = rate_limit.reset_datetime
    sleep_time = reset_time - datetime.datetime.now()
    sleep_sec = sleep_time.seconds + 2
    until = datetime.datetime.fromtimestamp(reset_time)
    log.warning(
        f"Rate limit hit. Sleeping until {until} ({sleep_sec} seconds)"
    )
    sleep(sleep_sec)  # add 2 seconds for slop
    log.warning(f"<yawn>. Done sleeping; trying one more time.")
    return


def sleep_off_graphql_rate_limit(limit):
    assert limit

    cost = 10  # default cost
    remaining = limit["remaining"]

    if "cost" in limit:
        cost = limit["cost"]

    if remaining < cost:
        reset_time = parser.parse(limit["resetAt"])
        sleep_time = (
            datetime.datetime.fromtimestamp(reset_time)
            - datetime.datetime.now()
        )
        sleep_sec = sleep_time.seconds + 2
        until = datetime.datetime.fromtimestamp(reset_time)
        log.warning(
            f"Rate limit hit. Sleeping until {until} ({sleep_sec} seconds)"
        )
        sleep(sleep_sec)  # add 2 seconds for slop
        log.warning(f"<yawn>. Done sleeping; trying one more time.")
    return


def query_error_handler(errors):
    for e in errors:  # if we just hit a rate limit, sleep it off.
        if e["message"].startswith(
            '"You have exceeded a secondary rate limit.'
        ):
            log.warning("Secondary rate limit hit. Sleeping 4 minutes.")
            sleep(60 * 4)
            log.warning("Done sleeping")
            return
        if e["message"].startswith("API rate limit exceeded"):
            # TBD
            breakpoint()
    report_download_errors(errors)


def query_with_retry(endpoint, op, max_retries=2):
    op.rate_limit()
    for _ in range(max_retries):
        d = endpoint(op, timeout=600.0)
        print (d)
        errors = d.get("errors")
        if errors:
            query_error_handler(errors)
        elif "data" in d and "rateLimit" in d["data"]:
            print ('hit rate limit')
            sleep_off_graphql_rate_limit(d["data"]["rateLimit"])
            d["data"].pop("rateLimit")
            return d
        else:
            print (d)
            return d
        print ("Retrying...")
        print (f"Errors: {errors}")
    print("Failed retrying. Exiting")
    sys.exit(-2)


def query_repos(repos, endpoint):
    op = Operation(schema.Query)
    for owner, name in repos:
        select_repo(op=op, name=name, owner=owner)

    print("Querying base repo information...")
    d = query_with_retry(endpoint, op)

    repos = op + d
    print (repos)

    # Create a work list of repos that have a next page
    next_pages = repos_with_next_page(repos)

    # This code is longer because we are careful on our query size.
    # In particular, we make sure:
    #   * We are only querying repos with more pages
    #   * Only querying stargazers, forks, and watchers if there are more
    #     pages for the particular item.

    for name in repos:
        repo = repos[name]
        dbgstr = (
            f"{repo.name}"
            f" stargazers: {len(repo.stargazers.nodes)}/{repo.stargazer_count}"
            f" public forks: {len(repo.forks.nodes)}/{repo.forks.total_count}"
            f" watchers: {len(repo.watchers.nodes)}/{repo.watchers.total_count}"
        )
        log.info(dbgstr)

    while next_pages:
        op = Operation(schema.Query)
        for repo_name in next_pages:
            repo = repos[repo_name]
            r = op.repository(
                name=repo.name,
                owner=repo.owner.login,
                __alias__=camel_case(repo.name),
            )

            if has_next_page(repo.forks.page_info):
                select_forks(r, after=next_cursor(repo.forks.page_info))
            if has_next_page(repo.stargazers.page_info):
                select_stargazers(
                    r, after=next_cursor(repo.stargazers.page_info)
                )
            if has_next_page(repo.watchers.page_info):
                select_watchers(r, after=next_cursor(repo.watchers.page_info))

        # Perform the query to get the next pages of data
        # (one page for each repo that had has_next_page as True)
        pages = query_with_retry(endpoint, op)

        # pages = endpoint(op, timeout=60.0)
        # errors = pages.get('errors')
        # if errors:
        #     return report_download_errors(errors)

        # For each of the next pages of data, add it to the original repo
        page_data = op + pages
        for page in page_data:
            if "forks" in page_data[page]:
                repos[page].forks += page_data[page].forks
            if "stargazers" in page_data[page]:
                repos[page].stargazers += page_data[page].stargazers
            if "watchers" in page_data[page]:
                repos[page].watchers += page_data[page].watchers
            repo = repos[page]
            dbgstr = (
                f"{page}"
                f" stargazers: {len(repo.stargazers.nodes)}/{repo.stargazer_count}"
                f" public forks: {len(repo.forks.nodes)}/{repo.forks.total_count}"
                f" watchers: {len(repo.watchers.nodes)}/{repo.watchers.total_count}"
            )
            log.info(dbgstr)

        # Calculate new work list and iterate
        next_pages = repos_with_next_page(repos)

    ret = {}
    for repo in repos:
        ret[repo] = repos[repo]
    return ret


def cmd_save(repos):
    data_home = xdg.BaseDirectory.save_data_path("forksearch")
    Path(data_home).mkdir(parents=True, exist_ok=True)
    data = {}
    for r in repos:
        data = repos[r].__json_data__
        with open(data_home + f"/{r}.json", "w") as f:
            json.dump(
                data, f, sort_keys=True, indent=2, separators=(",", ": ")
            )


def cmd_load():
    return 
    caches = xdg.BaseDirectory.load_data_paths("forksearch")
    repos = {}
    # This code has never been tested and probably wrong.
    for dir in caches:
        # temp: is `c` a directory correct?
        for c in os.listdir(dir):
            with open(os.path.join(dir, c), "r") as f:
                json_data = json.load(f)
                result = schema.Repository(json_data)
                # for k, v in json_data.items():
                #     repos[c] = schema.Repository(v)

    return repos


def repositories(token, repos, nocache=False, cache=None):
    target_repos = [(repo.owner, repo.name) for repo in repos]
    results = query_repos(target_repos, endpoint)
    cmd_save(results)
    # XXX: Check that save worked
    foo = cmd_load()
    return results


def upstreams(repos, endpoint):
    op = Operation(schema.Query)
    for l in repos:
        owner, name = l.split("/")
        r = op.repository(name=name, owner=owner, __alias__=camel_case(name))
        r.__fields__(name_with_owner=True)
        r.parent.__fields__(id=True, name=True, name_with_owner=True)
    d = endpoint(op)
    errors = d.get("errors")
    if errors:
        return report_download_errors(errors)

    repos = op + d
    ret = {}
    for r in repos:
        repo = repos[r]
        if repo.parent:
            ret[repo.name_with_owner] = repo.parent.name_with_owner
        else:
            ret[repo.name_with_owner] = None

    return ret


def chunks(list_a, chunk_size):
    for i in range(0, len(list_a), chunk_size):
        yield list_a[i : i + chunk_size]


def query_repo_info(endpoint: RequestsEndpoint, name: str, owner: str):
    op = Operation(schema.Query)
    r = op.repository(name=name, owner=owner, __alias__=camel_case(name))
    # get info about the repo
    r.__fields__(
        id=True,
        is_fork=True,
        url=True,
        name=True,
        fork_count=True,
        stargazer_count=True,
    )
    print (r)

    # set up fields for owner
    u = r.owner.__as__(schema.User)
    set_user_fields(u)
    u = r.owner.__as__(schema.Organization)
    set_org_fields(u)

    # get count of watchers
    r.watchers.__fields__(total_count=True)
    r.parent.__fields__(name_with_owner=True)

    # get response of query
    d = endpoint(op)
    errors = d.get("errors")
    if errors:
        report_download_errors(errors)
        sys.exit(1)
    else:
        return d['data'][camel_case(name)]

def query_repo_list(endpoint: RequestsEndpoint, repositories: List[Tuple[str, str]]):
    repos = {}

    print(f"Fetching {len(repositories)} repos")
    for current in chunks(repositories, 3):
        print(f"Working on chunk: {current}")
        r = query_repos(current, endpoint)
        for k, v in r.items():
            repos[k] = v
        cmd_save(repos)
        foo = cmd_load()
