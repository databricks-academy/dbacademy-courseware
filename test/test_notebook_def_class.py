import unittest

import dbpublish.notebook_def_class


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
        self.assertEquals(len(notebook.warnings), 0)
        self.assertEquals(len(notebook.errors), 0)

    def test_good_double_spaced_i18n(self):
        command = """
# MAGIC %md  --i18n-TBD
# MAGIC 
# MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEquals(len(notebook.warnings), 0)
        self.assertEquals(len(notebook.errors), 0)

    def test_missing_i18n(self):
        command = """
        # MAGIC %md
        # MAGIC 
        # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEquals(len(notebook.warnings), 0)
        self.assertEquals(len(notebook.errors), 1)
        self.assertEquals(notebook.errors[0].message, "Expected the first line of MD in command #1 to have only two words, found 1: %md")


if __name__ == '__main__':
    unittest.main()
