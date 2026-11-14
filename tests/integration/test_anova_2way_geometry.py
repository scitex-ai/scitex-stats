"""Two-way ANOVA rejects undefined inference; balanced controls use OLS."""

import numpy as np
import pandas as pd
import pytest
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm

import scitex_stats as ss


INVALID = [
    ([], [], [], "at least two levels"),
    ([1,2,3,4,5,6], [0]*6, [0,0,0,1,1,1], "at least two levels"),
    ([1,2,3,4,5,6], [0,0,0,1,1,1], [0]*6, "at least two levels"),
    ([1,2,3,4], [0,0,1,1], [0,1,0,1], "positive residual degrees of freedom"),
    ([1]*8, [0]*4+[1]*4, [0,0,1,1]*2, "positive finite within-cell variance"),
    ([1,1,3,3,8,8,20,20], [0]*4+[1]*4, [0,0,1,1]*2, "positive finite within-cell variance"),
    ([1,2,3,4,5,6,7,np.nan], [0]*4+[1]*4, [0,0,1,1]*2, "finite response values"),
    ([1,2,3,4,5,6,7,np.inf], [0]*4+[1]*4, [0,0,1,1]*2, "finite response values"),
    ([1,2,3,4,5,6,7,-np.inf], [0]*4+[1]*4, [0,0,1,1]*2, "finite response values"),
]


def invoke(kind,y,a,b,**kwargs):
    if kind == "frame":
        return ss.test_anova_2way(pd.DataFrame({"y":y,"a":a,"b":b}),
                                  factor_a="a",factor_b="b",value="y",**kwargs)
    return ss.test_anova_2way(y,factor_a=a,factor_b=b,**kwargs)


@pytest.mark.parametrize("kind",["array","frame"])
@pytest.mark.parametrize("y,a,b,error",INVALID)
def test_undefined_design_fails_before_emitting_inference(kind,y,a,b,error):
    # Arrange
    # Act
    with pytest.raises(ValueError,match=error):
        # Assert
        invoke(kind,y,a,b)


def design(na,nb):
    a=np.repeat(np.arange(na),nb*4)
    b=np.tile(np.repeat(np.arange(nb),4),na)
    noise=np.tile([-1.3,-.4,.2,1.5],na*nb)
    y=2*a+1.2*b+1.7*a*b+noise
    return y,a,b


@pytest.mark.parametrize("na,nb",[(2,2),(2,3),(3,2)])
@pytest.mark.parametrize("kind",["array","frame"])
@pytest.mark.parametrize("return_as",["dict","dataframe"])
@pytest.mark.parametrize("alpha",[.01,.05])
def test_balanced_main_and_interaction_effects_match_independent_ols(na,nb,kind,return_as,alpha):
    # Arrange
    y,a,b=design(na,nb)
    frame=pd.DataFrame({"y":y,"a":a,"b":b})
    expected=anova_lm(ols("y ~ C(a)*C(b)",data=frame).fit(),typ=2)
    # Act
    result=invoke(kind,y,a,b,return_as=return_as,alpha=alpha,decimals=7)
    rows=pd.DataFrame(result)
    observed=rows[["statistic","pvalue","df_effect","df_error","effect_size"]].to_numpy(dtype=float)
    effects=expected.iloc[:3]
    reference=np.column_stack([effects["F"],effects["PR(>F)"],effects["df"],
        np.repeat(expected.loc["Residual","df"],3),
        effects["sum_sq"]/(effects["sum_sq"]+expected.loc["Residual","sum_sq"])])
    # Assert
    assert (observed == pytest.approx(reference,abs=6e-8),
            rows["significant"].tolist(),rows["effect_type"].tolist(),rows["alpha"].tolist()) == (
        True,(effects["PR(>F)"]<alpha).tolist(),["main","main","interaction"],[alpha]*3,
    )
