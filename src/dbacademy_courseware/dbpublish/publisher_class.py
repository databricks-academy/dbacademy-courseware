from typing import List
from .notebook_def_class import NotebookDef
from dbacademy_courseware.dbbuild import BuildConfig


class Publisher:
    def __init__(self, build_config: BuildConfig):
        assert type(build_config) == BuildConfig, f"Expected build_config to be of type BuildConfig, found {type(BuildConfig)}"

        self.build_config = build_config
        self.version_info_notebook = "Version Info"

        self.client = build_config.client
        self.version = build_config.version

        self.source_dir = build_config.source_dir
        self.target_dir = f"{self.build_config.source_repo}/Published/{self.build_config.name} - v{self.build_config.version}"

        self.i18n_resources_dir = f"{build_config.source_repo}/Resources/{build_config.i18n_language}"
        self.i18n_language = build_config.i18n_language

        self.notebooks = []
        self._init_notebooks(build_config.notebooks.values())

        self.white_list = build_config.white_list
        self.black_list = build_config.black_list
        self._validate_white_black_list()

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

    def publish(self, *, mode, verbose=False, debugging=False):
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

            deleted = []
            keepers = [f"{self.target_dir}/{k}" for k in [".gitignore", "README.md", "LICENSE", "docs"]]

            for path in [p.get("path") for p in self.client.workspace.ls(self.target_dir) if p.get("path") not in keepers]:
                deleted.append(path)
                self.print_if(verbose, f"...{path}")
                self.client.workspace().delete_path(path)

            self.print_if(verbose, f"...{len(deleted)} files")
            for path in deleted:
                self.print_if(verbose, print(f" - {path}"))

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

    def create_publish_message(self):
        from dbacademy_gems import dbgems
        from dbacademy_courseware import get_workspace_url

        name = self.build_config.name
        version = self.build_config.version
        source_repo = self.build_config.source_repo

        message = f"""
@channel Published {name}, v{version}

Release Notes:
* UPDATE FROM CHANGE LOG

Release notes, course-specific requirements, issue-tracking, and test results for this course can be found in the course's GitHub repository at https://github.com/databricks-academy/{source_repo.split("/")[-1]}

Please feel free to reach out to me (via Slack), or anyone on the curriculum team should you have any questions.""".strip()

        html = f"""
        <body>
            <p><a href="{get_workspace_url()}#workspace{self.target_dir}/{self.version_info_notebook}" target="_blank">Published Version</a></p>
            <textarea style="width:100%" rows=11> \n{message}</textarea>
        </body>"""
        dbgems.display_html(html)

    @staticmethod
    def print_if(condition, text):
        if condition:
            print(text)

    def reset_repo(self, target_dir, target_url):
        self.target_dir = target_dir

        print(f"Resetting git repo:")
        print(f" - {self.target_dir}")
        print(f" - {target_url}")

        status = self.client.workspace().get_status(self.target_dir)

        if status is None:
            print(f"...not found: {self.target_dir}")
        else:
            target_repo_id = status["object_id"]
            self.client.repos().delete(target_repo_id)
            print(f"...removed")

        # Re-create the repo to progress in testing
        self.client.repos().create(path=self.target_dir, url=target_url)
        print(f"...re-imported")

    # def copy_docs(self):
