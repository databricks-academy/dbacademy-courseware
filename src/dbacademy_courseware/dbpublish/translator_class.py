from dbacademy_courseware import validate_type

class Translator:
    from dbacademy_courseware.dbbuild import BuildConfig

    def __init__(self, build_config: BuildConfig):
        from dbacademy_courseware.dbbuild import BuildConfig

        self.build_config = validate_type(build_config, "build_config", BuildConfig)
        # Copied from build_config
        self.client = build_config.client
        self.notebooks = build_config.notebooks
        self.build_name = build_config.build_name

        # Defined in select_language
        self.version = None
        self.core_version = None
        self.common_language = None
        self.resources_folder = None

        # Defined in rest_repo
        self.source_branch = None
        self.source_dir = None
        self.source_repo_url = None

        self.target_branch = None
        self.target_dir = None
        self.target_repo_url = None

        self._select_i18n_language(build_config.source_repo)

    def _select_i18n_language(self, source_repo: str):
        from dbacademy_gems import dbgems

        self.resources_folder = f"{source_repo}/Resources"

        resources = self.client.workspace().ls(self.resources_folder)
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

    def reset_source_repo(self, source_dir: str = None, source_repo_url: str = None, source_branch: str = "published"):
        from dbacademy_courseware.dbpublish import Publisher

        self.source_branch = source_branch or f"published-{self.core_version}"
        self.source_dir = source_dir or f"/Repos/Working/{self.build_name}-english-{self.source_branch}"
        self.source_repo_url = source_repo_url or f"https://github.com/databricks-academy/{self.build_name}-english.git"

        Publisher.reset_git_repo(self.client, self.source_dir, self.source_repo_url, self.source_branch)

    def reset_target_repo(self, target_dir: str = None, target_repo_url: str = None, target_branch: str = None):
        from dbacademy_courseware.dbpublish import Publisher

        self.target_branch = target_branch or "published"
        self.target_dir = target_dir or f"/Repos/Working/{self.build_name}-{self.common_language}-{self.target_branch}"
        self.target_repo_url = target_repo_url or f"https://github.com/databricks-academy/{self.build_name}-{self.common_language}.git"

        Publisher.reset_git_repo(self.client, self.target_dir, self.target_repo_url, self.target_branch)
