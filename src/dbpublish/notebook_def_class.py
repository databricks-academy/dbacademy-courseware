import os
from typing import Callable
from typing import Union

D_TODO = "TODO"
D_ANSWER = "ANSWER"
D_SOURCE_ONLY = "SOURCE_ONLY"
D_DUMMY = "DUMMY"

D_INCLUDE_HEADER_TRUE = "INCLUDE_HEADER_TRUE"
D_INCLUDE_HEADER_FALSE = "INCLUDE_HEADER_FALSE"
D_INCLUDE_FOOTER_TRUE = "INCLUDE_FOOTER_TRUE"
D_INCLUDE_FOOTER_FALSE = "INCLUDE_FOOTER_FALSE"

SUPPORTED_DIRECTIVES = [D_SOURCE_ONLY, D_ANSWER, D_TODO, D_DUMMY,
                        D_INCLUDE_HEADER_TRUE, D_INCLUDE_HEADER_FALSE, D_INCLUDE_FOOTER_TRUE, D_INCLUDE_FOOTER_FALSE, ]


class NotebookError:
    def __init__(self, message):
        self.message = message

    def __str__(self):
        print(self.message)


class NotebookDef:
    def __init__(self,
                 path: str,
                 replacements: dict,
                 include_solution: bool,
                 test_round: int,
                 ignored: bool,
                 order: int,
                 i18n: bool,
                 i18n_language: Union[None, str],
                 ignoring: list):

        assert type(path) == str, f"""Expected the parameter "path" to be of type "str", found "{type(path)}" """
        assert type(replacements) == dict, f"""Expected the parameter "replacements" to be of type "dict", found "{type(replacements)}" """
        assert type(include_solution) == bool, f"""Expected the parameter "include_solution" to be of type "bool", found "{type(include_solution)}" """

        self.path = path
        self.replacements = dict() if replacements is None else replacements

        self.include_solution = include_solution
        self.errors = list()
        self.warnings = list()

        self.test_round = test_round
        self.ignored = ignored
        self.order = order

        self.i18n = i18n
        self.i18n_language = i18n_language
        self.i18n_guids = list()

        self.ignoring = ignoring

    def __str__(self):
        result = self.path
        result += f"\n - include_solution = {self.include_solution}"
        result += f"\n - replacements = {self.replacements}"
        return result

    def test(self, assertion: Callable[[], bool], message: str) -> bool:
        if assertion is None or not assertion():
            self.errors.append(NotebookError(message))
            return False
        else:
            return True

    def warn(self, assertion: Callable[[], bool], message: str) -> bool:
        if assertion is None or not assertion():
            self.warnings.append(NotebookError(message))
            return False
        else:
            return True

    def assert_no_warnings(self) -> None:
        if len(self.warnings) > 0:
            what = "warning was" if len(self.warnings) == 1 else "warnings were"
            print(f"CAUTION: {len(self.warnings)} {what} found while publishing")
            for warning in self.warnings:
                print("-" * 80)
                print(warning.message)
            print()

    def assert_no_errors(self, print_warnings) -> None:
        if len(self.errors) > 0:
            what = "error was" if len(self.errors) == 1 else "errors were"
            print(f"ABORTING: {len(self.errors)} {what} found while publishing")
            for error in self.errors:
                print("-" * 80)
                print(error.message)
            raise Exception("Publish aborted - see previous errors for more information")

        if print_warnings:
            self.assert_no_warnings()

    def test_notebook_exists(self, i, what, original_target, target, other_notebooks):
        if not target.startswith("../") and not target.startswith("./"):
            self.warn(lambda: False, f"Cmd #{i+1} | Found unexpected, relative, {what} target: \"{original_target}\" resolved as \"{target}\"".strip())
            return

        all_paths = set()
        for other in other_notebooks:
            # Add the original notebook's path
            all_paths.add(other.path)

            # Get the notebook's directory
            directory = '/'.join(other.path.split("/")[:-1])
            all_paths.add(directory)

            # While there are still parent directories, keep processing
            while directory.count("/") > 0:
                directory = '/'.join(directory.split("/")[:-1])
                all_paths.add(directory)

        offset = -1

        if target.startswith("../"):
            while target.startswith("../"):
                offset -= 1
                target = target[3:] 

        elif target.startswith("./"):
            target = target[2:]

        if "/" in self.path:
            parent = '/'.join(self.path.split("/")[:offset])
            target = f"{parent}/{target}"

        if target.startswith("/"): target = target[1:]

        notebooks = [n for n in all_paths if target == n]

        message = f"Cmd #{i+1} | Cannot find notebook for the {what} target: \"{original_target}\" resolved as \"{target}\""
        # self.test(lambda: len(notebooks) != 0, message)
        self.test(lambda: len(notebooks) != 0, message)

    def test_run_cells(self, language: str, command: str, i: int, other_notebooks: list) -> None:
        """
        Validates %run cells meet specific requirements
        :param language: The langage of the corresponding notebook
        :param command: The %run command string to be evaluated
        :param i: The zero-based index to the command within the notebook
        :param other_notebooks: A complete list of notebooks for cross-validation
        :return:
        """

        # First verify that the specified command is a %run cell
        cm = self.get_comment_marker(language)
        prefix = f"{cm} MAGIC %run"
        if not command.startswith(prefix):
            return

        line_zero = command.split("\n")[0]
        link = line_zero[len(prefix):].strip()

        if link.startswith("\""):
            link = link[1:]
            pos = link.find("\"")
            if pos < 0:
                self.warn(lambda: False, f"Cmd #{i+1} | Missing closing quote in %run target")
                return
            else:
                link = link[:pos]
        else:
            pos = link.find(" ")
            if pos > 0:
                link = link[:pos]

        self.test_notebook_exists(i, "%run", link, link, other_notebooks)

    # def validate_single_tick(self, i, command):
    #     """Test for usage of single-ticks that should also be bolded"""
    #
    #     import re
    #
    #     for result in re.findall(r"[^\*]`[^\s]*`[^\*]", command):
    #         if "single-tick" not in self.ignoring:
    #             self.warn(lambda: False, f"Cmd #{i+1} | Found a single-tick block, expected the **`xx`** pattern: \"{result}\"")

    def validate_md_link(self, i, command, other_notebooks):
        """Test for MD links to be replaced with html links"""

        import re

        for link in re.findall(r"(?<!!)\[.*?\]\(.*?\)", command):

            # If this is a relative link, we can ignore it.
            match = re.search(r"\(\$.*\)", link)

            if not match:
                if "md-link" not in self.ignoring:
                    self.warn(lambda: False, f"Cmd #{i+1} | Found a MD link, expected HTML link: \"{link}\"")
            else:
                original_target = match.group()[1:-1]
                target = original_target[1:]
                self.test_notebook_exists(i, "MD link", original_target, target, other_notebooks)

    def validate_html_link(self, i, command):
        """Test all HTML links to ensure they have a target set to _blank"""

        import re

        for link in re.findall(r"<a .*?<\/a>", command):
            if "target=\"_blank\"" not in link:
                self.warn(lambda: False, f"Cmd #{i+1} | Found HTML link without the required target=\"_blank\": \"{link}\"")

    def test_source_for(self, command: str, i: int, what: str):
        if what in command:
            pos = command.find(what)
            pos_a = command.rfind("\n", 0, pos)
            pos_a = 0 if pos_a == -1 else pos_a

            pos_b = command.find("\n", pos)
            pos_b = len(command)-1 if pos_b == -1 else pos_b

            line = command[pos_a:pos_b].strip()

            prefix = f"Cmd #{i+1} "
            padding = " "*len(prefix)
            if "prohibited-dataset" not in self.ignoring:
                self.warn(lambda: False, f"{prefix}| Course includes prohibited use of {what}:\n{padding}| {line}")

    def test_source_cells(self, language: str, command: str, i: int):

        if language not in ["python", "scala", "sql", "java", "r"]:
            return command

        self.test_source_for(command, i, "/mnt/training")
        self.test_source_for(command, i, "/databricks-datasets")

        return command

    def test_md_cells(self, language: str, command: str, i: int, other_notebooks: list):

        # First verify that the specified command is a mark-down cell
        cm = self.get_comment_marker(language)
        if not command.startswith(f"{cm} MAGIC %md"):
            return command
            
        # self.validate_single_tick(i, command)
        self.validate_md_link(i, command, other_notebooks)
        self.validate_html_link(i, command)

        lines = command.strip().split("\n")
        line_0 = lines[0][7+len(cm):]

        if self.i18n:
            parts = line_0.strip().split(" ")
            for index, part in enumerate(parts):
                if part.strip() == "": del parts[index]
            md_tag = None if len(parts) < 1 else parts[0]
            guid = None if len(parts) < 2 else parts[1]

            debug_info = line_0

            passed = self.test(lambda: len(lines) > 1, f"Cmd #{i + 1} | Expected MD to have more than 1 line of code with i18n enabled: {debug_info}")

            if len(parts) == 1:
                passed = passed and self.test(lambda: False, f"Cmd #{i+1} | Missing the i18n directive: {debug_info}")
            else:
                passed = passed and self.test(lambda: len(parts) == 2, f"Cmd #{i+1} | Expected the first line of MD to have only two words, found {len(parts)}: {debug_info}")
                passed = passed and self.test(lambda: parts[0] in ["%md", "%md-sandbox"], f"Cmd #{i+1} | Expected word[0] of the first line of MD to be \"%md\" or \"%md-sandbox\", found {parts[0]}: {debug_info}")
                passed = passed and self.test(lambda: guid.startswith("--i18n-"), f"Cmd #{i+1} | Expected word[1] of the first line of MD to start with \"--i18n-\", found {guid}: {debug_info}")

            if passed:
                passed = passed and self.test(lambda: guid not in self.i18n_guids, f"Cmd #{i+1} | Duplicate i18n GUID found: {guid}")

            if passed:
                self.i18n_guids.append(guid)
                del lines[0]
                lines.insert(0, f"{cm} MAGIC {md_tag}")
                command = "\n".join(lines)

            return command

        return command

    def create_resource_bundle(self, natural_language: str, source_dir: str, target_dir: str) -> None:
        from dbacademy.dbrest import DBAcademyRestClient

        natural_language = None if natural_language is None else natural_language.lower()

        assert type(natural_language) == str, f"""Expected the parameter "natural_language" to be of type "str", found "{type(natural_language)}" """
        assert type(source_dir) == str, f"""Expected the parameter "source_dir" to be of type "str", found "{type(source_dir)}" """
        assert type(target_dir) == str, f"""Expected the parameter "target_dir" to be of type "str", found "{type(target_dir)}" """

        print("-" * 80)
        print(f".../{self.path}")

        source_notebook_path = f"{source_dir}/{self.path}"

        client = DBAcademyRestClient()

        source_info = client.workspace().get_status(source_notebook_path)
        language = source_info["language"].lower()

        raw_source = client.workspace().export_notebook(source_notebook_path)

        cmd_delim = self.get_cmd_delim(language)
        commands = raw_source.split(cmd_delim)

        md_commands = list()

        for i in range(len(commands)):
            command = commands[i].lstrip()

            cm = self.get_comment_marker(language)
            if command.startswith(f"{cm} MAGIC %md"):
                md_commands.append(command)

        if len(md_commands) == 0:
            print(f"Skipping resource - 0 MD cells: {self.path}")
        else:
            # self.publish_resource(language, md_commands, resource_root, resource_path)
            self.publish_resource(language, md_commands, target_dir, natural_language)

    def publish(self, source_dir: str, target_dir: str, i18n_resources_dir: str, verbose: bool, debugging: bool, other_notebooks: list) -> None:
        from dbacademy.dbrest import DBAcademyRestClient

        assert type(source_dir) == str, f"""Expected the parameter "source_dir" to be of type "str", found "{type(source_dir)}" """
        assert type(target_dir) == str, f"""Expected the parameter "target_dir" to be of type "str", found "{type(target_dir)}" """
        assert type(i18n_resources_dir) == str, f"""Expected the parameter "resources_dir" to be of type "str", found "{type(i18n_resources_dir)}" """
        assert type(verbose) == bool, f"""Expected the parameter "verbose" to be of type "bool", found "{type(verbose)}" """
        assert type(debugging) == bool, f"""Expected the parameter "debugging" to be of type "bool", found "{type(debugging)}" """

        assert type(other_notebooks) == list, f"""Expected the parameter "other_notebooks" to be of type "list", found "{type(other_notebooks)}" """
        for i, notebook in enumerate(other_notebooks):
            assert type(other_notebooks[i]) == NotebookDef, f"""Expected the parameter "other_notebooks[{i}]" to be of type "NotebookDef", found "{type(other_notebooks[i])}" """

        self.errors = list()
        self.warnings = list()
        self.i18n_guids = list()

        print()
        print("=" * 80)
        print(f".../{self.path}")

        source_notebook_path = f"{source_dir}/{self.path}"

        client = DBAcademyRestClient()

        source_info = client.workspace().get_status(source_notebook_path)
        language = source_info["language"].lower()

        raw_source = client.workspace().export_notebook(source_notebook_path)

        i18n_source_path = f"/Workspace{i18n_resources_dir}/{self.path}.md"
        if os.path.exists(i18n_source_path):
            with open(f"{i18n_source_path}") as f:
                i18n_source = f.read()
        else:
            print(f"Not found: {i18n_source_path}")
            i18n_source = ""

        skipped = 0
        students_commands = []
        solutions_commands = []

        cmd_delim = self.get_cmd_delim(language)
        commands = raw_source.split(cmd_delim)

        todo_count = 0
        answer_count = 0

        include_header = False
        found_header_directive = False

        include_footer = False
        found_footer_directive = False

        for i in range(len(commands)):
            if debugging:
                print("\n" + ("=" * 80))
                print(f"Debug Command {i + 1}")

            command = commands[i].lstrip()

            self.test(lambda: "DBTITLE" not in command, f"Cmd #{i+1} | Unsupported Cell-Title found")

            # Misc tests for language specific cells
            command = self.test_source_cells(language, command, i)

            # Misc tests specific to %md cells along with i18n specific rewrites
            command = self.test_md_cells(language, command, i, other_notebooks)
            
            # Misc tests specific to %run cells
            self.test_run_cells(language, command, i, other_notebooks)

            # Extract the leading comments and then the directives
            leading_comments = self.get_leading_comments(language, command.strip())
            directives = self.parse_directives(i, leading_comments)

            if debugging:
                if len(leading_comments) > 0:
                    print("   |-LEADING COMMENTS --" + ("-" * 57))
                    for comment in leading_comments:
                        print("   |" + comment)
                else:
                    print("   |-NO LEADING COMMENTS --" + ("-" * 54))

                if len(directives) > 0:
                    print("   |-DIRECTIVES --" + ("-" * 62))
                    for directive in directives:
                        print("   |" + directive)
                else:
                    print("   |-NO DIRECTIVES --" + ("-" * 59))

            # Update flags to indicate if we found the required header and footer directives
            include_header = True if D_INCLUDE_HEADER_TRUE in directives else include_header
            found_header_directive = True if D_INCLUDE_HEADER_TRUE in directives or D_INCLUDE_HEADER_FALSE in directives else found_header_directive

            include_footer = True if D_INCLUDE_FOOTER_TRUE in directives else include_footer
            found_footer_directive = True if D_INCLUDE_FOOTER_TRUE in directives or D_INCLUDE_FOOTER_FALSE in directives else found_footer_directive

            # Make sure we have one and only one directive in this command (ignoring the header directives)
            directive_count = 0
            for directive in directives:
                if directive not in [D_INCLUDE_HEADER_TRUE, D_INCLUDE_HEADER_FALSE, D_INCLUDE_FOOTER_TRUE, D_INCLUDE_FOOTER_FALSE]:
                    directive_count += 1
            self.test(lambda: directive_count <= 1, f"Cmd #{i+1} | Found multiple directives ({directive_count}): {directives}")

            # Process the various directives
            if command.strip() == "":
                skipped += self.skipping(i, "Empty Cell")
            elif D_SOURCE_ONLY in directives:          skipped += self.skipping(i, None)
            elif D_INCLUDE_HEADER_TRUE in directives:  skipped += self.skipping(i, None)
            elif D_INCLUDE_HEADER_FALSE in directives: skipped += self.skipping(i, None)
            elif D_INCLUDE_FOOTER_TRUE in directives:  skipped += self.skipping(i, None)
            elif D_INCLUDE_FOOTER_FALSE in directives: skipped += self.skipping(i, None)

            elif D_TODO in directives:
                # This is a TO-DO cell, exclude from solution notebooks
                todo_count += 1
                command = self.clean_todo_cell(language, command, i)
                students_commands.append(command)

            elif D_ANSWER in directives:
                # This is an ANSWER cell, exclude from lab notebooks
                answer_count += 1
                solutions_commands.append(command)

            elif D_DUMMY in directives:
                students_commands.append(command)
                solutions_commands.append(command.replace("DUMMY",
                                                          "DUMMY: Ya, that wasn't too smart. Then again, this is just a dummy-directive"))

            else:
                # Not a TO-DO or ANSWER, just append to both
                students_commands.append(command)
                solutions_commands.append(command)

            # Check the command for BDC markers
            bdc_tokens = ["IPYTHON_ONLY", "DATABRICKS_ONLY",
                          "AMAZON_ONLY", "AZURE_ONLY", "TEST", "PRIVATE_TEST", "INSTRUCTOR_NOTE", "INSTRUCTOR_ONLY",
                          "SCALA_ONLY", "PYTHON_ONLY", "SQL_ONLY", "R_ONLY"
                                                                   "VIDEO", "ILT_ONLY", "SELF_PACED_ONLY", "INLINE",
                          "NEW_PART", "{dbr}"]

            for token in bdc_tokens:
                self.test(lambda: token not in command, f"""Cmd #{i+1} | Found the token "{token}" """)

            cm = self.get_comment_marker(language)
            if not command.startswith(f"{cm} MAGIC %md"):
                if language.lower() == "python":
                    if "lang-python" not in self.ignoring:
                        self.warn(lambda: "%python" not in command, f"""Cmd #{i+1} | Found "%python" in a Python notebook""")
                elif language.lower() == "sql":
                    if "lang-sql" not in self.ignoring:
                        self.warn(lambda: "%sql" not in command, f"""Cmd #{i+1} | Found "%sql" in a SQL notebook""")
                elif language.lower() == "scala":
                    if "lang-scala" not in self.ignoring:
                        self.warn(lambda: "%scala" not in command, f"""Cmd #{i+1} | Found "%scala" in a Scala notebook""")
                elif language.lower() == "r":
                    # We have to check both cases so as not to catch %run by accident
                    if "lang-r" not in self.ignoring:
                        self.warn(lambda: "%r " not in command,  f"""Cmd #{i+1} | Found "%r" in an R notebook""")
                        self.warn(lambda: "%r\n" not in command, f"""Cmd #{i+1} | Found "%r" in an R notebook""")
                else:
                    raise Exception(f"The language {language} is not supported")

            for year in range(2017, 2999):
                tag = f"{year} Databricks, Inc"
                self.test(lambda: tag not in command, f"""Cmd #{i+1} | Found copyright ({tag}) """)

        self.test(lambda: found_header_directive, f"One of the two header directives ({D_INCLUDE_HEADER_TRUE} or {D_INCLUDE_HEADER_FALSE}) were not found.")
        self.test(lambda: found_footer_directive, f"One of the two footer directives ({D_INCLUDE_FOOTER_TRUE} or {D_INCLUDE_FOOTER_FALSE}) were not found.")
        self.test(lambda: answer_count >= todo_count, f"Found more {D_TODO} commands ({todo_count}) than {D_ANSWER} commands ({answer_count})")

        if include_header is True:
            students_commands.insert(0, self.get_header_cell(language))
            solutions_commands.insert(0, self.get_header_cell(language))

        if include_footer is True:
            students_commands.append(self.get_footer_cell(language))
            solutions_commands.append(self.get_footer_cell(language))

        for key in ["\"", "*", "<", ">", "?", "\\", "|", ":"]:
            # Not checking for forward slash as the platform itself enforces this.
            self.warn(lambda: key not in self.path,  f"Found invalid character {key} in notebook name: {self.path}")

        # Create the student's notebooks
        students_notebook_path = f"{target_dir}/{self.path}"
        if verbose: print(students_notebook_path)
        if verbose: print(f"...publishing {len(students_commands)} commands")
        self.publish_notebook(language, students_commands, students_notebook_path, print_warnings=True)

        # Create the solutions notebooks
        if self.include_solution:
            solutions_notebook_path = f"{target_dir}/Solutions/{self.path}"
            if verbose: print(solutions_notebook_path)
            if verbose: print(f"...publishing {len(solutions_commands)} commands")
            self.publish_notebook(language, solutions_commands, solutions_notebook_path, print_warnings=False)

    def publish_resource(self, language: str, md_commands: list, target_dir: str, natural_language: str) -> None:
        import os

        m = self.get_comment_marker(language)
        target_path = f"{target_dir}/{natural_language}/{self.path}"

        final_source = f"# /{self.path}\n"

        # Processes all commands except the last
        for md_command in md_commands:
            md_command = md_command.replace(f"{m} MAGIC ", "")
            md_command = md_command.replace(f"%md-sandbox --i18n-", f"<hr sandbox>--i18n-")
            md_command = md_command.replace(f"%md --i18n-", f"<hr>--i18n-")
            final_source += md_command
            final_source += "\n"

        final_source = self.replace_contents(final_source)

        target_file = "/Workspace"+target_path+".md"
        target_dir = "/".join(target_file.split("/")[:-1])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        if os.path.exists(target_file):
            os.remove(target_file)

        with open(target_file, "w") as w:
            w.write(final_source)

    def publish_notebook(self, language: str, commands: list, target_path: str, print_warnings: bool) -> None:
        from dbacademy.dbrest import DBAcademyRestClient

        m = self.get_comment_marker(language)
        final_source = f"{m} Databricks notebook source\n"

        # Processes all commands except the last
        for command in commands[:-1]:
            final_source += command
            final_source += self.get_cmd_delim(language)

        # Process the last command
        m = self.get_comment_marker(language)
        final_source += commands[-1]
        final_source += "" if commands[-1].startswith(f"{m} MAGIC") else "\n\n"

        final_source = self.replace_contents(final_source)

        self.assert_no_errors(print_warnings)

        client = DBAcademyRestClient()
        parent_dir = "/".join(target_path.split("/")[0:-1])
        client.workspace().mkdirs(parent_dir)
        client.workspace().import_notebook(language.upper(), target_path, final_source)

    def clean_todo_cell(self, source_language, command, i):
        new_command = ""
        lines = command.split("\n")
        source_m = self.get_comment_marker(source_language)

        first = 0
        prefix = source_m

        for test_a in ["%r", "%md", "%sql", "%python", "%scala"]:
            test_b = f"{source_m} MAGIC {test_a}"
            if len(lines) > 1 and (lines[0].startswith(test_a) or lines[0].startswith(test_b)):
                first = 1
                cell_m = self.get_comment_marker(test_a)
                prefix = f"{source_m} MAGIC {cell_m}"

        for index in range(len(lines)):
            line = lines[index]

            if index == 0 and first == 1:
                # This is the first line, but the first is a magic command
                new_command += line

            elif (index == first) and line.strip() not in [f"{prefix} {D_TODO}"]:
                self.test(lambda: False, f"""Cmd #{i + 1} | Expected line #{index + 1} to be the "{D_TODO}" directive: "{line}" """)

            elif not line.startswith(prefix) and line.strip() != "" and line.strip() != f"{source_m} MAGIC":
                self.test(lambda: False, f"""Cmd #{i + 1} | Expected line #{index + 1} to be commented out: "{line}" with prefix "{prefix}" """)

            elif line.strip().startswith(f"{prefix} {D_TODO}"):
                # Add as-is
                new_command += line

            elif line.strip() == "" or line.strip() == f"{source_m} MAGIC":
                # No comment, do not process
                new_command += line

            elif line.strip().startswith(f"{prefix} "):
                # Remove comment and space
                length = len(prefix) + 1
                new_command += line[length:]

            else:
                # Remove just the comment
                length = len(prefix)
                new_command += line[length:]

            # Add new line for all but the last line
            if index < len(lines) - 1:
                new_command += "\n"

        return new_command

    def replace_contents(self, contents: str):
        import re

        for key in self.replacements:
            old_value = "{{" + key + "}}"
            new_value = self.replacements[key]
            contents = contents.replace(old_value, new_value)

        mustache_pattern = re.compile(r"{{[a-zA-Z\-\\_\\#\\/]*}}")
        result = mustache_pattern.search(contents)
        if result is not None:
            self.test(lambda: False, f"A mustache pattern was detected after all replacements were processed: {result}")

        for icon in [":HINT:", ":CAUTION:", ":BESTPRACTICE:", ":SIDENOTE:", ":NOTE:"]:
            if icon in contents:
                self.test(lambda: False, f"The deprecated {icon} pattern was found after all replacements were processed.")

        # No longer supported
        # replacements[":HINT:"] =         """<img src="https://files.training.databricks.com/images/icon_hint_24.png"/>&nbsp;**Hint:**"""
        # replacements[":CAUTION:"] =      """<img src="https://files.training.databricks.com/images/icon_warn_24.png"/>"""
        # replacements[":BESTPRACTICE:"] = """<img src="https://files.training.databricks.com/images/icon_best_24.png"/>"""
        # replacements[":SIDENOTE:"] =     """<img src="https://files.training.databricks.com/images/icon_note_24.png"/>"""

        return contents

    def get_comment_marker(self, language):
        language = language.replace("%", "")

        if language.lower() in "python":
            return "#"
        elif language.lower() in "sql":
            return "--"
        elif language.lower() in "md":
            return "--"
        elif language.lower() in "r":
            return "#"
        elif language.lower() in "scala":
            return "//"
        else:
            raise ValueError(f"The language {language} is not supported.")

    def get_cmd_delim(self, language):
        marker = self.get_comment_marker(language)
        return f"\n{marker} COMMAND ----------\n"

    def get_leading_comments(self, language, command) -> list:
        leading_comments = []
        lines = command.split("\n")

        source_m = self.get_comment_marker(language)
        first_line = lines[0].lower()

        if first_line.startswith(f"{source_m} magic %md"):
            cell_m = self.get_comment_marker("md")
        elif first_line.startswith(f"{source_m} magic %sql"):
            cell_m = self.get_comment_marker("sql")
        elif first_line.startswith(f"{source_m} magic %python"):
            cell_m = self.get_comment_marker("python")
        elif first_line.startswith(f"{source_m} magic %scala"):
            cell_m = self.get_comment_marker("scala")
        elif first_line.startswith(f"{source_m} magic %run"):
            cell_m = source_m  # Included to preclude trapping for R language below
        elif first_line.startswith(f"{source_m} magic %r"):
            cell_m = self.get_comment_marker("r")
        else:
            cell_m = source_m

        for il in range(len(lines)):
            line = lines[il]

            # Start by removing any "source" prefix
            if line.startswith(f"{source_m} MAGIC"):
                length = len(source_m) + 6
                line = line[length:].strip()

            elif line.startswith(f"{source_m} COMMAND"):
                length = len(source_m) + 8
                line = line[length:].strip()

            # Next, if it starts with a magic command, remove it.
            if line.strip().startswith("%"):
                # Remove the magic command from this line
                pos = line.find(" ")
                if pos == -1:
                    line = ""
                else:
                    line = line[pos:].strip()

            # Finally process the refactored-line for any comments.
            if line.strip() == cell_m or line.strip() == "":
                # empty comment line, don't break, just ignore
                pass

            elif line.strip().startswith(cell_m):
                # append to our list
                comment = line.strip()[len(cell_m):].strip()
                leading_comments.append(comment)

            else:
                # All done, this is a non-comment
                return leading_comments

        return leading_comments

    def parse_directives(self, i, comments):
        import re

        directives = list()

        for line in comments:
            if line == line.upper():
                # The comment is in all upper case,
                # must be one or more directives
                directive = line.strip()
                mod_directive = re.sub("[^-a-zA-Z_]", "_", directive)

                if directive in ["SELECT", "FROM", "AS", "AND"]:
                    pass  # not a real directive, but flagged as one because of its SQL syntax

                elif directive in [D_TODO, D_ANSWER, D_SOURCE_ONLY,
                                   D_INCLUDE_HEADER_TRUE, D_INCLUDE_HEADER_FALSE,
                                   D_INCLUDE_FOOTER_TRUE, D_INCLUDE_FOOTER_FALSE]:
                    directives.append(line)

                elif "FILL-IN" in directive or "FILL_IN" in directive:
                    pass  # Not a directive, just a random chance

                elif directive != mod_directive:
                    if mod_directive in [f"__{D_TODO}", f"___{D_TODO}"]:
                        self.test(lambda: False, f"Cmd #{i+1} | Found double-comment of TODO directive")

                    # print(f"Skipping directive: {directive} vs {mod_directive}")
                    pass  # Number and symbols are not used in directives

                else:
                    reslut_a = self.warn(lambda: " " not in directive, f"""Cmd #{i+1} | Whitespace found in directive "{directive}": {line}""")
                    reslut_b = self.warn(lambda: "-" not in directive, f"""Cmd #{i+1} | Hyphen found in directive "{directive}": {line}""")
                    reslut_c = self.warn(lambda: directive in SUPPORTED_DIRECTIVES, f"""Cmd #{i+1} | Unsupported directive "{directive}", see dbacademy.dbpublish.help_html() for more information.""")
                    if reslut_a and reslut_b and reslut_c:
                        directives.append(line)

        return directives

    def skipping(self, i, label):
        if label:
            print(f"Cmd #{i+1} | Skipping: {label}")
        return 1

    def get_header_cell(self, language):
        m = self.get_comment_marker(language)
        return f"""
    {m} MAGIC
    {m} MAGIC %md-sandbox
    {m} MAGIC
    {m} MAGIC <div style="text-align: center; line-height: 0; padding-top: 9px;">
    {m} MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 600px">
    {m} MAGIC </div>
    """.strip()

    def get_footer_cell(self, language):
        from datetime import date

        m = self.get_comment_marker(language)
        return f"""
    {m} MAGIC %md-sandbox
    {m} MAGIC &copy; {date.today().year} Databricks, Inc. All rights reserved.<br/>
    {m} MAGIC Apache, Apache Spark, Spark and the Spark logo are trademarks of the <a href="https://www.apache.org/">Apache Software Foundation</a>.<br/>
    {m} MAGIC <br/>
    {m} MAGIC <a href="https://databricks.com/privacy-policy">Privacy Policy</a> | <a href="https://databricks.com/terms-of-use">Terms of Use</a> | <a href="https://help.databricks.com/">Support</a>
    """.strip()
