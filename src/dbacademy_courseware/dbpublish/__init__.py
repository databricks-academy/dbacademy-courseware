from dbacademy_courseware.dbbuild import BuildConfig
from deprecated.classic import deprecated

def help_html():
    from .notebook_def_class import D_TODO, D_ANSWER, D_SOURCE_ONLY, D_DUMMY
    from .notebook_def_class import SUPPORTED_DIRECTIVES
    from .notebook_def_class import D_INCLUDE_HEADER_TRUE, D_INCLUDE_HEADER_FALSE, D_INCLUDE_FOOTER_TRUE, D_INCLUDE_FOOTER_FALSE

    docs = {
        D_SOURCE_ONLY: f"Indicates that this cell is used in the source notebook only and is not to be included in the published version.",
        D_TODO: f"Indicates that this cell is an exercise for students - the entire cell is expected to be commented out.",
        D_ANSWER: f"Indicates that this cell is the solution to a preceding {D_TODO} cell. The build will fail if there total number of {D_TODO} cells is less than  the total number of {D_ANSWER} cells",
        D_DUMMY: f"{D_DUMMY}: A directive that replaces itself with a nice little message for you - used in unit tests for the build engine",

        D_INCLUDE_HEADER_TRUE: f"Indicates that this notebook should include the default header - to be included in the first cell of the notebook.",
        D_INCLUDE_HEADER_FALSE: f"Indicates that this notebook should NOT include the default header - to be included in the first cell of the notebook.",
        D_INCLUDE_FOOTER_TRUE: f"Indicates that this notebook should include the default footer - to be included in the first cell of the notebook.",
        D_INCLUDE_FOOTER_FALSE: f"Indicates that this notebook should NOT include the default footer - to be included in the first cell of the notebook.",
    }

    html = "<html><body>"
    html += f"<h1>Publishing Help</h1>"
    html += f"<h2>Supported directives</h2>"
    for directive in SUPPORTED_DIRECTIVES:
        if directive in docs:
            doc = docs[directive]
            html += f"<div><b>{directive}</b>: {doc}</div>"
        else:
            html += f"<div><b>{directive}</b>: Undocumented</div>"

    html += "</body>"
    return html

@deprecated(reason="Use from_build_config instead")
def from_test_config(build_config: BuildConfig, target_dir: str):
    from_build_config(build_config=build_config,
                      target_dir=target_dir)

def from_build_config(build_config: BuildConfig, target_dir: str = None):
    from .publisher_class import Publisher

    i18n_resources_dir = f"{build_config.source_repo}/Resources/{build_config.i18n_language}"
    if target_dir is None:
        target_dir = f"{build_config.source_repo}/Published/{build_config.name} - v{build_config.version}"

    publisher = Publisher(client=build_config.client,
                          version=build_config.version,
                          source_dir=build_config.source_dir,
                          target_dir=target_dir,
                          i18n_resources_dir=i18n_resources_dir,
                          i18n_language=build_config.i18n_language,
                          white_list=build_config.white_list,
                          black_list=build_config.black_list,
                          notebooks=build_config.notebooks.values())
    return publisher


def update_and_validate_git_branch(client, path, target_branch="published"):
    repo_id = client.workspace().get_status(path)["object_id"]

    a_repo = client.repos().get(repo_id)
    a_branch = a_repo["branch"]
    assert a_branch == target_branch, f"""Expected the branch to be "{target_branch}", found "{a_branch}" """

    b_repo = client.repos().update(repo_id, target_branch)

    print(f"""Path:   {path}""")
    print(f"""Before: {a_repo["branch"]}  |  {a_repo["head_commit_id"]}""")
    print(f"""After:  {b_repo["branch"]}  |  {b_repo["head_commit_id"]}""")
