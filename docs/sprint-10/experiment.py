"""Synthetic preference experiment; Python 3.11+, numpy 2.1.3, sklearn 1.5.2."""
import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

def generate(seed,n,shift=False):
    rng=np.random.default_rng(seed)
    rows=[]
    for i in range(n):
        z=rng.uniform(.65,1) if shift else rng.uniform(0,.65)
        v=rng.uniform(0,1,(8,3))
        limit=rng.uniform(.1,.5,2)
        feasible=(v[:,1:]>=limit).all(axis=1)
        # Independent, explicitly synthetic oracle: nonlinear interaction.
        u=(.2+.6*z)*v[:,0]+(.8-.6*z)*v[:,1:].mean(axis=1)+.15*v[:,0]*v[:,1]
        rows.append((z,v,feasible,u))
    return rows

def features(v,z,kind):
    if kind=="fixed": return v
    if kind=="linear": return np.column_stack((v,v*z))
    if kind=="no_context": return v
    return np.column_stack((v,np.full(len(v),z)))

def pairs(rows,kind):
    X=[]; Y=[]
    for z,v,f,u in rows:
        a=features(v,z,kind)
        ids=np.flatnonzero(f)
        for i in ids:
            for j in ids:
                if i!=j:
                    X.append(np.r_[a[i],a[j]] if kind in ("mlp","no_context") else a[i]-a[j])
                    Y.append(int(u[i]>u[j]))
    return np.asarray(X),np.asarray(Y)

def evaluate(model,rows,kind):
    out=[]
    for z,v,f,u in rows:
        ids=np.flatnonzero(f)
        if len(ids)<2: continue
        a=features(v,z,kind)
        if kind in ("mlp","no_context"):
            p=np.array([[model.predict_proba(np.r_[a[i],a[j]][None,:])[0,1] for j in ids] for i in ids])
            p=(p+1-p.T)/2
        else:
            p=model.predict_proba(np.array([a[i]-a[j] for i in ids for j in ids]))[:,1].reshape(len(ids),len(ids))
        mask=~np.eye(len(ids),dtype=bool)
        truth=u[ids,None]>u[ids][None,:]
        acc=((p>=.5)==truth)[mask].mean()
        chosen=ids[np.argmax(p.mean(axis=1))]
        out.append([acc,u[ids].max()-u[chosen],int(not f[chosen])])
    return np.asarray(out)

def main():
    train=generate(101,300)
    tests={"iid":generate(202,120),"shift":generate(303,120,True)}
    results={}
    for kind in ("fixed","linear","mlp","no_context"):
        X,y=pairs(train,kind)
        model=MLPClassifier(hidden_layer_sizes=(24,),random_state=42,max_iter=400) if kind in ("mlp","no_context") else LogisticRegression(max_iter=1000,fit_intercept=False)
        model.fit(X,y)
        results[kind]={k:evaluate(model,v,kind) for k,v in tests.items()}
    rng=np.random.default_rng(404)
    report={}
    for k in tests:
        report[k]={m:{"n":len(d[k]),"accuracy":float(d[k][:,0].mean()),"regret":float(d[k][:,1].mean()),"violations":int(d[k][:,2].sum())} for m,d in results.items()}
        diff=results["mlp"][k][:,0]-results["linear"][k][:,0]
        boot=diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(axis=1)
        report[k]["paired_delta_vs_linear"]={"mean":float(diff.mean()),"ci95":np.quantile(boot,[.025,.975]).tolist()}
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
