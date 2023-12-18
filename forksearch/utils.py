from types import FunctionType
from database import GitDB
from gh_utils import *
from rich import print, table
from typer import confirm as Confirm
import datetime

HOST = "localhost"
BOLTPORT = 7687
USERNAME = 'neo4j'
PASSWORD = 'password'

def init_db():
    return GitDB(HOST, BOLTPORT, USERNAME, PASSWORD)

def print_info(gh_info, db_info, owner, repo):
    if gh_info['isFork']:
        caption = f"Fork from [bold red]{gh_info['parent']['nameWithOwner']}[/bold red]"
    else:
        caption = ""

    # print info in table
    t = table.Table(title=f'Repository {owner}/{repo}', caption=caption)
    t.add_column("", justify="right", style="cyan", no_wrap=True)
    t.add_column("Database", justify="right", no_wrap=True)
    t.add_column("Github", justify="right", no_wrap=True)
    t.add_column("Percentage (%)", justify="right", no_wrap=True)

    t.add_row(
        "Watchers",
        str(db_info['watchers']),
        str(gh_info['watchers']['totalCount']),
        f"{db_info['watchers']/gh_info['watchers']['totalCount'] * 100:.1f}" if gh_info['watchers']['totalCount'] else "N/A",
        style="cyan"
    )
    t.add_row(
        "Forks",
        str(db_info['forks']),
        str(gh_info['forkCount']),
        f"{db_info['forks']/gh_info['forkCount'] * 100:.1f}" if gh_info['forkCount'] else "N/A",
        style="green"
    )
    t.add_row(
        "Stargazers",
        str(db_info['stargazers']),
        str(gh_info['stargazerCount']),
        f"{db_info['stargazers']/gh_info['stargazerCount'] * 100:.1f}" if gh_info['stargazerCount'] else "N/A",
        style="magenta"
    )

    print (t)
    print ()

def query_info(endpoint: RequestsEndpoint, db: GitDB, owner: str, name: str, wait_for_ratelimiter: bool = False):
    gh_info = query_repo_info(endpoint, owner=owner, name=name, wait_for_ratelimiter=wait_for_ratelimiter)
    # print("DEBUG HABBUD: gh_info={}".format(gh_info))
    needed_field = ['isFork', 'url', 'name']
    repo_properties = {k: gh_info[k] for k in needed_field}

    db_info = db.get_repo_info(id=gh_info['id'], login=owner, owner=gh_info['owner'], repo_properties=repo_properties)
    # print("DEBUG HABBUD: db_info={}".format(db_info))
    return gh_info, db_info

def get_unique_orgs(orgs_repos, organizations_number):
    orgs=[]
    for i in range(organizations_number):
        if(orgs_repos[i]['organizations']['name'] not in orgs):
            orgs.append(orgs_repos[i]['organizations']['name'])
        if(len(orgs) == organizations_number):
            break
    # print("DEBUG HABBUD: orgs={}".format(orgs))
    return orgs

def query_organizations(endpoint: RequestsEndpoint, db: GitDB, owner: str, name: str, db_info: dict, gh_info,  
                        orgs_logins, wait_for_ratelimiter: bool = False, REST_header: List[str] = []):
    # print (f"Querying top {organizations_number} fork organizations for [italic blue]{owner}/{name}[/italic blue]...")
    # orgs_repos = db.get_organizations_info(id=gh_info['id'], limit=organizations_number)
    # print("DEBUG HABBUD: orgs_repos={}".format(unpatched_orgs_forks))
    # orgs_logins=[]
    # for repo in orgs_repos:
    #     orgs_logins.append(repo['org']['login'])
    # print("DEBUG HABBUD: organizations={}".format(orgs_logins))
    all_libs=set()
    for organization_login in orgs_logins:
        # add rate limiter handling HABBUD
        print("Querying organization: {}".format(organization_login))
        repos_names= get_repos_by_owner(endpoint, organization_login, wait_for_ratelimiter)
        libs=query_org_repos(endpoint, lib_name=name, repos_names=repos_names, organization_login=organization_login, 
                             wait_for_ratelimiter=wait_for_ratelimiter, headers=REST_header)
        if libs != None:
            all_libs.union(libs)
        # exit(0)
        # TBD: run SBOM on the organization
    print("Found {} libraries in the organization, The Repos: ".format(len(all_libs), all_libs))

