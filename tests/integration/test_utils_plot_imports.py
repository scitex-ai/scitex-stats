"""Non-plotting utilities must not initialize the plotting stack."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image


CASES = [
    ("p2stars", "_formatters", "(.01)", "**"),
    ("cohens_d", "_effect_size", "([1,2,3],[2,4,6])", -2/(2.5**.5)),
    ("power_ttest", "_power", "(effect_size=0,n1=20,n2=20)", .05),
]


def environment(directory):
    return {**os.environ,"HOME":str(directory),"TMPDIR":str(directory),
            "SCITEX_DIR":str(directory/"state"),"XDG_CACHE_HOME":str(directory/"cache"),
            "PYTHONPATH":str(Path(__file__).resolve().parents[2]/"src"),"MPLBACKEND":"Agg"}


@pytest.mark.parametrize("access",["module","package"])
@pytest.mark.parametrize("name,module,arguments,expected",CASES)
def test_numeric_utilities_work_when_plotting_import_is_unavailable(access,name,module,arguments,expected,tmp_path):
    # Arrange
    statements={"module":f"from scitex_stats._utils.{module} import {name} as operation",
                "package":f"from scitex_stats._utils import {name} as operation"}
    code="""import importlib.abc,json,sys
class BlockPlotting(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='matplotlib' or fullname.startswith('matplotlib.'):
            raise RuntimeError('Non-plotting utility attempted plotting import: '+fullname)
sys.meta_path.insert(0,BlockPlotting())
"""+statements[access]+f"\nresult=operation{arguments}\nprint(json.dumps(result))\n"
    # Act
    result=subprocess.run([sys.executable,"-c",code],cwd=tmp_path,env=environment(tmp_path),capture_output=True,text=True,timeout=20,check=True)
    observed=json.loads(result.stdout)
    # Assert
    assert observed == pytest.approx(expected) if isinstance(expected,float) else observed == expected


@pytest.mark.parametrize("name",["p2stars","cohens_d","power_ttest"])
def test_private_utility_names_do_not_gain_unsupported_root_aliases(name,tmp_path):
    # Arrange
    code=f"""import json
import scitex_stats as ss
try:
    getattr(ss,{name!r})
except AttributeError:
    print(json.dumps({{"present":False,"declared":{name!r} in ss.__all__}}))
else:
    raise AssertionError('Unexpected new root alias')
"""
    # Act
    result=subprocess.run([sys.executable,"-c",code],cwd=tmp_path,env=environment(tmp_path),capture_output=True,text=True,timeout=20,check=True)
    # Assert
    assert json.loads(result.stdout) == {"present":False,"declared":False}


@pytest.mark.parametrize("module,filename",[("_formatters","p2stars_demo.jpg"),("_power","power_analysis_demo.jpg"),("_effect_size","cohens_d_demo.jpg")])
def test_demo_still_renders_and_closes_its_figure(module,filename,tmp_path):
    # Arrange
    code=f"from scitex_stats._utils.{module} import main\nfrom types import SimpleNamespace\nimport matplotlib.pyplot as plt\nassert main(SimpleNamespace(verbose=False))==0\nassert plt.get_fignums()==[]\n"
    # Act
    subprocess.run([sys.executable,"-c",code],cwd=tmp_path,env=environment(tmp_path),capture_output=True,text=True,timeout=30,check=True)
    with Image.open(tmp_path/filename) as artifact:
        observed=(artifact.format,artifact.width>0,artifact.height>0)
    # Assert
    assert observed == ("JPEG",True,True)
