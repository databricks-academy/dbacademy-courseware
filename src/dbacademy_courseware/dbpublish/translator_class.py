from dbacademy_courseware import validate_type

class Translator:
    from dbacademy_courseware.dbbuild import BuildConfig

    def __init__(self, build_config: BuildConfig):
        from dbacademy_courseware.dbbuild import BuildConfig

        self.build_config = validate_type(build_config, "build_config", BuildConfig)
        # Copied from build_config
        self.client = build_config.client
        self.source_repo = build_config.source_repo
        self.notebooks = build_config.notebooks
        self.version = build_config.version

        # Defined in rest_repo
        self.branch = None
        self.target_dir = None
        self.target_repo_url = None

        self._select_i18n_language()

    def _select_i18n_language(self):
        from dbacademy_gems import dbgems
        from dbacademy_courseware.dbbuild import BuildConfig

        resources_folder = f"{self.source_repo}/Resources"

        resources = self.client.workspace().ls(resources_folder)
        self.language_options = [r.get("path").split("/")[-1] for r in resources if not r.get("path").startswith("english-")]
        self.language_options.sort()

        dbgems.get_dbutils().widgets.dropdown("i18n_language",
                                              self.language_options[0],
                                              self.language_options,
                                              "i18n Language")

        self.i18n_language = dbgems.get_dbutils().widgets.get("i18n_language")
        self.i18n_language = None if self.i18n_language == BuildConfig.LANGUAGE_OPTIONS_DEFAULT else self.i18n_language

        assert self.i18n_language is None or self.i18n_language.endswith(self.version), f"The build version ({self.version}) and the selected language ({self.i18n_language}) do not correspond to each other."

        for notebook in self.notebooks.values():
            notebook.i18n_language = self.i18n_language

        if self.i18n_language is not None:
            # Include the i18n code in the version.
            # This hack just happens to work for japanese and korean
            code = self.i18n_language[0:2].upper()
            self.version = f"{self.version}-{code}"
            self.core_version = self.version if "-" not in self.version else self.version.split("-")[0]

    def reset_repo(self, target_dir: str, target_repo_url: str, branch: str = "published"):
        self.target_dir = validate_type(target_dir, "target_dir", str)
        self.target_repo_url = validate_type(target_repo_url, "target_repo_url", str)

        print(f"Resetting git repo:")
        print(f" - Branch: \"{branch}\"")
        print(f" - Target: {self.target_dir}")
        print(f" - Source: {self.target_repo_url}")

        status = self.client.workspace().get_status(self.target_dir)

        if status is not None:
            target_repo_id = status["object_id"]
            self.client.repos().delete(target_repo_id)

        # Re-create the repo to progress in testing
        response = self.client.repos.create(path=self.target_dir, url=target_repo_url)
        repo_id = response.get("id")

        if response.get("branch") != branch:
            self.client.repos.update(repo_id=repo_id, branch=branch)

        results = self.client.repos.get(repo_id)
        current_branch = results.get("branch")

        assert branch == current_branch, f"Expected the new branch to be {branch}, found {current_branch}"
