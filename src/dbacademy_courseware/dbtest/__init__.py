from .results_evaluator import ResultsEvaluator
from .test_suite import TestSuite

def to_job_url(*, job_id: str, run_id: str):
    import dbacademy.dbgems as dbgems

    workspaces = {
        "3551974319838082": "https://curriculum-dev.cloud.databricks.com/?o=3551974319838082",
        "8422030046858219": "https://8422030046858219.9.gcp.databricks.com/?o=8422030046858219",
        "2472203627577334": "https://westus2.azuredatabricks.net/?o=2472203627577334"
    }

    if dbgems.get_browser_host_name() is not None:
        base_url = f"https://{dbgems.get_browser_host_name()}/?o={dbgems.get_workspace_id()}"

    elif dbgems.get_workspace_id() in workspaces:
        base_url = workspaces.get(dbgems.get_workspace_id())

    else:
        base_url = f"https://{dbgems.get_notebooks_api_token()}/?o={dbgems.get_workspace_id()}"

    return f"{base_url}#job/{job_id}/run/{run_id}"
