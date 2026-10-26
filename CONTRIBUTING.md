# Contributing

The workspace pins every product repository as a submodule. Most changes
belong in those repositories; the workspace itself carries docs, scripts,
tools and the pinned commits.

## Working on your own forks

Clone the workspace as usual (from your fork of it, if you have one):

```sh
git clone --recurse-submodules <workspace-url>
```

Submodules are cloned from `github.com/markjfisher/...`, as `.gitmodules`
says. **Don't change those URLs.** In each submodule you work on, add your fork
as a second remote and push your branch there:

```sh
cd repos/fujinet-nio
git remote add fork git@github.com:<you>/fujinet-nio.git
git config remote.pushDefault fork     # `git push` goes to your fork
git switch -c my-feature
# ... commit ...
git push -u fork my-feature            # then open the PR from your fork
```

`origin` still tracks upstream, so `git pull` keeps working. The workspace
builds from whatever is checked out in each submodule, so your branches are
used for builds and tests without any URL change.

If you really need a submodule to clone from your fork, override the URL in
your local git config, which is never committed:

```sh
git config submodule.repos/fujinet-nio.url git@github.com:<you>/fujinet-nio.git
git submodule sync repos/fujinet-nio
```

## What goes in a workspace pull request

- **Yes:** docs, `backlog/` notes, scripts, tools and their tests.
- **Submodule pins:** maintainers bump a pin once the submodule pull request
  is merged. If you are not a maintainer, leave the `repos/*` pointer changes
  your work creates unstaged. A pin to a commit that is only on your fork, or
  only in an open pull request, fails CI and breaks `git submodule update` for
  everyone else.
- **No `.gitmodules` URL changes.**

Open the pull requests in the submodule repositories. Once they are merged,
the pins are bumped to the merged commits.

## Checks

CI runs both on every pull request; run them yourself first:

```sh
scripts/check-gitmodules.sh                    # every URL is on markjfisher/
scripts/check-submodule-pins.sh origin/master  # changed pins are on an upstream branch
```

## Commits

Commit as yourself, not as an agent identity. Don't add `Co-authored-by`
trailers or agent session links (such as `Claude-Session:`). See `AGENTS.md`
for the rest of the agent rules.
