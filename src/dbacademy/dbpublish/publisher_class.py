import typing
from .notebook_def_class import NotebookDef


class Publisher:
    def __init__(self, client, version: str, source_dir: str, target_dir: str, i18n_resources_dir: str, i18n_language: str):
        self.client = client
        self.version = version

        self.source_dir = source_dir
        self.target_dir = target_dir

        self.i18n_language = i18n_language
        self.i18n_resources_dir = i18n_resources_dir

        self.notebooks: typing.List[NotebookDef] = []

        self.version_info_notebook = "Version Info"

    def add_all(self, notebooks):

        if type(notebooks) == dict:
            print(f"DEBUG: Converting dict to list in Publisher.add_all")
            notebooks = list(notebooks.values())

        for notebook in notebooks:
            self.add_notebook(notebook)

    def add_notebook(self, notebook):
        from datetime import datetime

        assert type(notebook) == NotebookDef, f"""Expected the parameter "notebook" to be of type "NotebookDef", found "{type(notebook)}" """

        # Add the universal replacements
        notebook.replacements["version_number"] = self.version
        notebook.replacements["built_on"] = datetime.now().strftime("%b %-d, %Y at %H:%M:%S UTC")

        self.notebooks.append(notebook)

    def create_resource_bundle(self, natural_language: str, target_dir: str):
        for notebook in self.notebooks:
            notebook.create_resource_bundle(natural_language, self.source_dir, target_dir)

    def publish(self, testing, mode=None, verbose=False, debugging=False, exclude=None):
        main_notebooks: typing.List[NotebookDef] = []

        mode = str(mode).lower()
        expected_modes = ["delete", "overwrite", "no-overwrite"]
        assert mode in expected_modes, f"Expected mode {mode} to be one of {expected_modes}"

        found_version_info = False
        exclude = list() if exclude is None else exclude

        for notebook in self.notebooks:
            if notebook.path in exclude:
                print(f"Excluding: {notebook.path}")  # Don't do anything with this notebook
            else:
                if notebook.path == self.version_info_notebook: found_version_info = True
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
        print(f"  exclude =   {exclude}")

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

Please feel free to reach out to me (via Slack) or anyone on the curriculum team should you have any questions.""".strip()

        return f"""
        <body>
            <p><a href="https://{domain}/?o={workspace_id}#workspace{self.target_dir}/{self.version_info_notebook}" target="_blank">Published Version</a></p>
            <textarea style="width:100%" rows=11> \n{message}</textarea>
        </body>"""

    @staticmethod
    def print_if(condition, text):
        if condition:
            print(text)
