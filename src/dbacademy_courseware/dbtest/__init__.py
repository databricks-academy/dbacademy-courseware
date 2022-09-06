from dbacademy_courseware.dbbuild import BuildConfig

def to_job_url(cloud, job_id, run_id):
    import dbacademy.dbgems as dbgems

    if dbgems.get_browser_host_name() is not None:
        return f"https://{dbgems.get_browser_host_name()}/?o={dbgems.get_workspace_id()}#job/{job_id}/run/{run_id}"
    else:
        aws_workspace = "https://curriculum-dev.cloud.databricks.com/?o=3551974319838082"
        gcp_workspace = "https://8422030046858219.9.gcp.databricks.com/?o=8422030046858219"
        msa_workspace = "https://westus2.azuredatabricks.net/?o=2472203627577334"

        if cloud == "AWS": return f"{aws_workspace}#job/{job_id}/run/{run_id}"
        if cloud == "GCP": return f"{gcp_workspace}#job/{job_id}/run/{run_id}"
        if cloud == "MSA": return f"{msa_workspace}#job/{job_id}/run/{run_id}"
        raise Exception(f"The cloud {cloud} is not supported")


def to_job_link(cloud, job_id, run_id, label):
    url = to_job_url(cloud, job_id, run_id)
    return f"""<a href="{url}" target="_blank">{label}</a>"""


def create_test_job(client, test_config, job_name, notebook_path, policy_id=None):
    import re

    test_config.spark_conf["dbacademy.smoke-test"] = "true"

    course_name = re.sub(r"[^a-zA-Z\d]", "-", test_config.name.lower())
    while "--" in course_name: course_name = course_name.replace("--", "-")

    test_type = re.sub(r"[^a-zA-Z\d]", "-", test_config.test_type.lower())
    while "--" in test_type: test_type = test_type.replace("--", "-")

    params = {
        "name": f"{job_name}",
        "tags": {
            "dbacademy.course": course_name,
            "dbacademy.source": "dbacadmey-smoke-test",
            "dbacademy.test-type": test_type
        },
        "email_notifications": {},
        "timeout_seconds": 7200,
        "max_concurrent_runs": 1,
        "format": "MULTI_TASK",
        "tasks": [
            {
                "task_key": "Smoke-Test",
                "description": "Executes a single notebook, hoping that the magic smoke doesn't escape",
                "libraries": test_config.libraries,
                "notebook_task": {
                    "notebook_path": f"{notebook_path}",
                    "base_parameters": test_config.job_arguments
                },
                "new_cluster": {
                    "num_workers": test_config.workers,
                    "spark_version": f"{test_config.spark_version}",
                    "spark_conf": test_config.spark_conf,
                    "instance_pool_id": f"{test_config.instance_pool}",
                    "spark_env_vars": {
                        "WSFS_ENABLE_WRITE_SUPPORT": "true"
                    },
                },
            },
        ],
    }

    if policy_id is not None:
        policy = client.cluster_policies.get_by_id(policy_id)
        assert policy is not None, f"The policy \"{policy_id}\" does not exist or you do not have permissions to use specified policy: {[p.get('name') for p in client.cluster_policies.list()]}"
        params.get("tasks")[0].get("new_cluster")["policy_id"] = policy_id

    json_response = client.jobs().create(params)
    return json_response["job_id"]

class TestInstance:
    def __init__(self, test_config, notebook, test_dir, test_type):
        import hashlib

        self.notebook = notebook
        self.job_id = 0
        self.run_id = 0

        if notebook.include_solution:
            self.notebook_path = f"{test_dir}/Solutions/{notebook.path}"
        else:
            self.notebook_path = f"{test_dir}/{notebook.path}"

        hash_code = hashlib.sha256(self.notebook_path.encode()).hexdigest()
        test_name = test_config.name.lower().replace(" ", "-")
        self.job_name = f"[TEST] {test_name} | {test_type} | {hash_code}"

        # Hack to bring the test type down into the test results via the test_config
        test_config.test_type = test_type


