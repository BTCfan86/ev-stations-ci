# Running the EV Stations scripts on GitHub Actions

This package lets your EV scripts run on GitHub's own runners, which have full
outbound internet access (unlike Claude's cloud sandbox, which only reaches
package registries). GitHub Actions can't be triggered *by* Claude — you (or
a schedule) trigger it, it runs, and then Claude can read the results back
since GitHub itself is reachable to Claude.

## 1. Security first — do NOT commit your real API keys

`Set_API_KEYs.py` in your original project has real credentials hardcoded
(NREL, Census, EIA, BLS, SEC, Fannie Mae, an email password, etc.). **Do not
push that file as-is.** Git history is permanent — even if you delete the
file in a later commit, the keys stay recoverable in the repo's history
forever, and a private repo can still leak keys via CI logs, GitHub Apps,
or a future collaborator.

This package includes a replacement `Set_API_KEYs.py` that reads each key
from an environment variable instead. In GitHub:

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Add a secret for each key you actually use, e.g.:
   - `NREL_API_KEY`
   - `CENSUS_API_KEY` (only if a script needs it)
   - etc.
3. The workflow file below maps those secrets into environment variables
   at run time — they're never written to disk in the repo.

Your **existing** `Set_API_KEYs.py` (with real values) should stay wherever
it already lives on your own machine / in this Claude project — just don't
commit it to the repo. Add it to `.gitignore` as a safety net.

## 2. Repo layout

Lay the repo out to match your actual PyCharm project structure so the
`Renewables.EV_Data...` imports resolve without changes:

```
your-repo/
├── Set_API_KEYs.py                  <- the env-var version, included below
├── requirements.txt
├── .gitignore
├── .github/workflows/run-ev-scripts.yml
├── ci/ci_runner.py
└── Renewables/
    ├── EV_Data/
    │   ├── WA_EVs_v01.py
    │   ├── NC_EVs_v01.py
    │   ├── NY_EVs_v01.py
    │   ├── MD_EVs_v01.py
    │   ├── CA_EVs_v01.py
    │   └── Combined_EV_Data_v01.py
    └── EV_Stations/
        ├── EV_Stations_v08.py
        ├── EV_Stations_Analysis_v02.py
        ├── Basemap_State_Corners.xlsx
        └── City_Locations_v01.xlsx
```

Copy the fixed versions of `WA_EVs_v01.py`, `Combined_EV_Data_v01.py`, and
`EV_Stations_Analysis_v02.py` from your Claude Project (I already patched
the real bugs there — the WA state filter, the pandas chained-assignment
bug, the dead `cif` import). Copy `NC_EVs_v01.py`, `NY_EVs_v01.py`,
`MD_EVs_v01.py`, `CA_EVs_v01.py`, `EV_Stations_v08.py` over unchanged, or
ask me to give them the same portability pass first.

## 3. What `ci_runner.py` does

Your scripts call `plt.show()`, which does nothing useful on a headless CI
runner (no display). `ci_runner.py` monkeypatches `plt.show` to save each
figure as a PNG instead, then calls whichever function you tell it to via
a command-line argument. Outputs land in `ci_output/` and the workflow
uploads that folder as a downloadable artifact after each run.

## 4. Triggering it

The workflow is set to `workflow_dispatch` (a manual "Run workflow" button
in the Actions tab) plus a weekly schedule. Trigger it manually first to
confirm it works, then leave the schedule running if you want fresh data
regularly.

## 5. What I can/can't do here

I can't create the GitHub repo or push these files for you — this Claude
session has no GitHub connection. You'll need to `git init`, add these
files, push, and add the secrets yourself. Once a workflow run has
completed, tell me the repo URL and I can read the run's output artifacts
back (GitHub is reachable to me) to verify the real results.
