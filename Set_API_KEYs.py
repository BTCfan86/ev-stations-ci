import os

# CI-safe version: every key is read from an environment variable that
# GitHub Actions populates from your repo's encrypted Secrets at run time.
# Nothing here is a real credential - it's safe to commit this file.
#
# In GitHub: Settings -> Secrets and variables -> Actions -> New repository
# secret, then map it in .github/workflows/run-ev-scripts.yml's `env:` block.
#
# Locally (outside CI), set these as real environment variables yourself,
# or keep using your original hardcoded Set_API_KEYs.py on your own machine
# - just don't commit that version.

def set_NREL_API_KEY():
    os.environ['NREL_API_KEY'] = os.environ.get('NREL_API_KEY', '')

def set_Census_API_KEY():
    os.environ['Census_API_KEY'] = os.environ.get('Census_API_KEY', '')

def set_EIA_API_KEY():
    os.environ['EIA_API_KEY'] = os.environ.get('EIA_API_KEY', '')

def set_FRED_API_KEY():
    os.environ['FRED_API_KEY'] = os.environ.get('FRED_API_KEY', '')

def set_FX_API_KEY():
    os.environ['FX_API_KEY'] = os.environ.get('FX_API_KEY', '')

def set_BLS_API_KEY():
    os.environ['BLS_API_KEY'] = os.environ.get('BLS_API_KEY', '')

def set_Etherscan_API_KEY():
    os.environ['Etherscan_API_KEY'] = os.environ.get('Etherscan_API_KEY', '')

def set_SEC_API_KEY():
    os.environ['SEC_API_KEY'] = os.environ.get('SEC_API_KEY', '')

def set_MD_ID_API_KEY():
    os.environ['MD_ID_API_KEY'] = os.environ.get('MD_ID_API_KEY', '')

def set_MD_API_KEY():
    os.environ['MD_API_KEY'] = os.environ.get('MD_API_KEY', '')

def set_Rapid_API_KEY():
    os.environ['Rapid_API_KEY'] = os.environ.get('Rapid_API_KEY', '')

def set_USDA_API_KEY():
    os.environ['USDA_API_KEY'] = os.environ.get('USDA_API_KEY', '')

def set_USDA_API_KEY_PSD():
    os.environ['USDA_API_KEY_PSD'] = os.environ.get('USDA_API_KEY_PSD', '')

def set_BEA_API_KEY():
    os.environ['BEA_API_KEY'] = os.environ.get('BEA_API_KEY', '')

def set_NOAA_API_KEY():
    os.environ['NOAA_API_KEY'] = os.environ.get('NOAA_API_KEY', '')

def set_Adzuna_API_KEY():
    os.environ['Adzuna_API_ID'] = os.environ.get('Adzuna_API_ID', '')
    os.environ['Adzuna_API_KEY'] = os.environ.get('Adzuna_API_KEY', '')

# Note: email/Fannie Mae credentials deliberately omitted here - those are
# account passwords, not API keys, and don't belong in CI at all unless a
# specific script truly needs them. Add as its own secret only if required.
