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
        self.assertEqual(len(notebook.warnings), 0)
        self.assertEqual(len(notebook.errors), 0)

    def test_good_double_spaced_i18n(self):
        command = """
            # MAGIC %md  --i18n-TBD
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(len(notebook.warnings), 0)
        self.assertEqual(len(notebook.errors), 0)

    def test_missing_i18n(self):
        command = """
            # MAGIC %md
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(len(notebook.warnings), 0)
        self.assertEqual(len(notebook.errors), 1)
        self.assertEqual("Missing the i18n directive in command #4: %md", notebook.errors[0].message)

    def test_extra_word_i18n(self):
        command = """
            # MAGIC %md --i18n-TBD # Title
            # MAGIC 
            # MAGIC # Build-Time Substitutions""".strip()

        notebook = self.create_notebook()
        notebook.test_md_cells(language="Python", command=command, i=3, other_notebooks=[])
        self.assertEqual(len(notebook.warnings), 0)
        self.assertEqual(len(notebook.errors), 1)
        self.assertEqual("Expected the first line of MD in command #4 to have only two words, found 4: %md --i18n-TBD # Title", notebook.errors[0].message)


if __name__ == '__main__':
    unittest.main()
