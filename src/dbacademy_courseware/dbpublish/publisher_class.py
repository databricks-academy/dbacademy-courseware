from typing import List
from .notebook_def_class import NotebookDef


class Publisher:
    def __init__(self, client, version: str, source_dir: str, target_dir: str, i18n_resources_dir: str, i18n_language: str, white_list: List[str], black_list: List[str], notebooks: List[NotebookDef]):
        from datetime import datetime

        self.client = client
        self.version = version

        self.source_dir = source_dir
        self.target_dir = target_dir

        self.i18n_language = i18n_language
        self.i18n_resources_dir = i18n_resources_dir

        self.version_info_notebook = "Version Info"

        self.white_list = white_list
        self.black_list = black_list

        if self.white_list or self.black_list:
            assert self.white_list is not None, "The white_list must be specified when specifying a black_list"
            assert self.black_list is not None, "The black_list must be specified when specifying a white_list"

        self.notebooks = []
        for notebook in notebooks:
            assert type(notebook) == NotebookDef, f"Expected the parameter \"notebook\" to be of type \"NotebookDef\", found \"{type(notebook)}\"."

            # Add the universal replacements
            notebook.replacements["version_number"] = self.version
            notebook.replacements["built_on"] = datetime.now().strftime("%b %-d, %Y at %H:%M:%S UTC")
            self.notebooks.append(notebook)

        notebook_paths = [n.path for n in notebooks]
        # Validate white and black lists
        for path in white_list:
            assert path not in black_list, f"The white-list path \"{path}\" was also found in the black-list."
            assert path not in notebook_paths, f"The white-list path \"{path}\" does not exist in the complete set of notebooks.\n{notebook_paths}"

        for path in black_list:
            assert path not in white_list, f"The black-list path \"{path}\" was also found in the white-list."
            assert path not in notebook_paths, f"The black-list path \"{path}\" does not exist in the complete set of notebooks.\n{notebook_paths}"

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
            if notebook.path in self.black_list:
                # Don't do anything with this notebook
                print(f"Excluding: {notebook.path}")
            else:
                found_version_info = True if notebook.path == self.version_info_notebook else found_version_info
                main_notebooks.append(notebook)

        assert found_version_info, f"The required notebook \"{self.version_info_notebook}\" was not found."

        if len(self.black_list) > 0: print("-"*80)

        print(f"Source: {self.source_dir}")
        print(f"Target: {self.target_dir}")
        print()
        print("Arguments:")
        print(f"  mode =      {mode}")
        print(f"  verbose =   {verbose}")
        print(f"  debugging = {debugging}")
        print(f"  testing =   {testing}")
        print(f"  exclude =   {self.black_list}")

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
