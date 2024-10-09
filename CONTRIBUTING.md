# Contributing to ddopai
Thanks for checking out the contribution guide!

This guide is meant as a guide for those who wish to contribute to ddopai.
If you're looking for a particular project to work on, check out the [Issues](https://github.com/d3group/ddopai/issues) for things you might be interested in!
See the [Table of Contents](#table-of-contents) for different ways to help and details about we handle them.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [I Want To Contribute](#i-want-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

As contributors and maintainers of this project, and in the interest of fostering an open and welcoming community, we pledge to respect all people who contribute through reporting issues, posting feature requests, updating documentation, submitting pull requests or patches, and other activities.

We are committed to making participation in this project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery
* Personal attacks
* Trolling or insulting/derogatory comments
* Public or private harassment
* Publishing other's private information, such as physical or electronic addresses, without explicit permission
* Other unethical or unprofessional conduct

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct. By adopting this Code of Conduct, project maintainers commit themselves to fairly and consistently applying these principles to every aspect of managing this project. Project maintainers who do not follow or enforce the Code of Conduct may be permanently removed from the project team.

This code of conduct applies both within project spaces and in public spaces when an individual is representing the project or its community.

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by opening an issue or contacting one or more of the project maintainers.

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 1.2.0, available at https://www.contributor-covenant.org/version/1/2/0/code-of-conduct.html

***

## I Have a Question

Before you ask a question, it is best to search for existing [Issues](https://github.com/d3group/ddopai/issues) that might help you. In case you have found a suitable issue and still need clarification, you can write your question in this issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](https://github.com/d3group/ddopai/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (nodejs, npm, etc), depending on what seems relevant.

We will then take care of the issue as soon as possible.

***

## I Want To Contribute

> ### Legal Notice 
> When contributing to this project, you must agree that you have authored 100% of the content, that you have the necessary rights to the content and that the content you contribute may be provided under the project license.

### Preparation steps
*   The first thing to do is create your own [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo).
    This provides you a place to work on your changes without impacting any code from the original repository.

    To do this, navigate to [d3group/ddopai](https://github.com/d3group/ddopai) and hit the **fork** button in the top-right corner.
    This will copy the repository to your own account, including all of its different branches.
    You'll be able to access this at `https://github.com/{your-username}/ddopai`.

*   The next steps are to clone **your own fork** and to create a new [branch](https://docs.github.com/en/github/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches) where all your changes will go.
    It's important to work off the latest changes on the **development** branch.
    ```bash
    git clone --recurse-submodules git@github.com:your-username/ddopai.git
    cd ddopai

    # Create a new branch based off the main branch
    git checkout -b my_new_branch main
    ```

    The reason to create a new branch:

    *   Keep the commit history for your changes clean.
    *   Performing a **rebase** or a **merge** later is much easier.

*   It is strongly recommended to use a [virtual environment](https://docs.python.org/3/tutorial/venv.html) to work in. We recommend Conda, a popular alternative for managing Python projects.
*   Once you have created a new virtual environment, do not forget to activate it before install all dependencies.

Feel free to make the changes you wish to make.


### Pull Request

* Once you've made changes you're happy with, commit your code.
    ```bash
    # Check the changed files
    git status

    # Add the changes
    git add {changed files}
    git commit -m "Meaningful as you can make it message"

    # Push back to your fork
    git push --set-upstream origin my_new_branch
    ```
* Go to github, go to your fork and then make a pull request using the **Contribute** button.
    * `d3group/ddopai` | `main` <- `your-username/ddopai` | `my_new_branch`
* Write a Pull Request with a description of the changes, why you implemented them and any implications.
    * Check out this [blog post](https://hugooodias.medium.com/the-anatomy-of-a-perfect-pull-request-567382bb6067) for some inspiration!
* Once we see this, we will our Continuous Integration process on the pull request to ensure the changes fit our style and are compliant.
* We'll review the code and perhaps ask for some changes.
* Once we're happy with the result, we'll merge it in!


### Reporting Bugs

If you've encountered your own bugs you'd like fixed, we greatly appreciate any help!

#### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information. Therefore, we ask you to investigate carefully, collect information and describe the issue in detail in your report. Please complete the following steps in advance to help us fix any potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side e.g. using incompatible environment components/versions. If you are looking for support, you might want to check [this section](#i-have-a-question)).
- To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the [bug tracker](https://github.com/d3group/ddopai/issues?q=label%3Abug).
- Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
- Collect information about the bug:
- Stack trace (Traceback)
- OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
- Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on what seems relevant.
- Possibly your input and the output
- Can you reliably reproduce the issue? And can you also reproduce it with older versions?


#### How Do I Submit a Good Bug Report?

> You must never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Instead sensitive bugs must be sent by email to <ddopai@uni-wuerzburg.de>.


We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/d3group/ddopai/issues/new). (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be implemented by someone.

***

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestions, **including completely new features and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community to understand your suggestion and find related suggestions.

#### Before Submitting an Enhancement

- Make sure that you are using the latest version.
- Read the documentation carefully and find out if the functionality is already covered, maybe by an individual configuration.
- Search through the issues to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to make a strong case to convince the project's developers of the merits of this feature. Keep in mind that we want features that will be useful to the majority of our users and not just a small subset. If you're just targeting a minority of users, consider writing an add-on/plugin library.

#### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as Github Issues.

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point you can also tell which alternatives do not work for you.
- You may want to **include screenshots and animated GIFs** which help you demonstrate the steps or point out the part which the suggestion is related to.
- **Explain why this enhancement would be useful** to most users. You may also want to point out the other projects that solved it better and which could serve as inspiration.

***

## Attribution
This guide is based on the **contributing.md**.

***