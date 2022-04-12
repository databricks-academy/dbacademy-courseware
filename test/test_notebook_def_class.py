import unittest


class MyTestCase(unittest.TestCase):

    def __init__(self, method_name):
        super().__init__(method_name)

    def create_notebook(self):
        from dbpublish.notebook_def_class import NotebookDef
        return NotebookDef(path="Agenda",
                           replacements={},
                           include_solution=False,
                           test_round=2,
                           ignored=False,
                           order=0,
                           i18n=True)

    def test_good_single_space_i18n(self):
        command = """
            # MAGIC %md --i18n-TBD
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 error, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.i18n_guids), f"Expected 1 GUID, found {len(notebook.i18n_guids)}")
        self.assertEqual("--i18n-TBD", notebook.i18n_guids[0])

    def test_good_double_spaced_i18n(self):
        command = """
            # MAGIC %md  --i18n-TBD
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 error, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.i18n_guids), f"Expected 1 GUID, found {len(notebook.i18n_guids)}")
        self.assertEqual("--i18n-TBD", notebook.i18n_guids[0])

    def test_good_md_sandbox_i18n(self):
        command = """
            # MAGIC %md-sandbox --i18n-TBD
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 error, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.i18n_guids), f"Expected 1 GUID, found {len(notebook.i18n_guids)}")
        self.assertEqual("--i18n-TBD", notebook.i18n_guids[0])

    def test_missing_i18n_multi(self):
        command = """
            # MAGIC %md
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.errors), f"Expected 1 error, found {len(notebook.errors)}")
        self.assertEqual("Cmd #4 | Missing the i18n directive: %md", notebook.errors[0].message)

    def test_missing_i18n_single(self):
        command = """
            # MAGIC %md | # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.errors), f"Expected 1 error, found {len(notebook.errors)}")
        self.assertEqual("Cmd #4 | Expected MD to have more than 1 line of code with i18n enabled: %md | # Build-Time Substitutions", notebook.errors[0].message)

    def test_extra_word_i18n(self):
        command = """
            # MAGIC %md --i18n-TBD # Title
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.errors), f"Expected 1 error, found {len(notebook.errors)}")
        self.assertEqual("Cmd #4 | Expected the first line of MD to have only two words, found 4: %md --i18n-TBD # Title", notebook.errors[0].message)

    def test_duplicate_i18n_guid(self):
        command_a = """
            # MAGIC %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a
            # MAGIC # Some Title""".strip()
        command_b = """
            # MAGIC %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a
            # MAGIC # Some Title""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command_a, i=3, other_notebooks=[])
        notebook.test_md_cells(language="Python", command=command_b, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.errors), f"Expected 1 error, found {len(notebook.errors)}")
        self.assertEqual("Cmd #5 | Duplicate i18n GUID found: --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a", notebook.errors[0].message)

    def test_unique_i18n_guid(self):
        command_a = """
            # MAGIC %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a
            # MAGIC # Some Title""".strip()
        command_b = """
            # MAGIC %md --i18n-9d06d80d-2381-42d5-8f9e-cc99ee3cd82a
            # MAGIC # Some Title""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command_a, i=3, other_notebooks=[])
        notebook.test_md_cells(language="Python", command=command_b, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 errors, found {len(notebook.errors)}")

    def test_md_i18n_guid_removal(self):
        command = """# MAGIC %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a\n# MAGIC # Some Title""".strip()

        notebook = self.create_notebook()
        actual = notebook.test_md_cells(language="Python", command=command, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 errors, found {len(notebook.errors)}")

        expected = """# MAGIC %md\n# MAGIC # Some Title""".strip()
        self.assertEqual(expected, actual)

    def test_md_sandbox_i18n_guid_removal(self):
        command = """# MAGIC %md-sandbox --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a\n# MAGIC # Some Title""".strip()

        notebook = self.create_notebook()
        actual = notebook.test_md_cells(language="Python", command=command, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 errors, found {len(notebook.errors)}")

        expected = """# MAGIC %md-sandbox\n# MAGIC # Some Title""".strip()
        self.assertEqual(expected, actual)

    def test_i18n_sql(self):
        command = """-- MAGIC %md-sandbox --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a\n-- MAGIC # Some Title""".strip()

        notebook = self.create_notebook()
        actual = notebook.test_md_cells(language="SQL", command=command, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(0, len(notebook.errors), f"Expected 0 errors, found {len(notebook.errors)}")

        expected = """-- MAGIC %md-sandbox\n-- MAGIC # Some Title""".strip()
        self.assertEqual(expected, actual)

    def test_i18n_single_line(self):
        command = """-- MAGIC %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a # Some Title""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="SQL", command=command, i=4, other_notebooks=[])

        self.assertEqual(0, len(notebook.warnings), f"Expected 0 warnings, found {len(notebook.errors)}")
        self.assertEqual(1, len(notebook.errors), f"Expected 1 errors, found {len(notebook.errors)}")

        self.assertEqual("Cmd #5 | Expected MD to have more than 1 line of code with i18n enabled: %md --i18n-a6e39b59-1715-4750-bd5d-5d638cf57c3a # Some Title", notebook.errors[0].message)

    def test_replacement(self):
        import re
        command ="""# Databricks notebook source
# MAGIC %md --i18n-5f2cfc0b-1998-4182-966d-8efed6020eb2
# MAGIC 
# MAGIC 
# MAGIC 
# MAGIC # Getting Started with the Databricks Platform
# MAGIC 
# MAGIC This notebook provides a hands-on review of some of the basic functionality of the Databricks Data Science and Engineering Workspace.
# MAGIC 
# MAGIC ## Learning Objectives
# MAGIC By the end of this lessons, you will be able to:
# MAGIC - Rename a notebook and change the default language
# MAGIC - Attach a cluster
# MAGIC - Use the **`%run`** magic command
# MAGIC - Run Python and SQL cells
# MAGIC - Create a Markdown cell

# COMMAND ----------
# MAGIC %md --i18n-05dca5e4-6c50-4b39-a497-a35cd6d99434
# MAGIC 
# MAGIC 
# MAGIC 
# MAGIC # Renaming a Notebook
# MAGIC 
# MAGIC Changing the name of a notebook is easy. Click on the name at the top of this page, then make changes to the name. To make it easier to navigate back to this notebook later in case you need to, append a short test string to the end of the existing name."""
        m = "#"
        result = command.replace(f"{m} MAGIC ", "")
        print(result)


if __name__ == '__main__':
    unittest.main()
