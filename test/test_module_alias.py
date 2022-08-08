import unittest


# noinspection PyUnresolvedReferences
class MyTestCase(unittest.TestCase):

    def test_dbpublish(self):
        from dbacademy.dbpublish.notebook_def_class import NotebookDef
        notebook = NotebookDef(path="Agenda",
                               replacements={},
                               include_solution=False,
                               test_round=2,
                               ignored=False,
                               order=0,
                               i18n=True,
                               ignoring=[],
                               i18n_language="English")
        self.assertIsNotNone(notebook)

    def test_dbtest(self):
        from dbacademy.dbtest.results_evaluator import ResultsEvaluator
        results_evaluator = ResultsEvaluator([])
        self.assertIsNotNone(results_evaluator)


if __name__ == '__main__':
    unittest.main()