def query_unpatched_orgs(endpoint, db, id, patch_date):
     forks_repos = db.get_forks_info(id)    
     orgs_forks_repos = db.get_orgs_forks_info(id)    
     if(len(forks_repos) == 0):
         print("Local DataBase seems to be empty, please query the repo first.")
         exit(0)
         
    #  print("DEBUG HABBUD: forks_repos={}".format(forks_repos))
     unpatched_forks=set()
     for repo in forks_repos:
         fork_name= repo['fork']['name']
         fork_owner= repo['fork']['login']
         fork_patch_date= repo['fork']['patch_date']

         if(fork_patch_date=='None'):
             name_with_owner=fork_owner+'/'+fork_name
             unpatched_forks.add(name_with_owner)
             continue
        #  fork_merged_date = datetime.datetime.strptime(fork_patch_date, '%Y-%m-%dT%H:%M:%SZ')
         if(patch_date>fork_patch_date):
             unpatched_forks.add(fork_owner+fork_name)  
     unpatched_orgs_forks=set()
     unpatched_orgs_logins=set()
     if(len(orgs_forks_repos) != 0):
         for repo in orgs_forks_repos:
            fork_name= repo['fork']['name']
            fork_owner= repo['fork']['login']
            fork_patch_date= repo['fork']['patch_date']
            if(fork_patch_date=='None'):
                unpatched_orgs_forks.add(fork_owner+fork_name)
                unpatched_orgs_logins.add(repo['org_login'])
                continue
            #  fork_merged_date = datetime.datetime.strptime(fork_patch_date, '%Y-%m-%dT%H:%M:%SZ')
            if(patch_date>fork_patch_date):
                unpatched_orgs_forks.add(fork_owner+fork_name) 
                unpatched_orgs_logins.add(repo['org_login']) 
     print("Found {} unpatched forks out of {}, unpatched_forks={}".format(len(unpatched_forks),len(forks_repos), unpatched_forks))
     print("Found {} unpatched organizations forks out of {}, unpatched_orgs_logins={}".format(len(unpatched_orgs_forks), len(orgs_forks_repos),unpatched_orgs_logins))
         
     return unpatched_orgs_logins

# def check_repo_patch(endpoint, owner, name, parent_nameWithOwner, patch_date, wait_for_ratelimiter) :
#      has_previous_page = True
#      startCursor = None
#      patched=False
#      while has_previous_page:
#         op = Operation(schema.Query)
#         r = op.repository(owner=owner, name=name, __alias__=camel_case(name))
#         r.__fields__(id=True)
#         # r.__fields__(pull_requests=True)
#         select_pulls(r, last=100, before=startCursor)
#         p = query_with_retry(endpoint, op, wait_for_ratelimiter=wait_for_ratelimiter)
#         data = p['data'][camel_case(name)]
#         # print("DEBUG HABBUD query_patched_orgs: data={}".format(data['pullRequests']['nodes']))
#         has_previous_page = data['pullRequests']['pageInfo']['hasPreviousPage']
#         startCursor = data['pullRequests']['pageInfo']['startCursor']
#         # print("DEBUG HABBUD query_patched_org: pageInfo={}".format(data['pullRequests']['pageInfo']))
#         for pull in data['pullRequests']['nodes']:
#             if(pull['mergedAt'] != None and pull['headRepository'] != None):
#                 merged_date = datetime.datetime.strptime(pull['mergedAt'], '%Y-%m-%dT%H:%M:%SZ')
#                 pull_repo_nameWithOwner=pull['headRepository']['nameWithOwner']
#                 # if(not pull_repo_name.contains(name)):
#                 print("DEBUG HABBUD check_repo_patch: pull_repo_nameWithOwner={}, parent_nameWithOwner={}".format(pull_repo_nameWithOwner,parent_nameWithOwner))
#                 #     exit(0)
#                 if(merged_date> patch_date and pull_repo_nameWithOwner == parent_nameWithOwner):
#                     patched=True
#                     has_previous_page=False
#                     break
#                 else :
#                     has_previous_page=False
#      print("DEBUG HABBUD query_patched_org: owner={}, repo={}, patched={}".format(owner, name ,patched))
#      return patched
        # exit(0)
        # if len(data['pullRequests']['nodes']) > 0:
        #     after_cursor = data['pullRequests']['pageInfo']['endCursor']
        