class TestSuite:
    def __init__(self, test_config: BuildConfig, test_dir: str, test_type: str, keep_success: bool = False):
        self.test_dir = test_dir
        self.test_config = test_config
        self.client = test_config.client
        self.test_type = test_type
        self.test_rounds = dict()

        self.test_results = list()
        self.slack_thread_ts = None
        self.slack_first_message = None

        self.keep_success = keep_success

        assert test_type is not None and test_type.strip() != "", "The test type must be specified."

        # Define each test_round first to make the next step full-proof
        for notebook in test_config.notebooks.values():
            self.test_rounds[notebook.test_round] = list()

        # Add each notebook to the dictionary or rounds which is a dictionary of tests
        for notebook in test_config.notebooks.values():
            if notebook.test_round > 0:
                # [job_name] = (notebook_path, 0, 0, ignored)
                test_instance = TestInstance(test_config, notebook, test_dir, test_type)
                self.test_rounds[notebook.test_round].append(test_instance)

                if self.client.workspace().get_status(test_instance.notebook_path) is None:
                    raise Exception(f"Notebook not found: {test_instance.notebook_path}")

    def get_all_job_names(self):
        job_names = list()
        for test_round in self.test_rounds:
            job_names.extend([j.job_name for j in self.test_rounds[test_round]])

        return job_names

    def reset_test_suite(self):
        # Delete all jobs, even those that were successful
        self.client.jobs().delete_by_name(job_names=self.get_all_job_names(), success_only=False)
        print()

    @staticmethod
    def delete_all_jobs(success_only=None):
        print("*" * 80)
        print("* DEPRECATION WARNING")
        print("* delete_all_jobs() has been replaced by reset_test_suite() and cleanup()")
        print("*" * 80)

    def cleanup(self):
        if self.keep_success:
            print(f"Skipping deletion of all jobs: TestSuite.keep_success == {self.keep_success}")
        else:
            # Delete all successful jobs, keeping those jobs that failed
            self.client.jobs().delete_by_name(job_names=self.get_all_job_names(), success_only=True)

    def test_all_synchronously(self, test_round, fail_fast=True, service_principal: str = None, policy_id: str = None) -> bool:
        from dbacademy_gems import dbgems

        if test_round not in self.test_rounds:
            print(f"** WARNING ** There are no notebooks in round #{test_round}")
            return True

        tests = sorted(self.test_rounds[test_round], key=lambda t: t.notebook.order)

        self.send_first_message()

        what = "notebook" if len(tests) == 1 else "notebooks"
        self.send_status_update("info", f"Round #{test_round}: Testing {len(tests)} {what}  synchronously")

        print(f"Round #{test_round} test order:")
        for i, test in enumerate(tests):
            print(f"{i+1:>4}: {test.notebook.path}")
        print()

        # Assume that all tests passed
        passed = True

        for test in tests:

            if fail_fast and not passed:
                self.log_run(test, {})

                print("-" * 80)
                print(f"Skipping job, previous failure for {test.job_name}")
                print("-" * 80)

            else:
                self.send_status_update("info", f"Starting */{test.notebook.path}*")

                job_id = create_test_job(self.client, self.test_config, test.job_name, test.notebook_path, policy_id=policy_id)
                if service_principal:
                    sp = self.client.scim.service_principals.get_by_name(service_principal)
                    self.client.permissions.jobs.change_owner(job_id=job_id, owner_type="service_principal", owner_id=sp.get("applicationId"))

                run_id = self.client.jobs().run_now(job_id)["run_id"]

                host_name = dbgems.get_notebooks_api_endpoint() if dbgems.get_browser_host_name() is None else f"https://{dbgems.get_browser_host_name()}"
                print(f"""/{test.notebook.path}\n - {host_name}?o={dbgems.get_workspace_id()}#job/{job_id}/run/{run_id}""")

                response = self.client.runs().wait_for(run_id)
                passed = False if not self.conclude_test(test, response) else passed

        return passed

    def test_all_asynchronously(self, test_round: int, service_principal: str = None, policy_id: str = None) -> bool:
        from dbacademy_gems import dbgems

        tests = self.test_rounds[test_round]

        self.send_first_message()

        what = "notebook" if len(tests) == 1 else "notebooks"
        self.send_status_update("info", f"Round #{test_round}: Testing {len(tests)} {what}  asynchronously")

        # Launch each test
        for test in tests:
            self.send_status_update("info", f"Starting */{test.notebook.path}*")

            test.job_id = create_test_job(self.client, self.test_config, test.job_name, test.notebook_path, policy_id=policy_id)
            if service_principal:
                sp = self.client.scim.service_principals.get_by_name(service_principal)
                self.client.permissions.jobs.change_owner(job_id=test.job_id, owner_type="service_principal", owner_id=sp.get("applicationId"))

            test.run_id = self.client.jobs().run_now(test.job_id)["run_id"]

            print(f"""/{test.notebook.path}\n - https://{dbgems.get_browser_host_name()}?o={dbgems.get_workspace_id()}#job/{test.job_id}/run/{test.run_id}""")

        # Assume that all tests passed
        passed = True
        print(f"""\nWaiting for all test to complete:""")

        # Block until all tests completed
        for test in tests:
            self.send_status_update("info", f"Waiting for */{test.notebook.path}*")

            response = self.client.runs().wait_for(test.run_id)
            passed = False if not self.conclude_test(test, response) else passed

        return passed

    def conclude_test(self, test, response) -> bool:
        import json
        self.log_run(test, response)

        if response['state']['life_cycle_state'] == 'INTERNAL_ERROR':
            print()  # Usually a notebook-not-found
            print(json.dumps(response, indent=1))
            raise RuntimeError(response['state']['state_message'])

        result_state = response['state']['result_state']
        run_id = response.get("run_id", 0)
        job_id = response.get("job_id", 0)

        print("-" * 80)
        print(f"Job #{job_id}-{run_id} is {response['state']['life_cycle_state']} - {result_state}")
        print("-" * 80)

        return result_state != 'FAILED'

    def to_results_evaluator(self):
        from .results_evaluator import ResultsEvaluator
        return ResultsEvaluator(self.test_results, self.keep_success)

    def log_run(self, test, response):
        import time, uuid, requests, json

        job_id = response.get("job_id", 0)
        run_id = response.get("run_id", 0)

        result_state = response.get("state", {}).get("result_state", "UNKNOWN")
        if result_state == "FAILED" and test.notebook.ignored: result_state = "IGNORED"

        execution_duration = response.get("execution_duration", 0)
        notebook_path = response.get("task", {}).get("notebook_task", {}).get("notebook_path", "UNKNOWN")

        test_id = str(time.time()) + "-" + str(uuid.uuid1())

        self.test_results.append({
            "suite_id": self.test_config.suite_id,
            "test_id": test_id,
            "name": self.test_config.name,
            "result_state": result_state,
            "execution_duration": execution_duration,
            "cloud": self.test_config.cloud,
            "job_name": test.job_name,
            "job_id": job_id,
            "run_id": run_id,
            "notebook_path": notebook_path,
            "spark_version": self.test_config.spark_version,
            "test_type": self.test_config.test_type
        })

        response = requests.put("https://rqbr3jqop0.execute-api.us-west-2.amazonaws.com/prod/tests/smoke-tests", data=json.dumps({
            "suite_id": self.test_config.suite_id,
            "test_id": test_id,
            "name": self.test_config.name,
            "result_state": result_state,
            "execution_duration": execution_duration,
            "cloud": self.test_config.cloud,
            "job_name": test.job_name,
            "job_id": job_id,
            "run_id": run_id,
            "notebook_path": notebook_path,
            "spark_version": self.test_config.spark_version,
            "test_type": self.test_config.test_type,
        }))
        assert response.status_code == 200, f"({response.status_code}): {response.text}"

        if result_state == "FAILED":
            message_type = "error"
        elif result_state == "IGNORED":
            message_type = "warn"
        else:
            message_type = "info"
        url = to_job_url(self.test_config.cloud, job_id, run_id)
        self.send_status_update(message_type, f"*`{result_state}` /{test.notebook.path}*\n\n{url}")

    def send_first_message(self):
        if self.slack_first_message is None:
            self.send_status_update("info", f"*{self.test_config.name}*\nCloud: *{self.test_config.cloud}* | Mode: *{self.test_type}*")

    def send_status_update(self, message_type, message):
        import requests, json

        if self.slack_first_message is None: self.slack_first_message = message

        payload = {
            "channel": "curr-smoke-tests",
            "message": message,
            "message_type": message_type,
            "first_message": self.slack_first_message,
            "thread_ts": self.slack_thread_ts
        }

        response = requests.post("https://rqbr3jqop0.execute-api.us-west-2.amazonaws.com/prod/slack/client", data=json.dumps(payload))
        assert response.status_code == 200, f"({response.status_code}): {response.text}"
        self.slack_thread_ts = response.json()["data"]["thread_ts"]
