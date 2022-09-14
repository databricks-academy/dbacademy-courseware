from dbacademy_courseware import validate_type

class Translator:
    from dbacademy_courseware.dbbuild import BuildConfig

    def __init__(self, build_config: BuildConfig):
        from dbacademy_courseware.dbbuild import BuildConfig

        self.build_config = validate_type(build_config, "build_config", BuildConfig)
        # Copied from build_config
        self.client = build_config.client
        # self.source_repo = build_config.source_repo
        self.notebooks = build_config.notebooks
        self.build_name = build_config.build_name

        # Defined in select_language
        self.version = None
        self.core_version = None
        self.common_language = None
        self.resources_folder = None

        # Defined in rest_repo
        self.branch = None
        self.target_dir = None
        self.target_repo_url = None

        self._select_i18n_language()

    def _select_i18n_language(self):
        from dbacademy_gems import dbgems
        from dbacademy_courseware.dbbuild import BuildConfig

        self.resources_folder = f"{self.source_repo}/Resources"

        resources = self.client.workspace().ls(resources_folder)
        self.language_options = [r.get("path").split("/")[-1] for r in resources if not r.get("path").startswith("english-")]
        self.language_options.sort()

        dbgems.get_dbutils().widgets.dropdown("i18n_language",
                                              self.language_options[0],
                                              self.language_options,
                                              "i18n Language")

        self.i18n_language = dbgems.get_parameter("i18n_language", None)
        assert self.i18n_language is not None, f"The i18n language must be specified."

        for notebook in self.notebooks.values():
            notebook.i18n_language = self.i18n_language

        # Include the i18n code in the version.
        # This hack just happens to work for japanese and korean
        code = self.i18n_language[0:2].upper()
        self.common_language, self.core_version = self.i18n_language.split("-")
        self.version = f"{self.core_version}-{code}"

        # Include the i18n code in the version.
        # This hack just happens to work for japanese and korean
        self.common_language = self.i18n_language.split("-")[0]

    def reset_repo(self, target_dir: str = None, target_repo_url: str = None, branch: str = "published"):

        self.branch = branch
        self.target_dir = target_dir or f"/Repos/Working/{self.build_name}-{self.common_language}"
        self.target_repo_url = target_repo_url or f"https://github.com/databricks-academy/ml-in-production-{self.common_language}.git"

        print(f"Resetting git repo:")
        print(f" - Branch: \"{self.branch}\"")
        print(f" - Target: {self.target_dir}")
        print(f" - Source: {self.target_repo_url}")

        status = self.client.workspace().get_status(self.target_dir)

        if status is not None:
            target_repo_id = status["object_id"]
            self.client.repos().delete(target_repo_id)

        # Re-create the repo to progress in testing
        response = self.client.repos.create(path=self.target_dir, url=self.target_repo_url)
        repo_id = response.get("id")

        if response.get("branch") != self.branch:
            self.client.repos.update(repo_id=repo_id, branch=self.branch)

        results = self.client.repos.get(repo_id)
        current_branch = results.get("branch")

        assert self.branch == current_branch, f"Expected the new branch to be {self.branch}, found {current_branch}"