def find_patch_date(endpoint, owner, name, parent_nameWithOwner, wait_for_ratelimiter) :
     has_previous_page = True
     start_cursor = None
     date=None
    #  print("DEBUG HABBUD: find_patch_date: owner={}, name={}, parent_nameWithOwner={}".format(owner, name, parent_nameWithOwner))
     while has_previous_page:
        op = Operation(schema.Query)
        r = op.repository(owner=owner, name=name, __alias__=camel_case(name))
        r.__fields__(id=True)
        # r.__fields__(pull_requests=True)
        select_pulls(r, last=100, before=start_cursor)
        p = query_with_retry(endpoint, op, wait_for_ratelimiter=wait_for_ratelimiter)
        data = p['data'][camel_case(name)]
        # print("DEBUG HABBUD query_patched_orgs: data={}".format(data['pullRequests']['nodes']))
        has_previous_page = data['pullRequests']['pageInfo']['hasPreviousPage']
        start_cursor = data['pullRequests']['pageInfo']['startCursor']
        # print("DEBUG HABBUD query_patched_org: pageInfo={}".format(data['pullRequests']['pageInfo']))
        for pull in data['pullRequests']['nodes']:
            if(pull['mergedAt'] != None and pull['headRepository'] != None):
                merged_date = datetime.datetime.strptime(pull['mergedAt'], '%Y-%m-%dT%H:%M:%SZ')
                pull_repo_nameWithOwner=pull['headRepository']['nameWithOwner']
                # if(not pull_repo_name.contains(name)):
                # print("DEBUG HABBUD check_repo_patch: pull_repo_nameWithOwner={}, parent_nameWithOwner={}".format(pull_repo_nameWithOwner,parent_nameWithOwner))
                #     exit(0)
                if(pull_repo_nameWithOwner == parent_nameWithOwner):
                    date=merged_date
                    has_previous_page=False
    #  print("DEBUG HABBUD query_patched_org: owner={}, repo={}, date={}".format(owner, name ,date))
     return date
        # exit(0)
        # if len(data['pullRequests']['nodes']) > 0:
        #     after_cursor = data['pullRequests']['pageInfo']['endCursor']

def filter_data(data):
    fields=['watchers', 'forks', 'stargazers']
    for field in fields:
        if(data[field]['nodes'] == None):
            data[field]['nodes']=[]
        else:
            data[field]['nodes']=list(filter(None, data[field]['nodes']))
        continue
    return data
            
def find_patch_date_by_CVE(endpoint, owner, name, cve_info, wait_for_ratelimiter) :
    has_previous_page = True
    start_cursor = None
    cve_year= cve_info.split('-')[1].lower()
    cve_number= cve_info.split('-')[2].lower()
    # print("DEBUG HABBUD: find_patch_date_by_CVE: owner={}, cve_year={}, cve_number={}".format(owner, cve_year, cve_number))
    while has_previous_page:
        op = Operation(schema.Query)
        r = op.repository(owner=owner, name=name, __alias__=camel_case(name))
        r.__fields__(id=True)
        select_comments(r, last=100, before=start_cursor)
        p = query_with_retry(endpoint, op, wait_for_ratelimiter=wait_for_ratelimiter)
        data = p['data'][camel_case(name)]
        has_previous_page = data['issues']['pageInfo']['hasPreviousPage']
        start_cursor = data['issues']['pageInfo']['startCursor']
        # print("DEBUG HABBUD query_patched_org: pageInfo={}".format(data['issues']['pageInfo']))
        for node in data['issues']['nodes']:
            comments=node['comments']['nodes']
            for comment in comments:
                if(comment['updatedAt']<cve_year) :
                    has_previous_page=False
                    break
                if("CVE".lower() in comment['bodyText'].lower()) :
                    print("Debug: Habbud comment['bodyText']={}".format(comment['bodyText']))
                    # print("Debug HABBUD comment['updatedAt']={}", comment['updatedAt'])
                    # return comment['updatedAt']
                if("CVE".lower() in comment['bodyText'].lower() and cve_number in comment['bodyText'].lower()) :
                    # print("Debug: Habbud commit['bodyText']={}".format(comment['bodyText']))
                    # print("Debug HABBUD commit['updatedAt']={}", comment['updatedAt'])
                    return comment['updatedAt']
    return None

