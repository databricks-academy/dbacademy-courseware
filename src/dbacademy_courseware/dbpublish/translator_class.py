from typing import Callable
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

        self.errors = []
        self.warnings = []
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
        self.core_version = self.core_version[1:]
        self.version = f"{self.core_version}-{code}"

        # Include the i18n code in the version.
        # This hack just happens to work for japanese and korean
        self.common_language = self.i18n_language.split("-")[0]

    def _reset_source_repo(self, source_dir: str = None, source_repo_url: str = None, source_branch: str = None):
        from dbacademy_courseware.dbpublish import Publisher

        self.source_branch = source_branch or f"published-v{self.core_version}"
        self.source_dir = source_dir or f"/Repos/Working/{self.build_name}-english_{self.source_branch}"
        self.source_repo_url = source_repo_url or f"https://github.com/databricks-academy/{self.build_name}-english.git"

        Publisher.reset_git_repo(self.client, self.source_dir, self.source_repo_url, self.source_branch)

    def _reset_target_repo(self, target_dir: str = None, target_repo_url: str = None, target_branch: str = None):
        from dbacademy_courseware.dbpublish import Publisher

        self.target_branch = target_branch or "published"
        self.target_dir = target_dir or f"/Repos/Working/{self.build_name}-{self.common_language}-{self.core_version}"
        self.target_repo_url = target_repo_url or f"https://github.com/databricks-academy/{self.build_name}-{self.common_language}.git"

        Publisher.reset_git_repo(self.client, self.target_dir, self.target_repo_url, self.target_branch)

    def validate(self):
        self._reset_source_repo()
        self._reset_target_repo()
        print(f"version:          {self.version}")
        print(f"core_version:     {self.core_version}")
        print(f"common_language:  {self.common_language}")
        print(f"resources_folder: {self.resources_folder}")

    def _load_i18n_source(self, path):
        import os

        if path.startswith("Solutions/"): path = path[10:]
        if path.startswith("Includes/"): return ""

        i18n_source_path = f"/Workspace{self.resources_folder}/{self.i18n_language}/{path}.md"
        assert os.path.exists(i18n_source_path), f"Cannot find {i18n_source_path}"

        with open(f"{i18n_source_path}") as f:
            source = f.read()
            source = source.replace("<hr />\n--i18n-", "<hr>--i18n-")
            source = source.replace("<hr sandbox />\n--i18n-", "<hr sandbox>--i18n-")
            return source

    @staticmethod
    def _load_i18n_guid_map(path: str, i18n_source: str):
        import re
        from dbacademy_courseware.dbpublish import NotebookDef

        if i18n_source is None:
            return dict()

        i18n_guid_map = dict()

        # parts = re.split(r"^<hr>--i18n-", i18n_source, flags=re.MULTILINE)
        parts = re.split(r"^<hr>--i18n-|^<hr sandbox>--i18n-", i18n_source, flags=re.MULTILINE)

        name = parts[0].strip()[3:]
        path = path[10:] if path.startswith("Solutions/") else path
        if not path.startswith("Includes/"):
            assert name == path, f"Expected the notebook \"{path}\", found \"{name}\""

        for part in parts[1:]:
            guid, value = NotebookDef.parse_guid_and_value(part)

            i18n_guid_map[guid] = value

        return i18n_guid_map

    def publish(self):
        from datetime import datetime
        from dbacademy_courseware.dbpublish import Publisher, NotebookDef

        Publisher.clean_target_dir(self.client, self.target_dir, verbose=False)

        prefix = len(self.source_dir) + 1
        source_files = [f.get("path")[prefix:] for f in self.client.workspace.ls(self.source_dir, recursive=True)]

        for file in source_files:
            source = self._load_i18n_source(file)
            i18n_guid_map = self._load_i18n_guid_map(file, source)

            source_notebook_path = f"{self.source_dir}/{file}"
            target_notebook_path = f"{self.target_dir}/{file}"

            source_info = self.client.workspace().get_status(source_notebook_path)
            language = source_info["language"].lower()
            cmd_delim = NotebookDef.get_cmd_delim(language)
            cm = NotebookDef.get_comment_marker(language)

            raw_source = self.client.workspace().export_notebook(source_notebook_path)
            raw_lines = raw_source.split("\n")
            header = raw_lines.pop(0)
            source = "\n".join(raw_lines)

            commands = source.split(cmd_delim)
            new_commands = [commands.pop(0)]

            for i, command in enumerate(commands):
                command = command.strip()
                line_zero = command.split("\n")[0]

                pos_a = line_zero.find("<i18n value=\"")
                if pos_a == -1:
                    new_commands.append(command)
                    continue

                pos_b = line_zero.find("/>")
                guid = f"--i18n-{command[pos_a + 13:pos_b - 1]}"
                assert guid in i18n_guid_map

                lines = [f"{cm} MAGIC {line}" for line in i18n_guid_map[guid].split("\n")]
                lines.insert(0, line_zero)
                new_command = "\n".join(lines)
                new_commands.append(new_command)

            new_source = f"{header}\n"
            new_source += f"\n{cmd_delim}\n".join(new_commands)

            new_source = new_source.replace("{{version_number}}", self.version)

            built_on = datetime.now().strftime("%b %-d, %Y at %H:%M:%S UTC")
            new_source = new_source.replace("{{built_on}}", built_on)

            target_notebook_dir = "/".join(target_notebook_path.split("/")[:-1])

            self.client.workspace.mkdirs(target_notebook_dir)
            self.client.workspace.import_notebook(language=language.upper(),
                                                  notebook_path=target_notebook_path,
                                                  content=new_source,
                                                  overwrite=True)
