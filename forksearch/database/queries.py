# note: labels
## note: nodes
OWNER = 'Owner'
USER = 'User'
ORGANIZATION = 'Organization'
REPOSITORY = 'Repository'
## note: relationships
OWN = 'OWN'
FORK = 'FORK'
STAR = 'STAR'
WATCH = 'WATCH'

# note: constraints
drop_constraint = lambda name: f'DROP CONSTRAINT {name} IF EXISTS'
create_unique_constraint = lambda name, label, property: f'''
CREATE CONSTRAINT {name} IF NOT EXISTS
FOR (n:{label})
REQUIRE n.{property} IS UNIQUE
'''
create_index = lambda name, label, property: f'''
CREATE INDEX {name} IF NOT EXISTS
FOR (n:{label})
ON (n.{property})
'''

CREATE_OWNER_UNIQUENESS = create_unique_constraint('owner_uniqueness', OWNER, 'login')
CREATE_REPO_UNIQUENESS = create_unique_constraint('repo_uniqueness', REPOSITORY, 'id')
DROP_OWNER_UNIQUENESS = drop_constraint('owner_uniqueness')

# note: insert nodes
CREATE_OWNER = f'call apoc.merge.node(["{OWNER}", $label], $properties, $on_create, $on_merge) yield node as owner'
CREATE_REPOSITORY_WITHOUT_RET = f'''
{CREATE_OWNER}
MERGE (repo:{REPOSITORY} {{id: $id}})<-[:{OWN}]-(owner)
SET repo += $repo_properties
'''
CREATE_REPOSITORY = f'''
{CREATE_REPOSITORY_WITHOUT_RET}
return repo.id as id
'''

# add_edges = lambda edge: f'''
# WITH $nodes as batch
# MATCH (repo:{REPOSITORY} {{name: $name}})<-[:{OWN}]-(:{OWNER} {{login: $login}})
# SET repo.{edge.lower()}_cursor = $nodes.pageInfo.endCursor
# WITH repo, batch
# UNWIND batch.nodes AS user
# call apoc.merge.node(["{OWNER}", user.__typename], {{login: user.login}}, user, user) yield node as watcher
# MERGE (repo) <-[:{edge}]- (watcher)
# return watcher.login
# '''

# ADD_FORKS = f'''
# WITH $forks as batch
# MATCH (parent_repo:{REPOSITORY} {{name: $name}})<-[:{OWN}]-(:{OWNER} {{login: $login}})
# SET parent_repo.fork_cursor = $forks.pageInfo.endCursor
# WITH parent_repo, batch
# UNWIND batch.nodes as fork
# call apoc.merge.node(["{OWNER}", fork.owner.__typename], {{login: fork.owner.login}}, fork.owner, fork.owner) yield node as owner
# MERGE (repo:{REPOSITORY} {{name: fork.name}})<-[:{OWN}]-(owner)
# SET repo += {{isFork: fork.isFork, id: fork.id, url: fork.url}}
# MERGE (repo)<-[:{OWN}]-(owner)
# MERGE (parent_repo)<-[:{FORK}]-(repo)
# return owner.name, repo.name
# '''

ADD_ALL_EDGES = f'''
WITH $nodes as batch
MATCH (parent:{REPOSITORY} {{id: $nodes.id}})
WITH $nodes.stargazers.pageInfo.endCursor as starCursor,
    $nodes.watchers.pageInfo.endCursor as watchCursor,
    $nodes.forks.pageInfo.endCursor as forkCursor,
    $nodes.stargazers.nodes as stargazers,
    $nodes.watchers.nodes as watchers,
    $nodes.forks.nodes as forks,
    parent
SET parent.stargazer_cursor = (CASE WHEN starCursor IS NULL OR isEmpty(stargazers) THEN parent.stargazer_cursor ELSE starCursor END),
    parent.watcher_cursor = (CASE WHEN watchCursor IS NULL OR isEmpty(watchers) THEN parent.watcher_cursor ELSE watchCursor END),
    parent.fork_cursor = (CASE WHEN forkCursor IS NULL OR isEmpty(forks) THEN parent.fork_cursor ELSE forkCursor END)
WITH parent, stargazers, watchers, forks
CALL {{
    WITH parent, stargazers
    UNWIND stargazers AS user
    call apoc.merge.node(["{OWNER}", user.__typename], {{login: user.login}}, user, user) yield node as stargazer
    MERGE (parent) <-[:{STAR}]- (stargazer)
    return stargazer.login as result
UNION all
    WITH parent, watchers
    UNWIND watchers AS user
    call apoc.merge.node(["{OWNER}", user.__typename], {{login: user.login}}, user, user) yield node as watcher
    MERGE (parent) <-[:{WATCH}]- (watcher)
    return watcher.login as result
UNION all
    WITH parent, forks
    UNWIND forks as fork
    call apoc.merge.node(["{OWNER}", fork.owner.__typename], {{login: fork.owner.login}}, fork.owner, fork.owner) yield node as owner
    MERGE (repo:{REPOSITORY} {{id: fork.id}})<-[:{OWN}]-(owner)
    SET repo += {{ isFork: fork.isFork, name: fork.name, url: fork.url, login: fork.owner.login, patch_date: fork.patch_date }}
    MERGE (repo)<-[:{OWN}]-(owner)
    MERGE (parent)<-[:{FORK}]-(repo)
    return owner.login as result
}}
return result
'''

# read nodes/relationships
# GET_FORK_COUNT = f'''
# MATCH (:{OWNER} {{login: $login}})-[:{OWN}]->(:{REPOSITORY} {{name: $name}})<-[:{FORK}*]-(fork:{REPOSITORY})
# return count(fork) as count
# '''
GET_COUNTS = f'''
{CREATE_REPOSITORY_WITHOUT_RET}
return COUNT {{ (repo)<-[:{STAR}]-() }} as stargazers,
    COUNT {{ (repo)<-[:{WATCH}]-() }} as watchers,
    COUNT {{ (repo)<-[:{FORK}*]-() }} as forks,
    repo.stargazer_cursor as stargazer_cursor,
    repo.watcher_cursor as watcher_cursor,
    repo.fork_cursor as fork_cursor,
    repo.name as name
'''


GET_TOP_ORGANIZATIONS = f'''
MATCH (organizations:{REPOSITORY})-[r:{FORK}]->(repo:{REPOSITORY} {{id: $id}}) RETURN organizations as org, COUNT  {{(organizations)<-[r2:{FORK}]-()}}  as forkcount ORDER BY forkcount DESC LIMIT $limit
'''


GET_FORKS = f'''
MATCH (forks:{REPOSITORY})-[r:{FORK}]->(repo:{REPOSITORY} {{id: $id}}) RETURN forks as fork
'''

DELETE_REPO = f'''
MATCH (downstream)-[edges*]->(r:{REPOSITORY} {{name: $name}})<-[:OWN]-(:{OWNER} {{login: $login}}) FOREACH (e in edges | DELETE e) DETACH DELETE downstream,r
'''
