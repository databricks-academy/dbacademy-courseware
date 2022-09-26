from dbacademy_gems import dbgems
from dbacademy_courseware import validate_type

class Validator:
    from .publisher_class import Publisher

    def __init__(self, publisher: Publisher):
        self.i18n = publisher.i18n
        self.common_language = publisher.common_language

        self.build_name = publisher.build_name
        self.version = publisher.version
        self.core_version = publisher.core_version
        self.build_name = publisher.build_name
        self.client = publisher.client

        self.target_repo_url = publisher.target_repo_url
        self.temp_repo_dir = publisher.temp_repo_dir
        self.temp_work_dir = publisher.temp_work_dir
        self.username = publisher.username

    def validate_publishing_processes(self):
        self.validate_distribution_dbc(as_latest=True)
        print("-" * 80)
        self.validate_distribution_dbc(as_latest=False)
        print("-" * 80)
        self.validate_git_releases_dbc()
        print("-" * 80)
        self.validate_git_branch("published")
        print("-" * 80)
        self.validate_git_branch(f"published-v{self.core_version}")

    @dbgems.deprecated(reason="Validator.validate_distribution_dbc() was deprecated, see Validator.validate_publishing_processes()() instead")
    def validate_distribution_dbc(self, as_latest: bool):
        from dbacademy_gems import dbgems

        label = "vLatest" if as_latest else self.version
        file_name = f"vLATEST/notebooks.dbc" if as_latest else f"v{self.version}/{self.build_name}-v{self.version}.dbc"

        print(f"\nValidating the DBC in DBAcademy's distribution system ({label})\n")

        target_path = f"dbfs:/mnt/secured.training.databricks.com/distributions/{self.build_name}/{file_name}"
        files = dbgems.dbutils.fs.ls(target_path)  # Generates an un-catchable exception
        assert len(files) == 1, f"The distribution DBC was not found at \"{target_path}\"."

        print(f"PASSED: v{self.version} found in \"s3://secured.training.databricks.com/distributions/{self.build_name}/{file_name}\".")

    @dbgems.deprecated(reason="Validator.validate_distribution_dbc() was deprecated, see Validator.validate_publishing_processes()() instead")
    def validate_git_releases_dbc(self, version=None):
        print("Validating the DBC in GitHub's Releases page\n")

        version = version or self.version
        core_version = version.split("-")[0]

        base_url = self.target_repo_url[:-4] if self.target_repo_url.endswith(".git") else self.target_repo_url
        dbc_url = f"{base_url}/releases/download/v{core_version}/{self.build_name}-v{self.version}.dbc"

        return self.__validate_dbc(version=version,
                                   dbc_url=dbc_url)

    def __validate_dbc(self, version=None, dbc_url=None):
        version = version or self.version

        self.client.workspace.mkdirs(self.temp_work_dir)
        dbc_target_dir = f"{self.temp_work_dir}/{self.build_name}-v{version}"

        name = dbc_url.split("/")[-1]
        print(f"Importing {name}")
        print(f" - Source: {dbc_url}")
        print(f" - Target: {dbc_target_dir}")

        self.client.workspace.delete_path(dbc_target_dir)
        self.client.workspace.import_dbc_files(dbc_target_dir, source_url=dbc_url)

        print()
        self.__validate_version_info(version, dbc_target_dir)

    def __validate_version_info(self, version, dbc_dir):
        version = version or self.version

        version_info_path = f"{dbc_dir}/Version Info"
        source = self.client.workspace.export_notebook(version_info_path)
        assert f"**{version}**" in source, f"Expected the notebook \"Version Info\" at \"{version_info_path}\" to contain the version \"{version}\""
        print(f"PASSED: v{version} found in \"{version_info_path}\"")

    @dbgems.deprecated(reason="Validator.validate_git_branch() was deprecated, see Validator.validate_publishing_processes()() instead")
    def validate_git_branch(self, branch="published", version=None):
        print(f"Validating the \"{branch}\" branch in the public, student-facing repo.\n")

        if self.i18n:
            target_dir = f"{self.temp_repo_dir}/{self.username}-{self.build_name}-{self.common_language}-{branch}"
            self.__reset_repo(branch=branch,
                              target_dir=target_dir,
                              target_repo_url=f"https://github.com/databricks-academy/{self.build_name}-{self.common_language}.git")
        else:
            target_dir = f"{self.temp_repo_dir}/{self.username}-{self.build_name}-{branch}"
            self.__reset_repo(branch=branch,
                              target_dir=target_dir,
                              target_repo_url=f"https://github.com/databricks-academy/{self.build_name}.git")
        print()
        self.__validate_version_info(version, target_dir)

    def __reset_repo(self, *, target_dir: str, target_repo_url: str, branch: str = "published"):
        target_dir = validate_type(target_dir, "target_dir", str)
        target_repo_url = validate_type(target_repo_url, "target_repo_url", str)

        print(f"Resetting git repo:")
        print(f" - Branch: \"{branch}\"")
        print(f" - Source: {target_repo_url}")
        print(f" - Target: {target_dir}")

        status = self.client.workspace().get_status(target_dir)

        if status is not None:
            target_repo_id = status["object_id"]
            self.client.repos().delete(target_repo_id)

        # Re-create the repo to progress in testing
        response = self.client.repos.create(path=target_dir, url=target_repo_url)
        repo_id = response.get("id")

        if response.get("branch") != branch:
            self.client.repos.update(repo_id=repo_id, branch=branch)

        results = self.client.repos.get(repo_id)
        current_branch = results.get("branch")

        assert branch == current_branch, f"Expected the new branch to be {branch}, found {current_branch}"