def query_all(endpoint: RequestsEndpoint, db: GitDB, owner: str, name: str, db_info: dict, id: str, wait_for_ratelimiter: bool = False, pushedAt: str = None):
    print (f"Querying all watchers, forks, and stargazers for [italic blue]{owner}/{name}[/italic blue]...")

    has_next_page = True
    repo_nameWithOwner=owner+'/'+name
    # initialize watchers/forks/stargazers counts
    counts = {
        'watchers': db_info['watchers'],
        'forks': db_info['forks'],
        'stargazers': db_info['stargazers'],
    }

    # initialize cursor from db_info
    cursors = {
        'watchers': db_info['watcher_cursor'],
        'forks': db_info['fork_cursor'],
        'stargazers': db_info['stargazer_cursor'],
    }
    if db_info['pushedAt'] == None:
        db.update_pushedAt(id, pushedAt)
    while has_next_page:
        op = Operation(schema.Query)
        r = op.repository(owner=owner, name=name, __alias__=camel_case(name))
        r.__fields__(id=True)
        # r.__fields__(pull_requests=True)
        select_watchers(r, after=cursors['watchers'])
        select_forks(r, after=cursors['forks'])
        select_stargazers(r, after=cursors['stargazers'])

        p = query_with_retry(endpoint, op, wait_for_ratelimiter=wait_for_ratelimiter)
        
        data = p['data'][camel_case(name)]
        # add all edged in database
        #check data doesnt have nulls
        for fork in data['forks']['nodes']:
            fork_owner=fork['owner']['login']
            fork_name=fork['name']
            # print("DEBUG HABBUD: fork_owner={}, fork_name={}".format(fork_owner, fork_name))
            date=find_patch_date(endpoint, fork_owner, fork_name, repo_nameWithOwner, wait_for_ratelimiter)
            fork['patch_date']=str(date)
        # print("DEBUG HABBUD: data={}".format(data['forks']['nodes']))
        # exit(0)

        try:
            result = db.add_all_edges(data)
        except:
            data=filter_data(data)
            db.add_all_edges(data)

        # get all length of nodes
        watchers_len = len(data['watchers']['nodes'])
        # print("DEBUG HABBUD: data['forks']['nodes']={}".format(data['forks']['nodes']))
        forks_len = len(data['forks']['nodes'])
        stargazers_len = len(data['stargazers']['nodes'])

        # update counts
        counts['watchers'] += watchers_len
        counts['forks'] += forks_len
        counts['stargazers'] += stargazers_len

        # print count of watchers/forks/stargazers
        print(f"Watchers: {counts['watchers']}, Forks: {counts['forks']}, Stargazers: {counts['stargazers']} ({len(result)} edges added)")

        # update has_next_page if any of the page has next page
        has_next_page = data['watchers']['pageInfo']['hasNextPage'] \
            or data['forks']['pageInfo']['hasNextPage'] \
            or data['stargazers']['pageInfo']['hasNextPage']

        if watchers_len > 0:
            cursors['watchers'] = data['watchers']['pageInfo']['endCursor']
        if forks_len > 0:
            cursors['forks'] = data['forks']['pageInfo']['endCursor']
        if stargazers_len > 0:
            cursors['stargazers'] = data['stargazers']['pageInfo']['endCursor']

