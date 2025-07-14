# Setup

This markdown document has documentation on how to setup this repository.

## Workflows

### `check_pr_labels.yml`

To setup this workflow, you just need a `CONTRIBUTING.md` file in the root of your project. At minimum it should have a section called `No semver label!` ([Link to example](https://github.com/alexchristy/PyOPN/blob/main/CONTRIBUTING.md#no-semver-label)). The workflow will automatically link this section when it fails so user's can fix their PRs. Feel free to copy the example.

### `auto_release.yml`

1) Install the [Auto release tool](https://intuit.github.io/auto/docs) ([Latest release](https://github.com/intuit/auto/releases))

2) Navigate to the repository

    ```bash
    cd /path/to/repo/API/
    ```

3) Initialize Auto

    For this step the choose `Git Tag` as the *package manager plugin*. Fill in the rest of the information relevant to the repo and keep **all** default values. 

    When prompted for a *Github PAT*, go to the next step.

    ```bash
    auto init
    ```

4) Create repository tags

    This will allow you to tag your PRs and control the semantic version changes.

    ```bash
    auto create-labels
    ```

5) Create a GitHub App

    ***Note:** OpenLabs already has the `auto-release-app` installed. Skip to step 7.*

    This allows us to enforce branch protection rules while allowing the Auto release tool to bypass the protections when running automated workflows. (Source: [Comment Link](https://github.com/orgs/community/discussions/13836#discussioncomment-8535364))
    
    Link: [Making authenticated API requests with a GitHub App in a GitHub Actions workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)

6) Configure the app with the following permissions

    * Actions (read/write)
    * Administration (read/write)
    * Contents (read/write)

7) Update the ruleset bypass list to include the GitHub App

8) Add GitHub app variables and secrets

    **Secrets:**
    * `AUTO_RELEASE_APP_PRIVATE_KEY`
    * `AUTO_RELEASE_APP_ID`
