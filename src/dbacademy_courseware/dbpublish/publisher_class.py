from typing import List
from .notebook_def_class import NotebookDef
from dbacademy_courseware.dbbuild import BuildConfig


class Publisher:

    MODE_DELETE = "delete"
    MODE_OVERWRITE = "overwrite"
    MODE_NO_OVERWRITE = "no-overwrite"
    EXPECTED_MODES = [MODE_DELETE, MODE_OVERWRITE, MODE_NO_OVERWRITE]

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

        if build_config.i18n_language is None:
            self.common_language = "english"
        else:
            # Include the i18n code in the version.
            # This hack just happens to work for japanese and korean
            self.common_language = build_config.i18n_language.split("-")[0]

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

    def publish_notebooks(self, *, mode, verbose=False, debugging=False):
        from dbacademy_gems import dbgems
        from dbacademy_courseware import get_workspace_url

        main_notebooks: List[NotebookDef] = []

        mode = str(mode).lower()

        assert mode in Publisher.EXPECTED_MODES, f"Expected mode {mode} to be one of {Publisher.EXPECTED_MODES}"

        found_version_info = False

        for notebook in self.notebooks:
            if self.black_list is None or notebook.path not in self.black_list:
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

        elif mode == Publisher.MODE_NO_OVERWRITE:
            assert target_status is None, f"The target path already exists and the build is configured for {Publisher.MODE_NO_OVERWRITE}"

        elif mode == Publisher.MODE_DELETE:
            self.print_if(verbose, "-"*80)
            self.print_if(verbose, f"Deleting from {self.target_dir}...")

            deleted = []
            keepers = [f"{self.target_dir}/{k}" for k in [".gitignore", "README.md", "LICENSE", "docs"]]

            for path in [p.get("path") for p in self.client.workspace.ls(self.target_dir) if p.get("path") not in keepers]:
                deleted.append(path)
                self.print_if(verbose, f"...{path}")
                self.client.workspace().delete_path(path)

        elif mode.lower() != Publisher.MODE_OVERWRITE:
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

        html = f"""<html><body><p><a href="{get_workspace_url()}#workspace{self.target_dir}/{self.version_info_notebook}" target="_blank">Published Version</a></p></body></html>"""
        dbgems.display_html(html)

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

        content = "<div>"
        for group_name, group in self.build_config.publishing_info.items():
            content += f"""<div style="font-size:16px; margin-bottom:1em">{group_name}</div>"""
            for link_name, url in group.items():
                content += f"""<li><a href="{url}" target="_blank" style="font-size:16px">{link_name}</a></li>"""
        content += "</div>"

        message = f"""@channel Published {name}, v{version}

Change Log:\n"""

        for entry in self.build_config.change_log:
            message += entry
            message += "\n"

        message += f"""
\n\nRelease notes, course-specific requirements, issue-tracking, and test results for this course can be found in the course's GitHub repository at https://github.com/databricks-academy/{source_repo.split("/")[-1]}

Please feel free to reach out to me (via Slack), or anyone on the curriculum team should you have any questions.""".strip()

        rows = len(message.split("\n"))+1
        html = f"""
        <body>
            {content}
            <p><a href="{get_workspace_url()}#workspace{self.target_dir}/{self.version_info_notebook}" target="_blank">Published Version</a></p>
            <textarea style="width:100%" rows={rows}>{message}</textarea>
        </body>"""
        dbgems.display_html(html)

    @staticmethod
    def print_if(condition, text):
        if condition:
            print(text)

    def validate(self):
        print(f"Source: {self.source_dir}")
        print(f"Target: {self.target_dir}")

        print("\nChange Log:")
        for entry in self.build_config.change_log:
            print(f"  {entry}")
        return

    def reset_repo(self, target_dir, target_url):
        self.target_dir = target_dir

        print(f"Resetting git repo:")
        print(f" - {self.target_dir}")
        print(f" - {target_url}")

        status = self.client.workspace().get_status(self.target_dir)

        if status is not None:
            target_repo_id = status["object_id"]
            self.client.repos().delete(target_repo_id)

        # Re-create the repo to progress in testing
        self.client.repos().create(path=self.target_dir, url=target_url)

    def publish_docs(self):
        import os, shutil

        source_docs_path = f"{self.build_config.source_repo}/docs"
        target_docs_path = f"{self.target_dir}/docs/v{self.build_config.version}"

        print(f"Source: {source_docs_path}")
        print(f"Target: {target_docs_path}")

        if os.path.exists(f"/Workspace/{target_docs_path}"):
            shutil.rmtree(f"/Workspace/{target_docs_path}")

        shutil.copytree(src=f"/Workspace/{source_docs_path}",
                        dst=f"/Workspace/{target_docs_path}")

        print("-" * 80)
        for file in os.listdir(f"/Workspace/{target_docs_path}"):
            print(file)

    def to_test_suite(self, test_type: str, keep_success: bool = False):
        from dbacademy_courseware.dbtest import TestSuite
        return TestSuite(build_config=self.build_config,
                         test_dir=self.target_dir,
                         test_type=test_type,
                         keep_success=keep_success)

    def _generate_html(self, notebook):
        import time
        from dbacademy_gems import dbgems

        if notebook.test_round < 2:
            return  # Skip for rounds 0 & 1

        start = int(time.time())

        path = f"../Source/{notebook.path}"
        dbgems.get_dbutils().notebook.run(path, timeout_seconds=60 * 5, arguments={
            "version": self.build_config.version,
            "generating_docs": True
        })

        print(f"Completed {notebook.path} in {int(time.time()) - start} seconds")

    def generate_docs(self):
        from multiprocessing.pool import ThreadPool

        with ThreadPool(len(self.build_config.notebooks)) as pool:
            pool.map(self._generate_html, self.build_config.notebooks.values())

    def create_dbc(self, target_file: str = None):
        import os, shutil
        from dbacademy_gems import dbgems

        data = self.build_config.client.workspace.export_dbc(self.target_dir)

        target_file = target_file or f"dbfs:/FileStore/tmp/{self.build_config.build_name}-v{self.build_config.version}.dbc"
        target_file = target_file.replace("dbfs:/", "/dbfs/")
        target_dir = "/".join(target_file.split("/")[:-1])

        if os.path.exists(target_dir): shutil.rmtree(target_dir)
        os.mkdir(target_dir)

        with open(target_file, "wb") as f:
            f.write(data)

        url = target_file.replace("/dbfs/FileStore/", "/files/")
        dbgems.display_html(f"""<a href="{url}" target="_blank">Download</a>""")
