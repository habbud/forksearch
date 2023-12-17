from .queries import *

from neo4j import GraphDatabase
from neo4j.time import DateTime

class GitDB:
    DEFAULT_REPO_INFO = {
        'stargazers': 0,
        'watchers': 0,
        'forks': 0,
        'stargazer_cursor': None,
        'watcher_cursor': None,
        'fork_cursor': None,
    }

    def __init__(self, host, port, user, pwd, db = 'neo4j') -> None:
        self.driver = GraphDatabase.driver(
            uri=f'bolt://{host}:{port}',
            auth=(user, pwd),
        )
        self.db = db

        # create uniqueness constraints
        ## indexes created when constraints are created
        print ("Creating uniqueness constraints...")
        def uniquenesses(tx):
            tx.run(CREATE_OWNER_UNIQUENESS)
            tx.run(CREATE_REPO_UNIQUENESS)

        self._write(uniquenesses)

    def close(self) -> None:
        self.driver.close()

    def __del__(self) -> None:
        self.close()

    def _(self):
        with self.driver.session(database=self.db) as session:
            results = session.execute_read(lambda tx: tx.run())
        return results

    def _write(self, func):
        with self.driver.session(database=self.db) as session:
            results = session.execute_write(func)
        return results

    def _read(self, func):
        with self.driver.session(database=self.db) as session:
            results = session.execute_read(func)
        return results

    def add_user(self, login, properties):
        # warn: be careful! this will actually modify the original dictionary
        label = properties.pop('__typename')

        result = self._write(
            lambda tx: tx.run(
                CREATE_OWNER,
                label = label,
                properties = {'login': login},
                on_create = {**properties, 'created': DateTime.now()},
                on_merge = {**properties, 'lastSeen': DateTime.now()},
            ).data()
        )

        return result

    def add_all_edges(self, nodes):
        # try:
        # print(list(nodes))
            # print(d)
        result = self._write(
                lambda tx: tx.run(
                    ADD_ALL_EDGES,
                    nodes = nodes,
                ).data()
        )
        # for node in nodes:
        #     print (node)
        #     try:
        #         result = self._write(
        #             lambda tx: tx.run(
        #                 ADD_ALL_EDGES,
        #                 nodes = [node],
        #             ).data()
        #         )
        #     except Exception as e:
        #         print(e)
        #         print("Error adding edges: Node: {},".format(node))
        #         return None

        return result

    def get_repo_info(self, id, login, owner, repo_properties):
        result = self._write(
            lambda tx: tx.run(
                GET_COUNTS,
                id = id,
                login = login,
                label = owner['__typename'],
                properties = {'login': owner['login']},
                on_create = owner,
                on_merge = owner,
                repo_properties = repo_properties,
            ).data()
        )

        # check if result is empty
        if not result:
            return self.DEFAULT_REPO_INFO
        return result[0]
    
    def get_organizations_info(self, id, limit):
        result = self._write(
            lambda tx: tx.run(
                GET_TOP_ORGANIZATIONS,
                id = id,
                limit = limit
            ).data()
        )

        # # check if result is empty
        # print("DEBUG: result is" + str(result))
        if not result:
            return self.DEFAULT_REPO_INFO
        return result
    
    def get_forks_info(self, id,limit=1000):
        result = self._write(
            lambda tx: tx.run(
                GET_FORKS,
                id = id,
                limit=limit
            ).data()
        )

        # # check if result is empty
        # print("DEBUG: result is" + str(result))
        return result
    def get_orgs_forks_info(self, id,limit=1000):
        result = self._write(
            lambda tx: tx.run(
                GET_ORGS_FORKS,
                id = id,
                limit=limit
            ).data()
        )

        # # check if result is empty
        # print("DEBUG: result is" + str(result))
        return result
    
    def delete_repo_info(self, owner, name):
        result = self._write(
            lambda tx: tx.run(
                DELETE_REPO,
                login = owner,
                name = name
            ).data()
        )

        # # check if result is empty
        # print("DEBUG: result is" + str(result))
        return result
