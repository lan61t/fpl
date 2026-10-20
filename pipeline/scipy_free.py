"""Spearman rank correlation without scipy, so the scheduled job only needs pandas and numpy."""
import numpy as np
def _rank(a):
    a=np.asarray(a,float); order=a.argsort(kind='mergesort'); r=np.empty(len(a)); r[order]=np.arange(len(a))
    # average ranks for ties
    s=a[order]; i=0
    while i<len(a):
        j=i
        while j+1<len(a) and s[j+1]==s[i]: j+=1
        r[order[i:j+1]]=(i+j)/2.0; i=j+1
    return r
def spearman(x,y):
    rx,ry=_rank(x),_rank(y)
    if rx.std()==0 or ry.std()==0: return float('nan')
    return float(np.corrcoef(rx,ry)[0,1])
