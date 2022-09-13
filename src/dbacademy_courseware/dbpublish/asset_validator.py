from dbacademy_courseware import validate_type

class AssetValidator:
    from .publisher_class import Publisher

    def __init__(self, publisher: Publisher):
        self.common_language = publisher.common_language
        self.version = publisher.version
        self.core_version = publisher.core_version
        self.build_name = publisher.build_name
        self.client = publisher.client
        self.target_repo_url = publisher.target_repo_url

    @staticmethod
    def validate_distribution_dbc():
        print("Validating the DBC in DBAcademy's distribution system\n")

        print("NOT-IMPLEMENTED: This is projected to be implemented soon.")

        # version = version or self.version
        #
        # dbc_url = f"s3://dbacademy-secured/distributions/{self.build_name}/{self.build_name}-v{version}.dbc"
        #
        # return self.validate_dbc(version=version,
        #                          dbc_url=dbc_url)validate_distribution_dbc

    def validate_git_releases_dbc(self, version=None):
        print("Validating the DBC in GitHub's Releases page\n")

        version = version or self.version
        core_version = version.split("-")[0]

        base_url = self.target_repo_url[:-4] if self.target_repo_url.endswith(".git") else self.target_repo_url
        dbc_url = f"{base_url}/releases/download/v{core_version}/{self.build_name}-v{version}.dbc"

        return self.validate_dbc(version=version,
                                 dbc_url=dbc_url)

    def validate_dbc(self, version=None, dbc_url=None):
        version = version or self.version

        dbc_target_dir = f"/Shared/Working/{self.build_name}-v{version}"

        name = dbc_url.split("/")[-1]
        print(f"Importing {name}")
        print(f" - Source: {dbc_url}")
        print(f" - Target: {dbc_target_dir}")

        self.client.workspace.delete_path(dbc_target_dir)
        self.client.workspace.import_dbc_files(dbc_target_dir, source_url=dbc_url)

        print()
        self._validate_version_info(version, dbc_target_dir)

    def _validate_version_info(self, version, dbc_dir):
        version = version or self.version
        core_version = version.split("-")[0]

        version_info_path = f"{dbc_dir}/Version Info"
        source = self.client.workspace.export_notebook(version_info_path)
        assert f"# MAGIC * Version:  **{core_version}**" in source, f"Expected the notebook \"Version Info\" at \"{version_info_path}\" to contain the version \"{core_version}\""
        print(f"PASSED: v{core_version} found in \"{version_info_path}\"")

    def validate_git_branch(self, branch="published", version=None):
        print(f"Validating the \"{branch}\" branch in the public, student-facing repo.\n")

        if self.common_language is None:
            target_dir = f"/Repos/Working/{self.build_name}-{branch}"
            self.reset_repo(branch=branch,
                            target_dir=target_dir,
                            target_repo_url=f"https://github.com/databricks-academy/{self.build_name}.git")
        else:
            target_dir = f"/Repos/Working/{self.build_name}-{self.common_language}-{branch}"
            self.reset_repo(branch=branch,
                            target_dir=target_dir,
                            target_repo_url=f"https://github.com/databricks-academy/{self.build_name}-{self.common_language}.git")
        print()
        self._validate_version_info(version, target_dir)

    def reset_repo(self, *, target_dir: str, target_repo_url: str, branch: str = "published"):
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