def request_repo(endpoint: RequestsEndpoint, db: GitDB, owner: str, name: str, info: FunctionType = print_info, 
                 is_recursive: bool = False, do_request: bool = False, wait_for_ratelimiter: bool =False, refresh: bool = False, 
                 REST_header: List[str] = []):
    # print("DEBUG HABBUD: query_info with endpoint={}, db={}, owner={}, name={}".format(endpoint, db, owner, name))
    if(refresh) :
        db.delete_repo_info(owner, name)
    gh_info, db_info = query_info(endpoint = endpoint, db = db, owner = owner, name = name, wait_for_ratelimiter=wait_for_ratelimiter)
    print("DEBUG HABBUD: db_info={}".format(db_info))
    info(gh_info, db_info, owner, name)

    if gh_info['isFork']:
        if is_recursive:
            parent_owner, parent_name = gh_info['parent']['nameWithOwner'].split('/')
            request_repo(endpoint, db, parent_owner, parent_name, info, is_recursive, do_request)
            info(gh_info, db_info, owner, name)

        elif Confirm("Do you want to request parent repo?"):
            parent_owner, parent_name = gh_info['parent']['nameWithOwner'].split('/')

            request_repo(endpoint, db, parent_owner, parent_name, info, is_recursive, do_request)
            info(gh_info, db_info, owner, name)

    if do_request or refresh or Confirm("Do you want to query all data?") :
        query_all(endpoint, db, owner, name, db_info, gh_info['id'], wait_for_ratelimiter, gh_info['pushedAt'])

    gh_info, db_info = query_info(endpoint = endpoint, db = db, owner = owner, name = name)
    info(gh_info, db_info, owner, name)

    if do_request or Confirm("Do you want to query unpatched forks?"):
        patch_info = input("Please enter the date of the patch or the CVE number: (e.g. 2021-12-31 or CVE-2021-1234))").lstrip().rstrip()

        # Try to convert the user's input to an integer
        
        
        split_date=patch_info.split('-') 
        # print("DEBUG HABBUD: split_date={}".format(split_date))
        if(len(split_date) == 3 and split_date[0].isdigit() and split_date[1].isdigit() and split_date[2].isdigit()):
            patch_date=patch_info
        elif(patch_info.split('-')[0].lower() == 'CVE'.lower()):
            # print("DEBUG HABBUD: patch_info={}".format(patch_info))
            #TODO: habbud support this flow 
            patch_date=find_patch_date_by_CVE(endpoint, owner, name, patch_info, wait_for_ratelimiter)
            if(patch_date == None):
                print("Could not find a commit associated with the given CVE, please confirm the CVE number and try again.")
                return
            print("Found a commit associated with the given CVE, the commit date is {}".format(patch_date))
        unpatched_orgs_forks=query_unpatched_orgs(endpoint, db, gh_info['id'], patch_date)




    if do_request or Confirm("Do you want to query potential vulnerable organizations?"):
        # organizations_number = input("Please enter the number of organization you want to query:")

        # # Try to convert the user's input to an integer
        # try:
        #     organizations_number = int(organizations_number)
        # except ValueError:
        #     print("Invalid input. Please enter a valid integer.")

        # if(organizations_number <=0) :
        #     print("Invalid input. Please enter a valid positive integer.")
        # else:
        page_number=1
        orgs_in_code_search=set()
        lines=set()
        i=0
        while True:
            code_result=query_code_search(name,REST_header, page_number)
            try:
                code_result['items']
            except:
                break
            for line in code_result["items"]:
                i=i+1
                for org in unpatched_orgs_forks:
                    print("DEBUG HABBUD: org={}, line={}".format(org, line["repository"]["owner"]["login"]))
                    if(org == line["repository"]["owner"]["login"]):
                        print("Found a potential vulnerable organization: {}".format(org))
                        orgs_in_code_search.add(org)
                        lines.add(line["repository"])
                        exit(0)
            page_number=page_number+1
        print("i={}".format(i))
        print("Found {} potential vulnerable organizations: {}".format(len(orgs_in_code_search), orgs_in_code_search))
        print("The lines are: {}".format(lines))
        # query_organizations(endpoint, db, owner, name, db_info, gh_info, unpatched_orgs_forks, wait_for_ratelimiter, REST_header)
