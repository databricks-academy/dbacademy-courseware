from typing import Type, List
from deprecated.classic import deprecated

class BuildConfig:

    @staticmethod
    def load(file):
        import json

        with open(file) as f:
            config = json.load(f)

            configurations = config.get("notebook_config", dict())
            if "notebook_config" in config: del config["notebook_config"]

            publish_only = config.get("publish_only", None)
            if "publish_only" in config: del config["publish_only"]

            build_config = BuildConfig(**config)

            def validate_type(key: str, expected_type: Type, actual_value):
                assert type(actual_value) == expected_type, f"Expected the value for \"{key}\" to be of type \"{expected_type}\", found \"{type(actual_value)}\"."
                return actual_value

            for name in configurations:
                assert name in build_config.notebooks, f"The notebook \"{name}\" doesn't exist."
                notebook = build_config.notebooks[name]
                notebook_config = configurations.get(name)

                param = "include_solution"
                if param in notebook_config:
                    value = validate_type(param, bool, notebook_config.get(param))
                    notebook.include_solution = value

                param = "test_round"
                if param in notebook_config:
                    value = validate_type(param, int, notebook_config.get(param))
                    notebook.test_round = value

                param = "ignored"
                if param in notebook_config:
                    value = validate_type(param, bool, notebook_config.get(param))
                    notebook.ignored = value

                param = "order"
                if param in notebook_config:
                    value = validate_type(param, int, notebook_config.get(param))
                    notebook.order = value

                param = "replacements"
                if param in notebook_config:
                    value = validate_type(param, int, notebook_config.get(param))
                    notebook.replacements = value

                param = "ignored_errors"
                if param in notebook_config:
                    value = validate_type(param, List, notebook_config.get(param))
                    notebook.ignoring = value

            if publish_only is not None:
                build_config.white_list = publish_only.get("white_list", None)
                assert build_config.white_list is not None, "The white_list must be specified when specifying publish_only"

                build_config.black_list = publish_only.get("black_list", None)
                assert build_config.black_list is not None, "The black_list must be specified when specifying publish_only"

            return build_config

    def __init__(self,
                 name: str,
                 version: str = 0,
                 spark_version: str = None,
                 cloud: str = None,
                 instance_pool: str = None,
                 workers: int = None,
                 libraries: list = None,
                 client=None,
                 source_dir: str = None,
                 source_repo: str = None,
                 spark_conf: dict = None,
                 job_arguments: dict = None,
                 include_solutions: bool = True,
                 i18n: bool = False,
                 i18n_language: str = None,
                 ignoring: list = None):

        import uuid, time
        from dbacademy import dbrest
        from dbacademy_gems import dbgems

        self.ignoring = [] if ignoring is None else ignoring

        self.i18n = i18n
        self.i18n_language = i18n_language

        self.test_type = None
        self.notebooks = None
        self.client = dbrest.DBAcademyRestClient() if client is None else client

        # The instance of this test run
        self.suite_id = str(time.time()) + "-" + str(uuid.uuid1())

        # The name of the cloud on which this tests was ran
        self.cloud = dbgems.get_cloud() if cloud is None else cloud

        # Course Name
        self.name = name
        assert self.name is not None, "The course's name must be specified."

        # The Distribution's version
        self.version = version
        assert self.version is not None, "The course's version must be specified."

        # The runtime you wish to test against
        self.spark_version = self.client.clusters().get_current_spark_version() if spark_version is None else spark_version

        # We can use local-mode clusters here
        self.workers = 0 if workers is None else workers

        # The instance pool from which to obtain VMs
        self.instance_pool = self.client.clusters().get_current_instance_pool_id() if instance_pool is None else instance_pool

        # Spark configuration parameters
        self.spark_conf = dict() if spark_conf is None else spark_conf
        if self.workers == 0:
            self.spark_conf["spark.master"] = "local[*]"

        # Test-Job's arguments
        self.job_arguments = dict() if job_arguments is None else job_arguments

        # The libraries to be attached to the cluster
        self.libraries = [] if libraries is None else libraries

        self.source_repo = dbgems.get_notebook_dir(offset=-2) if source_repo is None else source_repo
        self.source_dir = f"{self.source_repo}/Source" if source_dir is None else source_dir

        # We don't want the folling function to fail if we are using the "default" path which
        # may or may not exists. The implication being that this will fail if called explicitly
        self.include_solutions = include_solutions
        self.index_notebooks(include_solutions=include_solutions, fail_fast=source_dir is not None)

        self.white_list = None
        self.black_list = None

    def get_distribution_name(self, version):
        distribution_name = f"{self.name}" if version is None else f"{self.name}-v{version}"
        return distribution_name.replace(" ", "-").replace(" ", "-").replace(" ", "-")

    def index_notebooks(self, include_solutions=True, fail_fast=True):
        from ..dbpublish.notebook_def_class import NotebookDef

        assert self.source_dir is not None, "BuildConfig.source_dir must be specified"

        self.notebooks = dict()
        entities = self.client.workspace().ls(self.source_dir, recursive=True)

        if entities is None and fail_fast is False:
            return  # The directory doesn't exist
        elif entities is None and fail_fast is True:
            raise Exception(f"The specified directory ({self.source_dir}) does not exist (fail_fast={fail_fast}).")

        entities.sort(key=lambda e: e["path"])

        for i in range(len(entities)):
            entity = entities[i]
            order = i       # Start with the natural order
            test_round = 2  # Default test_round for all notebooks
            include_solution = include_solutions  # Initialize to the default value
            path = entity["path"][len(self.source_dir) + 1:]  # Get the notebook's path relative too the source root

            if "includes/" in path.lower():  # Any folder that ends in "includes/"
                test_round = 0  # Never test notebooks in the "includes" folders

            if path.lower() == "includes/reset":
                order = 0                 # Reset needs to run first.
                test_round = 1            # Add to test_round #1
                include_solution = False  # Exclude from the solutions folder

            if path.lower() == "includes/workspace-setup":
                order = 1                 # Reset needs to run first.
                test_round = 1            # Add to test_round #1
                include_solution = False  # Exclude from the solutions folder

            # if path.lower() == "version info":
            #     order = 2                 # Version info to run second.
            #     test_round = 1            # Add to test_round #1
            #     include_solution = False  # Exclude from the solutions folder

            if "wip" in path.lower():
                print(f"""** WARNING ** The notebook "{path}" is excluded from the build as a work in progress (WIP)""")
            else:
                # Add our notebook to the set of notebooks to be tested.
                self.notebooks[path] = NotebookDef(test_round=test_round,
                                                   path=path,
                                                   ignored=False,
                                                   include_solution=include_solution,
                                                   replacements=dict(),
                                                   order=order,
                                                   i18n=self.i18n,
                                                   i18n_language=self.i18n_language,
                                                   ignoring=self.ignoring)

    def print(self):
        print("Build Configuration")
        print(f"suite_id:          {self.suite_id}")
        print(f"name:              {self.name}")
        print(f"version:           {self.version}")
        print(f"spark_version:     {self.spark_version}")
        print(f"workers:           {self.workers}")
        print(f"instance_pool:     {self.instance_pool}")
        print(f"spark_conf:        {self.spark_conf}")
        print(f"cloud:             {self.cloud}")
        print(f"libraries:         {self.libraries}")
        print(f"source_repo:       {self.source_repo}")
        print(f"source_dir:        {self.source_dir}")
        print(f"i18n:              {self.i18n}")
        print(f"i18n_language:     {self.i18n_language}")

        max_name_length = 0
        for path in self.notebooks: max_name_length = len(path) if len(path) > max_name_length else max_name_length

        if len(self.notebooks) == 0:
            print(f"notebooks:         none")
        else:
            print(f"notebooks:         {len(self.notebooks)}")

            rounds = list(map(lambda notebook_path: self.notebooks[notebook_path].test_round, self.notebooks))
            rounds.sort()
            rounds = set(rounds)

            for test_round in rounds:
                if test_round == 0:
                    print("\nRound #0: (published but not tested)")
                else:
                    print(f"\nRound #{test_round}")

                notebook_paths = list(self.notebooks.keys())
                notebook_paths.sort()

                # for path in notebook_paths:
                for notebook in sorted(self.notebooks.values(), key=lambda n: n.order):
                    # notebook = self.notebooks[path]
                    if test_round == notebook.test_round:
                        path = notebook.path.ljust(max_name_length)
                        ignored = str(notebook.ignored).ljust(5)
                        include_solution = str(notebook.include_solution).ljust(5)
                        if len(notebook.replacements.keys()) == 0:
                            print(f"  {notebook.order: >2}: {path}   ignored={ignored}   include_solution={include_solution}   replacements={notebook.replacements}")
                        else:
                            print(f"  {notebook.order: >2}: {path}   ignored={ignored}   include_solution={include_solution}   replacements={{")
                            max_key_length = 0
                            for key in notebook.replacements: max_key_length = len(key) if len(key) > max_key_length else max_key_length

                            for key in notebook.replacements:
                                value = notebook.replacements[key]
                                print(f"        {key}", end="")
                                print(" "*(max_key_length-len(key)), end="")
                                print(f": {value}")
                            print("      }")

        print("-" * 100)

    def to_publisher(self):
        from dbacademy_courseware.dbpublish import Publisher
        return Publisher(self)

@deprecated(reason="Use BuildConfig instead")
class TestConfig(BuildConfig):
    def __init__(self, name: str, version: str = 0, spark_version: str = None, cloud: str = None, instance_pool: str = None, workers: int = None, libraries: list = None, client=None, source_dir: str = None, source_repo: str = None, spark_conf: dict = None, job_arguments: dict = None, include_solutions: bool = True, i18n: bool = False, i18n_language: str = None, ignoring: list = None):
        super().__init__(name=name,
                         version=version,
                         spark_version=spark_version,
                         cloud=cloud,
                         instance_pool=instance_pool,
                         workers=workers,
                         libraries=libraries,
                         client=client,
                         source_dir=source_dir,
                         source_repo=source_repo,
                         spark_conf=spark_conf,
                         job_arguments=job_arguments,
                         include_solutions=include_solutions,
                         i18n=i18n,
                         i18n_language=i18n_language,
                         ignoring=ignoring)
