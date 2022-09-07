from typing import List
from .notebook_def_class import NotebookDef
from dbacademy_courseware.dbbuild import BuildConfig


class Publisher:
    def __init__(self, build_config: BuildConfig, target_dir: str = None):
        assert type(build_config) == BuildConfig, f"Expected build_config to be of type BuildConfig, found {type(BuildConfig)}"

        self.version_info_notebook = "Version Info"

        self.client = build_config.client
        self.version = build_config.version

        self.source_dir = build_config.source_dir
        self.target_dir = target_dir or f"{build_config.source_repo}/Published/{build_config.name} - v{build_config.version}"

        self.i18n_resources_dir = f"{build_config.source_repo}/Resources/{build_config.i18n_language}"
        self.i18n_language = build_config.i18n_language

        self.white_list = build_config.white_list
        self.black_list = build_config.black_list
        self._validate_white_black_list()

        self.notebooks = []
        self._init_notebooks(build_config.notebooks.values())

    def _init_notebooks(self, notebooks):
        from datetime import datetime

        for notebook in notebooks:
            assert type(notebook) == NotebookDef, f"Expected the parameter \"notebook\" to be of type \"NotebookDef\", found \"{type(notebook)}\"."

            # Add the universal replacements
            notebook.replacements["version_number"] = self.version
            notebook.replacements["built_on"] = datetime.now().strftime("%b %-d, %Y at %H:%M:%S UTC")

            self.notebooks.append(notebook)

    def _validate_white_black_list(self):
        if self.white_list or self.black_list:
            assert self.white_list is not None, "The white_list must be specified when specifying a black_list"
            assert self.black_list is not None, "The black_list must be specified when specifying a white_list"

            notebook_paths = [n.path for n in self.notebooks]

            # Validate white and black lists
            for path in self.white_list:
                assert path not in self.black_list, f"The white-list path \"{path}\" was also found in the black-list."
                assert path in notebook_paths, f"The white-list path \"{path}\" does not exist in the complete set of notebooks.\n{notebook_paths}"

            for path in self.black_list:
                assert path not in self.white_list, f"The black-list path \"{path}\" was also found in the white-list."
                assert path in notebook_paths, f"The black-list path \"{path}\" does not exist in the complete set of notebooks.\n{notebook_paths}"

            for path in notebook_paths:
                assert path in self.white_list or path in self.black_list, f"The notebook \"{path}\" was not found in either the white-list or black-list."

    def create_resource_bundle(self, natural_language: str, target_dir: str):
        for notebook in self.notebooks:
            notebook.create_resource_bundle(natural_language, self.source_dir, target_dir)

    def publish(self, testing, mode=None, verbose=False, debugging=False):
        main_notebooks: List[NotebookDef] = []

        mode = str(mode).lower()
        expected_modes = ["delete", "overwrite", "no-overwrite"]
        assert mode in expected_modes, f"Expected mode {mode} to be one of {expected_modes}"

        found_version_info = False

        for notebook in self.notebooks:
            if notebook.path not in self.black_list:
                found_version_info = True if notebook.path == self.version_info_notebook else found_version_info
                main_notebooks.append(notebook)

        assert found_version_info, f"The required notebook \"{self.version_info_notebook}\" was not found."

        print(f"Source: {self.source_dir}")
        print(f"Target: {self.target_dir}")
        print()
        print("Arguments:")
        print(f"  mode =      {mode}")
        print(f"  verbose =   {verbose}")
        print(f"  debugging = {debugging}")
        print(f"  testing =   {testing}")

        if self.black_list is None:
            print(f"  exclude:    none")
        else:
            self.black_list.sort()
            print(f"\n  exclude:    {self.black_list[0]}")
            for path in self.black_list[1:]:
                print(f"              {path}")

        if self.white_list is None:
            print(f"  include:    none")
        else:
            self.white_list.sort()
            print(f"\n  include:    {self.white_list[0]}")
            for path in self.white_list[1:]:
                print(f"              {path}")

        # Now that we backed up the version-info, we can delete everything.
        target_status = self.client.workspace().get_status(self.target_dir)
        if target_status is None:
            pass  # Who cares, it doesn't already exist.

        elif mode == "no-overwrite":
            assert target_status is None, "The target path already exists and the build is configured for no-overwrite"

        elif mode == "delete":
            self.print_if(verbose, "-"*80)
            self.print_if(verbose, f"Deleting from {self.target_dir}...")

            keepers = [f"{self.target_dir}/{k}" for k in [".gitignore", "README.md", "LICENSE", "docs"]]

            deleted_count = 0
            for path in [p.get("path") for p in self.client.workspace.ls(self.target_dir) if p.get("path") not in keepers]:
                deleted_count += 1
                self.print_if(verbose, f"...{path}")
                self.client.workspace().delete_path(path)
            self.print_if(verbose, f"...{deleted_count} files")

        elif mode.lower() != "overwrite":
            self.print_if(verbose, "-"*80)
            self.print_if(verbose, f"Overwriting target directory (unused files will not be removed)...")
            raise Exception("Expected mode to be one of None, DELETE or OVERWRITE")

        for notebook in main_notebooks:
            notebook.publish(source_dir=self.source_dir,
                             target_dir=self.target_dir,
                             i18n_resources_dir=self.i18n_resources_dir,
                             verbose=verbose, 
                             debugging=debugging,
                             other_notebooks=self.notebooks)

        print("-"*80)
        print("All done!")

    def create_new_resource_message(self, language, resource_dir, domain="curriculum-dev.cloud.databricks.com", workspace_id="3551974319838082"):
        return f"""
                <body>
                    <p><a href="https://{domain}/?o={workspace_id}#workspace{resource_dir}/{language}/{self.version_info_notebook}.md" target="_blank">Resource Bundle: {language}</a></p>
                </body>"""

    def create_publish_message(self, test_config, domain="curriculum-dev.cloud.databricks.com", workspace_id="3551974319838082"):
        name = test_config.name
        version = test_config.version
        source_repo = test_config.source_repo

        message = f"""
@channel Published {name}, v{version}

Release Notes:
* UPDATE FROM CHANGE LOG

Release notes, course-specific requirements, issue-tracking, and test results for this course can be found in the course's GitHub repository at https://github.com/databricks-academy/{source_repo.split("/")[-1]}

Please feel free to reach out to me (via Slack), or anyone on the curriculum team should you have any questions.""".strip()

        return f"""
        <body>
            <p><a href="https://{domain}/?o={workspace_id}#workspace{self.target_dir}/{self.version_info_notebook}" target="_blank">Published Version</a></p>
            <textarea style="width:100%" rows=11> \n{message}</textarea>
        </body>"""

    @staticmethod
    def print_if(condition, text):
        if condition:
            print(text)
