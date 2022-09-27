from typing import Union, List
from dbacademy.dbrest import DBAcademyRestClient

def print_if(condition, text):
    if condition:
        print(text)

def clean_target_dir(client, target_dir: str, verbose):
    from dbacademy_courseware.dbpublish.publisher_class import Publisher
    if verbose: print(f"Cleaning {target_dir}...")

    keepers = [f"{target_dir}/{k}" for k in Publisher.KEEPERS]

    for path in [p.get("path") for p in client.workspace.ls(target_dir) if p.get("path") not in keepers]:
        if verbose: print(f"...{path}")
        client.workspace().delete_path(path)

# noinspection PyUnusedLocal
def write_file(*, data: bytearray, target_file: str, overwrite: bool, target_name):
    import os
    print(f"\nWriting DBC to {target_name}:\n   {target_file}")

    target_file = target_file.replace("dbfs:/", "/dbfs/")

    if os.path.exists(target_file):
        # assert overwrite, f"Cannot overwrite existing file: {target_file}"
        # print(f"Removing existing file: {target_file}")
        os.remove(target_file)

    course_dir = "/".join(target_file.split("/")[:-2])
    if not os.path.exists(course_dir): os.mkdir(course_dir)

    version_dir = "/".join(target_file.split("/")[:-1])
    if not os.path.exists(version_dir): os.mkdir(version_dir)

    with open(target_file, "wb") as f:
        # print(f"Writing data: {target_file}")
        f.write(data)

def reset_git_repo(*, client: DBAcademyRestClient, directory: str, repo_url: str, branch: str, which: Union[str, None]):

    which = "" if which is None else f" ({which})"

    print(f"Resetting git repo{which}:")
    print(f" - Branch:   \"{branch}\"")
    print(f" - Directory: {directory}")
    print(f" - Repo URL:  {repo_url}")
    print()

    status = client.workspace().get_status(directory)

    if status is not None:
        target_repo_id = status["object_id"]
        client.repos().delete(target_repo_id)

    # Re-create the repo to progress in testing
    response = client.repos.create(path=directory, url=repo_url)
    repo_id = response.get("id")

    actual_branch = response.get("branch")
    if actual_branch != branch:
        if actual_branch != "published": print(f"\n*** Unexpected branch: {actual_branch}, expected {branch} ***\n")
        client.repos.update(repo_id=repo_id, branch=branch)

    results = client.repos.get(repo_id)
    current_branch = results.get("branch")

    assert branch == current_branch, f"Expected the new branch to be {branch}, found {current_branch}"

def validate_not_uncommitted(*, client: DBAcademyRestClient, build_name: str, repo_url: str, directory: str, ignored: List[str]):
    repo_dir = f"/Repos/Temp/{build_name}-diff"

    print(f"Comparing {directory}")
    print(f"to        {repo_dir}")
    print()

    reset_git_repo(client=client,
                   directory=repo_dir,
                   repo_url=repo_url,
                   branch="published",
                   which="clean")

    index_a = index_repo_dir(client=client, repo_dir=repo_dir, ignored=ignored)
    index_b = index_repo_dir(client=client, repo_dir=directory, ignored=ignored)

    return compare_results(index_a, index_b)

def index_repo_dir(*, client: DBAcademyRestClient, repo_dir: str, ignored: List[str]):
    results = {}

    print(f"...indexing \"{repo_dir}\"")
    notebooks = client.workspace().ls(repo_dir, recursive=True)
    assert notebooks is not None, f"No notebooks found for the path {repo_dir}"

    def is_ignored(test_path: str):
        for ignore in ignored:
            if test_path.startswith(ignore):
                return True
        return False

    for notebook in notebooks:
        path = notebook.get("path")

        object_type = notebook.get("object_type")
        source = "" if object_type != "NOTEBOOK" else client.workspace().export_notebook(path)

        relative_path = path[len(repo_dir):]
        if is_ignored(relative_path): continue

        results[relative_path] = {
            "path": relative_path,
            "object_type": object_type,
            "source": source.strip(),
        }

    return results

def compare_results(index_a, index_b):
    results = []

    index_a_notebooks = list(index_a.keys())
    index_b_notebooks = list(index_b.keys())

    for path_a in index_a_notebooks:
        if path_a not in index_b_notebooks:
            results.append(f"Notebook deleted: `{path_a}`")

    for path_b in index_b_notebooks:
        if path_b not in index_a_notebooks:
            results.append(f"Notebook added: `{path_b}`")

    for path in index_a_notebooks:
        if path in index_b:
            source_a = index_a[path]["source"]
            source_b = index_b[path]["source"]

            len_a = len(source_a)
            len_b = len(source_b)
            if source_a != source_b:
                results.append(f"Differences: ({len_a} vs {len_b})\n`{path}`")

    return results
