class AssetValidator:
    from .publisher_class import Publisher

    def __init__(self, publisher: Publisher):
        self.build_config = publisher.build_config
        self.publisher = publisher

    def validate_distribution_dbc(self, version=None):
        version = version or self.build_config.version
        build_name = self.build_config.build_name

        dbc_url = f"s3://dbacademy-secured/distributions/{build_name}/{build_name}-v{version}.dbc"

        return self.validate_dbc(version=version,
                                 dbc_url=dbc_url)

    def validate_git_releases_dbc(self, version=None):
        version = version or self.build_config.version
        build_name = self.build_config.build_name

        target_url = self.publisher.target_repo_url
        base_url = target_url[:-4] if target_url.endswith(".git") else target_url
        dbc_url = f"{base_url}/releases/download/v{version}/{build_name}-v{version}.dbc"

        return self.validate_dbc(version=version,
                                 dbc_url=dbc_url)

    def validate_dbc(self, version=None, dbc_url=None):
        version = version or self.build_config.version
        build_name = self.build_config.build_name
        client = self.build_config.client

        dbc_target_dir = f"/Shared/Working/{build_name}-v{version}"

        name = dbc_url.split("/")[-1]
        print(f"Importing {name}")
        print(f" - Source: {dbc_url}")
        print(f" - Target: {dbc_target_dir}")

        client.workspace.delete_path(dbc_target_dir)
        client.workspace.import_dbc_files(dbc_target_dir, source_url=dbc_url)

        print()
        self._validate_version_info(version, dbc_target_dir)

    def _validate_version_info(self, version, dbc_dir):
        version_info_path = f"{dbc_dir}/Version Info"
        source = self.build_config.client.workspace.export_notebook(version_info_path)
        assert "# MAGIC * Version:  **2.3.5**" in source, f"Expected the notebook \"Version Info\" at \"{version_info_path}\" to contain the version \"{version}\""
        print(f"PASSED: v{version} at {version_info_path}")

    def validate_git_branch(self, branch="published", version=None):
        version = version or self.build_config.version
        build_name = self.build_config.build_name
        common_language = self.publisher.common_language

        if common_language is None:
            target_dir = f"/Repos/Working/{build_name}"
            self.publisher.reset_repo(branch=branch,
                                      target_dir=target_dir,
                                      target_repo_url=f"https://github.com/databricks-academy/{build_name}.git")
        else:
            target_dir = f"/Repos/Working/{build_name}-{common_language}"
            self.publisher.reset_repo(branch=branch,
                                      target_dir=target_dir,
                                      target_repo_url=f"https://github.com/databricks-academy/{build_name}-{common_language}.git")
        print()
        self._validate_version_info(version, target_dir)
